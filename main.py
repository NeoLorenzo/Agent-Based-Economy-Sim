# main.py

import json
import pygame
import pygame.gfxdraw
import sys
import random
import math
import numpy as np
import logging
import collections
import os
import matplotlib.pyplot as plt
from simulation import Simulation
import constants as C
import logging_setup

#======================================
# PARTICLE CLASS for Animation
#======================================
class Particle:
    """Represents an animated particle for visualizing flows with smooth easing."""
    def __init__(self, start_pos, end_pos, color):
        self.start_pos = pygame.math.Vector2(start_pos)
        self.end_pos = pygame.math.Vector2(end_pos)
        self.current_pos = self.start_pos
        self.color = color
        self.progress = 0.0  # Animation progress from 0.0 to 1.0
        self.finished = False

    def update(self):
        """
        Moves the particle along its path using an ease-in-out curve.
        This creates a smooth, natural-looking acceleration and deceleration.
        """
        if self.finished:
            return

        # Increment progress based on a fixed duration
        self.progress += 1.0 / C.PARTICLE_DURATION
        
        if self.progress >= 1.0:
            self.progress = 1.0
            self.finished = True

        # Apply a cosine easing function for smooth motion.
        # This maps a linear progress (0 to 1) to a smooth S-curve.
        eased_progress = (1 - math.cos(self.progress * math.pi)) / 2
        
        # Interpolate the position based on the eased progress
        self.current_pos = self.start_pos.lerp(self.end_pos, eased_progress)

    def draw(self, surface):
        """Draws a smooth, anti-aliased particle on the screen."""
        # We draw the particle regardless of its 'finished' state. This allows us
        # to render it one last time at its final destination after the update() call
        # that sets finished = True. It will be removed from the active list
        # immediately after this final draw call, effectively disappearing on the next frame.
        x, y = int(self.current_pos.x), int(self.current_pos.y)
        # Use gfxdraw for a high-quality anti-aliased circle
        pygame.gfxdraw.aacircle(surface, x, y, C.PARTICLE_RADIUS, self.color)
        pygame.gfxdraw.filled_circle(surface, x, y, C.PARTICLE_RADIUS, self.color)

#======================================
# HELPER FUNCTIONS
#======================================
def calculate_agent_positions(num_firms, num_households):
    """
    Calculates random screen positions for all firms and households, ensuring
    they do not overlap. This uses rejection sampling to find valid positions.
    """
    firm_positions = {}
    hh_positions = {}
    
    total_agents = num_firms + num_households

    # Define minimum distance to prevent overlap, using squared distance for efficiency.
    # This is derived from constants to adhere to Rule 1.
    min_dist = 5 * (C.AGENT_RADIUS + C.AGENT_OUTLINE_WIDTH)
    min_dist_sq = min_dist ** 2
    
    generated_positions = []

    for _ in range(total_agents):
        while True:
            # Generate a new candidate position, avoiding the graph area (Rule 12)
            min_x = C.GRAPH_X + C.GRAPH_WIDTH + C.SCREEN_PADDING
            x = np.random.randint(min_x, C.SCREEN_WIDTH - C.SCREEN_PADDING)
            y = np.random.randint(C.SCREEN_PADDING, C.SCREEN_HEIGHT - C.SCREEN_PADDING)
            candidate_pos = (x, y)
            
            # Check for collisions with all previously placed agents
            is_valid = True
            for pos in generated_positions:
                dist_sq = (pos[0] - candidate_pos[0])**2 + (pos[1] - candidate_pos[1])**2
                if dist_sq < min_dist_sq:
                    is_valid = False
                    break # Collision detected, generate a new position
            
            if is_valid:
                generated_positions.append(candidate_pos)
                break # Position is valid, move to the next agent

    # Shuffle the list of generated positions to ensure random assignment
    random.shuffle(generated_positions)

    # Assign positions to firms, assuming IDs are 0 to N-1
    firm_ids = list(range(num_firms))
    for i in range(num_firms):
        firm_id = firm_ids[i]
        position = generated_positions.pop()
        firm_positions[firm_id] = position

    # Assign the remaining positions to households, assuming IDs are 0 to N-1
    household_ids = list(range(num_households))
    for i in range(num_households):
        household_id = household_ids[i]
        position = generated_positions.pop()
        hh_positions[household_id] = position
        
    return firm_positions, hh_positions

def draw_grid(surface):
    """Draws a subtle grid on the background."""
    for x in range(0, C.SCREEN_WIDTH, C.GRID_SPACING):
        pygame.draw.line(surface, C.COLOR_GRID, (x, 0), (x, C.SCREEN_HEIGHT))
    for y in range(0, C.SCREEN_HEIGHT, C.GRID_SPACING):
        pygame.draw.line(surface, C.COLOR_GRID, (0, y), (C.SCREEN_WIDTH, y))

def draw_agent_shadows(surface, agent_positions):
    """Draws only the drop shadows for all agents."""
    for pos in agent_positions.values():
        x, y = int(pos[0]), int(pos[1])
        shadow_pos = (x + C.SHADOW_OFFSET, y + C.SHADOW_OFFSET)
        outline_radius = C.AGENT_RADIUS + C.AGENT_OUTLINE_WIDTH

        # Use gfxdraw for a smooth, anti-aliased circle
        pygame.gfxdraw.aacircle(surface, shadow_pos[0], shadow_pos[1], outline_radius, C.COLOR_SHADOW)
        pygame.gfxdraw.filled_circle(surface, shadow_pos[0], shadow_pos[1], outline_radius, C.COLOR_SHADOW)

def draw_agent_bodies(surface, agent_positions, color):
    """
    Draws the visible bodies (outline and fill) for all agents.
    This should be called after shadows and particles are drawn.
    """
    for pos in agent_positions.values():
        x, y = int(pos[0]), int(pos[1])
        outline_radius = C.AGENT_RADIUS + C.AGENT_OUTLINE_WIDTH

        # 1. Draw the anti-aliased outline
        pygame.gfxdraw.aacircle(surface, x, y, outline_radius, C.COLOR_OUTLINE)
        pygame.gfxdraw.filled_circle(surface, x, y, outline_radius, C.COLOR_OUTLINE)

        # 2. Draw the anti-aliased agent body on top
        pygame.gfxdraw.aacircle(surface, x, y, C.AGENT_RADIUS, color)
        pygame.gfxdraw.filled_circle(surface, x, y, C.AGENT_RADIUS, color)

def update_graph_data(graph_data, sim):
    """Appends the current inventory of each firm to the historical data deque."""
    # Access the entire 'inventory' column from the NumPy array
    inventories = sim.firms['inventory']
    # Enumerate through the inventories to get the firm_id (index) and value
    for firm_id, inventory_value in enumerate(inventories):
        graph_data[firm_id].append(inventory_value)

def draw_graph(surface, graph_data, config, font):
    """Draws a dynamic, auto-scaling graph with axes, labels, and a legend."""
    # 1. Draw background and border
    graph_rect = pygame.Rect(C.GRAPH_X, C.GRAPH_Y, C.GRAPH_WIDTH, C.GRAPH_HEIGHT)
    pygame.draw.rect(surface, C.GRAPH_BG_COLOR, graph_rect)
    pygame.draw.rect(surface, C.GRAPH_AXIS_COLOR, graph_rect, 1)

    # 2. Define plot area, leaving space for labels
    plot_start_x = C.GRAPH_X + C.GRAPH_AXIS_LABEL_PADDING
    plot_start_y = C.GRAPH_Y + C.GRAPH_PADDING
    plot_area_width = C.GRAPH_WIDTH - C.GRAPH_AXIS_LABEL_PADDING - C.GRAPH_PADDING
    plot_area_height = C.GRAPH_HEIGHT - 2 * C.GRAPH_PADDING

    # 3. Dynamically determine Y-axis scale based on visible data
    max_y_val = 1 # Start with a minimum value
    for history in graph_data.values():
        if history:
            max_y_val = max(max_y_val, max(history))
    max_y_val *= 1.1  # Add a 10% buffer to the top
    if max_y_val < 10: max_y_val = 10 # Ensure a minimum sensible scale

    # 4. Draw Axes and Labels
    # Y-Axis Line
    y_axis_start = (plot_start_x, plot_start_y)
    y_axis_end = (plot_start_x, plot_start_y + plot_area_height)
    pygame.draw.line(surface, C.GRAPH_AXIS_COLOR, y_axis_start, y_axis_end)
    # X-Axis Line
    x_axis_start = (plot_start_x, plot_start_y + plot_area_height)
    x_axis_end = (plot_start_x + plot_area_width, plot_start_y + plot_area_height)
    pygame.draw.line(surface, C.GRAPH_AXIS_COLOR, x_axis_start, x_axis_end)

    # Y-Axis Labels
    max_y_text = font.render(f"{int(max_y_val)}", True, C.GRAPH_FONT_COLOR)
    surface.blit(max_y_text, (plot_start_x - max_y_text.get_width() - 5, plot_start_y - 7))
    min_y_text = font.render("0", True, C.GRAPH_FONT_COLOR)
    surface.blit(min_y_text, (plot_start_x - min_y_text.get_width() - 5, plot_start_y + plot_area_height - 7))

    # 5. Draw each firm's inventory line
    spacing_x = plot_area_width / (C.GRAPH_MAX_HISTORY - 1) if C.GRAPH_MAX_HISTORY > 1 else 0
    for i, (firm_id, history) in enumerate(graph_data.items()):
        color = C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)]
        if len(history) < 2: continue

        points = []
        start_offset = C.GRAPH_MAX_HISTORY - len(history)
        for tick_index, value in enumerate(history):
            x = plot_start_x + (start_offset + tick_index) * spacing_x
            y = plot_start_y + plot_area_height * (1 - (value / max_y_val))
            points.append((x, y))
        pygame.draw.lines(surface, color, False, points, C.GRAPH_LINE_WIDTH)

    # 6. Draw Title and Legend
    title_text = font.render("Firm Inventory", True, C.GRAPH_FONT_COLOR)
    surface.blit(title_text, (plot_start_x + 5, C.GRAPH_Y + 5))
    legend_start_x = C.GRAPH_X + C.GRAPH_WIDTH - C.GRAPH_PADDING - 70
    legend_start_y = C.GRAPH_Y + C.GRAPH_PADDING
    for i, firm_id in enumerate(graph_data.keys()):
        color = C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)]
        text_surface = font.render(f"Firm {firm_id}", True, C.GRAPH_FONT_COLOR)
        item_y = legend_start_y + (i * 15)
        pygame.draw.rect(surface, color, (legend_start_x, item_y, 10, 10))
        surface.blit(text_surface, (legend_start_x + 15, item_y - 2))

def display_inventory_graph(graph_data):
    """
    Displays the firm inventory history in a Matplotlib window.
    The plot is styled to closely match the in-sim graph.
    """
    logger = logging.getLogger(__name__)
    logger.info("Displaying final inventory graph...")

    # Helper to convert Pygame RGB (0-255) to Matplotlib float (0-1)
    to_mpl_color = lambda c: tuple(x / 255.0 for x in c)

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(8, 6)) # Create a figure and an axes

    # Plot each firm's data
    for i, (firm_id, history) in enumerate(graph_data.items()):
        color = to_mpl_color(C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)])
        ax.plot(list(history), label=f"Firm {firm_id}", color=color, linewidth=C.GRAPH_LINE_WIDTH)

    # --- Style the plot to match the simulation ---
    ax.set_title("Firm Inventory", fontsize=14)
    ax.set_xlabel("Tick", fontsize=10)
    ax.set_ylabel("Inventory", fontsize=10)
    ax.set_facecolor(to_mpl_color(C.GRAPH_BG_COLOR))
    ax.grid(True, color=to_mpl_color(C.COLOR_GRID), linestyle='--', linewidth=0.5)
    ax.legend()
    
    # Set axis and tick colors
    axis_color = to_mpl_color(C.GRAPH_AXIS_COLOR)
    tick_color = to_mpl_color(C.GRAPH_FONT_COLOR)
    ax.spines['top'].set_color(axis_color)
    ax.spines['bottom'].set_color(axis_color)
    ax.spines['left'].set_color(axis_color)
    ax.spines['right'].set_color(axis_color)
    ax.tick_params(axis='x', colors=tick_color)
    ax.tick_params(axis='y', colors=tick_color)

    # --- Display the plot ---
    try:
        plt.show()
    except Exception as e:
        logger.error("Failed to display Matplotlib graph.", exc_info=True)

#======================================
# MAIN APPLICATION
#======================================
def main():
    # --- Initialization ---
    context_filter, run_dir = logging_setup.setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Application starting...")
    
    pygame.init()
    screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
    pygame.display.set_caption("Agent-Based Economy Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 12)
    
    with open('config.json', 'r') as f:
        config = json.load(f)

    # --- Seeding (Rule 12) ---
    master_seed = config['seed']
    random.seed(master_seed)
    np.random.seed(master_seed)
    logger.info("RNGs seeded with master seed: %d", master_seed)
    
    # Calculate static agent positions once by passing agent counts from the config.
    firm_positions, household_positions = calculate_agent_positions(
        config['N_F'], config['N_H']
    )

    # Now, create the final simulation object with the position data
    sim = Simulation(config, firm_positions, household_positions)
    
    # Initialize data structure for the graph
    # We now iterate from 0 to N-1, as sim.firms is a NumPy array.
    graph_data = {
        firm_id: collections.deque(maxlen=C.GRAPH_MAX_HISTORY)
        for firm_id in range(len(sim.firms))
    }
    
    active_particles = []
    tick_counter = 0

    # --- MAIN LOOP ---
    running = True
    time_per_tick = 1000.0 / config['ticks_per_second'] # Time in ms for one tick
    time_since_last_tick = 0.0
    
    try:
        logger.info("Starting main simulation loop...")
        while running:
            # --- Event Handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False

            # --- Time Management ---
            # Get time in milliseconds since the last frame
            delta_time = clock.tick(C.FPS)
            time_since_last_tick += delta_time

            # --- Simulation Step (run if enough time has passed) ---
            if time_since_last_tick >= time_per_tick:
                time_since_last_tick -= time_per_tick # Decrement accumulator
                
                context_filter.tick = tick_counter
                logger.debug("Running simulation tick %d", tick_counter)
                transactions = sim.run_one_tick()
                update_graph_data(graph_data, sim) # Capture inventory state for the graph
                
                # Create new particles for each transaction
                for trans in transactions:
                    start_pos, end_pos = None, None
                    color = None

                    if trans['type'] == 'spending':
                        # Spending: Household -> Firm
                        start_pos = household_positions.get(trans['from_id'])
                        end_pos = firm_positions.get(trans['to_id'])
                        color = C.COLOR_MONEY
                    elif trans['type'] == 'wage':
                        # Wage: Firm -> Household
                        start_pos = firm_positions.get(trans['from_id'])
                        end_pos = household_positions.get(trans['to_id'])
                        color = C.COLOR_WAGE
                    
                    if start_pos and end_pos:
                        active_particles.append(Particle(start_pos, end_pos, color))
                
                tick_counter += 1

            # --- Update and Draw (run every frame for smooth animation) ---
            screen.fill(C.COLOR_BACKGROUND)
            draw_grid(screen)
            
            # Draw the graph on the left side
            draw_graph(screen, graph_data, config, font)
            
            # 1. Draw shadows first, so they are under everything else
            draw_agent_shadows(screen, firm_positions)
            draw_agent_shadows(screen, household_positions)
            
            # 2. Update and draw particles on top of shadows
            for particle in active_particles:
                particle.update()
                particle.draw(screen)
            
            # 3. Draw agent bodies on top of particles
            draw_agent_bodies(screen, firm_positions, C.COLOR_FIRM)
            draw_agent_bodies(screen, household_positions, C.COLOR_HOUSEHOLD)
                
            active_particles = [p for p in active_particles if not p.finished]
            
            pygame.display.flip()
            
    except Exception as e:
        logger.critical("Unhandled exception in main loop, shutting down.", exc_info=True)
    finally:
        # --- Shutdown ---
        logger.info("Simulation loop ended. Shutting down.")
        display_inventory_graph(graph_data)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()