# src/systems/labor_system.py

"""
================================================================================
Labor Market System
================================================================================
This system manages all labor market dynamics, including hiring, firing, and
job switching.
================================================================================
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def update(sim, total_payout, summary):
    """
    Firms hire and fire workers based on economic conditions.
    
    Args:
        sim: The simulation state object.
        total_payout: An array of the payroll costs for each firm.
        summary: A dictionary to accumulate summary statistics for the tick.
    """
    logger.debug("Start Labor Market Phase")
    active_mask = ~sim.firms['is_bankrupt']

    # --- Strategic Layoffs to meet new targets ---
    downsizing_mask = (sim.firms['num_workers'] > sim.firms['target_num_workers']) & active_mask
    for firm_id in np.where(downsizing_mask)[0]:
        surplus = sim.firms['num_workers'][firm_id] - sim.firms['target_num_workers'][firm_id]
        
        # Get all employees, then explicitly filter out the owner.
        all_employee_indices = np.where(sim.households['employer_id'] == firm_id)[0]
        owner_id = sim.firms['owner_id'][firm_id]
        employee_indices = all_employee_indices[all_employee_indices != owner_id]
        
        if surplus > len(employee_indices):
            surplus = len(employee_indices) # Cannot fire more than you have

        if surplus > 0:
            layoff_candidates = np.random.choice(employee_indices, size=surplus, replace=False)
            sim.households['employer_id'][layoff_candidates] = -1
            sim.firms['num_workers'][firm_id] -= surplus
            sim.tick_events['strategic_layoffs'] += surplus

    # --- Emergency Firing Logic (due to low capital) ---
    # A firm will never fire its owner, only regular employees.
    layoff_threshold = total_payout * sim.config['firm_layoff_capital_threshold_factor']
    should_fire_mask = (sim.firms['balance'] < layoff_threshold) & (sim.firms['num_workers'] > 1) & active_mask
    firms_that_should_fire = np.where(should_fire_mask)[0]
    for firm_id in firms_that_should_fire:
        # Get all employees, then explicitly filter out the owner.
        all_employee_indices = np.where(sim.households['employer_id'] == firm_id)[0]
        owner_id = sim.firms['owner_id'][firm_id]
        employee_indices = all_employee_indices[all_employee_indices != owner_id]

        if len(employee_indices) > 0:
            layoff_candidate_idx = np.random.choice(employee_indices, size=min(1, len(employee_indices)), replace=False)
            sim.households['employer_id'][layoff_candidate_idx] = -1
            sim.firms['num_workers'][firm_id] -= len(layoff_candidate_idx)
            sim.tick_events['emergency_layoffs'] += len(layoff_candidate_idx)

    # Hiring Logic
    sim.firms['failed_to_hire_last_tick'][:] = False
    unemployed_hh_indices = np.where(sim.households['employer_id'] == -1)[0]
    
    if len(unemployed_hh_indices) > 0:
        hiring_revenue_threshold = total_payout * sim.config['firm_hiring_revenue_threshold_factor']
        hiring_firms_mask = (sim.firms['balance'] > hiring_revenue_threshold) & (sim.firms['num_workers'] < sim.firms['target_num_workers']) & active_mask
        hiring_firm_ids = np.where(hiring_firms_mask)[0]

        if len(hiring_firm_ids) > 0:
            # A firm is considered to have failed to hire until it proves it has met its target.
            sim.firms['failed_to_hire_last_tick'][hiring_firm_ids] = True
            
            open_positions = []
            for firm_id in hiring_firm_ids:
                num_openings = sim.firms['target_num_workers'][firm_id] - sim.firms['num_workers'][firm_id]
                wage = sim.firms['wage_rate'][firm_id]
                for _ in range(num_openings):
                    open_positions.append({'firm_id': firm_id, 'wage': wage})
            
            open_positions.sort(key=lambda x: x['wage'], reverse=True)
            np.random.shuffle(unemployed_hh_indices)
            
            num_to_hire = min(len(open_positions), len(unemployed_hh_indices))
            for i in range(num_to_hire):
                job = open_positions[i]
                worker_id = unemployed_hh_indices[i]
                firm_id = job['firm_id']
                
                sim.households['employer_id'][worker_id] = firm_id
                sim.firms['num_workers'][firm_id] += 1
                # BUG FIX: Do NOT set the flag to False here. A firm has not succeeded
                # until it has filled ALL its open positions.
                sim.tick_events['hires'] += 1

            # NEW: After the hiring loop, check which firms actually met their targets.
            # Only these firms will have their "failed_to_hire" flag cleared.
            successful_hires_mask = (sim.firms['num_workers'] >= sim.firms['target_num_workers'])
            # We only care about firms that were hiring in the first place.
            final_success_mask = successful_hires_mask & hiring_firms_mask
            sim.firms['failed_to_hire_last_tick'][final_success_mask] = False

    # Job Switching Logic for Employed Households
    employed_mask = sim.households['employer_id'] != -1
    employed_indices = np.where(employed_mask)[0]
    np.random.shuffle(employed_indices) # Randomize order to prevent bias
    
    job_switching_threshold = sim.config.get('job_switching_wage_threshold', 1.01)

    for hh_id in employed_indices:
        current_employer_id = sim.households['employer_id'][hh_id]
        current_wage = sim.firms['wage_rate'][current_employer_id]
        
        # Find the best alternative job offer (only from non-bankrupt firms)
        potential_employers_mask = (sim.firms['wage_rate'] > current_wage * job_switching_threshold) & active_mask
        potential_employers = np.where(potential_employers_mask)[0]
        
        if len(potential_employers) > 0:
            # Find the highest paying alternative employer
            best_new_employer_id = potential_employers[np.argmax(sim.firms['wage_rate'][potential_employers])]
            
            # Switch jobs
            old_wage = sim.firms['wage_rate'][current_employer_id]
            new_wage = sim.firms['wage_rate'][best_new_employer_id]

            sim.households['employer_id'][hh_id] = best_new_employer_id
            sim.firms['num_workers'][current_employer_id] -= 1
            sim.firms['num_workers'][best_new_employer_id] += 1
            
            # The firm that lost an employee is now under pressure to raise wages
            sim.firms['failed_to_hire_last_tick'][current_employer_id] = True
            
            sim.tick_events['job_switches'] += 1

    summary['unemployment_rate'] = (np.count_nonzero(sim.households['employer_id'] == -1) / sim.config['N_H']) * 100