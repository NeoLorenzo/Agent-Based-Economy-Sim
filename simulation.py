# simulation.py

import random
import logging
import math

logger = logging.getLogger(__name__)

#======================================
# AGENT DEFINITIONS
#======================================

class Household:
    """Represents a household that consumes goods and provides labor."""
    def __init__(self, id, balance, size):
        self.id = id
        self.balance = float(balance)
        self.size = size
        # self.labor_supply = 1 # Not used in MVP but good to keep in mind
        self.employer_id = None # The ID of the firm that employs this household

    def determine_food_demand(self, food_per_person):
        """Calculates how much food the household wants to buy."""
        return self.size * food_per_person

class Firm:
    """Represents a firm that produces goods and employs households."""
    def __init__(self, id, price, wage_rate, production_per_tick):
        self.id = id
        self.balance = 0.0
        self.price = float(price)
        self.wage_rate = float(wage_rate)
        self.production_per_tick = production_per_tick
        self.inventory = 0
        self.worker_ids = [] # A list of household IDs
        self.revenue_this_tick = 0.0

    def add_worker(self, household_id):
        """Assigns a household to this firm."""
        self.worker_ids.append(household_id)

    def produce_goods(self):
        """Produces goods and adds them to inventory."""
        self.inventory += self.production_per_tick

    def process_sale(self, requested_quantity):
        """
        Processes a sale request, checking against available inventory.
        Returns the actual quantity sold.
        """
        if requested_quantity <= 0:
            return 0

        if self.inventory <= 0:
            logger.debug("Firm %d is stocked out. Denying sale of %d units.", self.id, requested_quantity)
            return 0

        sold_quantity = min(requested_quantity, self.inventory)
        
        if sold_quantity < requested_quantity:
            logger.debug(
                "Firm %d inventory is %d, but %d were requested. Selling remaining %d.",
                self.id, self.inventory, requested_quantity, sold_quantity
            )

        self.inventory -= sold_quantity
        return sold_quantity

    def receive_payment(self, amount):
        """Collects money from sales."""
        self.revenue_this_tick += amount

    def pay_workers(self, households_dict):
        """
        Pays wages to all its employees and returns a list of transactions.
        """
        # First, update balance with revenue from this tick's sales
        self.balance += self.revenue_this_tick
        self.revenue_this_tick = 0 # Reset for next tick
        
        wage_transactions = []

        if not self.worker_ids:
            return wage_transactions # No workers to pay

        # Calculate the total amount to be paid as wages
        total_payout = self.balance * self.wage_rate
        
        # Avoid division by zero if there are no workers
        if not self.worker_ids:
            return wage_transactions
            
        wage_per_worker = total_payout / len(self.worker_ids)

        # Distribute wages
        for worker_id in self.worker_ids:
            households_dict[worker_id].balance += wage_per_worker
            wage_transactions.append({
                'type': 'wage',
                'from_id': self.id,
                'to_id': worker_id,
                'amount': wage_per_worker
            })

        # Update the firm's balance after paying wages
        self.balance -= total_payout
        
        return wage_transactions

#======================================
# SIMULATION ENGINE
#======================================

class Simulation:
    """Manages the overall simulation state and tick loop."""
    def __init__(self, config, firm_positions=None, household_positions=None):
        self.config = config
        self.firm_positions = firm_positions
        self.household_positions = household_positions
        self.households = {} # Use a dictionary for easy lookup by ID
        self.firms = {}      # Use a dictionary for easy lookup by ID
        self._setup_world()

    def _setup_world(self):
        """Initializes all households and firms based on the config file."""
        logger.info("Setting up the simulation world...")
        # Create Firms
        for i in range(self.config['N_F']):
            self.firms[i] = Firm(
                id=i, 
                price=self.config['p'], 
                wage_rate=self.config['wage_rate'],
                production_per_tick=self.config['firm_production_per_tick']
            )
        logger.debug("Created %d firms.", self.config['N_F'])

        # Get a list of firm IDs to assign workers to
        firm_ids = list(self.firms.keys())

        # Create Households
        initial_balance = self.config['M0'] / self.config['N_H']
        for i in range(self.config['N_H']):
            # Create the household
            self.households[i] = Household(id=i, balance=initial_balance, size=self.config['household_size'])
            
            # Assign the household to a random firm
            employer_firm_id = random.choice(firm_ids)
            self.households[i].employer_id = employer_firm_id
            self.firms[employer_firm_id].add_worker(i)
        logger.debug("Created %d households and assigned them to firms.", self.config['N_H'])
        logger.info("World setup complete.")

    def _get_closest_firm(self, household_id):
        """Finds the firm geographically closest to a given household."""
        if not self.firm_positions or not self.household_positions:
            return None # Should not happen if configured correctly

        hh_pos = self.household_positions[household_id]
        closest_firm = None
        min_dist_sq = float('inf')

        for firm_id, firm_pos in self.firm_positions.items():
            dist_sq = (hh_pos[0] - firm_pos[0])**2 + (hh_pos[1] - firm_pos[1])**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_firm = self.firms[firm_id]
        
        if closest_firm:
            logger.debug(
                "Household %d evaluating firms... Found closest: Firm %d (Distance: %.1f)",
                household_id, closest_firm.id, math.sqrt(min_dist_sq)
            )
        return closest_firm

    def run_one_tick(self):
        """
        Executes one full cycle of the simulation loop.
        Returns a list of transactions that occurred.
        """
        firm_list = list(self.firms.values())
        transactions_this_tick = []

        # 1. Production Phase
        logger.debug("Start Production Phase")
        for f in self.firms.values():
            f.produce_goods()

        # 2. Shopping Phase
        logger.debug("Start Shopping Phase")
        for hh in self.households.values():
            chosen_firm = None
            if self.config.get('enable_proximity_choice', False):
                chosen_firm = self._get_closest_firm(hh.id)
            else:
                # Fallback to original random choice behavior
                chosen_firm = random.choice(firm_list)

            if not chosen_firm:
                logger.warning("Household %d could not choose a firm. Skipping.", hh.id)
                continue
            
            # Household determines what it wants and can afford
            requested_qty = hh.determine_food_demand(self.config['food_per_person'])
            max_affordable_qty = int(hh.balance / chosen_firm.price)
            purchase_request_qty = min(requested_qty, max_affordable_qty)

            # Firm processes the sale based on its inventory
            actual_qty_sold = chosen_firm.process_sale(purchase_request_qty)

            if actual_qty_sold > 0:
                # A transaction occurred, record it
                amount = actual_qty_sold * chosen_firm.price
                hh.balance -= amount # Manually update balance
                chosen_firm.receive_payment(amount)
                transactions_this_tick.append({
                    'type': 'spending',
                    'from_id': hh.id,
                    'to_id': chosen_firm.id,
                    'amount': amount
                })
                logger.debug("Transaction: Household %d -> Firm %d, Amount: %.2f, Qty: %d", hh.id, chosen_firm.id, amount, actual_qty_sold)

        # 2. Payday Phase
        logger.debug("Start Payday Phase")
        for f in self.firms.values():
            wage_transactions = f.pay_workers(self.households)
            transactions_this_tick.extend(wage_transactions) # Add wage payments to the list
            
        return transactions_this_tick