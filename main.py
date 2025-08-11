# main.py

import json
import pygame
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
    """Represents an animated particle for visualizing flows."""
    def __init__(self, start_pos, end_pos, color):
        self.start_pos = pygame.math.Vector2(start_pos)
        self.end_pos = pygame.math.Vector2(end_pos)
        self.current_pos = self.start_pos
        self.color = color
        self.distance_to_travel = (self.end_pos - self.start_pos).length()
        
        if self.distance_to_travel > 0:
            self.direction = (self.end_pos - self.start_pos).normalize()
        else:
            self.direction = pygame.math.Vector2(0, 0)
        
        self.finished = False

    def update(self):
        """Moves the particle closer to its destination without overshooting."""
        if not self.finished:
            # Calculate remaining distance to the destination
            remaining_distance = (self.end_pos - self.current_pos).length()

            # If the next step is longer than the remaining distance,
            # just move to the end point. Otherwise, take a normal step.
            if remaining_distance <= C.PARTICLE_SPEED:
                self.current_pos = self.end_pos
                self.finished = True
            else:
                self.current_pos += self.direction * C.PARTICLE_SPEED

    def draw(self, surface):
        """Draws the particle on the screen."""
        # We draw the particle regardless of its 'finished' state. This allows us
        # to render it one last time at its final destination after the update() call
        # that sets finished = True. It will be removed from the active list
        # immediately after this final draw call, effectively disappearing on the next frame.
        pygame.draw.circle(surface, self.color, (int(self.current_pos.x), int(self.current_pos.y)), C.PARTICLE_RADIUS)

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
    """Draws agents based on their pre-calculated positions."""
    for pos in agent_positions.values():
        pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), C.AGENT_RADIUS)

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
    try:
        logger.info("Starting main simulation loop...")
        while running:
            context_filter.tick = tick_counter
            
            # --- Event Handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False

            # --- Simulation Step ---
            logger.debug("Running simulation tick %d", tick_counter)
            transactions = sim.run_one_tick()
            
            # Create new particles for each transaction
            for trans in transactions:
                # Determine if it's a payment from a household to a firm, or a wage from a firm to a household
                start_pos = household_positions.get(trans['from_id'], firm_positions.get(trans['from_id']))
                end_pos = firm_positions.get(trans['to_id'], household_positions.get(trans['to_id']))
                
                if start_pos and end_pos:
                    color = C.COLOR_MONEY if trans['type'] == 'spending' else C.COLOR_WAGE
                    active_particles.append(Particle(start_pos, end_pos, color))

            # --- Update and Draw ---
            screen.fill(C.COLOR_BACKGROUND)
            
            draw_agents(screen, firm_positions, C.COLOR_FIRM)
            draw_agents(screen, household_positions, C.COLOR_HOUSEHOLD)
            
            for particle in active_particles:
                particle.update()
                particle.draw(screen)
                
            active_particles = [p for p in active_particles if not p.finished]
            
            pygame.display.flip()
            clock.tick(C.FPS)
            tick_counter += 1
            
    except Exception as e:
        logger.critical("Unhandled exception in main loop, shutting down.", exc_info=True)
    finally:
        # --- Shutdown ---
        logger.info("Simulation loop ended. Shutting down.")
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()