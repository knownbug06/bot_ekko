import pygame
import math
from bot_ekko.sys_config import CYAN, MAIN_FONT

class EffectsRenderer:
    def render_zzz(self, surface, particles):
        for p in particles:
            # p is [x, y, alpha]
            if len(p) >= 3:
                z_surf = MAIN_FONT.render("Z", True, CYAN)
                z_surf.set_alpha(p[2])
                surface.blit(z_surf, (p[0], p[1]))

    def render_loading_dots(self, surface, center_x, center_y, now, color=CYAN):
        """Renders 3 bouncing dots for loading animation."""
        radius = 5
        spacing = 20
        amplitude = 10
        speed = 0.005 # frequency
        
        for i in range(3):
            offset_x = (i - 1) * spacing 
            # Sine wave offset based on time and index
            offset_y = math.sin(now * speed + i * 1.5) * amplitude
            
            pygame.draw.circle(surface, color, (center_x + offset_x, center_y + int(offset_y)), radius)
