import pygame

_screen = None
_logical_surface = None

def init_display(physical_size, logical_size, fullscreen=False):
    global _screen, _logical_surface

    pygame.init()

    flags = pygame.FULLSCREEN if fullscreen else 0
    _screen = pygame.display.set_mode(physical_size, flags)
    pygame.mouse.set_visible(False)

    _logical_surface = pygame.Surface(logical_size)

    return _screen, _logical_surface


def release_display():
    global _screen, _logical_surface

    if pygame.get_init():
        pygame.display.quit()
        pygame.quit()

    _screen = None
    _logical_surface = None


def get_surfaces():
    return _screen, _logical_surface
