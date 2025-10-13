# src/systems/profit_distribution_system.py

"""
================================================================================
Profit Distribution System
================================================================================
This system handles firms distributing a portion of their profits to their
household owners as dividends.
================================================================================
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def update(sim, transactions, summary):
    """
    Firms distribute a portion of their profits to their owners as dividends.
    
    Args:
        sim: The simulation state object.
        transactions: A list to record transaction details for visualization.
        summary: A dictionary to accumulate summary statistics for the tick.
    """
    logger.debug("Start Profit Distribution Phase")
    
    payout_rate = sim.config.get('dividend_payout_rate', 0.0)
    if payout_rate == 0:
        return

    # Only firms that made a profit and are not bankrupt can pay dividends
    profitable_mask = (sim.firms['profit_last_tick'] > 0) & (~sim.firms['is_bankrupt'])
    
    if np.any(profitable_mask):
        profits_to_distribute = sim.firms['profit_last_tick'][profitable_mask]
        dividends = profits_to_distribute * payout_rate
        
        # Ensure firms can afford the dividend payment
        can_afford_mask = sim.firms['balance'][profitable_mask] >= dividends
        
        payable_dividends = dividends[can_afford_mask]
        paying_firm_indices = np.where(profitable_mask)[0][can_afford_mask]

        if len(paying_firm_indices) > 0:
            owner_ids = sim.firms['owner_id'][paying_firm_indices]

            # Vectorized update for firm balances
            sim.firms['balance'][paying_firm_indices] -= payable_dividends
            
            # Vectorized update for household balances using np.add.at for safety
            np.add.at(sim.households['balance'], owner_ids, payable_dividends)

            total_paid = np.sum(payable_dividends)
            summary['total_dividends_paid'] = total_paid
            sim.tick_events['dividend_payments'] += len(paying_firm_indices)