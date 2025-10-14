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
from src.simulation import Simulation
from src import constants as C
from src import logging_setup
from src import visualization as viz # Import the new module

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
    
def _format_summary_string(counter):
    """Helper function to format a counter into a compact string like 'N(4) C(1)'."""
    if not counter:
        return ""
    # Abbreviate for conciseness
    abbreviations = {'Normal': 'N', 'Crisis': 'C', 'InvCrisis': 'I'}
    
    # Sort by count descending to show the most dominant state first
    sorted_items = sorted(counter.items(), key=lambda item: item[1], reverse=True)
    
    parts = []
    for item, count in sorted_items:
        abbr = abbreviations.get(item, item) # Use abbreviation if available
        parts.append(f"{abbr}({count})")
    return " ".join(parts)

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
    event_log_aggregator = collections.Counter()
    summary_aggregator = collections.Counter()
    
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
                
                transactions, summary, tick_events = sim.run_one_tick(tick_counter)
                event_log_aggregator.update(tick_events)
                summary_aggregator.update(summary)
                
                # Log a detailed summary every 5 ticks.
                if tick_counter > 0 and tick_counter % 5 == 0:
                    # Log the high-level summary
                    logger.info(
                        "--- Tick %d Summary --- Sales: $%.2f (%d units) | Wages: $%.2f | Dividends: $%.2f | Unemployment: %.1f%%",
                        tick_counter,
                        summary.get('total_sales_volume', 0.0),
                        summary.get('total_sales_units', 0),
                        summary.get('total_wages_paid', 0.0),
                        summary.get('total_dividends_paid', 0.0),
                        summary.get('unemployment_rate', 0.0)
                    )

                    # --- NEW: Household & Wealth Distribution Metrics ---
                    mean_hh_balance = np.mean(sim.households['balance'])
                    median_hh_balance = np.median(sim.households['balance'])
                    total_firm_capital = np.sum(sim.firms['balance'])
                    total_money = sim.config['M0'] + (sim.config['firm_initial_capital'] * sim.config['N_F'])
                    firm_wealth_share = (total_firm_capital / total_money) * 100 if total_money > 0 else 0
                    
                    logger.info(
                        "  Wealth: HH Mean Bal: $%7.2f | HH Median Bal: $%7.2f | Firm Wealth Share: %.1f%%",
                        mean_hh_balance,
                        median_hh_balance,
                        firm_wealth_share
                    )

                    # --- NEW: Labor Market Metrics ---
                    total_target_workers = sim.firms['target_prod_workers'] + sim.firms['target_logi_workers'] + sim.firms['target_sales_workers']
                    current_total_workers = sim.firms['num_prod_workers'] + sim.firms['num_logi_workers'] + sim.firms['num_sales_workers']
                    unfilled_positions = np.sum(np.maximum(0, total_target_workers - current_total_workers))
                    logger.info(
                        "  Labor: Unfilled Positions: %d",
                        unfilled_positions
                    )

                    # Log the detailed state of each active firm
                    logger.info("  Firms:")
                    # Pre-calculate constants for the loop
                    raw_material_cost = sim.config['raw_material_cost_per_unit']
                    prod_per_worker = sim.config['production_per_worker']
                    
                    for i, firm in enumerate(sim.firms):
                        if not firm['is_bankrupt']:
                            # Calculate metrics specific to this firm
                            total_cost_last_tick = firm['production_cost_last_tick'] + firm['wages_paid_last_tick']
                            units_sold_last_tick = firm['units_sold_last_tick']
                            fallback_cost = raw_material_cost + (firm['wage_rate'] / prod_per_worker) if prod_per_worker > 0 else raw_material_cost
                            unit_cost = total_cost_last_tick / units_sold_last_tick if units_sold_last_tick > 0 else fallback_cost
                            average_sales = np.mean(sim.firm_sales_history[i])
                            
                            total_workers = firm['num_prod_workers'] + firm['num_logi_workers'] + firm['num_sales_workers']
                            total_target = firm['target_prod_workers'] + firm['target_logi_workers'] + firm['target_sales_workers']
                            worker_str = f"{total_workers}/{total_target} ({firm['num_prod_workers']}/{firm['num_logi_workers']}/{firm['num_sales_workers']})"

                            logger.info(
                                "    - Firm %d: Bal: %9.2f | Inv: %5d | Price: %5.2f (UC: %4.2f) | Workers: %-15s | Profit: %9.2f | Avg Sales: %5.1f",
                                i,
                                firm['balance'],
                                firm['inventory'],
                                firm['price'],
                                unit_cost,
                                worker_str,
                                firm['profit_last_tick'],
                                average_sales
                            )
                            # --- NEW: Log the output of the Unified Strategy AI for validation ---
                            if hasattr(sim, 'proposed_strategy') and sim.proposed_strategy:
                                health_str = f"H(I:{firm['health_inventory']:.1f} S:{firm['health_sales']:.1f} P:{firm['health_profit']:.1f} C:{firm['health_capital']:.1f})"
                                
                                # Safely get proposed values for the current firm 'i'
                                active_mask = ~sim.firms['is_bankrupt']
                                active_indices_list = np.where(active_mask)[0].tolist()
                                if i in active_indices_list:
                                    idx_in_proposal = active_indices_list.index(i)
                                    
                                    prop_price = sim.proposed_strategy['price'][idx_in_proposal]
                                    price_imp = sim.proposed_strategy['price_impulse'][idx_in_proposal]
                                    prop_p = sim.proposed_strategy['target_prod'][idx_in_proposal]
                                    prop_l = sim.proposed_strategy['target_logi'][idx_in_proposal]
                                    prop_s = sim.proposed_strategy['target_sales'][idx_in_proposal]
                                    prod_imp = sim.proposed_strategy['prod_impulse'][idx_in_proposal]
                                    
                                    proposal_str = f"Price->{prop_price:.2f} (Imp:{price_imp:.2f}) | Workers->{prop_p}/{prop_l}/{prop_s} (Imp:{prod_imp:.2f})"
                                    
                                    logger.info("      [NEW AI] %-45s | %s", health_str, proposal_str)

                    # Log the aggregated production stats over the last 5 ticks
                    logger.info(
                        "  Production (last 5 ticks): %d units | Total Material Cost (re-distributed): $%.2f",
                        summary_aggregator['total_production_units'],
                        summary_aggregator['total_production_cost']
                    )
                    summary_aggregator.clear()

                    # Log the aggregated events over the last 5 ticks
                    if event_log_aggregator:
                        event_str = " | ".join(f"{key.replace('_', ' ').title()}: {val}" for key, val in sorted(event_log_aggregator.items()))
                        logger.info("  Events (last 5 ticks): %s", event_str)
                        event_log_aggregator.clear()

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

            # Draw ownership links after bodies so they render on top
            viz.draw_ownership_links(screen, sim.firm_positions, sim.household_positions, sim.firm_owner_map)
                
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