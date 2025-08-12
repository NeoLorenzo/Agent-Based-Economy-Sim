# main.py

import json
import pygame
import pygame.gfxdraw
import sys
import random
import math
import numpy as np
import logging
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
def calculate_agent_positions(sim):
    """
    Calculates random screen positions for all firms and households.
    This abstraction moves away from an artificial grid layout to a more
    organic, random distribution, which is a step towards greater realism.
    """
    firm_positions = {}
    hh_positions = {}
    
    num_firms = len(sim.firms)
    num_households = len(sim.households)
    total_agents = num_firms + num_households

    # Generate all possible positions at once using NumPy for efficiency (Rule 12)
    # This creates a more organic, realistic distribution of agents (Rule 3)
    rand_x = np.random.randint(C.SCREEN_PADDING, C.SCREEN_WIDTH - C.SCREEN_PADDING, total_agents)
    rand_y = np.random.randint(C.SCREEN_PADDING, C.SCREEN_HEIGHT - C.SCREEN_PADDING, total_agents)
    all_positions = list(zip(rand_x, rand_y))
    
    # Shuffle the list of generated positions to ensure random assignment
    random.shuffle(all_positions)

    # Assign positions to firms
    firm_ids = list(sim.firms.keys())
    for i in range(num_firms):
        firm_id = firm_ids[i]
        position = all_positions.pop()
        firm_positions[firm_id] = position

    # Assign the remaining positions to households
    household_ids = list(sim.households.keys())
    for i in range(num_households):
        household_id = household_ids[i]
        position = all_positions.pop()
        hh_positions[household_id] = position
        
    return firm_positions, hh_positions

def draw_agents(surface, agent_positions, color):
    """
    Draws smooth, anti-aliased agents with an outline based on their
    pre-calculated positions.
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

#======================================
# MAIN APPLICATION
#======================================
def main():
    # --- Initialization ---
    context_filter = logging_setup.setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Application starting...")
    
    pygame.init()
    screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
    pygame.display.set_caption("Agent-Based Economy Simulation")
    clock = pygame.time.Clock()
    
    with open('config.json', 'r') as f:
        config = json.load(f)

    # --- Seeding (Rule 12) ---
    master_seed = config['seed']
    random.seed(master_seed)
    np.random.seed(master_seed)
    logger.info("RNGs seeded with master seed: %d", master_seed)
    
    # Calculate static agent positions once before creating the simulation object
    # This requires a temporary instance of the simulation to know agent counts,
    # which is slightly inefficient but clean. A future refactor could address this.
    temp_sim = Simulation(config)
    firm_positions, household_positions = calculate_agent_positions(temp_sim)
    del temp_sim # clean up temporary object

    # Now, create the final simulation object with the position data
    sim = Simulation(config, firm_positions, household_positions)
    
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
                
                # Create new particles for each transaction
                for trans in transactions:
                    start_pos = household_positions.get(trans['from_id'], firm_positions.get(trans['from_id']))
                    end_pos = firm_positions.get(trans['to_id'], household_positions.get(trans['to_id']))
                    
                    if start_pos and end_pos:
                        color = C.COLOR_MONEY if trans['type'] == 'spending' else C.COLOR_WAGE
                        active_particles.append(Particle(start_pos, end_pos, color))
                
                tick_counter += 1

            # --- Update and Draw (run every frame for smooth animation) ---
            screen.fill(C.COLOR_BACKGROUND)
            
            # Update and draw particles first, so they appear underneath the agents
            for particle in active_particles:
                particle.update()
                particle.draw(screen)
            
            # Draw agents on top of the particles
            draw_agents(screen, firm_positions, C.COLOR_FIRM)
            draw_agents(screen, household_positions, C.COLOR_HOUSEHOLD)
                
            active_particles = [p for p in active_particles if not p.finished]
            
            pygame.display.flip()
            
    except Exception as e:
        logger.critical("Unhandled exception in main loop, shutting down.", exc_info=True)
    finally:
        # --- Shutdown ---
        logger.info("Simulation loop ended. Shutting down.")
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()