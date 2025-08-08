import random

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

    def place_order_and_pay(self, price):
        """
        Calculates food demand, determines what can be afforded,
        and returns the quantity purchased. Updates balance.
        """
        food_demand = self.determine_food_demand(food_per_person=1) # Using a default from your doc
        cost = food_demand * price

        if self.balance >= cost:
            # Can afford the desired amount
            purchased_quantity = food_demand
            self.balance -= cost
            return purchased_quantity
        else:
            # Cannot afford, buys as much as possible
            purchased_quantity = int(self.balance / price) # floor division
            self.balance -= purchased_quantity * price
            return purchased_quantity

class Firm:
    """Represents a firm that produces goods and employs households."""
    def __init__(self, id, price, wage_rate):
        self.id = id
        self.balance = 0.0
        self.price = float(price)
        self.wage_rate = float(wage_rate)
        self.worker_ids = [] # A list of household IDs
        self.revenue_this_tick = 0.0

    def add_worker(self, household_id):
        """Assigns a household to this firm."""
        self.worker_ids.append(household_id)

    def receive_payment(self, amount):
        """Collects money from sales."""
        self.revenue_this_tick += amount

    def pay_workers(self, households_dict):
        """Pays wages to all its employees."""
        # First, update balance with revenue from this tick's sales
        self.balance += self.revenue_this_tick
        self.revenue_this_tick = 0 # Reset for next tick

        if not self.worker_ids:
            return # No workers to pay

        # Calculate the total amount to be paid as wages
        total_payout = self.balance * self.wage_rate
        wage_per_worker = total_payout / len(self.worker_ids)

        # Distribute wages
        for worker_id in self.worker_ids:
            households_dict[worker_id].balance += wage_per_worker

        # Update the firm's balance after paying wages
        self.balance -= total_payout

#======================================
# SIMULATION ENGINE
#======================================

class Simulation:
    """Manages the overall simulation state and tick loop."""
    def __init__(self, config):
        self.config = config
        self.households = {} # Use a dictionary for easy lookup by ID
        self.firms = {}      # Use a dictionary for easy lookup by ID
        self._setup_world()

    def _setup_world(self):
        """Initializes all households and firms based on the config file."""
        # Create Firms
        for i in range(self.config['N_F']):
            self.firms[i] = Firm(id=i, price=self.config['p'], wage_rate=self.config['wage_rate'])

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

    def run_one_tick(self):
        """
        Executes one full cycle of the simulation loop.
        Returns a list of transactions that occurred.
        """
        firm_list = list(self.firms.values())
        transactions_this_tick = []

        # 1. Shopping Phase
        for hh in self.households.values():
            chosen_firm = random.choice(firm_list)
            purchased_qty = hh.place_order_and_pay(price=chosen_firm.price)

            if purchased_qty > 0:
                # A transaction occurred, record it
                amount = purchased_qty * chosen_firm.price
                chosen_firm.receive_payment(amount)
                transactions_this_tick.append({
                    'from_id': hh.id,
                    'to_id': chosen_firm.id,
                    'amount': amount
                })

        # 2. Payday Phase
        for f in self.firms.values():
            f.pay_workers(self.households)
            
        return transactions_this_tick