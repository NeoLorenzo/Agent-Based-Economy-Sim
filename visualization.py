#visualization.py

import pygame
import pygame.gfxdraw
import math
import constants as C
import logging
import matplotlib.pyplot as plt

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
        self.progress = 0.0
        self.finished = False

    def update(self):
        """Moves the particle along its path using an ease-in-out curve."""
        if self.finished:
            return

        self.progress += 1.0 / C.PARTICLE_DURATION
        if self.progress >= 1.0:
            self.progress = 1.0
            self.finished = True

        eased_progress = (1 - math.cos(self.progress * math.pi)) / 2
        self.current_pos = self.start_pos.lerp(self.end_pos, eased_progress)

    def draw(self, surface):
        """Draws a smooth, anti-aliased particle on the screen."""
        x, y = int(self.current_pos.x), int(self.current_pos.y)
        pygame.gfxdraw.aacircle(surface, x, y, C.PARTICLE_RADIUS, self.color)
        pygame.gfxdraw.filled_circle(surface, x, y, C.PARTICLE_RADIUS, self.color)

#======================================
# DRAWING HELPER FUNCTIONS
#======================================
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
        pygame.gfxdraw.aacircle(surface, shadow_pos[0], shadow_pos[1], outline_radius, C.COLOR_SHADOW)
        pygame.gfxdraw.filled_circle(surface, shadow_pos[0], shadow_pos[1], outline_radius, C.COLOR_SHADOW)

def draw_agent_bodies(surface, agent_positions, color):
    """Draws the visible bodies (outline and fill) for all agents."""
    for pos in agent_positions.values():
        x, y = int(pos[0]), int(pos[1])
        outline_radius = C.AGENT_RADIUS + C.AGENT_OUTLINE_WIDTH
        pygame.gfxdraw.aacircle(surface, x, y, outline_radius, C.COLOR_OUTLINE)
        pygame.gfxdraw.filled_circle(surface, x, y, outline_radius, C.COLOR_OUTLINE)
        pygame.gfxdraw.aacircle(surface, x, y, C.AGENT_RADIUS, color)
        pygame.gfxdraw.filled_circle(surface, x, y, C.AGENT_RADIUS, color)

def draw_graph(surface, graph_data, font, x, y, width, height, title):
    """Draws a dynamic, auto-scaling graph with axes, labels, and a legend."""
    graph_rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, C.GRAPH_BG_COLOR, graph_rect)
    pygame.draw.rect(surface, C.GRAPH_AXIS_COLOR, graph_rect, 1)

    plot_start_x = x + C.GRAPH_AXIS_LABEL_PADDING
    plot_start_y = y + C.GRAPH_PADDING
    plot_area_width = width - C.GRAPH_AXIS_LABEL_PADDING - C.GRAPH_PADDING
    plot_area_height = height - 2 * C.GRAPH_PADDING

    max_y_val = 1
    min_y_val = 0
    has_data = any(history for history in graph_data.values())
    if has_data:
        max_y_val = max(max(h) for h in graph_data.values() if h)
        min_y_val = min(min(h) for h in graph_data.values() if h)

    y_range = max_y_val - min_y_val
    if y_range == 0: y_range = 1
    max_y_val += y_range * 0.1
    min_y_val -= y_range * 0.1
    if min_y_val < 0: min_y_val = 0
    if max_y_val == min_y_val: max_y_val = min_y_val + 1

    y_axis_start = (plot_start_x, plot_start_y)
    y_axis_end = (plot_start_x, plot_start_y + plot_area_height)
    pygame.draw.line(surface, C.GRAPH_AXIS_COLOR, y_axis_start, y_axis_end)
    x_axis_start = (plot_start_x, plot_start_y + plot_area_height)
    x_axis_end = (plot_start_x + plot_area_width, plot_start_y + plot_area_height)
    pygame.draw.line(surface, C.GRAPH_AXIS_COLOR, x_axis_start, x_axis_end)

    max_y_text = font.render(f"{max_y_val:.1f}", True, C.GRAPH_FONT_COLOR)
    surface.blit(max_y_text, (plot_start_x - max_y_text.get_width() - 5, plot_start_y - 7))
    min_y_text = font.render(f"{min_y_val:.1f}", True, C.GRAPH_FONT_COLOR)
    surface.blit(min_y_text, (plot_start_x - min_y_text.get_width() - 5, plot_start_y + plot_area_height - 7))

    num_ticks_to_display = max(len(h) for h in graph_data.values()) if has_data else 0
    if num_ticks_to_display > 1:
        spacing_x = plot_area_width / (num_ticks_to_display - 1)
        for i, (firm_id, history) in enumerate(graph_data.items()):
            color = C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)]
            if len(history) < 2:
                continue
            points = []
            for tick_index, value in enumerate(history):
                px = plot_start_x + tick_index * spacing_x
                py = plot_start_y + plot_area_height * (1 - ((value - min_y_val) / (max_y_val - min_y_val)))
                points.append((px, py))
            pygame.draw.lines(surface, color, False, points, C.GRAPH_LINE_WIDTH)

    title_text = font.render(title, True, C.GRAPH_FONT_COLOR)
    surface.blit(title_text, (plot_start_x + 5, y + 5))
    legend_start_x = x + width - C.GRAPH_PADDING - 70
    legend_start_y = y + C.GRAPH_PADDING
    for i, firm_id in enumerate(graph_data.keys()):
        color = C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)]
        text_surface = font.render(f"Firm {firm_id}", True, C.GRAPH_FONT_COLOR)
        item_y = legend_start_y + (i * 15)
        pygame.draw.rect(surface, color, (legend_start_x, item_y, 10, 10))
        surface.blit(text_surface, (legend_start_x + 15, item_y - 2))

def display_final_graphs(inventory_data, price_data, capital_data, employee_data, wage_data):
    """
    Displays the firm inventory, price, capital, employee, and wage history in a Matplotlib window.
    """
    logger = logging.getLogger(__name__)
    logger.info("Displaying final inventory, price, capital, employee, and wage graphs...")

    to_mpl_color = lambda c: tuple(x / 255.0 for x in c)
    plt.style.use('dark_background')
    fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(10, 18), sharex=True)

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

    # Plot 4: Employees
    for i, (firm_id, history) in enumerate(employee_data.items()):
        color = to_mpl_color(C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)])
        ax4.plot(list(history), label=f"Firm {firm_id}", color=color, linewidth=C.GRAPH_LINE_WIDTH, drawstyle='steps-post')
    ax4.set_title("Firm Employees Over Time", fontsize=14)
    ax4.set_xlabel("Tick", fontsize=10)
    ax4.set_ylabel("Employees", fontsize=10)
    ax4.set_facecolor(to_mpl_color(C.GRAPH_BG_COLOR))
    ax4.grid(True, color=to_mpl_color(C.COLOR_GRID), linestyle='--', linewidth=0.5)
    ax4.legend()

    # Plot 5: Wages
    for i, (firm_id, history) in enumerate(wage_data.items()):
        color = to_mpl_color(C.GRAPH_LINE_COLORS[i % len(C.GRAPH_LINE_COLORS)])
        ax5.plot(list(history), label=f"Firm {firm_id}", color=color, linewidth=C.GRAPH_LINE_WIDTH)
    ax5.set_title("Firm Wage Rate Over Time", fontsize=14)
    ax5.set_xlabel("Tick", fontsize=10)
    ax5.set_ylabel("Wage Rate", fontsize=10)
    ax5.set_facecolor(to_mpl_color(C.GRAPH_BG_COLOR))
    ax5.grid(True, color=to_mpl_color(C.COLOR_GRID), linestyle='--', linewidth=0.5)
    ax5.legend()

    for ax in [ax1, ax2, ax3, ax4, ax5]:
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