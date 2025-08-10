import json
import pygame
import sys
import random
import math
import numpy as np
from simulation import Simulation

#======================================
# VISUALIZATION SETTINGS
#======================================
# --- Colors ---
COLOR_BACKGROUND = (25, 25, 25)
COLOR_HOUSEHOLD = (173, 216, 230) # Light Blue
COLOR_FIRM = (255, 182, 193)      # Light Pink
COLOR_MONEY = (255, 255, 0)       # Yellow

# --- Layout ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_PADDING = 50 # Used for random agent placement
FIRM_Y_POSITION = 100
HOUSEHOLD_GRID_START_Y = 250
AGENT_RADIUS = 5
PARTICLE_RADIUS = 2
PARTICLE_SPEED = 4

#======================================
# PARTICLE CLASS for Animation
#======================================
class Particle:
    """Represents an animated particle for visualizing flows."""
    def __init__(self, start_pos, end_pos):
        self.start_pos = pygame.math.Vector2(start_pos)
        self.end_pos = pygame.math.Vector2(end_pos)
        self.current_pos = self.start_pos
        self.distance_to_travel = (self.end_pos - self.start_pos).length()
        
        if self.distance_to_travel > 0:
            self.direction = (self.end_pos - self.start_pos).normalize()
        else:
            self.direction = pygame.math.Vector2(0, 0)
        
        self.finished = False

    def update(self):
        """Moves the particle closer to its destination."""
        if not self.finished:
            self.current_pos += self.direction * PARTICLE_SPEED
            # Check if particle has reached or passed the destination
            if (self.current_pos - self.start_pos).length() >= self.distance_to_travel:
                self.finished = True

    def draw(self, surface):
        """Draws the particle on the screen."""
        if not self.finished:
            pygame.draw.circle(surface, COLOR_MONEY, (int(self.current_pos.x), int(self.current_pos.y)), PARTICLE_RADIUS)

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
    rand_x = np.random.randint(SCREEN_PADDING, SCREEN_WIDTH - SCREEN_PADDING, total_agents)
    rand_y = np.random.randint(SCREEN_PADDING, SCREEN_HEIGHT - SCREEN_PADDING, total_agents)
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
        pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), AGENT_RADIUS)

#======================================
# MAIN APPLICATION
#======================================
def main():
    # --- Initialization ---
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Agent-Based Economy Simulation")
    clock = pygame.time.Clock()
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    sim = Simulation(config)

    # Calculate static agent positions once
    firm_positions, household_positions = calculate_agent_positions(sim)
    
    active_particles = []

    # --- MAIN LOOP ---
    running = True
    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # --- Simulation Step ---
        # Run one tick and get the list of financial transactions
        transactions = sim.run_one_tick()
        
        # Create new particles for each transaction
        for trans in transactions:
            start_pos = household_positions.get(trans['from_id'])
            end_pos = firm_positions.get(trans['to_id'])
            if start_pos and end_pos:
                active_particles.append(Particle(start_pos, end_pos))

        # --- Update and Draw ---
        screen.fill(COLOR_BACKGROUND)
        
        # Draw static agents
        draw_agents(screen, firm_positions, COLOR_FIRM)
        draw_agents(screen, household_positions, COLOR_HOUSEHOLD)
        
        # Update and draw all active particles
        for particle in active_particles:
            particle.update()
            particle.draw(screen)
            
        # Remove particles that have finished their journey
        active_particles = [p for p in active_particles if not p.finished]
        
        pygame.display.flip()
        clock.tick(60)

    # --- Shutdown ---
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()