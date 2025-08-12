# constants.py

"""
================================================================================
Constants and Configuration
================================================================================
This file contains all the static configuration parameters for the simulation,
as required by Rule 1.

- VISUALIZATION: Settings related to the Pygame window and drawing.
- SIMULATION: Core parameters that affect simulation logic but are not part of
              the primary economic model defined in config.json.
================================================================================
"""

#======================================
# VISUALIZATION SETTINGS
#======================================
# --- Window and Frame Rate ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60  # Frames per second for the visualization

# --- Layout and Sizing ---
SCREEN_PADDING = 50     # Minimum distance of agents from the screen edges
AGENT_RADIUS = 5        # Visual radius of Firm and Household agents
PARTICLE_RADIUS = 1     # Visual radius of money particles
PARTICLE_DURATION = 30  # Duration of particle travel in frames (e.g., 30 frames = 0.5s at 60 FPS)

# --- Colors ---
COLOR_BACKGROUND = (30, 35, 40)         # Dark Slate Grey
COLOR_HOUSEHOLD = (100, 180, 255)       # Sky Blue
COLOR_FIRM = (255, 160, 170)            # Calm Pink
COLOR_MONEY = (255, 225, 0)             # Gold
COLOR_WAGE = (80, 220, 120)             # Sea Green
COLOR_OUTLINE = (255, 255, 255)         # White

# --- Agent Visuals ---
AGENT_OUTLINE_WIDTH = 3 # Width of the agent's outline in pixels