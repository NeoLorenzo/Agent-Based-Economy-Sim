# src/systems/production_system.py

"""
================================================================================
Production System
================================================================================
This system is responsible for firms producing goods based on their workforce.
================================================================================
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def update(sim, summary):
    """
    Firms produce new goods based on their workforce.
    
    Args:
        sim: The simulation state object.
        summary: A dictionary to accumulate summary statistics for the tick.
    """
    logger.debug("Start Production Phase")
    
    # Reset costs for this tick
    sim.firms['production_cost_last_tick'][:] = 0

    # Production is a function of the number of workers
    production_per_worker = sim.config['production_per_worker']
    produced_quantity = sim.firms['num_prod_workers'] * production_per_worker
    
    # Production has a cost (raw materials)
    material_cost_per_unit = sim.config['raw_material_cost_per_unit']
    production_cost = produced_quantity * material_cost_per_unit
    
    # Firms can only produce if they can afford the raw materials
    can_afford_mask = sim.firms['balance'] >= production_cost
    
    # Update state for firms that can afford to produce
    sim.firms['balance'][can_afford_mask] -= production_cost[can_afford_mask]
    sim.firms['production_cost_last_tick'][can_afford_mask] = production_cost[can_afford_mask]
    sim.firms['inventory'][can_afford_mask] += produced_quantity[can_afford_mask]
    
    total_produced = np.sum(produced_quantity[can_afford_mask])
    total_cost = np.sum(production_cost[can_afford_mask])

    # --- PATCH THE MONEY LEAK ---
    # Re-inject the money spent on raw materials back into the economy as household income.
    # This represents households owning all primary resources.
    if total_cost > 0:
        income_per_household = total_cost / sim.config['N_H']
        sim.households['balance'] += income_per_household
    
    # Update summary (renaming fields for clarity)
    summary['total_production_units'] = total_produced
    summary['total_production_cost'] = total_cost