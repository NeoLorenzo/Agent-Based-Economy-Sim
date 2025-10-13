# src/systems/banking_system.py

"""
================================================================================
Banking System
================================================================================
This system handles debt servicing between firms and the bank.
================================================================================
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def update(sim):
    """
    Firms service their debt and may take loans from the bank.
    
    Args:
        sim: The simulation state object.
    """
    if sim.config.get('N_B', 0) == 0: return
    
    logger.debug("Start Banking Phase")

    # --- Debt Servicing ---
    firms_with_debt = np.where(sim.firms['debt'] > 0)[0]
    if len(firms_with_debt) > 0:
        interest_payment = sim.firms['debt'] * sim.config['interest_rate']
        principal_payment = sim.firms['debt'] * sim.config['loan_repayment_rate']
        total_payment = interest_payment + principal_payment

        # Deduct payments from firms with debt
        sim.firms['balance'][firms_with_debt] -= total_payment[firms_with_debt]
        sim.firms['debt'][firms_with_debt] -= principal_payment[firms_with_debt]
        
        # Transfer collected payments to the bank
        total_collected = np.sum(total_payment[firms_with_debt])
        sim.banks['balance'][0] += total_collected
        
        for firm_id in firms_with_debt:
            logger.info(
                "Firm %d paid $%.2f interest and $%.2f principal. Remaining debt: $%.2f",
                firm_id, interest_payment[firm_id], principal_payment[firm_id], sim.firms['debt'][firm_id]
            )
        
        if total_collected > 0:
            logger.info(
                "Bank collected a total of $%.2f in debt payments this tick. New balance: $%.2f",
                total_collected, sim.banks['balance'][0]
            )

    # --- Loan Issuance (DISABLED) ---
    # This logic has been removed to prevent infinite debt loops and enable firm failure.
    # Firms must now manage their capital without automatic bailouts.