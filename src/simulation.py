# src/simulation.py

"""
================================================================================
Simulation State Manager
================================================================================
This module contains the Simulation class, which is responsible for initializing
and managing the state of the simulation world (agents, environment, etc.).
It does not contain any core economic logic itself, but instead orchestrates
the series of systems that operate on its state.
================================================================================
"""

import logging
import numpy as np
import collections
import random

from src import constants as C
from src.systems import (
    production_system,
    market_system,
    payday_system,
    profit_distribution_system,
    labor_system,
    strategy_system,
    banking_system
)

logger = logging.getLogger(__name__)

class Simulation:
    """
    Manages the overall simulation state and orchestrates the systems that run the tick loop.
    Agent data is stored in structured NumPy arrays for performance.
    """
    def __init__(self, config):
        self.config = config
        self.tick_events = collections.Counter()
        self.firm_owner_map = {}
        
        self.firm_positions = {}
        self.household_positions = {}
        self.bank_positions = {}
        self.firm_pos_array = np.array([])
        self.household_pos_array = np.array([])
        self.bank_pos_array = np.array([])
        self._calculate_agent_positions()

        self.households = None
        self.firms = None
        self.banks = None
        self._setup_world()

    def _calculate_agent_positions(self):
        """
        Calculates and stores non-overlapping screen positions for all agents.
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

        self.firm_pos_array = np.array(list(self.firm_positions.values()))
        self.household_pos_array = np.array(list(self.household_positions.values()))
        self.bank_pos_array = np.array(list(self.bank_positions.values()))

    def _setup_world(self):
        """Initializes all agent data in structured NumPy arrays."""
        logger.info("Setting up the simulation world with NumPy arrays...")
        
        firm_dtype = [
            ('owner_id', 'i4'),
            ('balance', 'f8'), ('debt', 'f8'), ('price', 'f8'), ('wage_rate', 'f8'),
            ('inventory', 'i4'), ('target_inventory', 'i4'), ('revenue_this_tick', 'f8'),
            ('units_sold_last_tick', 'i4'), ('production_cost_last_tick', 'f8'),
            ('wages_paid_last_tick', 'f8'), ('profit_last_tick', 'f8'),
            ('previous_profit', 'f8'), ('ticks_of_falling_profit', 'i4'),
            ('ticks_of_stable_profit', 'i4'), ('last_price_direction', 'i4'),
            ('num_workers', 'i4'), ('target_num_workers', 'i4'),
            ('failed_to_hire_last_tick', '?'), ('is_bankrupt', '?')
        ]
        self.firms = np.zeros(self.config['N_F'], dtype=firm_dtype)
        
        self.firms['balance'] = self.config['firm_initial_capital']
        self.firms['price'] = self.config['p']
        self.firms['wage_rate'] = self.config['wage_rate']
        self.firms['last_price_direction'] = 1
        
        household_dtype = [('balance', 'f8'), ('size', 'i4'), ('employer_id', 'i4')]
        self.households = np.zeros(self.config['N_H'], dtype=household_dtype)

        self.households['balance'] = self.config['M0'] / self.config['N_H']
        self.households['size'] = self.config['household_size']
        self.households['employer_id'] = -1
        
        diffs = self.firm_pos_array[:, np.newaxis, :] - self.household_pos_array[np.newaxis, :, :]
        dist_sq = np.sum(diffs**2, axis=2)
        owner_ids = np.argmin(dist_sq, axis=1)

        for firm_id, owner_id in enumerate(owner_ids):
            self.firms['owner_id'][firm_id] = owner_id
            self.households['employer_id'][owner_id] = firm_id
            self.firm_owner_map[firm_id] = owner_id

        self.firms['num_workers'] = 1
        self.firms['target_num_workers'] = 1
        
        bank_dtype = [('balance', 'f8')]
        self.banks = np.zeros(self.config.get('N_B', 0), dtype=bank_dtype)
        self.banks['balance'] = 1e12

        history_ticks = self.config.get('sales_history_ticks', 10)
        self.firm_sales_history = np.zeros((self.config['N_F'], history_ticks), dtype=int)
        
        logger.info("World setup complete.")

    def update_and_get_firm_data_for_render(self):
        """Updates and returns historical data for visualization."""
        if not hasattr(self, '_inventory_history'):
            self._inventory_history = {i: [] for i in range(self.config['N_F'])}
            self._price_history = {i: [] for i in range(self.config['N_F'])}
            self._capital_history = {i: [] for i in range(self.config['N_F'])}
            self._employee_history = {i: [] for i in range(self.config['N_F'])}
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
        Orchestrates the systems that execute one full cycle of the simulation.
        """
        self._current_tick = current_tick
        self.tick_events.clear()
        transactions = []
        summary = {
            'total_production_units': 0, 'total_production_cost': 0.0,
            'total_sales_volume': 0.0, 'total_sales_units': 0,
            'total_wages_paid': 0.0, 'unemployment_rate': 0.0,
            'total_dividends_paid': 0.0
        }

        # --- ECONOMIC PHASES AS MODULAR SYSTEMS ---
        production_system.update(self, summary)
        market_system.update(self, transactions, summary)
        total_payout = payday_system.update(self, transactions, summary)
        profit_distribution_system.update(self, transactions, summary)
        labor_system.update(self, total_payout, summary)
        strategy_system.update(self, summary)
        banking_system.update(self)

        return transactions, summary, self.tick_events