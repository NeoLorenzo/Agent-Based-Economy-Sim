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

def update(sim, summary):
    """
    Firms make strategic decisions about price and production to maximize profit.
    
    Args:
        sim: The simulation state object.
        summary: A dictionary to accumulate summary statistics for the tick.
    """
    logger.debug("Start Firm Adjustment Phase")
    active_mask = ~sim.firms['is_bankrupt']
    if not np.any(active_mask): return

    # --- Step 1: Assess Profit Situation ---
    profit = sim.firms['profit_last_tick']
    prev_profit = sim.firms['previous_profit']
    
    profit_fell_mask = (profit < prev_profit) & active_mask
    sim.firms['ticks_of_falling_profit'][profit_fell_mask] += 1
    
    profit_rose_mask = (profit >= prev_profit) & active_mask
    sim.firms['ticks_of_falling_profit'][profit_rose_mask] = 0

    # --- Step 2: Choose Mode (Exploration vs. Exploitation) ---
    crisis_threshold = sim.config['profit_crisis_threshold']
    crisis_mask = (sim.firms['ticks_of_falling_profit'] > crisis_threshold) & active_mask
    normal_mask = ~crisis_mask & active_mask

    # --- Step 3: Execute Logic Based on Mode ---
    
    # --- Mode A: CRISIS / EXPLORATION ---
    if np.any(crisis_mask):
        sim.tick_events['crisis_triggers'] += np.sum(crisis_mask)
        for firm_id in np.where(crisis_mask)[0]:
            # 1. Drastic Price Cut
            cut_rate = sim.config['crisis_price_cut_rate']
            sim.firms['price'][firm_id] *= (1 - cut_rate)
            sim.firms['last_price_direction'][firm_id] = -1 # Force downward exploration
            
            # 2. Aggressive Workforce Reduction
            # Cut target workforce by a significant margin to reduce costs
            new_target = int(sim.firms['num_workers'][firm_id] * 0.75)
            sim.firms['target_num_workers'][firm_id] = max(sim.config['min_target_workers'], new_target)

            # 3. Reset Crisis Counter
            sim.firms['ticks_of_falling_profit'][firm_id] = 0

    # --- Mode B: NORMAL / EXPLOITATION ---
    if np.any(normal_mask):
        # --- Update Stability Counter ---
        profitable_mask = (sim.firms['profit_last_tick'] > 0) & normal_mask
        sim.firms['ticks_of_stable_profit'][profitable_mask] += 1
        unprofitable_mask = (sim.firms['profit_last_tick'] <= 0) & normal_mask
        sim.firms['ticks_of_stable_profit'][unprofitable_mask] = 0

        # --- Wage Adjustment Logic (Unemployment-Driven) ---
        # Wages are now set based on the unemployment rate, the most direct measure of
        # labor supply and demand in the simulation.

        # 1. Get the current state of the labor market.
        unemployment_rate = summary.get('unemployment_rate', 0.0) / 100.0 # Convert to 0-1 scale
        increase_threshold = sim.config.get('unemployment_threshold_for_increases', 0.05)
        cut_threshold = sim.config.get('unemployment_threshold_for_cuts', 0.10)

        # 2. Apply a single, coherent wage strategy based on the market state.
        
        # State 1: Tight Labor Market (Worker's Market) -> Increase Wages
        # If unemployment is very low, firms must compete for scarce workers.
        if unemployment_rate < increase_threshold:
            increase_rate = sim.config['competitive_wage_increase_rate']
            sim.firms['wage_rate'][normal_mask] *= (1 + increase_rate)
            sim.tick_events['wage_increases'] += np.sum(normal_mask)
        
        # State 2: Slack Labor Market (Employer's Market) -> Decrease Wages
        # If unemployment is high, firms have leverage to cut costs.
        elif unemployment_rate > cut_threshold:
            cut_rate = sim.config.get('wage_cut_rate', 0.01)
            sim.firms['wage_rate'][normal_mask] *= (1 - cut_rate)
            sim.tick_events['wage_cuts'] += np.sum(normal_mask)

        # State 3: Balanced Market -> Hold Wages Steady (No action needed)
        # If unemployment is in the stable range between the two thresholds.

        # --- New Pricing Logic (Replaces profit-delta logic) ---
        adj_rate = sim.config['price_adjustment_rate']
        
        # BUG FIX: Calculate average_sales here, outside the conditional block.
        # It is needed for both pricing and workforce target calculations.
        average_sales = np.mean(sim.firm_sales_history, axis=1)

        # Rule 1: Survival Mode for unprofitable firms (already implemented)
        unprofitable_mask = (sim.firms['profit_last_tick'] < 0) & normal_mask
        sim.firms['price'][unprofitable_mask] *= (1 - adj_rate)
        sim.firms['last_price_direction'][unprofitable_mask] = -1

        # For profitable firms, pricing is now based on inventory management.
        profitable_mask = ~unprofitable_mask & normal_mask
        if np.any(profitable_mask):
            # Calculate target inventory based on smoothed sales history
            ticks_to_hold = sim.config['target_inventory_production_ticks_factor']
            target_inventory = average_sales[profitable_mask] * ticks_to_hold
            sim.firms['target_inventory'][profitable_mask] = target_inventory.astype(int)

            # Rule 2: Inventory Surplus -> Cut Price
            upper_factor = sim.config['inventory_upper_threshold_factor']
            surplus_mask = (sim.firms['inventory'] > sim.firms['target_inventory'] * upper_factor) & profitable_mask
            sim.firms['price'][surplus_mask] *= (1 - adj_rate)
            sim.firms['last_price_direction'][surplus_mask] = -1
            
            # Rule 3: Inventory Shortage -> Raise Price
            lower_factor = sim.config['inventory_lower_threshold_factor']
            shortage_mask = (sim.firms['inventory'] < sim.firms['target_inventory'] * lower_factor) & profitable_mask
            sim.firms['price'][shortage_mask] *= (1 + adj_rate)
            sim.firms['last_price_direction'][shortage_mask] = 1

        # 2. Adjust Workforce Target Based on Inventory, Sales, and Ambition
        # This entire block now operates on data pre-filtered by `normal_mask` to ensure consistent array shapes.
        
        # First, calculate the conservative target based on inventory needs using SMOOTHED sales data.
        ticks_of_sales_to_hold = sim.config['target_inventory_production_ticks_factor']
        desired_inventory = average_sales[normal_mask] * ticks_of_sales_to_hold
        current_inventory = sim.firms['inventory'][normal_mask]
        production_need = desired_inventory - current_inventory
        
        production_per_worker = sim.config['production_per_worker']
        new_target_workers = np.ceil(np.maximum(0, production_need) / production_per_worker).astype(int)
        
        # If inventory is in surplus, target is minimum.
        # This sub-mask is now the same size as `new_target_workers`.
        surplus_sub_mask = (production_need <= 0)
        new_target_workers[surplus_sub_mask] = sim.config['min_target_workers']

        # --- AMBITION LOGIC ---
        ambition_threshold = sim.config['ambition_threshold']
        # Create a sub-mask from data already filtered by `normal_mask`.
        stable_profit_ticks_normal = sim.firms['ticks_of_stable_profit'][normal_mask]
        ambitious_sub_mask = (stable_profit_ticks_normal > ambition_threshold)
        
        if np.any(ambitious_sub_mask):
            # Get the global indices of the ambitious firms for logging and state updates
            ambitious_global_indices = np.where(normal_mask)[0][ambitious_sub_mask]
            sim.tick_events['ambition_triggers'] += len(ambitious_global_indices)
            
            current_workers_ambitious = sim.firms['num_workers'][ambitious_global_indices]
            expansion_targets = np.maximum(np.ceil(current_workers_ambitious * 1.2).astype(int), current_workers_ambitious + 1)
            
            # Use the sub-mask to update the correctly-sized `new_target_workers` array
            new_target_workers[ambitious_sub_mask] = expansion_targets
            
            for i, firm_id in enumerate(ambitious_global_indices):
                logger.info(
                    "FIRM STRATEGY: Firm %d is stable. Experimenting with expansion to %d workers.",
                    firm_id, expansion_targets[i]
                )
            # Reset counter on the main firms array using the global indices
            sim.firms['ticks_of_stable_profit'][ambitious_global_indices] = 0

        # --- PROFITABILITY GATEKEEPER (STRENGTHENED) ---
        profits_normal = sim.firms['profit_last_tick'][normal_mask]
        unprofitable_sub_mask = (profits_normal < 0)
        
        if np.any(unprofitable_sub_mask):
            current_workers_unprofitable = sim.firms['num_workers'][normal_mask][unprofitable_sub_mask]
            
            # Cap the target for these firms at their current workforce size.
            new_target_workers[unprofitable_sub_mask] = np.minimum(
                new_target_workers[unprofitable_sub_mask], 
                current_workers_unprofitable
            )
        
        # --- BUDGETARY CONSTRAINT (FINAL VALIDATION) ---
        budget_rate = sim.config['expansion_budget_rate']
        capital_for_expansion = sim.firms['balance'][normal_mask] * budget_rate
        
        raw_material_cost = sim.config['raw_material_cost_per_unit']
        cost_per_new_hire = sim.firms['wage_rate'][normal_mask] + (raw_material_cost * production_per_worker)
        cost_per_new_hire[cost_per_new_hire == 0] = 1 
        
        affordable_new_hires = (capital_for_expansion / cost_per_new_hire).astype(int)
        
        current_workers_normal = sim.firms['num_workers'][normal_mask]
        max_affordable_target = current_workers_normal + affordable_new_hires
        
        final_target = np.minimum(new_target_workers, max_affordable_target)

        sim.firms['target_num_workers'][normal_mask] = np.maximum(sim.config['min_target_workers'], final_target)

    # --- Final Price Floor Enforcement ---
    # A firm is forbidden from selling a product for less than its marginal cost.
    # This is the absolute floor for any price adjustment.
    old_prices_for_floor_check = sim.firms['price'].copy()
    
    raw_material_cost = sim.config['raw_material_cost_per_unit']
    prod_per_worker = sim.config['production_per_worker']
    marginal_cost = raw_material_cost + (sim.firms['wage_rate'] / prod_per_worker)
    
    price_floor_mask = (sim.firms['price'] < marginal_cost) & active_mask
    if np.any(price_floor_mask):
        sim.firms['price'][price_floor_mask] = marginal_cost[price_floor_mask]
        # Instead of logging every hit, we aggregate this event.
        # The count will be displayed in the main 5-tick summary.
        num_hits = np.sum(price_floor_mask)
        sim.tick_events['price_floor_hits'] += num_hits

    # --- Step 4: Update Memory for Next Tick ---
    sim.firms['previous_profit'] = sim.firms['profit_last_tick']