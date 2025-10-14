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
    This version includes logic for different job roles and internal reassignment.
    """
    # --- Step 0: Resynchronize Worker Counts ---
    # This is a critical bug fix. The firm's worker counts can become stale
    # during chaotic periods of hiring and firing. We must recalculate the
    # actual number of employees from the authoritative source (the households
    # array) before any new labor market decisions are made.
    
    num_firms = sim.config['N_F']
    prod_counts = np.zeros(num_firms, dtype=int)
    logi_counts = np.zeros(num_firms, dtype=int)
    sales_counts = np.zeros(num_firms, dtype=int)

    employed_mask = sim.households['employer_id'] != -1
    employer_ids = sim.households['employer_id'][employed_mask]
    job_roles = sim.households['job_role'][employed_mask]

    # Create masks for each role to count them
    is_prod = job_roles == 1
    is_logi = job_roles == 2
    is_sales = job_roles == 3

    # Use np.add.at for a safe and efficient vectorized count
    np.add.at(prod_counts, employer_ids[is_prod], 1)
    np.add.at(logi_counts, employer_ids[is_logi], 1)
    np.add.at(sales_counts, employer_ids[is_sales], 1)

    # Overwrite the stale cache with the ground truth
    sim.firms['num_prod_workers'] = prod_counts
    sim.firms['num_logi_workers'] = logi_counts
    sim.firms['num_sales_workers'] = sales_counts
    
    logger.debug("Resynchronized firm worker counts from household data.")
    
    logger.debug("Start Labor Market Phase")
    active_mask = ~sim.firms['is_bankrupt']

    # --- Step 1: Internal Reassignment ---
    # Firms first try to fill open roles by reassigning existing employees.
    for firm_id in np.where(active_mask)[0]:
        current_counts = np.array([
            sim.firms['num_prod_workers'][firm_id], sim.firms['num_logi_workers'][firm_id], sim.firms['num_sales_workers'][firm_id]
        ])
        target_counts = np.array([
            sim.firms['target_prod_workers'][firm_id], sim.firms['target_logi_workers'][firm_id], sim.firms['target_sales_workers'][firm_id]
        ])
        deficits = np.maximum(0, target_counts - current_counts)
        surpluses = np.maximum(0, current_counts - target_counts)

        if np.sum(deficits) > 0 and np.sum(surpluses) > 0:
            all_employee_indices = np.where(sim.households['employer_id'] == firm_id)[0]
            np.random.shuffle(all_employee_indices)
            for hh_id in all_employee_indices:
                current_role_idx = sim.households['job_role'][hh_id] - 1
                if surpluses[current_role_idx] > 0:
                    for new_role_idx in range(len(deficits)):
                        if deficits[new_role_idx] > 0:
                            sim.households['job_role'][hh_id] = new_role_idx + 1
                            surpluses[current_role_idx] -= 1; deficits[new_role_idx] -= 1
                            sim.tick_events['internal_reassignments'] += 1
                            break

    # --- Step 2: Strategic Layoffs (Post-Reassignment) ---
    # A firm downsizes if ANY role is over-staffed.
    prod_surplus_mask = sim.firms['num_prod_workers'] > sim.firms['target_prod_workers']
    logi_surplus_mask = sim.firms['num_logi_workers'] > sim.firms['target_logi_workers']
    sales_surplus_mask = sim.firms['num_sales_workers'] > sim.firms['target_sales_workers']
    downsizing_mask = (prod_surplus_mask | logi_surplus_mask | sales_surplus_mask) & active_mask
    
    for firm_id in np.where(downsizing_mask)[0]:
        prod_surplus = max(0, sim.firms['num_prod_workers'][firm_id] - sim.firms['target_prod_workers'][firm_id])
        logi_surplus = max(0, sim.firms['num_logi_workers'][firm_id] - sim.firms['target_logi_workers'][firm_id])
        sales_surplus = max(0, sim.firms['num_sales_workers'][firm_id] - sim.firms['target_sales_workers'][firm_id])
        num_to_layoff = prod_surplus + logi_surplus + sales_surplus
        
        if num_to_layoff <= 0: continue

        all_employee_indices = np.where(sim.households['employer_id'] == firm_id)[0]
        owner_id = sim.firms['owner_id'][firm_id]
        employee_indices = all_employee_indices[all_employee_indices != owner_id]
        
        layoff_candidates = [hh_id for hh_id in employee_indices if (
            (sim.households['job_role'][hh_id] == 1 and prod_surplus > 0) or
            (sim.households['job_role'][hh_id] == 2 and logi_surplus > 0) or
            (sim.households['job_role'][hh_id] == 3 and sales_surplus > 0)
        )]
        np.random.shuffle(layoff_candidates)

        for i in range(min(num_to_layoff, len(layoff_candidates))):
            hh_id = layoff_candidates[i]
            laid_off_role = sim.households['job_role'][hh_id]
            sim.households['employer_id'][hh_id] = -1; sim.households['job_role'][hh_id] = 0
            if laid_off_role == 1: sim.firms['num_prod_workers'][firm_id] = max(0, sim.firms['num_prod_workers'][firm_id] - 1)
            elif laid_off_role == 2: sim.firms['num_logi_workers'][firm_id] = max(0, sim.firms['num_logi_workers'][firm_id] - 1)
            elif laid_off_role == 3: sim.firms['num_sales_workers'][firm_id] = max(0, sim.firms['num_sales_workers'][firm_id] - 1)
            sim.tick_events['strategic_layoffs'] += 1

    # --- Step 3: Emergency Firing Logic (due to low capital) ---
    # (This logic remains unchanged as it's an independent, single-employee action)
    current_total_workers = sim.firms['num_prod_workers'] + sim.firms['num_logi_workers'] + sim.firms['num_sales_workers']
    layoff_threshold = total_payout * sim.config['firm_layoff_capital_threshold_factor']
    should_fire_mask = (sim.firms['balance'] < layoff_threshold) & (current_total_workers > 1) & active_mask
    for firm_id in np.where(should_fire_mask)[0]:
        all_employee_indices = np.where(sim.households['employer_id'] == firm_id)[0]
        owner_id = sim.firms['owner_id'][firm_id]
        employee_indices = all_employee_indices[all_employee_indices != owner_id]
        if len(employee_indices) > 0:
            layoff_candidate_idx = np.random.choice(employee_indices, size=1, replace=False)[0]
            laid_off_role = sim.households['job_role'][layoff_candidate_idx]
            sim.households['employer_id'][layoff_candidate_idx] = -1; sim.households['job_role'][layoff_candidate_idx] = 0
            if laid_off_role == 1: sim.firms['num_prod_workers'][firm_id] = max(0, sim.firms['num_prod_workers'][firm_id] - 1)
            elif laid_off_role == 2: sim.firms['num_logi_workers'][firm_id] = max(0, sim.firms['num_logi_workers'][firm_id] - 1)
            elif laid_off_role == 3: sim.firms['num_sales_workers'][firm_id] = max(0, sim.firms['num_sales_workers'][firm_id] - 1)
            sim.tick_events['emergency_layoffs'] += 1

    # --- Step 4: Hiring Logic ---
    sim.firms['failed_to_hire_last_tick'][:] = False
    all_unemployed_hh = np.where(sim.households['employer_id'] == -1)[0]

    # --- NEW: Introduce Labor Market Friction ---
    # A firm cannot instantly interview and hire the entire unemployed population.
    # This models search costs and matching friction.
    hiring_limit_rate = sim.config.get('max_hires_per_tick_rate', 1.0)
    num_hirable = int(np.ceil(len(all_unemployed_hh) * hiring_limit_rate))
    unemployed_hh_indices = np.random.choice(all_unemployed_hh, size=num_hirable, replace=False)

    if len(unemployed_hh_indices) > 0:
        prod_deficit_mask = sim.firms['num_prod_workers'] < sim.firms['target_prod_workers']
        logi_deficit_mask = sim.firms['num_logi_workers'] < sim.firms['target_logi_workers']
        sales_deficit_mask = sim.firms['num_sales_workers'] < sim.firms['target_sales_workers']
        budget_mask = sim.firms['balance'] > (total_payout * sim.config['firm_hiring_revenue_threshold_factor'])
        hiring_firms_mask = (prod_deficit_mask | logi_deficit_mask | sales_deficit_mask) & budget_mask & active_mask
        hiring_firm_ids = np.where(hiring_firms_mask)[0]

        if len(hiring_firm_ids) > 0:
            sim.firms['failed_to_hire_last_tick'][hiring_firm_ids] = True
            open_positions = []
            for firm_id in hiring_firm_ids:
                wage = sim.firms['wage_rate'][firm_id]
                for _ in range(max(0, sim.firms['target_prod_workers'][firm_id] - sim.firms['num_prod_workers'][firm_id])): open_positions.append({'firm_id': firm_id, 'wage': wage, 'role': 1})
                for _ in range(max(0, sim.firms['target_logi_workers'][firm_id] - sim.firms['num_logi_workers'][firm_id])): open_positions.append({'firm_id': firm_id, 'wage': wage, 'role': 2})
                for _ in range(max(0, sim.firms['target_sales_workers'][firm_id] - sim.firms['num_sales_workers'][firm_id])): open_positions.append({'firm_id': firm_id, 'wage': wage, 'role': 3})
            
            open_positions.sort(key=lambda x: x['wage'], reverse=True)
            np.random.shuffle(unemployed_hh_indices)
            
            hired_workers = set()
            for job in open_positions:
                if len(hired_workers) == len(unemployed_hh_indices): break
                firm_id, role = job['firm_id'], job['role']
                for worker_id in unemployed_hh_indices:
                    if worker_id not in hired_workers:
                        sim.households['employer_id'][worker_id] = firm_id; sim.households['job_role'][worker_id] = role
                        if role == 1: sim.firms['num_prod_workers'][firm_id] += 1
                        elif role == 2: sim.firms['num_logi_workers'][firm_id] += 1
                        elif role == 3: sim.firms['num_sales_workers'][firm_id] += 1
                        sim.tick_events['hires'] += 1
                        hired_workers.add(worker_id)
                        break
            
            current_total = sim.firms['num_prod_workers'] + sim.firms['num_logi_workers'] + sim.firms['num_sales_workers']
            target_total = sim.firms['target_prod_workers'] + sim.firms['target_logi_workers'] + sim.firms['target_sales_workers']
            successful_hires_mask = (current_total >= target_total)
            final_success_mask = successful_hires_mask & hiring_firms_mask
            sim.firms['failed_to_hire_last_tick'][final_success_mask] = False

    # --- Step 5: Job Switching Logic for Employed Households ---
    open_positions_for_switching = []
    prod_deficit_mask = sim.firms['num_prod_workers'] < sim.firms['target_prod_workers']
    logi_deficit_mask = sim.firms['num_logi_workers'] < sim.firms['target_logi_workers']
    sales_deficit_mask = sim.firms['num_sales_workers'] < sim.firms['target_sales_workers']
    still_hiring_mask = (prod_deficit_mask | logi_deficit_mask | sales_deficit_mask) & active_mask
    for firm_id in np.where(still_hiring_mask)[0]:
        wage = sim.firms['wage_rate'][firm_id]
        for _ in range(max(0, sim.firms['target_prod_workers'][firm_id] - sim.firms['num_prod_workers'][firm_id])): open_positions_for_switching.append({'firm_id': firm_id, 'wage': wage, 'role': 1})
        for _ in range(max(0, sim.firms['target_logi_workers'][firm_id] - sim.firms['num_logi_workers'][firm_id])): open_positions_for_switching.append({'firm_id': firm_id, 'wage': wage, 'role': 2})
        for _ in range(max(0, sim.firms['target_sales_workers'][firm_id] - sim.firms['num_sales_workers'][firm_id])): open_positions_for_switching.append({'firm_id': firm_id, 'wage': wage, 'role': 3})

    if open_positions_for_switching:
        employed_indices = np.where(sim.households['employer_id'] != -1)[0]
        np.random.shuffle(employed_indices)
        job_switching_threshold = sim.config.get('job_switching_wage_threshold', 1.01)
        for hh_id in employed_indices:
            current_employer_id = sim.households['employer_id'][hh_id]
            current_wage = sim.firms['wage_rate'][current_employer_id]
            best_offer = None
            for offer in open_positions_for_switching:
                if offer['firm_id'] != current_employer_id and offer['wage'] > current_wage * job_switching_threshold:
                    if best_offer is None or offer['wage'] > best_offer['wage']: best_offer = offer
            if best_offer:
                new_employer_id, new_role = best_offer['firm_id'], best_offer['role']
                old_role = sim.households['job_role'][hh_id]
                if old_role == 1: sim.firms['num_prod_workers'][current_employer_id] = max(0, sim.firms['num_prod_workers'][current_employer_id] - 1)
                elif old_role == 2: sim.firms['num_logi_workers'][current_employer_id] = max(0, sim.firms['num_logi_workers'][current_employer_id] - 1)
                elif old_role == 3: sim.firms['num_sales_workers'][current_employer_id] = max(0, sim.firms['num_sales_workers'][current_employer_id] - 1)
                if new_role == 1: sim.firms['num_prod_workers'][new_employer_id] += 1
                elif new_role == 2: sim.firms['num_logi_workers'][new_employer_id] += 1
                elif new_role == 3: sim.firms['num_sales_workers'][new_employer_id] += 1
                sim.households['employer_id'][hh_id] = new_employer_id; sim.households['job_role'][hh_id] = new_role
                sim.firms['failed_to_hire_last_tick'][current_employer_id] = True
                sim.tick_events['job_switches'] += 1
                open_positions_for_switching.remove(best_offer)
                if not open_positions_for_switching: break

    summary['unemployment_rate'] = (np.count_nonzero(sim.households['employer_id'] == -1) / sim.config['N_H']) * 100