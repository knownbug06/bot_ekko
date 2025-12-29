import pygame

LOGICAL_W, LOGICAL_H = 800, 480
PHYSICAL_W, PHYSICAL_H = 480, 800
CYAN = (0, 255, 180)
RED = (255, 50, 50)
BLACK = (0, 0, 0)

pygame.font.init()
MAIN_FONT = pygame.font.SysFont("Arial", 40, bold=True)


# STATE DATA: [Base_Height, Gaze_Speed, Radius, Close_Spd, Open_Spd]
STATES = {
    "ACTIVE":     [160, 0.1,  30, 0.5, 0.15], # Was NEUTRAL
    "SQUINTING":  [85,  0.07, 15, 0.4, 0.12], # Was SQUINT
    "SLEEPING":   [8,   0.02, 4,  0.1, 0.1],  # Was SLEEP
    "WAKING":     [140, 0.05, 20, 0.3, 0.1],  # Was CONFUSED
    "CONFUSED":   [140, 0.05, 20, 0.3, 0.1],  # Kept for compatibility if needed, or mapped to WAKING
    "THINKING":   [130, 0.1,  40, 0.3, 0.2],
    "ANGRY":      [120, 0.1,  10, 0.4, 0.2],  # Angry layout
    "INTERFACE":  [0,   0,    0,  0,   0],     # Eyes hidden
    "PROXIMITY":  [160, 0.1,  10, 0.5, 0.5],  # Angry layout
    "DISTANCE":   [160, 0.1,  10, 0.5, 0.5],  # Angry layout
    "SCARED":     [160, 0.2,  10, 0.5, 0.2],  # Scared layout (wide eyes, fast gaze)
}

# BLUETOOTH CONFIGURATION
BLUETOOTH_NAME = "ekko_bt"

