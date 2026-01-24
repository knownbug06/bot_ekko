import pygame
from typing import Tuple, Optional

class DisplayManager:
    """
    Manages the Pygame display surface and logical rendering surface.
    
    Attributes:
        physical_size (Tuple[int, int]): The actual screen resolution.
        logical_size (Tuple[int, int]): The internal resolution for rendering.
        fullscreen (bool): Whether to run in fullscreen mode.
        screen (pygame.Surface): The main display surface.
        logical_surface (pygame.Surface): The logical surface for rendering before scaling/rotation.
    """

    def __init__(self, physical_size: Tuple[int, int], logical_size: Tuple[int, int], fullscreen: bool = False):
        """
        Initialize the DisplayManager.

        Args:
            physical_size (Tuple[int, int]): Width and height of the physical screen.
            logical_size (Tuple[int, int]): Width and height of the logical render area.
            fullscreen (bool, optional): functionality. Defaults to False.
        """
        self.physical_size = physical_size
        self.logical_size = logical_size
        self.fullscreen = fullscreen
        
        self.screen: Optional[pygame.Surface] = None
        self.logical_surface: Optional[pygame.Surface] = None
        self._initialized = False

    def init_display(self) -> Tuple[pygame.Surface, pygame.Surface]:
        """
        Initializes the Pygame display surface.

        Returns:
            Tuple[pygame.Surface, pygame.Surface]: The physical screen surface and the logical surface.
        """
        if self._initialized and self.screen and self.logical_surface:
            return self.screen, self.logical_surface

        pygame.init()

        flags = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE if self.fullscreen else 0
        self.screen = pygame.display.set_mode(self.physical_size, flags)
        pygame.mouse.set_visible(False)

        self.logical_surface = pygame.Surface(self.logical_size)
        self._initialized = True

        return self.screen, self.logical_surface

    def release_display(self) -> None:
        """
        Uninitializes and quits Pygame display.
        """
        if pygame.get_init():
            pygame.display.quit()
            pygame.quit()

        self.screen = None
        self.logical_surface = None
        self._initialized = False

    @property
    def surfaces(self) -> Tuple[Optional[pygame.Surface], Optional[pygame.Surface]]:
        """
        Returns the current display surfaces.

        Returns:
            Tuple[Optional[pygame.Surface], Optional[pygame.Surface]]: (screen, logical_surface)
        """
        return self.screen, self.logical_surface
