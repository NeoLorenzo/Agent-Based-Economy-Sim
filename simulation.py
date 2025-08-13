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

class Simulation:
    """
    Manages the overall simulation state and tick loop using NumPy for performance.
    Agent data is stored in structured NumPy arrays rather than individual objects.
    """
    def __init__(self, config):
        self.config = config
        
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
            ('num_workers', 'i4'),
            ('target_num_workers', 'i4'),
            ('failed_to_hire_last_tick', '?') # Boolean flag
        ]
        self.firms = np.zeros(self.config['N_F'], dtype=firm_dtype)
        
        # --- Initialize Firm data ---
        self.firms['balance'] = self.config['firm_initial_capital']
        self.firms['price'] = self.config['p']
        self.firms['wage_rate'] = self.config['wage_rate']
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
        # For now, let's assume firms want to hire a proportional share of the workforce.
        # This is an initial target; their actual hiring will be constrained by revenue.
        initial_target_workers = math.ceil(self.config['N_H'] / self.config['N_F'])
        self.firms['target_num_workers'] = initial_target_workers
        
        # --- Define data structure for Banks ---
        bank_dtype = [('balance', 'f8')]
        self.banks = np.zeros(self.config.get('N_B', 0), dtype=bank_dtype)
        # The bank has infinite capital for now; we represent this with a very large number.
        self.banks['balance'] = 1e12 
        
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
        Returns a list of transactions for visualization and a summary for logging.
        """
        self._current_tick = current_tick
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

        return transactions, summary

    def _production_phase(self, summary):
        """Firms produce new goods based on their workforce."""
        logger.debug("Start Production Phase")
        
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
        self.firms['inventory'][can_afford_mask] += produced_quantity[can_afford_mask]
        
        total_produced = np.sum(produced_quantity[can_afford_mask])
        total_cost = np.sum(production_cost[can_afford_mask])
        
        if total_produced > 0:
            logger.info(
                "Total production this tick: %d units at a total raw material cost of $%.2f.",
                total_produced, total_cost
            )
        
        # Update summary (renaming fields for clarity)
        summary['total_production_units'] = total_produced
        summary['total_production_cost'] = total_cost

    def _shopping_phase(self, transactions, summary):
        """Households choose firms and purchase goods."""
        logger.debug("Start Shopping Phase")
        
        if self.config.get('enable_proximity_choice', False):
            diffs = self.household_pos_array[:, np.newaxis, :] - self.firm_pos_array[np.newaxis, :, :]
            dist_sq = np.sum(diffs**2, axis=2)
            closest_firm_indices = np.argsort(dist_sq, axis=1)
            n_to_consider = self.config.get('shopping_firms_to_consider', 1)
            candidate_indices = closest_firm_indices[:, :n_to_consider]
            candidate_prices = self.firms['price'][candidate_indices]
            cheapest_candidate_idx = np.argmin(candidate_prices, axis=1)
            chosen_firm_ids = candidate_indices[np.arange(self.config['N_H']), cheapest_candidate_idx]
        else:
            firm_ids_list = list(range(self.config['N_F']))
            chosen_firm_ids = np.array([random.choice(firm_ids_list) for _ in range(self.config['N_H'])])
        
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
                
                summary['total_sales_units'] += sold_quantity
                summary['total_sales_volume'] += amount
                transactions.append({'type': 'spending', 'from_id': hh_id, 'to_id': firm_id, 'amount': amount})

    def _payday_phase(self, transactions, summary):
        """Firms pay wages to their employees."""
        logger.debug("Start Payday Phase")
        
        self.firms['balance'] += self.firms['revenue_this_tick']
        total_payout = self.firms['num_workers'] * self.firms['wage_rate']
        
        self.firms['balance'] -= total_payout
        self.firms['revenue_this_tick'][:] = 0
        
        num_workers = self.firms['num_workers']
        wage_per_worker = np.divide(total_payout, num_workers, out=np.zeros_like(total_payout), where=num_workers!=0)
        
        employed_mask = self.households['employer_id'] != -1
        employer_ids = self.households['employer_id'][employed_mask]
        self.households['balance'][employed_mask] += wage_per_worker[employer_ids]
        
        for firm_id, payout in enumerate(total_payout):
            if payout > 0:
                worker_ids = np.where(self.households['employer_id'] == firm_id)[0]
                individual_wage = wage_per_worker[firm_id]
                for worker_id in worker_ids:
                    transactions.append({'type': 'wage', 'from_id': firm_id, 'to_id': int(worker_id), 'amount': individual_wage})
        
        summary['total_wages_paid'] = np.sum(total_payout)
        return total_payout

    def _labor_market_phase(self, total_payout, summary):
        """Firms hire and fire workers based on economic conditions."""
        logger.debug("Start Labor Market Phase")

        # Firing Logic
        layoff_threshold = total_payout * self.config['firm_layoff_capital_threshold_factor']
        firms_that_should_fire = np.where((self.firms['balance'] < layoff_threshold) & (self.firms['num_workers'] > 0))[0]
        for firm_id in firms_that_should_fire:
            employee_indices = np.where(self.households['employer_id'] == firm_id)[0]
            if len(employee_indices) > 0:
                layoff_candidate_idx = np.random.choice(employee_indices, size=min(1, len(employee_indices)), replace=False)
                self.households['employer_id'][layoff_candidate_idx] = -1
                self.firms['num_workers'][firm_id] -= len(layoff_candidate_idx)
                logger.info("Firm %d laid off %d worker(s) due to low capital.", firm_id, len(layoff_candidate_idx))

        # Hiring Logic
        self.firms['failed_to_hire_last_tick'][:] = False
        unemployed_hh_indices = np.where(self.households['employer_id'] == -1)[0]
        
        if len(unemployed_hh_indices) > 0:
            hiring_revenue_threshold = total_payout * self.config['firm_hiring_revenue_threshold_factor']
            hiring_firms_mask = (self.firms['balance'] > hiring_revenue_threshold) & (self.firms['num_workers'] < self.firms['target_num_workers'])
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
                    logger.info("Firm %d hired 1 new worker (Wage: %.2f).", firm_id, job['wage'])

        # Job Switching Logic for Employed Households
        employed_mask = self.households['employer_id'] != -1
        employed_indices = np.where(employed_mask)[0]
        np.random.shuffle(employed_indices) # Randomize order to prevent bias
        
        job_switching_threshold = self.config.get('job_switching_wage_threshold', 1.01)

        for hh_id in employed_indices:
            current_employer_id = self.households['employer_id'][hh_id]
            current_wage = self.firms['wage_rate'][current_employer_id]
            
            # Find the best alternative job offer
            potential_employers = np.where(self.firms['wage_rate'] > current_wage * job_switching_threshold)[0]
            
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
                
                logger.info(
                    "Household %d switched employer from Firm %d to Firm %d for a higher wage (New: %.2f, Old: %.2f).",
                    hh_id, current_employer_id, best_new_employer_id, new_wage, old_wage
                )

        summary['unemployment_rate'] = (np.count_nonzero(self.households['employer_id'] == -1) / self.config['N_H']) * 100

    def _firm_adjustment_phase(self, summary):
        """Firms adjust prices based on inventory and wages based on unemployment."""
        logger.debug("Start Firm Adjustment Phase")

        # Dynamic Target Inventory Calculation
        # A firm's target inventory is to hold a buffer equivalent to a certain number of ticks of its own production.
        prod_rate = self.firms['num_workers'] * self.config['production_per_worker']
        ticks_of_prod_to_hold = self.config['target_inventory_production_ticks_factor']
        self.firms['target_inventory'] = prod_rate * ticks_of_prod_to_hold
        logger.debug(
            "Firms updated target inventories. Example Firm 0: Target=%d (based on %d workers)",
            self.firms['target_inventory'][0], self.firms['num_workers'][0]
        )
        
        # Price Adjustments
        upper_thresh = self.firms['target_inventory'] * self.config['inventory_upper_threshold_factor']
        lower_thresh = self.firms['target_inventory'] * self.config['inventory_lower_threshold_factor']
        old_prices = self.firms['price'].copy()
        adj_rate = self.config['price_adjustment_rate']
        self.firms['price'][self.firms['inventory'] < lower_thresh] *= (1 + adj_rate)
        self.firms['price'][self.firms['inventory'] > upper_thresh] *= (1 - adj_rate)
        if len(np.where(old_prices != self.firms['price'])[0]) > 0:
            logger.info("%d firms adjusted their prices this tick.", len(np.where(old_prices != self.firms['price'])[0]))

        # Competitive Wage Adjustments
        increase_rate = self.config.get('competitive_wage_increase_rate', 0.02)

        # Condition 1: Proactive wage increase by profitable firms
        current_wage_bill = self.firms['num_workers'] * self.firms['wage_rate']
        profitability_threshold = current_wage_bill * self.config['firm_hiring_revenue_threshold_factor']
        profitable_firms = (self.firms['balance'] > profitability_threshold)

        # Condition 2: Reactive wage increase from losing an employee
        lost_employee_firms = self.firms['failed_to_hire_last_tick']

        # Combine conditions: A firm will raise wages if it's profitable OR it lost an employee
        firms_raising_wages = np.where(profitable_firms | lost_employee_firms)[0]

        for firm_id in firms_raising_wages:
            old_wage = self.firms['wage_rate'][firm_id]
            new_wage = old_wage * (1 + increase_rate)
            self.firms['wage_rate'][firm_id] = new_wage
            
            # Log the reason for the wage increase
            if profitable_firms[firm_id] and not lost_employee_firms[firm_id]:
                reason = "is profitable, proactively"
            elif lost_employee_firms[firm_id]:
                reason = "lost an employee,"
            else: # Should not happen but for completeness
                reason = "is adjusting"

            logger.info(
                "Firm %d %s increasing wage from %.2f to %.2f.",
                firm_id, reason, old_wage, new_wage
            )

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

        # --- Loan Issuance ---
        lookahead = self.config['loan_trigger_lookahead_ticks']
        future_expenses = (self.firms['num_workers'] * self.firms['wage_rate']) * lookahead
        needs_loan = np.where((self.firms['balance'] < future_expenses) & (self.firms['balance'] > 0))[0]

        if len(needs_loan) > 0:
            multiplier = self.config['loan_amount_multiplier']
            for firm_id in needs_loan:
                loan_amount = future_expenses[firm_id] * multiplier
                self.firms['balance'][firm_id] += loan_amount
                self.firms['debt'][firm_id] += loan_amount
                logger.info("Firm %d took a loan of %.2f. New total debt is %.2f.", firm_id, loan_amount, self.firms['debt'][firm_id])