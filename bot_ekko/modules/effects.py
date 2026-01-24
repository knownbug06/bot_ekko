import pygame
import math
from typing import List, Tuple
from bot_ekko.sys_config import CYAN, MAIN_FONT

class EffectsRenderer:
    """
    Renders visual effects overlays on the robot's face.
    """
    
    def render_zzz(self, surface: pygame.Surface, particles: List[List[float]]) -> None:
        """
        Renders 'Z' characters for sleeping animation.
        
        Args:
            surface (pygame.Surface): Destination surface.
            particles (List[List[float]]): List of particles [x, y, alpha].
        """
        for p in particles:
            # p is [x, y, alpha]
            if len(p) >= 3:
                z_surf = MAIN_FONT.render("Z", True, CYAN)
                z_surf.set_alpha(int(p[2]))
                surface.blit(z_surf, (int(p[0]), int(p[1])))

    def render_loading_dots(self, surface: pygame.Surface, center_x: int, center_y: int, now: int, color: Tuple[int, int, int] = CYAN) -> None:
        """
        Renders 3 bouncing dots for loading animation.
        
        Args:
            surface (pygame.Surface): Destination surface.
            center_x (int): Center X coordinate.
            center_y (int): Center Y coordinate.
            now (int): Current timestamp (ms).
            color (Tuple[int, int, int], optional): Color of dots. Defaults to CYAN.
        """
        radius = 5
        spacing = 20
        amplitude = 10
        speed = 0.005 # frequency
        
        for i in range(3):
            offset_x = (i - 1) * spacing 
            # Sine wave offset based on time and index
            offset_y = math.sin(now * speed + i * 1.5) * amplitude
            
            pygame.draw.circle(surface, color, (center_x + offset_x, center_y + int(offset_y)), radius)
