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
PARTICLE_RADIUS = 2     # Visual radius of money particles
PARTICLE_SPEED = 4      # Speed of money particles in pixels per frame

# --- Colors ---
COLOR_BACKGROUND = (25, 25, 25)
COLOR_HOUSEHOLD = (173, 216, 230) # Light Blue
COLOR_FIRM = (255, 182, 193)      # Light Pink
COLOR_MONEY = (255, 255, 0)       # Yellow for spending
COLOR_WAGE = (0, 255, 0)          # Green for wages