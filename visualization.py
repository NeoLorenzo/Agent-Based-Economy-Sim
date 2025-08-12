import pygame
import pygame.gfxdraw
import math
import constants as C

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