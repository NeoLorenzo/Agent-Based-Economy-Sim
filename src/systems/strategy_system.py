# src/systems/strategy_system.py

"""
================================================================================
Strategy System
================================================================================
This system contains the core "AI" for the firms, allowing them to make
strategic decisions about price, production, and wages to maximize profit.
================================================================================
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def _calculate_health_scores(sim, active_mask):
    """
    Performs a modular health check on each core business function for all active firms.
    Calculates and stores a health score from -1.0 (critical) to +1.0 (excellent)
    for Inventory, Sales, Profit, and Capital.
    """
    # Convenience references
    firms = sim.firms[active_mask]
    config = sim.config.get('unified_strategy_ai', {}).get('health_check_params', {})

    # --- 1. Inventory Health ---
    healthy_ratio = config.get('inventory_ratio_healthy', 1.0)
    crit_surplus = config.get('inventory_ratio_critical_surplus', 5.0)
    crit_shortage = config.get('inventory_ratio_critical_shortage', 0.0)
    
    # Safely calculate inventory ratio
    target_inv = firms['target_inventory']
    inv_ratio = np.divide(firms['inventory'], target_inv, out=np.full_like(target_inv, healthy_ratio, dtype=float), where=target_inv!=0)

    # Normalize to score
    inv_health = np.zeros_like(inv_ratio)
    surplus_mask = inv_ratio > healthy_ratio
    shortage_mask = inv_ratio < healthy_ratio
    
    # Score for surplus
    denominator = crit_surplus - healthy_ratio
    inv_health[surplus_mask] = 1.0 - (inv_ratio[surplus_mask] - healthy_ratio) / denominator if denominator > 0 else 0
    
    # Score for shortage
    denominator = healthy_ratio - crit_shortage
    inv_health[shortage_mask] = 1.0 - (healthy_ratio - inv_ratio[shortage_mask]) / denominator if denominator > 0 else 0
    
    sim.firms['health_inventory'][active_mask] = np.clip(inv_health, -1.0, 1.0)

    # --- 2. Sales & 3. Profit Health (Trend-Based) ---
    # Initialize EWMA on first run with the current value to prevent starting at 0
    if sim._current_tick == 0:
        sim.firm_sales_ewma_short[active_mask] = firms['units_sold_last_tick']
        sim.firm_sales_ewma_long[active_mask] = firms['units_sold_last_tick']
        sim.firm_profit_ewma_short[active_mask] = firms['profit_last_tick']
        sim.firm_profit_ewma_long[active_mask] = firms['profit_last_tick']

    # Get EWMA alphas from config
    alpha_sales_short = 2 / (config.get('sales_trend_ema_short_ticks', 3) + 1)
    alpha_sales_long = 2 / (config.get('sales_trend_ema_long_ticks', 10) + 1)
    alpha_profit_short = 2 / (config.get('profit_trend_ema_short_ticks', 3) + 1)
    alpha_profit_long = 2 / (config.get('profit_trend_ema_long_ticks', 10) + 1)
    
    # Update EWMAs for active firms
    sales_now = firms['units_sold_last_tick']
    profit_now = firms['profit_last_tick']
    sim.firm_sales_ewma_short[active_mask] = alpha_sales_short * sales_now + (1 - alpha_sales_short) * sim.firm_sales_ewma_short[active_mask]
    sim.firm_sales_ewma_long[active_mask] = alpha_sales_long * sales_now + (1 - alpha_sales_long) * sim.firm_sales_ewma_long[active_mask]
    sim.firm_profit_ewma_short[active_mask] = alpha_profit_short * profit_now + (1 - alpha_profit_short) * sim.firm_profit_ewma_short[active_mask]
    sim.firm_profit_ewma_long[active_mask] = alpha_profit_long * profit_now + (1 - alpha_profit_long) * sim.firm_profit_ewma_long[active_mask]

    # Calculate trend ratios
    sales_ratio = np.divide(sim.firm_sales_ewma_short[active_mask], sim.firm_sales_ewma_long[active_mask], out=np.ones_like(sales_now, dtype=float), where=sim.firm_sales_ewma_long[active_mask]!=0)
    profit_ratio = np.divide(sim.firm_profit_ewma_short[active_mask], sim.firm_profit_ewma_long[active_mask], out=np.ones_like(profit_now, dtype=float), where=sim.firm_profit_ewma_long[active_mask]!=0)
    
    # Normalize with tanh to get a score from -1 to 1
    scaler = config.get('trend_ratio_tanh_scaler', 2.0)
    sim.firms['health_sales'][active_mask] = np.tanh((sales_ratio - 1.0) * scaler)
    sim.firms['health_profit'][active_mask] = np.tanh((profit_ratio - 1.0) * scaler)

    # --- 4. Capital Health ---
    healthy_ticks = config.get('capital_coverage_healthy_ticks', 20.0)
    critical_ticks = config.get('capital_coverage_critical_ticks', 2.0)
    
    wages_paid = firms['wages_paid_last_tick']
    coverage = np.divide(firms['balance'], wages_paid, out=np.full_like(wages_paid, healthy_ticks, dtype=float), where=wages_paid!=0)
    
    # Normalize 0-1, then scale to -1 to 1
    denominator = healthy_ticks - critical_ticks
    capital_health = (coverage - critical_ticks) / denominator if denominator > 0 else 0.0
    sim.firms['health_capital'][active_mask] = np.clip((capital_health * 2) - 1, -1.0, 1.0)

    # --- Validation Logging ---
    for firm_id in np.where(active_mask)[0]:
        logger.debug(
            "Firm %d Health Scores | Inv: %.2f, Sales: %.2f, Profit: %.2f, Capital: %.2f",
            firm_id,
            sim.firms['health_inventory'][firm_id],
            sim.firms['health_sales'][firm_id],
            sim.firms['health_profit'][firm_id],
            sim.firms['health_capital'][firm_id]
        )

def _calculate_unified_strategy(sim, active_mask):
    """
    Translates firm health scores into unified strategic impulses for price and production.
    Returns the proposed strategic actions for logging and eventual application.
    """
    # Convenience references
    firms = sim.firms[active_mask]
    config = sim.config.get('unified_strategy_ai', {})
    impulse_weights = config.get('impulse_weight_params', {})
    action_params = config.get('action_synthesis_params', {})

    # --- 1. Synthesize Price Strategy ---
    price_impulse_inv = firms['health_inventory'] * impulse_weights.get('price_impulse_weight_inventory', 0)
    price_impulse_sales = firms['health_sales'] * impulse_weights.get('price_impulse_weight_sales', 0)
    price_impulse_profit = firms['health_profit'] * impulse_weights.get('price_impulse_weight_profit', 0)

    total_price_impulse = np.clip(
        price_impulse_inv + price_impulse_sales + price_impulse_profit,
        -1.0,
        1.0
    )

    price_adjustment = total_price_impulse * action_params.get('max_price_adjustment_factor', 0.1)
    proposed_new_price = firms['price'] * (1 + price_adjustment)

    # --- 2. Synthesize Workforce Strategy ---
    prod_impulse_inv = firms['health_inventory'] * impulse_weights.get('production_impulse_weight_inventory', 0)
    prod_impulse_sales = firms['health_sales'] * impulse_weights.get('production_impulse_weight_sales', 0)
    prod_impulse_profit = firms['health_profit'] * impulse_weights.get('production_impulse_weight_profit', 0)

    total_production_impulse = np.clip(
        prod_impulse_inv + prod_impulse_sales + prod_impulse_profit,
        -1.0,
        1.0
    )
    
    base_ticks_factor = sim.config.get('target_inventory_production_ticks_factor', 4)
    dynamic_ticks_factor = base_ticks_factor * (1 + total_production_impulse)

    average_sales = np.mean(sim.firm_sales_history[active_mask], axis=1)
    desired_inventory = average_sales * dynamic_ticks_factor
    current_inventory = firms['inventory']
    production_need = desired_inventory - current_inventory
    
    production_per_worker = sim.config.get('production_per_worker', 5)
    proposed_target_prod_workers = np.ceil(np.maximum(0, production_need) / production_per_worker).astype(int)
    
    surplus_mask = (production_need <= 0)
    proposed_target_prod_workers[surplus_mask] = sim.config.get('min_target_workers', 1)

    logi_ratio = sim.config.get('logistics_to_production_ratio', 0.2)
    sales_ratio = sim.config.get('sales_to_production_ratio', 0.1)
    proposed_target_logi_workers = np.ceil(proposed_target_prod_workers * logi_ratio).astype(int)
    proposed_target_sales_workers = np.ceil(proposed_target_prod_workers * sales_ratio).astype(int)

    # --- Capital Veto ---
    capital_veto_mask = firms['health_capital'] < -0.5
    if np.any(capital_veto_mask):
        current_total_workers = firms['num_prod_workers'] + firms['num_logi_workers'] + firms['num_sales_workers']
        proposed_total_workers = proposed_target_prod_workers + proposed_target_logi_workers + proposed_target_sales_workers
        
        expansion_mask = proposed_total_workers > current_total_workers
        final_veto_mask = capital_veto_mask & expansion_mask

        proposed_target_prod_workers[final_veto_mask] = firms['num_prod_workers'][final_veto_mask]
        proposed_target_logi_workers[final_veto_mask] = firms['num_logi_workers'][final_veto_mask]
        proposed_target_sales_workers[final_veto_mask] = firms['num_sales_workers'][final_veto_mask]

    # --- Package and Return Proposed Actions ---
    proposals = {
        'price': proposed_new_price,
        'price_impulse': total_price_impulse,
        'target_prod': proposed_target_prod_workers,
        'target_logi': proposed_target_logi_workers,
        'target_sales': proposed_target_sales_workers,
        'prod_impulse': total_production_impulse
    }
    return proposals

def update(sim, summary):
    """
    Firms make strategic decisions about price and production to maximize profit.
    
    Args:
        sim: The simulation state object
        summary: A dictionary to accumulate summary statistics for the tick.
    """
    logger.debug("Start Firm Adjustment Phase")
    active_mask = ~sim.firms['is_bankrupt']
    if not np.any(active_mask): return

    # --- NEW: Calculate Unified Health Scores (Run in parallel with old AI for now) ---
    _calculate_health_scores(sim, active_mask)
    # --- NEW: Calculate proposed strategy from health scores ---
    proposed_strategy = _calculate_unified_strategy(sim, active_mask)
    # Store proposals on the sim object to be read by the main loop for logging
    sim.proposed_strategy = proposed_strategy

    # --- APPLY THE NEW UNIFIED STRATEGY ---
    active_indices = np.where(active_mask)[0]
    if len(active_indices) > 0:
        sim.firms['price'][active_mask] = proposed_strategy['price']
        sim.firms['target_prod_workers'][active_mask] = proposed_strategy['target_prod']
        sim.firms['target_logi_workers'][active_mask] = proposed_strategy['target_logi']
        sim.firms['target_sales_workers'][active_mask] = proposed_strategy['target_sales']

    # --- Final Price Floor Enforcement ---
    # A firm is forbidden from selling a product for less than its true unit cost.
    # This includes all labor and material costs from the previous tick.
    old_prices_for_floor_check = sim.firms['price'].copy()
    
    # Calculate the total cost of operations from the last tick.
    total_cost_last_tick = sim.firms['production_cost_last_tick'] + sim.firms['wages_paid_last_tick']
    units_sold_last_tick = sim.firms['units_sold_last_tick']

    # Calculate the fallback marginal cost for firms that sold nothing.
    raw_material_cost = sim.config['raw_material_cost_per_unit']
    prod_per_worker = sim.config['production_per_worker']
    fallback_cost = raw_material_cost + (sim.firms['wage_rate'] / prod_per_worker)

    # Calculate the true unit cost, using the fallback if no units were sold.
    unit_cost = np.divide(
        total_cost_last_tick, 
        units_sold_last_tick, 
        out=fallback_cost, 
        where=units_sold_last_tick > 0
    )
    
    price_floor_mask = (sim.firms['price'] < unit_cost) & active_mask
    if np.any(price_floor_mask):
        sim.firms['price'][price_floor_mask] = unit_cost[price_floor_mask]
        # sim.firms['price_driver'][price_floor_mask] = 'FL' # Obsolete field
        # Instead of logging every hit, we aggregate this event.
        # The count will be displayed in the main 5-tick summary.
        num_hits = np.sum(price_floor_mask)
        sim.tick_events['price_floor_hits'] += num_hits

    # --- Step 4: Update Memory for Next Tick ---
    sim.firms['previous_profit'] = sim.firms['profit_last_tick']