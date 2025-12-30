import pygame


def release_pygame_display():
    pygame.display.quit()     # release framebuffer / window
    pygame.quit()             # fully release SDL video

