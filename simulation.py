# simulation.py

import random
import logging
import math
import numpy as np

logger = logging.getLogger(__name__)

#======================================
# SIMULATION ENGINE
#======================================

class Simulation:
    """
    Manages the overall simulation state and tick loop using NumPy for performance.
    Agent data is stored in structured NumPy arrays rather than individual objects.
    """
    def __init__(self, config, firm_positions=None, household_positions=None):
        self.config = config
        
        # Convert position dicts to NumPy arrays for vectorized calculations
        self.firm_pos_array = np.array(list(firm_positions.values()))
        self.household_pos_array = np.array(list(household_positions.values()))
        
        self.households = None # Will be a NumPy structured array
        self.firms = None      # Will be a NumPy structured array
        self._setup_world()

    def _setup_world(self):
        """Initializes all agent data in structured NumPy arrays."""
        logger.info("Setting up the simulation world with NumPy arrays...")
        
        # --- Define data structure for Firms ---
        firm_dtype = [
            ('balance', 'f8'),
            ('price', 'f8'),
            ('wage_rate', 'f8'),
            ('production_per_tick', 'i4'),
            ('inventory', 'i4'),
            ('target_inventory', 'i4'),
            ('revenue_this_tick', 'f8'),
            ('num_workers', 'i4'),
            ('target_num_workers', 'i4')
        ]
        self.firms = np.zeros(self.config['N_F'], dtype=firm_dtype)
        
        # --- Initialize Firm data ---
        self.firms['balance'] = self.config['firm_initial_capital']
        self.firms['price'] = self.config['p']
        self.firms['wage_rate'] = self.config['wage_rate']
        self.firms['production_per_tick'] = self.config['firm_production_per_tick']
        self.firms['target_inventory'] = self.firms['production_per_tick'] * self.config['target_inventory_level_factor']
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

        for i in range(self.config['N_F']):
            self._inventory_history[i].append(self.firms['inventory'][i])
            self._price_history[i].append(self.firms['price'][i])
            self._capital_history[i].append(self.firms['balance'][i])
            self._employee_history[i].append(self.firms['num_workers'][i])

        return self._inventory_history, self._price_history, self._capital_history, self._employee_history

    def run_one_tick(self):
        """
        Executes one full cycle of the simulation using vectorized operations.
        Returns a list of transactions for visualization and a summary for logging.
        """
        transactions_this_tick = []
        tick_summary = {
            'total_restock_cost': 0.0,
            'total_restock_units': 0,
            'total_sales_volume': 0.0,
            'total_sales_units': 0,
            'total_wages_paid': 0.0,
            'unemployment_rate': 0.0
        }

        # 1. Wholesale Restocking Phase (Vectorized)
        logger.debug("Start Wholesale Restocking Phase")
        wholesale_price = self.config['wholesale_price']
        
        needed_quantity = self.firms['target_inventory'] - self.firms['inventory']
        needed_quantity[needed_quantity < 0] = 0
        
        affordable_quantity = (self.firms['balance'] / wholesale_price).astype(int)
        
        ordered_quantity = np.minimum(needed_quantity, affordable_quantity)
        
        order_cost = ordered_quantity * wholesale_price
        self.firms['balance'] -= order_cost
        self.firms['inventory'] += ordered_quantity
        
        # Aggregate restocking data for the summary
        tick_summary['total_restock_units'] = np.sum(ordered_quantity)
        tick_summary['total_restock_cost'] = np.sum(order_cost)

        # 2. Shopping Phase
        logger.debug("Start Shopping Phase")
        
        # --- Determine which firm each household will shop at (Vectorized) ---
        if self.config.get('enable_proximity_choice', False):
            # Households consider a few of the closest firms, then choose the cheapest among them.
            # This models realistic shopping behavior where consumers balance convenience and price.
            
            # 1. Calculate squared distances from every household to every firm.
            diffs = self.household_pos_array[:, np.newaxis, :] - self.firm_pos_array[np.newaxis, :, :]
            dist_sq = np.sum(diffs**2, axis=2) # Shape: (N_H, N_F)
            
            # 2. Get the indices of the N closest firms for each household.
            # `np.argsort` gives us the indices that would sort the array.
            closest_firm_indices = np.argsort(dist_sq, axis=1)
            
            # 3. Limit the choice to the N closest firms specified in the config.
            n_to_consider = self.config.get('shopping_firms_to_consider', 1)
            candidate_indices = closest_firm_indices[:, :n_to_consider] # Shape: (N_H, n_to_consider)
            
            # 4. Get the prices of these candidate firms.
            candidate_prices = self.firms['price'][candidate_indices] # Shape: (N_H, n_to_consider)
            
            # 5. Find the index of the minimum price *within the candidates*.
            # This gives us an index from 0 to n_to_consider-1 for each household.
            cheapest_candidate_idx = np.argmin(candidate_prices, axis=1) # Shape: (N_H,)
            
            # 6. Use the index from step 5 to select the final firm ID from our candidate list.
            # This is the core of the advanced indexing to get the final result.
            chosen_firm_ids = candidate_indices[np.arange(self.config['N_H']), cheapest_candidate_idx]

        else:
            # Fallback to simple random choice if proximity is disabled.
            firm_ids_list = list(range(self.config['N_F']))
            chosen_firm_ids = np.array([random.choice(firm_ids_list) for _ in range(self.config['N_H'])])
        
        # --- Calculate purchase requests for all households (Vectorized) ---
        requested_qty = self.households['size'] * self.config['food_per_person']
        firm_prices = self.firms['price'][chosen_firm_ids]
        max_affordable_qty = (self.households['balance'] / firm_prices).astype(int)
        purchase_request_qty = np.minimum(requested_qty, max_affordable_qty)

        # --- Process sales iteratively (to handle inventory correctly) ---
        # This loop is kept to prevent race conditions where multiple households
        # buy from the same firm's inventory simultaneously in a vectorized op.
        for hh_id in range(self.config['N_H']):
            firm_id = chosen_firm_ids[hh_id]
            request = purchase_request_qty[hh_id]

            if request <= 0:
                continue

            firm_inventory = self.firms['inventory'][firm_id]
            if firm_inventory <= 0:
                continue

            sold_quantity = min(request, firm_inventory)
            
            # Update inventory and balances
            amount = sold_quantity * self.firms['price'][firm_id]
            self.households['balance'][hh_id] -= amount
            self.firms['inventory'][firm_id] -= sold_quantity
            self.firms['revenue_this_tick'][firm_id] += amount
            
            # Aggregate sales data
            tick_summary['total_sales_units'] += sold_quantity
            tick_summary['total_sales_volume'] += amount

            transactions_this_tick.append({
                'type': 'spending', 'from_id': hh_id, 'to_id': firm_id, 'amount': amount
            })

        # 3. Payday Phase (Vectorized)
        logger.debug("Start Payday Phase")
        
        # Bank revenue before paying wages
        self.firms['balance'] += self.firms['revenue_this_tick']
        
        # Calculate total wage payout per firm based on a fixed wage per employee
        total_payout = self.firms['num_workers'] * self.firms['wage_rate']
        
        # Firms pay wages from their balance
        self.firms['balance'] -= total_payout
        self.firms['revenue_this_tick'][:] = 0 # Reset for next tick
        
        # Calculate wage per worker for each firm, handling firms with no workers
        num_workers = self.firms['num_workers']
        wage_per_worker = np.divide(total_payout, num_workers, out=np.zeros_like(total_payout), where=num_workers!=0)
        
        # Distribute wages only to employed households
        employed_mask = self.households['employer_id'] != -1
        employer_ids = self.households['employer_id'][employed_mask]
        payouts_to_households = wage_per_worker[employer_ids]
        self.households['balance'][employed_mask] += payouts_to_households
        
        # Create wage transaction logs
        for firm_id, payout in enumerate(total_payout):
            if payout > 0:
                # Find all workers for this firm
                worker_ids = np.where(self.households['employer_id'] == firm_id)[0]
                individual_wage = wage_per_worker[firm_id]
                for worker_id in worker_ids:
                    transactions_this_tick.append({
                        'type': 'wage', 'from_id': firm_id, 'to_id': int(worker_id), 'amount': individual_wage
                    })
        
        # Aggregate wage data
        tick_summary['total_wages_paid'] = np.sum(total_payout)

        # 4. Labor Market Phase (Hiring and Firing)
        logger.debug("Start Labor Market Phase")

        # --- Firing Logic ---
        # Firms lay off workers if their capital is too low to support the wage bill from last tick.
        layoff_threshold = total_payout * self.config['firm_layoff_capital_threshold_factor']
        firms_that_should_fire = np.where((self.firms['balance'] < layoff_threshold) & (self.firms['num_workers'] > 0))[0]

        for firm_id in firms_that_should_fire:
            workers_to_fire = 1 # Fire one worker at a time for stability
            
            # Find employees of this firm
            employee_indices = np.where(self.households['employer_id'] == firm_id)[0]
            
            if len(employee_indices) > 0:
                # Choose a random worker to lay off
                layoff_candidate_idx = np.random.choice(employee_indices, size=min(workers_to_fire, len(employee_indices)), replace=False)
                
                # Set them to unemployed
                self.households['employer_id'][layoff_candidate_idx] = -1
                
                num_fired = len(layoff_candidate_idx)
                self.firms['num_workers'][firm_id] -= num_fired
                logger.info("Firm %d laid off %d worker(s) due to low capital.", firm_id, num_fired)

        # --- Hiring Logic ---
        # Firms hire if they have high revenue and are below their target workforce
        unemployed_hh_indices = np.where(self.households['employer_id'] == -1)[0]
        
        if len(unemployed_hh_indices) > 0:
            # Firms hire if their last revenue was high and they have capacity
            hiring_revenue_threshold = total_payout * self.config['firm_hiring_revenue_threshold_factor']
            firms_that_should_hire = np.where((self.firms['balance'] > hiring_revenue_threshold) & (self.firms['num_workers'] < self.firms['target_num_workers']))[0]

            # Shuffle to give firms a random chance to hire first
            np.random.shuffle(firms_that_should_hire)

            for firm_id in firms_that_should_hire:
                # Stop if there are no more unemployed people to hire
                if len(unemployed_hh_indices) == 0:
                    break
                
                # Hire one worker
                worker_to_hire_idx = np.random.choice(unemployed_hh_indices)
                
                self.households['employer_id'][worker_to_hire_idx] = firm_id
                self.firms['num_workers'][firm_id] += 1
                logger.info("Firm %d hired 1 new worker.", firm_id)
                
                # Remove the hired person from the pool of unemployed
                unemployed_hh_indices = np.setdiff1d(unemployed_hh_indices, [worker_to_hire_idx])

        # Update unemployment rate for summary
        num_unemployed = np.count_nonzero(self.households['employer_id'] == -1)
        tick_summary['unemployment_rate'] = (num_unemployed / self.config['N_H']) * 100

        # 5. Firm Adjustment Phase (e.g., Price Changes)
        logger.debug("Start Firm Adjustment Phase")
        
        upper_threshold = self.firms['production_per_tick'] * self.config['inventory_upper_threshold_factor']
        lower_threshold = self.firms['production_per_tick'] * self.config['inventory_lower_threshold_factor']
        
        should_raise_price = self.firms['inventory'] < lower_threshold
        should_lower_price = self.firms['inventory'] > upper_threshold
        
        old_prices = self.firms['price'].copy()
        
        adj_rate = self.config['price_adjustment_rate']
        self.firms['price'][should_raise_price] *= (1 + adj_rate)
        self.firms['price'][should_lower_price] *= (1 - adj_rate)
        
        # Aggregate price change information for logging to avoid spam.
        price_changes = np.where(old_prices != self.firms['price'])[0]
        if len(price_changes) > 0:
            # For a more detailed but still throttled log, you could list a few changes.
            # For now, a simple count is best to adhere to Rule 2.4.
            logger.info(
                "%d firms adjusted their prices this tick.",
                len(price_changes)
            )
            
        return transactions_this_tick, tick_summary