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
            ('revenue_this_tick', 'f8'),
            ('num_workers', 'i4')
        ]
        self.firms = np.zeros(self.config['N_F'], dtype=firm_dtype)
        
        # --- Initialize Firm data ---
        self.firms['price'] = self.config['p']
        self.firms['wage_rate'] = self.config['wage_rate']
        self.firms['production_per_tick'] = self.config['firm_production_per_tick']
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
        
        # Assign households to firms and count workers per firm
        # Reverting to `random.choice` in a loop to ensure deterministic
        # behavior identical to the original implementation.
        firm_ids_list = list(range(self.config['N_F']))
        assigned_employers = np.zeros(self.config['N_H'], dtype=int)
        for i in range(self.config['N_H']):
            assigned_employers[i] = random.choice(firm_ids_list)
        
        self.households['employer_id'] = assigned_employers
        
        # Count number of workers for each firm efficiently
        ids, counts = np.unique(assigned_employers, return_counts=True)
        self.firms['num_workers'][ids] = counts
        
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

    def run_one_tick(self):
        """
        Executes one full cycle of the simulation using vectorized operations.
        Returns a list of transactions that occurred.
        """
        transactions_this_tick = []

        # 1. Production Phase (Vectorized)
        logger.debug("Start Production Phase")
        self.firms['inventory'] += self.firms['production_per_tick']

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
            
            transactions_this_tick.append({
                'type': 'spending', 'from_id': hh_id, 'to_id': firm_id, 'amount': amount
            })
            logger.debug("Transaction: Household %d -> Firm %d, Amount: %.2f, Qty: %d", hh_id, firm_id, amount, sold_quantity)

        # 3. Payday Phase (Vectorized)
        logger.debug("Start Payday Phase")
        
        # Calculate total wage payout per firm
        total_payout = self.firms['revenue_this_tick'] * self.firms['wage_rate']
        
        # Update firm balances (revenue is now banked)
        self.firms['balance'] += self.firms['revenue_this_tick'] - total_payout
        self.firms['revenue_this_tick'][:] = 0 # Reset for next tick
        
        # Calculate wage per worker for each firm, handling firms with no workers
        num_workers = self.firms['num_workers']
        wage_per_worker = np.divide(total_payout, num_workers, out=np.zeros_like(total_payout), where=num_workers!=0)
        
        # Distribute wages to all households based on their employer
        payouts_to_households = wage_per_worker[self.households['employer_id']]
        self.households['balance'] += payouts_to_households
        
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

        # 4. Firm Adjustment Phase (e.g., Price Changes)
        logger.debug("Start Firm Adjustment Phase")
        
        # Define inventory thresholds based on production capacity
        upper_threshold = self.firms['production_per_tick'] * self.config['inventory_upper_threshold_factor']
        lower_threshold = self.firms['production_per_tick'] * self.config['inventory_lower_threshold_factor']
        
        # Vectorized conditions for price changes
        should_raise_price = self.firms['inventory'] < lower_threshold
        should_lower_price = self.firms['inventory'] > upper_threshold
        
        # Store old prices for logging
        old_prices = self.firms['price'].copy()
        
        # Apply price adjustments
        adj_rate = self.config['price_adjustment_rate']
        self.firms['price'][should_raise_price] *= (1 + adj_rate)
        self.firms['price'][should_lower_price] *= (1 - adj_rate)
        
        # Log changes where prices were actually modified
        for firm_id in range(self.config['N_F']):
            if old_prices[firm_id] != self.firms['price'][firm_id]:
                logger.info(
                    "Firm %d adjusted price from %.2f to %.2f due to inventory level of %d",
                    firm_id,
                    old_prices[firm_id],
                    self.firms['price'][firm_id],
                    self.firms['inventory'][firm_id]
                )
            
        return transactions_this_tick