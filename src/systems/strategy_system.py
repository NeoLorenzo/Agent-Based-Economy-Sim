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

    # Set default states for the tick. These will be overwritten by specific logic.
    sim.firms['ai_mode'][active_mask] = 'Normal'
    sim.firms['price_driver'][active_mask] = '--'

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
            # Set AI state for logging
            sim.firms['ai_mode'][firm_id] = 'Crisis'
            sim.firms['price_driver'][firm_id] = 'C!'

            # 1. Drastic Price Cut
            cut_rate = sim.config['crisis_price_cut_rate']
            sim.firms['price'][firm_id] *= (1 - cut_rate)
            sim.firms['last_price_direction'][firm_id] = -1 # Force downward exploration
            
            # 2. Rational Workforce Pivot: Halt Production, Focus on Sales & Logistics.
            # Immediately halt production to stop accumulating more inventory.
            sim.firms['target_prod_workers'][firm_id] = sim.config['min_target_workers']
            
            # Calculate logistics staff needed to manage the current inventory surplus.
            logi_ratio = sim.config['crisis_logistics_per_1000_units']
            logi_target = np.ceil(sim.firms['inventory'][firm_id] / 1000.0 * logi_ratio).astype(int)
            sim.firms['target_logi_workers'][firm_id] = logi_target
            
            # Maintain a minimum sales force to try and sell off the inventory.
            sim.firms['target_sales_workers'][firm_id] = sim.config['crisis_sales_staff_floor']

            # 3. Reset Crisis Counter
            sim.firms['ticks_of_falling_profit'][firm_id] = 0

    # --- Mode B: NORMAL / EXPLOITATION ---
    if np.any(normal_mask):
        # --- NEW: Inventory Crisis Check (Overrides all other logic) ---
        # If a firm has a massive inventory surplus, it must pivot to selling it off,
        # regardless of its profitability or sales history.
        inventory_crisis_factor = 5.0 # New hardcoded value; can be moved to config
        inventory_crisis_mask = (sim.firms['inventory'] > sim.firms['target_inventory'] * inventory_crisis_factor) & normal_mask
        
        if np.any(inventory_crisis_mask):
            # Get the global indices of firms in an inventory crisis
            crisis_indices = np.where(inventory_crisis_mask)[0]
            sim.tick_events['inventory_crisis_triggers'] += len(crisis_indices)
            sim.firms['ai_mode'][crisis_indices] = 'InvCrisis'

            # Halt production
            sim.firms['target_prod_workers'][crisis_indices] = sim.config['min_target_workers']
            
            # Staff logistics based on inventory size
            logi_ratio = sim.config['crisis_logistics_per_1000_units']
            inventory_in_crisis = sim.firms['inventory'][crisis_indices]
            logi_target = np.ceil(inventory_in_crisis / 1000.0 * logi_ratio).astype(int)
            sim.firms['target_logi_workers'][crisis_indices] = logi_target
            
            # Maintain a sales floor
            sim.firms['target_sales_workers'][crisis_indices] = sim.config['crisis_sales_staff_floor']

            # Remove these firms from the normal processing mask for this tick
            normal_mask[crisis_indices] = False

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
        sim.firms['price_driver'][unprofitable_mask] = 'P-'

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
            sim.firms['price_driver'][surplus_mask] = 'I-'
            
            # Rule 3: Inventory Shortage -> Raise Price
            lower_factor = sim.config['inventory_lower_threshold_factor']
            shortage_mask = (sim.firms['inventory'] < sim.firms['target_inventory'] * lower_factor) & profitable_mask
            sim.firms['price'][shortage_mask] *= (1 + adj_rate)
            sim.firms['last_price_direction'][shortage_mask] = 1
            sim.firms['price_driver'][shortage_mask] = 'I+'

        # 2. Adjust Workforce Target Based on Inventory, Sales, and Ambition
        # This entire block now operates on data pre-filtered by `normal_mask` to ensure consistent array shapes.
        
        # First, calculate the conservative target for PRODUCTION workers based on inventory needs.
        ticks_of_sales_to_hold = sim.config['target_inventory_production_ticks_factor']
        desired_inventory = average_sales[normal_mask] * ticks_of_sales_to_hold
        current_inventory = sim.firms['inventory'][normal_mask]
        production_need = desired_inventory - current_inventory
        
        production_per_worker = sim.config['production_per_worker']
        target_prod_workers = np.ceil(np.maximum(0, production_need) / production_per_worker).astype(int)
        
        # If inventory is in surplus, production target is minimum.
        surplus_sub_mask = (production_need <= 0)
        target_prod_workers[surplus_sub_mask] = sim.config['min_target_workers']

        # --- AMBITION LOGIC ---
        ambition_threshold = sim.config['ambition_threshold']
        stable_profit_ticks_normal = sim.firms['ticks_of_stable_profit'][normal_mask]
        ambitious_sub_mask = (stable_profit_ticks_normal > ambition_threshold)
        
        if np.any(ambitious_sub_mask):
            ambitious_global_indices = np.where(normal_mask)[0][ambitious_sub_mask]
            sim.tick_events['ambition_triggers'] += len(ambitious_global_indices)
            
            current_prod_workers_ambitious = sim.firms['num_prod_workers'][ambitious_global_indices]
            expansion_targets = np.maximum(np.ceil(current_prod_workers_ambitious * 1.2).astype(int), current_prod_workers_ambitious + 1)
            
            target_prod_workers[ambitious_sub_mask] = expansion_targets
            
            for i, firm_id in enumerate(ambitious_global_indices):
                logger.info(
                    "FIRM STRATEGY: Firm %d is stable. Experimenting with expansion to %d production workers.",
                    firm_id, expansion_targets[i]
                )
            sim.firms['ticks_of_stable_profit'][ambitious_global_indices] = 0

        # Second, calculate support staff targets based on the production target and config ratios.
        logi_ratio = sim.config['logistics_to_production_ratio']
        sales_ratio = sim.config['sales_to_production_ratio']
        target_logi_workers = np.ceil(target_prod_workers * logi_ratio).astype(int)
        target_sales_workers = np.ceil(target_prod_workers * sales_ratio).astype(int)

        # --- PROFITABILITY GATEKEEPER (STRENGTHENED) ---
        # Unprofitable firms are not allowed to expand their total workforce.
        profits_normal = sim.firms['profit_last_tick'][normal_mask]
        unprofitable_sub_mask = (profits_normal < 0)
        if np.any(unprofitable_sub_mask):
            current_total_workers_unprofitable = (sim.firms['num_prod_workers'][normal_mask][unprofitable_sub_mask] +
                                                  sim.firms['num_logi_workers'][normal_mask][unprofitable_sub_mask] +
                                                  sim.firms['num_sales_workers'][normal_mask][unprofitable_sub_mask])
            
            ideal_total_target = (target_prod_workers[unprofitable_sub_mask] +
                                  target_logi_workers[unprofitable_sub_mask] +
                                  target_sales_workers[unprofitable_sub_mask])

            # Scale down targets proportionally if the ideal total exceeds the current total.
            needs_scaling_mask = ideal_total_target > current_total_workers_unprofitable
            if np.any(needs_scaling_mask):
                scalable_ideal_totals = ideal_total_target[needs_scaling_mask]
                scalable_ideal_totals[scalable_ideal_totals == 0] = 1 # Avoid division by zero
                scale_factor = current_total_workers_unprofitable[needs_scaling_mask] / scalable_ideal_totals
                
                # Create temporary views to apply scaling
                prod_view = target_prod_workers[unprofitable_sub_mask]
                logi_view = target_logi_workers[unprofitable_sub_mask]
                sales_view = target_sales_workers[unprofitable_sub_mask]

                prod_view[needs_scaling_mask] = (prod_view[needs_scaling_mask] * scale_factor).astype(int)
                logi_view[needs_scaling_mask] = (logi_view[needs_scaling_mask] * scale_factor).astype(int)
                sales_view[needs_scaling_mask] = (sales_view[needs_scaling_mask] * scale_factor).astype(int)

        # --- BUDGETARY CONSTRAINT (FINAL VALIDATION) ---
        budget_rate = sim.config['expansion_budget_rate']
        capital_for_expansion = sim.firms['balance'][normal_mask] * budget_rate
        
        raw_material_cost = sim.config['raw_material_cost_per_unit']
        cost_per_new_hire = sim.firms['wage_rate'][normal_mask] + (raw_material_cost * production_per_worker)
        cost_per_new_hire[cost_per_new_hire == 0] = 1 
        
        affordable_new_hires = (capital_for_expansion / cost_per_new_hire).astype(int)
        
        current_workers_normal = (sim.firms['num_prod_workers'][normal_mask] +
                                  sim.firms['num_logi_workers'][normal_mask] +
                                  sim.firms['num_sales_workers'][normal_mask])
        max_affordable_target = current_workers_normal + affordable_new_hires
        
        ideal_total_target = target_prod_workers + target_logi_workers + target_sales_workers
        
        needs_scaling_mask = ideal_total_target > max_affordable_target
        if np.any(needs_scaling_mask):
            scalable_ideal_totals = ideal_total_target[needs_scaling_mask]
            scalable_ideal_totals[scalable_ideal_totals == 0] = 1
            scale_factor = max_affordable_target[needs_scaling_mask] / scalable_ideal_totals
            
            target_prod_workers[needs_scaling_mask] = (target_prod_workers[needs_scaling_mask] * scale_factor).astype(int)
            target_logi_workers[needs_scaling_mask] = (target_logi_workers[needs_scaling_mask] * scale_factor).astype(int)
            target_sales_workers[needs_scaling_mask] = (target_sales_workers[needs_scaling_mask] * scale_factor).astype(int)

        # Set final targets, ensuring production workers never fall below the minimum.
        sim.firms['target_prod_workers'][normal_mask] = np.maximum(sim.config['min_target_workers'], target_prod_workers)
        sim.firms['target_logi_workers'][normal_mask] = target_logi_workers
        sim.firms['target_sales_workers'][normal_mask] = target_sales_workers

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
        sim.firms['price_driver'][price_floor_mask] = 'FL'
        # Instead of logging every hit, we aggregate this event.
        # The count will be displayed in the main 5-tick summary.
        num_hits = np.sum(price_floor_mask)
        sim.tick_events['price_floor_hits'] += num_hits

    # --- Step 4: Update Memory for Next Tick ---
    sim.firms['previous_profit'] = sim.firms['profit_last_tick']