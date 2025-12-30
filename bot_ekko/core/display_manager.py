import pygame

_screen = None
_logical_surface = None

def init_display(physical_size, logical_size, fullscreen=False):
    """
    Initializes the Pygame display surface.

    Args:
        physical_size (tuple): The actual screen resolution (width, height).
        logical_size (tuple): The internal resolution for rendering (width, height).
        fullscreen (bool): Whether to run in fullscreen mode.
    
    Returns:
        tuple: (screen_surface, logical_surface)
    """
    global _screen, _logical_surface

    pygame.init()

    flags = pygame.FULLSCREEN if fullscreen else 0
    _screen = pygame.display.set_mode(physical_size, flags)
    pygame.mouse.set_visible(False)

    _logical_surface = pygame.Surface(logical_size)

    return _screen, _logical_surface


def release_display():
    """
    Unitializes and quits Pygame display.
    """
    global _screen, _logical_surface

    if pygame.get_init():
        pygame.display.quit()
        pygame.quit()

    _screen = None
    _logical_surface = None


def get_surfaces():
    """
    Returns the current global display surfaces.
    
    Returns:
        tuple: (screen_surface, logical_surface) or (None, None) if not initialized.
    """
    return _screen, _logical_surface
