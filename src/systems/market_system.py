# src/systems/market_system.py

"""
================================================================================
Market System
================================================================================
This system handles the process of households choosing firms and purchasing goods.
================================================================================
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def update(sim, transactions, summary):
    """
    Households choose firms and purchase goods.
    
    Args:
        sim: The simulation state object.
        transactions: A list to record transaction details for visualization.
        summary: A dictionary to accumulate summary statistics for the tick.
    """
    logger.debug("Start Shopping Phase")
    
    # Reset sales counter for this tick
    sim.firms['units_sold_last_tick'][:] = 0

    active_firm_ids = np.where(~sim.firms['is_bankrupt'])[0]
    if len(active_firm_ids) == 0:
        logger.warning("All firms are bankrupt. No shopping can occur.")
        return

    active_firm_pos = sim.firm_pos_array[active_firm_ids]
    active_firm_prices = sim.firms['price'][active_firm_ids]
    
    if sim.config.get('enable_proximity_choice', False):
        diffs = sim.household_pos_array[:, np.newaxis, :] - active_firm_pos[np.newaxis, :, :]
        dist_sq = np.sum(diffs**2, axis=2)
        
        n_to_consider = min(sim.config.get('shopping_firms_to_consider', 1), len(active_firm_ids))
        
        closest_local_indices = np.argsort(dist_sq, axis=1)[:, :n_to_consider]
        candidate_prices = active_firm_prices[closest_local_indices]
        
        cheapest_candidate_local_idx = np.argmin(candidate_prices, axis=1)
        chosen_firm_local_indices = closest_local_indices[np.arange(sim.config['N_H']), cheapest_candidate_local_idx]
        chosen_firm_ids = active_firm_ids[chosen_firm_local_indices]
    else:
        chosen_firm_ids = np.random.choice(active_firm_ids, size=sim.config['N_H'])
    
    requested_qty = sim.households['size'] * sim.config['food_per_person']
    firm_prices = sim.firms['price'][chosen_firm_ids]
    max_affordable_qty = (sim.households['balance'] / firm_prices).astype(int)
    purchase_request_qty = np.minimum(requested_qty, max_affordable_qty)

    for hh_id in range(sim.config['N_H']):
        firm_id = chosen_firm_ids[hh_id]
        request = purchase_request_qty[hh_id]
        if request > 0 and sim.firms['inventory'][firm_id] > 0:
            sold_quantity = min(request, sim.firms['inventory'][firm_id])
            amount = sold_quantity * sim.firms['price'][firm_id]
            
            sim.households['balance'][hh_id] -= amount
            sim.firms['inventory'][firm_id] -= sold_quantity
            sim.firms['revenue_this_tick'][firm_id] += amount
            sim.firms['units_sold_last_tick'][firm_id] += sold_quantity
            
            summary['total_sales_units'] += sold_quantity
            summary['total_sales_volume'] += amount
            transactions.append({'type': 'spending', 'from_id': hh_id, 'to_id': firm_id, 'amount': amount})

    # After all shopping is done, update the sales history
    # Roll the array to make space for the new data
    sim.firm_sales_history = np.roll(sim.firm_sales_history, 1, axis=1)
    # Insert the latest sales data into the first column
    sim.firm_sales_history[:, 0] = sim.firms['units_sold_last_tick']