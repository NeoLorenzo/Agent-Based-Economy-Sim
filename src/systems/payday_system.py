# src/systems/payday_system.py

"""
================================================================================
Payday System
================================================================================
This system handles firms paying wages, calculating profit, and checking for
bankruptcy.
================================================================================
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def update(sim, transactions, summary):
    """
    Firms pay wages to their employees. Firms that cannot pay go bankrupt.
    
    Args:
        sim: The simulation state object.
        transactions: A list to record transaction details for visualization.
        summary: A dictionary to accumulate summary statistics for the tick.
        
    Returns:
        numpy.ndarray: An array containing the total wage payout for each firm.
    """
    logger.debug("Start Payday Phase")
    
    sim.firms['balance'] += sim.firms['revenue_this_tick']
    revenue_last_tick = sim.firms['revenue_this_tick'].copy()
    sim.firms['revenue_this_tick'][:] = 0
    
    total_payout = sim.firms['num_workers'] * sim.firms['wage_rate']
    sim.firms['wages_paid_last_tick'] = total_payout
    
    # --- Profit Calculation ---
    # Profit = Revenue - (Production Costs + Wage Costs)
    sim.firms['profit_last_tick'] = revenue_last_tick - (sim.firms['production_cost_last_tick'] + sim.firms['wages_paid_last_tick'])

    # --- Bankruptcy Check ---
    active_mask = ~sim.firms['is_bankrupt']
    bankrupt_mask = (sim.firms['balance'] < total_payout) & active_mask
    
    for firm_id in np.where(bankrupt_mask)[0]:
        logger.warning(
            "FIRM BANKRUPTCY: Firm %d is failing. Balance: %.2f, Payroll Due: %.2f, Debt: %.2f",
            firm_id, sim.firms['balance'][firm_id], total_payout[firm_id], sim.firms['debt'][firm_id]
        )
        sim.firms['is_bankrupt'][firm_id] = True
        
        # Fire all employees
        employee_indices = np.where(sim.households['employer_id'] == firm_id)[0]
        sim.households['employer_id'][employee_indices] = -1
        
        # Liquidate assets and reset state
        sim.firms['balance'][firm_id] = 0
        sim.firms['inventory'][firm_id] = 0
        sim.firms['num_workers'][firm_id] = 0
        sim.firms['debt'][firm_id] = 0 # Debt is written off
        total_payout[firm_id] = 0 # Cannot pay wages

    # --- Payday for Solvent Firms ---
    solvent_mask = ~bankrupt_mask
    sim.firms['balance'][solvent_mask] -= total_payout[solvent_mask]
    
    num_workers = sim.firms['num_workers']
    wage_per_worker = np.divide(total_payout, num_workers, out=np.zeros_like(total_payout), where=num_workers!=0)
    
    employed_mask = sim.households['employer_id'] != -1
    employer_ids = sim.households['employer_id'][employed_mask]
    sim.households['balance'][employed_mask] += wage_per_worker[employer_ids]
    
    for firm_id, payout in enumerate(total_payout):
        if payout > 0 and not sim.firms['is_bankrupt'][firm_id]:
            worker_ids = np.where(sim.households['employer_id'] == firm_id)[0]
            individual_wage = wage_per_worker[firm_id]
            for worker_id in worker_ids:
                transactions.append({'type': 'wage', 'from_id': firm_id, 'to_id': int(worker_id), 'amount': individual_wage})
    
    summary['total_wages_paid'] = np.sum(total_payout)
    return total_payout