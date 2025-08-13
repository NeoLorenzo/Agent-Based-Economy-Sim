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
    
    sim = Simulation(config)
    
    inventory_graph_data = {firm_id: [] for firm_id in range(len(sim.firms))}
    price_graph_data = {firm_id: [] for firm_id in range(len(sim.firms))}
    capital_graph_data = {firm_id: [] for firm_id in range(len(sim.firms))}
    employee_graph_data = {firm_id: [] for firm_id in range(len(sim.firms))}
    
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
                
                transactions, summary = sim.run_one_tick(tick_counter)
                if tick_counter % 100 == 0 or tick_counter == 1:
                    logger.info(
                        "Tick %d Summary: Sales: $%.2f (%d units), Wages: $%.2f, Restock: $%.2f (%d units), Unemployment: %.1f%%",
                        tick_counter,
                        summary['total_sales_volume'],
                        summary['total_sales_units'],
                        summary['total_wages_paid'],
                        summary['total_restock_cost'],
                        summary['total_restock_units'],
                        summary['unemployment_rate']
                    )

                inventory_graph_data, price_graph_data, capital_graph_data, employee_graph_data = sim.update_and_get_firm_data_for_render()
                
                for trans in transactions:
                    start_pos, end_pos, color = None, None, None
                    if trans['type'] == 'spending':
                        start_pos = sim.household_positions.get(trans['from_id'])
                        end_pos = sim.firm_positions.get(trans['to_id'])
                        color = C.COLOR_MONEY
                    elif trans['type'] == 'wage':
                        start_pos = sim.firm_positions.get(trans['from_id'])
                        end_pos = sim.household_positions.get(trans['to_id'])
                        color = C.COLOR_WAGE
                    if start_pos and end_pos:
                        active_particles.append(viz.Particle(start_pos, end_pos, color))
                
                tick_counter += 1

            screen.fill(C.COLOR_BACKGROUND)
            viz.draw_grid(screen)
            
            viz.draw_graph(screen, inventory_graph_data, font, C.INVENTORY_GRAPH_X, C.INVENTORY_GRAPH_Y, C.GRAPH_WIDTH, C.GRAPH_HEIGHT, "Firm Inventory")
            viz.draw_graph(screen, price_graph_data, font, C.PRICE_GRAPH_X, C.PRICE_GRAPH_Y, C.GRAPH_WIDTH, C.GRAPH_HEIGHT, "Firm Price")
            viz.draw_graph(screen, capital_graph_data, font, C.CAPITAL_GRAPH_X, C.CAPITAL_GRAPH_Y, C.GRAPH_WIDTH, C.GRAPH_HEIGHT, "Firm Capital")
            viz.draw_graph(screen, employee_graph_data, font, C.EMPLOYEE_GRAPH_X, C.EMPLOYEE_GRAPH_Y, C.GRAPH_WIDTH, C.GRAPH_HEIGHT, "Firm Employees")
            
            viz.draw_agent_shadows(screen, sim.firm_positions)
            viz.draw_agent_shadows(screen, sim.household_positions)
            viz.draw_agent_shadows(screen, sim.bank_positions)
            
            for particle in active_particles:
                particle.update()
                particle.draw(screen)
            
            viz.draw_agent_bodies(screen, sim.firm_positions, C.COLOR_FIRM)
            viz.draw_agent_bodies(screen, sim.household_positions, C.COLOR_HOUSEHOLD)
            viz.draw_agent_bodies(screen, sim.bank_positions, C.COLOR_BANK)
                
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
        wage_graph_data = sim._wage_history if hasattr(sim, '_wage_history') else {}
        viz.display_final_graphs(inventory_graph_data, price_graph_data, capital_graph_data, employee_graph_data, wage_graph_data)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()