# simulation.py

import random
import logging
import math
import numpy as np

logger = logging.getLogger(__name__)

#======================================
# SIMULATION ENGINE
#======================================

import constants as C
import collections

class Simulation:
    """
    Manages the overall simulation state and tick loop using NumPy for performance.
    Agent data is stored in structured NumPy arrays rather than individual objects.
    """
    def __init__(self, config):
        self.config = config
        self.tick_events = collections.Counter()
        
        # Agent positions are now generated and stored internally
        self.firm_positions = {}
        self.household_positions = {}
        self.bank_positions = {}
        self.firm_pos_array = np.array([])
        self.household_pos_array = np.array([])
        self.bank_pos_array = np.array([])
        self._calculate_agent_positions()

        self.households = None # Will be a NumPy structured array
        self.firms = None      # Will be a NumPy structured array
        self.banks = None      # Will be a NumPy structured array
        self._setup_world()

    def _calculate_agent_positions(self):
        """
        Calculates and stores non-overlapping screen positions for all agents.
        This is part of the simulation's internal setup.
        """
        num_firms = self.config['N_F']
        num_households = self.config['N_H']
        num_banks = self.config.get('N_B', 0)
        total_agents = num_firms + num_households + num_banks

        min_dist = 5 * (C.AGENT_RADIUS + C.AGENT_OUTLINE_WIDTH)
        min_dist_sq = min_dist ** 2
        
        generated_positions = []
        for _ in range(total_agents):
            while True:
                min_x = C.INVENTORY_GRAPH_X + C.GRAPH_WIDTH + C.SCREEN_PADDING
                x = np.random.randint(min_x, C.SCREEN_WIDTH - C.SCREEN_PADDING)
                y = np.random.randint(C.SCREEN_PADDING, C.SCREEN_HEIGHT - C.SCREEN_PADDING)
                candidate_pos = (x, y)
                is_valid = all(
                    ((pos[0] - candidate_pos[0])**2 + (pos[1] - candidate_pos[1])**2) >= min_dist_sq
                    for pos in generated_positions
                )
                if is_valid:
                    generated_positions.append(candidate_pos)
                    break
        
        random.shuffle(generated_positions)

        self.firm_positions = {i: generated_positions.pop() for i in range(num_firms)}
        self.household_positions = {i: generated_positions.pop() for i in range(num_households)}
        self.bank_positions = {i: generated_positions.pop() for i in range(num_banks)}

        # Also create the NumPy array versions for vectorized calculations
        self.firm_pos_array = np.array(list(self.firm_positions.values()))
        self.household_pos_array = np.array(list(self.household_positions.values()))
        self.bank_pos_array = np.array(list(self.bank_positions.values()))

    def _setup_world(self):
        """Initializes all agent data in structured NumPy arrays."""
        logger.info("Setting up the simulation world with NumPy arrays...")
        
        # --- Define data structure for Firms ---
        firm_dtype = [
            ('balance', 'f8'),
            ('debt', 'f8'),
            ('price', 'f8'),
            ('wage_rate', 'f8'),
            ('inventory', 'i4'),
            ('target_inventory', 'i4'),
            ('revenue_this_tick', 'f8'),
            ('units_sold_last_tick', 'i4'),
            ('production_cost_last_tick', 'f8'),
            ('wages_paid_last_tick', 'f8'),
            ('profit_last_tick', 'f8'),
            ('previous_profit', 'f8'),
            ('ticks_of_falling_profit', 'i4'),
            ('ticks_of_stable_profit', 'i4'),
            ('last_price_direction', 'i4'),
            ('num_workers', 'i4'),
            ('target_num_workers', 'i4'),
            ('failed_to_hire_last_tick', '?'), # Boolean flag
            ('is_bankrupt', '?') # Boolean flag
        ]
        self.firms = np.zeros(self.config['N_F'], dtype=firm_dtype)
        
        # --- Initialize Firm data ---
        self.firms['balance'] = self.config['firm_initial_capital']
        self.firms['price'] = self.config['p']
        self.firms['wage_rate'] = self.config['wage_rate']
        self.firms['last_price_direction'] = 1 # Default to trying to increase price
        # Target inventory is now calculated dynamically each tick based on production.
        # It starts at 0.
        logger.info(
            "Injected initial capital of %.2f into each of the %d firms.",
            self.config['firm_initial_capital'], self.config['N_F']
        )
        logger.debug("Created %d firms in a NumPy array.", self.config['N_F'])

        # --- Define data structure for Households ---
        household_dtype = [
            ('balance', 'f8'),
            ('size', 'i4'),
            ('employer_id', 'i4')
        ]
        self.households = np.zeros(self.config['N_H'], dtype=household_dtype)

        # --- Initialize Household data ---
        self.households['balance'] = self.config['M0'] / self.config['N_H']
        self.households['size'] = self.config['household_size']
        
        # All households start as unemployed. Firms will hire them in the
        # first few ticks based on their initial capital and revenue potential.
        self.households['employer_id'] = -1 # -1 signifies unemployed
        
        # All firms start with zero workers but have a target number of workers.
        # This target can be adjusted later based on performance.
        self.firms['num_workers'] = 0
        # Firms start small and must grow based on their success.
        initial_target_workers = 1
        self.firms['target_num_workers'] = initial_target_workers
        
        # --- Define data structure for Banks ---
        bank_dtype = [('balance', 'f8')]
        self.banks = np.zeros(self.config.get('N_B', 0), dtype=bank_dtype)
        # The bank has infinite capital for now; we represent this with a very large number.
        self.banks['balance'] = 1e12

        # Create a separate array to hold the moving average of sales for each firm
        history_ticks = self.config.get('sales_history_ticks', 10)
        self.firm_sales_history = np.zeros((self.config['N_F'], history_ticks), dtype=int)
        
        logger.debug("Created %d households and assigned them to firms.", self.config['N_H'])
        logger.info("World setup complete.")

    def _vectorized_find_closest_firms(self):
        """
        Finds the closest firm for all households in a single vectorized operation.
        This is significantly faster than looping through each household.
        
        NOTE: This method is no longer called in the main shopping logic when
        price-sensitive choice is enabled, but is kept for potential future use
        or alternative simulation modes. The new logic is integrated directly
        into `run_one_tick` for clarity.
        """
        # Use broadcasting to calculate squared distances between all households and all firms
        # household_pos_array is (N_H, 2) -> (N_H, 1, 2)
        # firm_pos_array is (N_F, 2) -> (1, N_F, 2)
        # The result of subtraction is a (N_H, N_F, 2) array
        diffs = self.household_pos_array[:, np.newaxis, :] - self.firm_pos_array[np.newaxis, :, :]
        dist_sq = np.sum(diffs**2, axis=2) # Sum along the x,y dimension
        
        # Find the index of the minimum distance for each household
        return np.argmin(dist_sq, axis=1)

    def update_and_get_firm_data_for_render(self):
        """
        Updates the historical data tracking for firms and returns it in a
        format suitable for the visualization module.

        This method is called once per tick by the main loop.

        Returns:
            tuple: A tuple containing four dictionaries:
                   - inventory_data (dict): {firm_id: [history]}
                   - price_data (dict): {firm_id: [history]}
                   - capital_data (dict): {firm_id: [history]}
                   - employee_data (dict): {firm_id: [history]}
        """
        # Initialize on first call
        if not hasattr(self, '_inventory_history'):
            self._inventory_history = {i: [] for i in range(self.config['N_F'])}
            self._price_history = {i: [] for i in range(self.config['N_F'])}
            self._capital_history = {i: [] for i in range(self.config['N_F'])}
            self._employee_history = {i: [] for i in range(self.config['N_F'])}
            # Add wage history tracking for validation
            self._wage_history = {i: [] for i in range(self.config['N_F'])}

        for i in range(self.config['N_F']):
            self._inventory_history[i].append(self.firms['inventory'][i])
            self._price_history[i].append(self.firms['price'][i])
            self._capital_history[i].append(self.firms['balance'][i])
            self._employee_history[i].append(self.firms['num_workers'][i])
            self._wage_history[i].append(self.firms['wage_rate'][i])

        return self._inventory_history, self._price_history, self._capital_history, self._employee_history

    def run_one_tick(self, current_tick):
        """
        Executes one full cycle of the simulation by calling phase-specific methods.
        This method orchestrates the high-level flow of a single tick.
        Returns transactions, a summary dict, and a Counter of key events.
        """
        self._current_tick = current_tick
        self.tick_events.clear() # Reset for the new tick
        transactions = []
        summary = {
            'total_restock_cost': 0.0, 'total_restock_units': 0,
            'total_sales_volume': 0.0, 'total_sales_units': 0,
            'total_wages_paid': 0.0, 'unemployment_rate': 0.0
        }

        self._production_phase(summary)
        self._shopping_phase(transactions, summary)
        total_payout = self._payday_phase(transactions, summary)
        self._labor_market_phase(total_payout, summary)
        self._firm_adjustment_phase(summary)
        self._banking_phase()

        return transactions, summary, self.tick_events

    def _production_phase(self, summary):
        """Firms produce new goods based on their workforce."""
        logger.debug("Start Production Phase")
        
        # Reset costs for this tick
        self.firms['production_cost_last_tick'][:] = 0

        # Production is a function of the number of workers
        production_per_worker = self.config['production_per_worker']
        produced_quantity = self.firms['num_workers'] * production_per_worker
        
        # Production has a cost (raw materials)
        material_cost_per_unit = self.config['raw_material_cost_per_unit']
        production_cost = produced_quantity * material_cost_per_unit
        
        # Firms can only produce if they can afford the raw materials
        can_afford_mask = self.firms['balance'] >= production_cost
        
        # Update state for firms that can afford to produce
        self.firms['balance'][can_afford_mask] -= production_cost[can_afford_mask]
        self.firms['production_cost_last_tick'][can_afford_mask] = production_cost[can_afford_mask]
        self.firms['inventory'][can_afford_mask] += produced_quantity[can_afford_mask]
        
        total_produced = np.sum(produced_quantity[can_afford_mask])
        total_cost = np.sum(production_cost[can_afford_mask])

        # --- PATCH THE MONEY LEAK ---
        # Re-inject the money spent on raw materials back into the economy as household income.
        # This represents households owning all primary resources.
        if total_cost > 0:
            income_per_household = total_cost / self.config['N_H']
            self.households['balance'] += income_per_household
        
        # Update summary (renaming fields for clarity)
        summary['total_production_units'] = total_produced
        summary['total_production_cost'] = total_cost

    def _shopping_phase(self, transactions, summary):
        """Households choose firms and purchase goods."""
        logger.debug("Start Shopping Phase")
        
        # Reset sales counter for this tick
        self.firms['units_sold_last_tick'][:] = 0

        active_firm_ids = np.where(~self.firms['is_bankrupt'])[0]
        if len(active_firm_ids) == 0:
            logger.warning("All firms are bankrupt. No shopping can occur.")
            return

        active_firm_pos = self.firm_pos_array[active_firm_ids]
        active_firm_prices = self.firms['price'][active_firm_ids]
        
        if self.config.get('enable_proximity_choice', False):
            diffs = self.household_pos_array[:, np.newaxis, :] - active_firm_pos[np.newaxis, :, :]
            dist_sq = np.sum(diffs**2, axis=2)
            
            n_to_consider = min(self.config.get('shopping_firms_to_consider', 1), len(active_firm_ids))
            
            closest_local_indices = np.argsort(dist_sq, axis=1)[:, :n_to_consider]
            candidate_prices = active_firm_prices[closest_local_indices]
            
            cheapest_candidate_local_idx = np.argmin(candidate_prices, axis=1)
            chosen_firm_local_indices = closest_local_indices[np.arange(self.config['N_H']), cheapest_candidate_local_idx]
            chosen_firm_ids = active_firm_ids[chosen_firm_local_indices]
        else:
            chosen_firm_ids = np.random.choice(active_firm_ids, size=self.config['N_H'])
        
        requested_qty = self.households['size'] * self.config['food_per_person']
        firm_prices = self.firms['price'][chosen_firm_ids]
        max_affordable_qty = (self.households['balance'] / firm_prices).astype(int)
        purchase_request_qty = np.minimum(requested_qty, max_affordable_qty)

        for hh_id in range(self.config['N_H']):
            firm_id = chosen_firm_ids[hh_id]
            request = purchase_request_qty[hh_id]
            if request > 0 and self.firms['inventory'][firm_id] > 0:
                sold_quantity = min(request, self.firms['inventory'][firm_id])
                amount = sold_quantity * self.firms['price'][firm_id]
                
                self.households['balance'][hh_id] -= amount
                self.firms['inventory'][firm_id] -= sold_quantity
                self.firms['revenue_this_tick'][firm_id] += amount
                self.firms['units_sold_last_tick'][firm_id] += sold_quantity
                
                summary['total_sales_units'] += sold_quantity
                summary['total_sales_volume'] += amount
                transactions.append({'type': 'spending', 'from_id': hh_id, 'to_id': firm_id, 'amount': amount})

        # After all shopping is done, update the sales history
        # Roll the array to make space for the new data
        self.firm_sales_history = np.roll(self.firm_sales_history, 1, axis=1)
        # Insert the latest sales data into the first column
        self.firm_sales_history[:, 0] = self.firms['units_sold_last_tick']

    def _payday_phase(self, transactions, summary):
        """Firms pay wages to their employees. Firms that cannot pay go bankrupt."""
        logger.debug("Start Payday Phase")
        
        self.firms['balance'] += self.firms['revenue_this_tick']
        revenue_last_tick = self.firms['revenue_this_tick'].copy()
        self.firms['revenue_this_tick'][:] = 0
        
        total_payout = self.firms['num_workers'] * self.firms['wage_rate']
        self.firms['wages_paid_last_tick'] = total_payout
        
        # --- Profit Calculation ---
        # Profit = Revenue - (Production Costs + Wage Costs)
        self.firms['profit_last_tick'] = revenue_last_tick - (self.firms['production_cost_last_tick'] + self.firms['wages_paid_last_tick'])

        # --- Bankruptcy Check ---
        active_mask = ~self.firms['is_bankrupt']
        bankrupt_mask = (self.firms['balance'] < total_payout) & active_mask
        
        for firm_id in np.where(bankrupt_mask)[0]:
            logger.warning(
                "FIRM BANKRUPTCY: Firm %d is failing. Balance: %.2f, Payroll Due: %.2f, Debt: %.2f",
                firm_id, self.firms['balance'][firm_id], total_payout[firm_id], self.firms['debt'][firm_id]
            )
            self.firms['is_bankrupt'][firm_id] = True
            
            # Fire all employees
            employee_indices = np.where(self.households['employer_id'] == firm_id)[0]
            self.households['employer_id'][employee_indices] = -1
            
            # Liquidate assets and reset state
            self.firms['balance'][firm_id] = 0
            self.firms['inventory'][firm_id] = 0
            self.firms['num_workers'][firm_id] = 0
            self.firms['debt'][firm_id] = 0 # Debt is written off
            total_payout[firm_id] = 0 # Cannot pay wages

        # --- Payday for Solvent Firms ---
        solvent_mask = ~bankrupt_mask
        self.firms['balance'][solvent_mask] -= total_payout[solvent_mask]
        
        num_workers = self.firms['num_workers']
        wage_per_worker = np.divide(total_payout, num_workers, out=np.zeros_like(total_payout), where=num_workers!=0)
        
        employed_mask = self.households['employer_id'] != -1
        employer_ids = self.households['employer_id'][employed_mask]
        self.households['balance'][employed_mask] += wage_per_worker[employer_ids]
        
        for firm_id, payout in enumerate(total_payout):
            if payout > 0 and not self.firms['is_bankrupt'][firm_id]:
                worker_ids = np.where(self.households['employer_id'] == firm_id)[0]
                individual_wage = wage_per_worker[firm_id]
                for worker_id in worker_ids:
                    transactions.append({'type': 'wage', 'from_id': firm_id, 'to_id': int(worker_id), 'amount': individual_wage})
        
        summary['total_wages_paid'] = np.sum(total_payout)
        return total_payout

    def _labor_market_phase(self, total_payout, summary):
        """Firms hire and fire workers based on economic conditions."""
        logger.debug("Start Labor Market Phase")
        active_mask = ~self.firms['is_bankrupt']

        # --- Strategic Layoffs to meet new targets ---
        downsizing_mask = (self.firms['num_workers'] > self.firms['target_num_workers']) & active_mask
        for firm_id in np.where(downsizing_mask)[0]:
            surplus = self.firms['num_workers'][firm_id] - self.firms['target_num_workers'][firm_id]
            employee_indices = np.where(self.households['employer_id'] == firm_id)[0]
            
            if surplus > len(employee_indices):
                surplus = len(employee_indices) # Cannot fire more than you have

            if surplus > 0:
                layoff_candidates = np.random.choice(employee_indices, size=surplus, replace=False)
                self.households['employer_id'][layoff_candidates] = -1
                self.firms['num_workers'][firm_id] -= surplus
                self.tick_events['strategic_layoffs'] += surplus

        # --- Emergency Firing Logic (due to low capital) ---
        layoff_threshold = total_payout * self.config['firm_layoff_capital_threshold_factor']
        should_fire_mask = (self.firms['balance'] < layoff_threshold) & (self.firms['num_workers'] > 0) & active_mask
        firms_that_should_fire = np.where(should_fire_mask)[0]
        for firm_id in firms_that_should_fire:
            employee_indices = np.where(self.households['employer_id'] == firm_id)[0]
            if len(employee_indices) > 0:
                layoff_candidate_idx = np.random.choice(employee_indices, size=min(1, len(employee_indices)), replace=False)
                self.households['employer_id'][layoff_candidate_idx] = -1
                self.firms['num_workers'][firm_id] -= len(layoff_candidate_idx)
                self.tick_events['emergency_layoffs'] += len(layoff_candidate_idx)

        # Hiring Logic
        self.firms['failed_to_hire_last_tick'][:] = False
        unemployed_hh_indices = np.where(self.households['employer_id'] == -1)[0]
        
        if len(unemployed_hh_indices) > 0:
            hiring_revenue_threshold = total_payout * self.config['firm_hiring_revenue_threshold_factor']
            hiring_firms_mask = (self.firms['balance'] > hiring_revenue_threshold) & (self.firms['num_workers'] < self.firms['target_num_workers']) & active_mask
            hiring_firm_ids = np.where(hiring_firms_mask)[0]

            if len(hiring_firm_ids) > 0:
                self.firms['failed_to_hire_last_tick'][hiring_firm_ids] = True
                
                open_positions = []
                for firm_id in hiring_firm_ids:
                    num_openings = self.firms['target_num_workers'][firm_id] - self.firms['num_workers'][firm_id]
                    wage = self.firms['wage_rate'][firm_id]
                    for _ in range(num_openings):
                        open_positions.append({'firm_id': firm_id, 'wage': wage})
                
                open_positions.sort(key=lambda x: x['wage'], reverse=True)
                np.random.shuffle(unemployed_hh_indices)
                
                num_to_hire = min(len(open_positions), len(unemployed_hh_indices))
                for i in range(num_to_hire):
                    job = open_positions[i]
                    worker_id = unemployed_hh_indices[i]
                    firm_id = job['firm_id']
                    
                    self.households['employer_id'][worker_id] = firm_id
                    self.firms['num_workers'][firm_id] += 1
                    self.firms['failed_to_hire_last_tick'][firm_id] = False
                    self.tick_events['hires'] += 1

        # Job Switching Logic for Employed Households
        employed_mask = self.households['employer_id'] != -1
        employed_indices = np.where(employed_mask)[0]
        np.random.shuffle(employed_indices) # Randomize order to prevent bias
        
        job_switching_threshold = self.config.get('job_switching_wage_threshold', 1.01)

        for hh_id in employed_indices:
            current_employer_id = self.households['employer_id'][hh_id]
            current_wage = self.firms['wage_rate'][current_employer_id]
            
            # Find the best alternative job offer (only from non-bankrupt firms)
            potential_employers_mask = (self.firms['wage_rate'] > current_wage * job_switching_threshold) & active_mask
            potential_employers = np.where(potential_employers_mask)[0]
            
            if len(potential_employers) > 0:
                # Find the highest paying alternative employer
                best_new_employer_id = potential_employers[np.argmax(self.firms['wage_rate'][potential_employers])]
                
                # Switch jobs
                old_wage = self.firms['wage_rate'][current_employer_id]
                new_wage = self.firms['wage_rate'][best_new_employer_id]

                self.households['employer_id'][hh_id] = best_new_employer_id
                self.firms['num_workers'][current_employer_id] -= 1
                self.firms['num_workers'][best_new_employer_id] += 1
                
                # The firm that lost an employee is now under pressure to raise wages
                self.firms['failed_to_hire_last_tick'][current_employer_id] = True
                
                self.tick_events['job_switches'] += 1

        summary['unemployment_rate'] = (np.count_nonzero(self.households['employer_id'] == -1) / self.config['N_H']) * 100

    def _firm_adjustment_phase(self, summary):
        """Firms make strategic decisions about price and production to maximize profit."""
        logger.debug("Start Firm Adjustment Phase")
        active_mask = ~self.firms['is_bankrupt']
        if not np.any(active_mask): return

        # --- Step 1: Assess Profit Situation ---
        profit = self.firms['profit_last_tick']
        prev_profit = self.firms['previous_profit']
        
        profit_fell_mask = (profit < prev_profit) & active_mask
        self.firms['ticks_of_falling_profit'][profit_fell_mask] += 1
        
        profit_rose_mask = (profit >= prev_profit) & active_mask
        self.firms['ticks_of_falling_profit'][profit_rose_mask] = 0

        # --- Step 2: Choose Mode (Exploration vs. Exploitation) ---
        crisis_threshold = self.config['profit_crisis_threshold']
        crisis_mask = (self.firms['ticks_of_falling_profit'] > crisis_threshold) & active_mask
        normal_mask = ~crisis_mask & active_mask

        # --- Step 3: Execute Logic Based on Mode ---
        
        # --- Mode A: CRISIS / EXPLORATION ---
        if np.any(crisis_mask):
            self.tick_events['crisis_triggers'] += np.sum(crisis_mask)
            for firm_id in np.where(crisis_mask)[0]:
                # 1. Drastic Price Cut
                cut_rate = self.config['crisis_price_cut_rate']
                self.firms['price'][firm_id] *= (1 - cut_rate)
                self.firms['last_price_direction'][firm_id] = -1 # Force downward exploration
                
                # 2. Aggressive Workforce Reduction
                # Cut target workforce by a significant margin to reduce costs
                new_target = int(self.firms['num_workers'][firm_id] * 0.75)
                self.firms['target_num_workers'][firm_id] = max(self.config['min_target_workers'], new_target)

                # 3. Reset Crisis Counter
                self.firms['ticks_of_falling_profit'][firm_id] = 0

        # --- Mode B: NORMAL / EXPLOITATION ---
        if np.any(normal_mask):
            # --- Update Stability Counter ---
            # Increment for profitable firms, reset for unprofitable ones.
            profitable_mask = (self.firms['profit_last_tick'] > 0) & normal_mask
            self.firms['ticks_of_stable_profit'][profitable_mask] += 1
            unprofitable_mask = (self.firms['profit_last_tick'] <= 0) & normal_mask
            self.firms['ticks_of_stable_profit'][unprofitable_mask] = 0

            # 1. Make Incremental Price Adjustments
            adj_rate = self.config['price_adjustment_rate']
            
            # If profit rose, continue last direction
            profit_grew_mask = (profit > prev_profit) & normal_mask
            increase_mask = (self.firms['last_price_direction'] == 1) & profit_grew_mask
            self.firms['price'][increase_mask] *= (1 + adj_rate)
            decrease_mask = (self.firms['last_price_direction'] == -1) & profit_grew_mask
            self.firms['price'][decrease_mask] *= (1 - adj_rate)

            # --- Calculate Smoothed Average Sales ---
            # Firms base strategic decisions on the trend, not single-tick noise.
            average_sales = np.mean(self.firm_sales_history, axis=1)

            # If profit was stable, use inventory as a tie-breaker
            profit_stable_mask = (profit == prev_profit) & normal_mask
            ticks_of_sales_to_hold = self.config['target_inventory_production_ticks_factor']
            target_inv = average_sales * ticks_of_sales_to_hold
            
            inv_increase_mask = (self.firms['inventory'] < target_inv) & profit_stable_mask
            self.firms['price'][inv_increase_mask] *= (1 + adj_rate)
            self.firms['last_price_direction'][inv_increase_mask] = 1

            inv_decrease_mask = (self.firms['inventory'] > target_inv) & profit_stable_mask
            self.firms['price'][inv_decrease_mask] *= (1 - adj_rate)
            self.firms['last_price_direction'][inv_decrease_mask] = -1

            # 2. Adjust Workforce Target Based on Inventory, Sales, and Ambition
            # First, calculate the conservative target based on inventory needs using SMOOTHED sales data.
            ticks_of_sales_to_hold = self.config['target_inventory_production_ticks_factor']
            desired_inventory = average_sales[normal_mask] * ticks_of_sales_to_hold
            current_inventory = self.firms['inventory']
            production_need = desired_inventory - current_inventory
            
            production_per_worker = self.config['production_per_worker']
            new_target_workers = np.ceil(np.maximum(0, production_need) / production_per_worker).astype(int)
            
            # If inventory is in surplus, target is minimum.
            surplus_mask = (production_need <= 0) & normal_mask
            new_target_workers[surplus_mask] = self.config['min_target_workers']

            # --- AMBITION LOGIC ---
            # If a firm has been stable for a long time, it may attempt to expand.
            ambition_threshold = self.config['ambition_threshold']
            ambitious_mask = (self.firms['ticks_of_stable_profit'] > ambition_threshold) & normal_mask
            if np.any(ambitious_mask):
                self.tick_events['ambition_triggers'] += np.sum(ambitious_mask)
                current_workers = self.firms['num_workers'][ambitious_mask]
                # Expand by 20% or at least 1 worker, whichever is greater.
                expansion_targets = np.maximum(np.ceil(current_workers * 1.2).astype(int), current_workers + 1)
                # This ambitious target OVERWRITES the conservative one.
                new_target_workers[ambitious_mask] = expansion_targets
                
                for firm_id in np.where(ambitious_mask)[0]:
                    logger.info(
                        "FIRM STRATEGY: Firm %d is stable. Experimenting with expansion to %d workers.",
                        firm_id, new_target_workers[firm_id]
                    )
                # Reset counter to prevent continuous expansion.
                self.firms['ticks_of_stable_profit'][ambitious_mask] = 0

            # --- PROFITABILITY GATEKEEPER ---
            # An unprofitable firm cannot hire. It can only maintain or downsize.
            unprofitable_mask = (self.firms['profit_last_tick'] < 0) & normal_mask
            if np.any(unprofitable_mask):
                current_workers = self.firms['num_workers'][unprofitable_mask]
                # Cap the target at the current number of workers.
                new_target_workers[unprofitable_mask] = np.minimum(new_target_workers[unprofitable_mask], current_workers)
            
            # --- BUDGETARY CONSTRAINT ---
            # A firm cannot set a target that requires hiring more workers than it can afford.
            budget_rate = self.config['expansion_budget_rate']
            capital_for_expansion = self.firms['balance'][normal_mask] * budget_rate
            
            # Define production constants locally for cost calculation
            raw_material_cost = self.config['raw_material_cost_per_unit']
            production_per_worker = self.config['production_per_worker']

            # Estimate the cost of a single new hire for one tick (wage + materials)
            cost_per_new_hire = self.firms['wage_rate'][normal_mask] + (raw_material_cost * production_per_worker)
            # Avoid division by zero if cost is somehow zero
            cost_per_new_hire[cost_per_new_hire == 0] = 1 
            
            affordable_new_hires = (capital_for_expansion / cost_per_new_hire).astype(int)
            
            current_workers = self.firms['num_workers'][normal_mask]
            max_affordable_target = current_workers + affordable_new_hires
            
            # Cap the final target at what is affordable
            final_target = np.minimum(new_target_workers[normal_mask], max_affordable_target)

            self.firms['target_num_workers'][normal_mask] = np.maximum(self.config['min_target_workers'], final_target)

        # --- Final Price Floor Enforcement ---
        # A firm is forbidden from selling a product for less than its marginal cost.
        # This is the absolute floor for any price adjustment.
        old_prices_for_floor_check = self.firms['price'].copy()
        
        raw_material_cost = self.config['raw_material_cost_per_unit']
        prod_per_worker = self.config['production_per_worker']
        marginal_cost = raw_material_cost + (self.firms['wage_rate'] / prod_per_worker)
        
        price_floor_mask = (self.firms['price'] < marginal_cost) & active_mask
        if np.any(price_floor_mask):
            self.firms['price'][price_floor_mask] = marginal_cost[price_floor_mask]
            for firm_id in np.where(price_floor_mask)[0]:
                logger.info(
                    "FIRM STRATEGY: Firm %d price adjustment from %.2f blocked by production cost floor of %.2f.",
                    firm_id, old_prices_for_floor_check[firm_id], marginal_cost[firm_id]
                )

        # --- Step 4: Update Memory for Next Tick ---
        self.firms['previous_profit'] = self.firms['profit_last_tick']

    def _banking_phase(self):
        """Firms service their debt and may take loans from the bank."""
        if self.config.get('N_B', 0) == 0: return
        
        logger.debug("Start Banking Phase")

        # --- Debt Servicing ---
        firms_with_debt = np.where(self.firms['debt'] > 0)[0]
        if len(firms_with_debt) > 0:
            interest_payment = self.firms['debt'] * self.config['interest_rate']
            principal_payment = self.firms['debt'] * self.config['loan_repayment_rate']
            total_payment = interest_payment + principal_payment

            # Deduct payments from firms with debt
            self.firms['balance'][firms_with_debt] -= total_payment[firms_with_debt]
            self.firms['debt'][firms_with_debt] -= principal_payment[firms_with_debt]
            
            # Transfer collected payments to the bank
            total_collected = np.sum(total_payment[firms_with_debt])
            self.banks['balance'][0] += total_collected
            
            for firm_id in firms_with_debt:
                logger.info(
                    "Firm %d paid $%.2f interest and $%.2f principal. Remaining debt: $%.2f",
                    firm_id, interest_payment[firm_id], principal_payment[firm_id], self.firms['debt'][firm_id]
                )
            
            if total_collected > 0:
                logger.info(
                    "Bank collected a total of $%.2f in debt payments this tick. New balance: $%.2f",
                    total_collected, self.banks['balance'][0]
                )

        # --- Loan Issuance (DISABLED) ---
        # This logic has been removed to prevent infinite debt loops and enable firm failure.
        # Firms must now manage their capital without automatic bailouts.