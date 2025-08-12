# main.py

import json
import pygame
import sys
import random
import numpy as np
import logging
import collections
import os
import matplotlib.pyplot as plt
from simulation import Simulation
import constants as C
import logging_setup
import visualization as viz # Import the new module

#======================================
# HELPER FUNCTIONS (Application Logic)
#======================================
def calculate_agent_positions(num_firms, num_households):
    """
    Calculates random screen positions for all firms and households, ensuring
    they do not overlap. This uses rejection sampling to find valid positions.
    """
    firm_positions = {}
    hh_positions = {}
    
    total_agents = num_firms + num_households

    min_dist = 5 * (C.AGENT_RADIUS + C.AGENT_OUTLINE_WIDTH)
    min_dist_sq = min_dist ** 2
    
    generated_positions = []

    for _ in range(total_agents):
        while True:
            min_x = C.INVENTORY_GRAPH_X + C.GRAPH_WIDTH + C.SCREEN_PADDING
            x = np.random.randint(min_x, C.SCREEN_WIDTH - C.SCREEN_PADDING)
            y = np.random.randint(C.SCREEN_PADDING, C.SCREEN_HEIGHT - C.SCREEN_PADDING)
            candidate_pos = (x, y)
            
            is_valid = True
            for pos in generated_positions:
                dist_sq = (pos[0] - candidate_pos[0])**2 + (pos[1] - candidate_pos[1])**2
                if dist_sq < min_dist_sq:
                    is_valid = False
                    break
            
            if is_valid:
                generated_positions.append(candidate_pos)
                break

    random.shuffle(generated_positions)

    firm_ids = list(range(num_firms))
    for i in range(num_firms):
        firm_id = firm_ids[i]
        position = generated_positions.pop()
        firm_positions[firm_id] = position

    household_ids = list(range(num_households))
    for i in range(num_households):
        household_id = household_ids[i]
        position = generated_positions.pop()
        hh_positions[household_id] = position
        
    return firm_positions, hh_positions

def update_graph_data(graph_data, sim):
    """Appends the current inventory of each firm to the historical data list."""
    inventories = sim.firms['inventory']
    for firm_id, inventory_value in enumerate(inventories):
        graph_data[firm_id].append(inventory_value)

def update_price_graph_data(price_graph_data, sim):
    """Appends the current price of each firm to the historical data list."""
    prices = sim.firms['price']
    for firm_id, price_value in enumerate(prices):
        price_graph_data[firm_id].append(price_value)

def update_capital_graph_data(capital_graph_data, sim):
    """Appends the current balance of each firm to the historical data list."""
    balances = sim.firms['balance']
    for firm_id, balance_value in enumerate(balances):
        capital_graph_data[firm_id].append(balance_value)

def display_final_graphs(inventory_data, price_data, capital_data):
    """
    Displays the firm inventory, price, and capital history in a Matplotlib window.
    """
    logger = logging.getLogger(__name__)
    logger.info("Displaying final inventory, price, and capital graphs...")

    to_mpl_color = lambda c: tuple(x / 255.0 for x in c)
    plt.style.use('dark_background')
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

    # Plot 1: Inventory
    for i, (firm_id, history) in enumerate(inventory_data.items()):
        color = to_mpl_color(C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)])
        ax1.plot(list(history), label=f"Firm {firm_id}", color=color, linewidth=C.GRAPH_LINE_WIDTH)
    ax1.set_title("Firm Inventory Over Time", fontsize=14)
    ax1.set_ylabel("Inventory", fontsize=10)
    ax1.set_facecolor(to_mpl_color(C.GRAPH_BG_COLOR))
    ax1.grid(True, color=to_mpl_color(C.COLOR_GRID), linestyle='--', linewidth=0.5)
    ax1.legend()

    # Plot 2: Price
    for i, (firm_id, history) in enumerate(price_data.items()):
        color = to_mpl_color(C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)])
        ax2.plot(list(history), label=f"Firm {firm_id}", color=color, linewidth=C.GRAPH_LINE_WIDTH)
    ax2.set_title("Firm Price Over Time", fontsize=14)
    ax2.set_xlabel("Tick", fontsize=10)
    ax2.set_ylabel("Price", fontsize=10)
    ax2.set_facecolor(to_mpl_color(C.GRAPH_BG_COLOR))
    ax2.grid(True, color=to_mpl_color(C.COLOR_GRID), linestyle='--', linewidth=0.5)
    ax2.legend()

    # Plot 3: Capital
    for i, (firm_id, history) in enumerate(capital_data.items()):
        color = to_mpl_color(C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)])
        ax3.plot(list(history), label=f"Firm {firm_id}", color=color, linewidth=C.GRAPH_LINE_WIDTH)
    ax3.set_title("Firm Capital Over Time", fontsize=14)
    ax3.set_xlabel("Tick", fontsize=10)
    ax3.set_ylabel("Capital", fontsize=10)
    ax3.set_facecolor(to_mpl_color(C.GRAPH_BG_COLOR))
    ax3.grid(True, color=to_mpl_color(C.COLOR_GRID), linestyle='--', linewidth=0.5)
    ax3.legend()

    for ax in [ax1, ax2, ax3]:
        axis_color = to_mpl_color(C.GRAPH_AXIS_COLOR)
        tick_color = to_mpl_color(C.GRAPH_FONT_COLOR)
        ax.spines['top'].set_color(axis_color)
        ax.spines['bottom'].set_color(axis_color)
        ax.spines['left'].set_color(axis_color)
        ax.spines['right'].set_color(axis_color)
        ax.tick_params(axis='x', colors=tick_color)
        ax.tick_params(axis='y', colors=tick_color)

    fig.tight_layout()
    try:
        plt.show()
    except Exception as e:
        logger.error("Failed to display Matplotlib graph.", exc_info=True)

#======================================
# MAIN APPLICATION
#======================================
def main():
    context_filter, run_dir, buffering_handler = logging_setup.setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Application starting...")
    
    pygame.init()
    screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
    pygame.display.set_caption("Agent-Based Economy Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(C.FONT_FACE, C.FONT_SIZE)
    
    with open('config.json', 'r') as f:
        config = json.load(f)

    master_seed = config['seed']
    random.seed(master_seed)
    np.random.seed(master_seed)
    logger.info("RNGs seeded with master seed: %d", master_seed)
    
    firm_positions, household_positions = calculate_agent_positions(
        config['N_F'], config['N_H']
    )

    sim = Simulation(config, firm_positions, household_positions)
    
    inventory_graph_data = {firm_id: [] for firm_id in range(len(sim.firms))}
    price_graph_data = {firm_id: [] for firm_id in range(len(sim.firms))}
    capital_graph_data = {firm_id: [] for firm_id in range(len(sim.firms))}
    
    active_particles = []
    tick_counter = 0
    running = True
    time_per_tick = 1000.0 / config['ticks_per_second']
    time_since_last_tick = 0.0
    
    try:
        logger.info("Starting main simulation loop...")
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False

            delta_time = clock.tick(C.FPS)
            time_since_last_tick += delta_time

            if time_since_last_tick >= time_per_tick:
                time_since_last_tick -= time_per_tick
                context_filter.tick = tick_counter
                
                transactions, summary = sim.run_one_tick()
                logger.info(
                    "Tick %d Summary: Sales: $%.2f (%d units), Wages: $%.2f, Restock: $%.2f (%d units)",
                    tick_counter,
                    summary['total_sales_volume'],
                    summary['total_sales_units'],
                    summary['total_wages_paid'],
                    summary['total_restock_cost'],
                    summary['total_restock_units']
                )

                update_graph_data(inventory_graph_data, sim)
                update_price_graph_data(price_graph_data, sim)
                update_capital_graph_data(capital_graph_data, sim)
                
                for trans in transactions:
                    start_pos, end_pos, color = None, None, None
                    if trans['type'] == 'spending':
                        start_pos, end_pos, color = household_positions.get(trans['from_id']), firm_positions.get(trans['to_id']), C.COLOR_MONEY
                    elif trans['type'] == 'wage':
                        start_pos, end_pos, color = firm_positions.get(trans['from_id']), household_positions.get(trans['to_id']), C.COLOR_WAGE
                    if start_pos and end_pos:
                        active_particles.append(viz.Particle(start_pos, end_pos, color))
                
                tick_counter += 1

            # --- Drawing is now delegated to the visualization module ---
            screen.fill(C.COLOR_BACKGROUND)
            viz.draw_grid(screen)
            
            viz.draw_graph(screen, inventory_graph_data, font, C.INVENTORY_GRAPH_X, C.INVENTORY_GRAPH_Y, C.GRAPH_WIDTH, C.GRAPH_HEIGHT, "Firm Inventory")
            viz.draw_graph(screen, price_graph_data, font, C.PRICE_GRAPH_X, C.PRICE_GRAPH_Y, C.GRAPH_WIDTH, C.GRAPH_HEIGHT, "Firm Price")
            viz.draw_graph(screen, capital_graph_data, font, C.CAPITAL_GRAPH_X, C.CAPITAL_GRAPH_Y, C.GRAPH_WIDTH, C.GRAPH_HEIGHT, "Firm Capital")
            
            viz.draw_agent_shadows(screen, firm_positions)
            viz.draw_agent_shadows(screen, household_positions)
            
            for particle in active_particles:
                particle.update()
                particle.draw(screen)
            
            viz.draw_agent_bodies(screen, firm_positions, C.COLOR_FIRM)
            viz.draw_agent_bodies(screen, household_positions, C.COLOR_HOUSEHOLD)
                
            active_particles = [p for p in active_particles if not p.finished]
            
            pygame.display.flip()
            
    except Exception as e:
        logger.error("--- START OF RECENT DEBUG CONTEXT (from crash) ---")
        for line in buffering_handler.get_buffer_lines():
            logger.error(line)
        logger.error("--- END OF RECENT DEBUG CONTEXT ---")
        logger.critical("Unhandled exception in main loop, shutting down.", exc_info=True)
    finally:
        logger.info("Simulation loop ended. Shutting down.")
        display_final_graphs(inventory_graph_data, price_graph_data, capital_graph_data)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()