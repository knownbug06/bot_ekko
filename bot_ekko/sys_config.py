import pygame

LOGICAL_W, LOGICAL_H = 800, 480
PHYSICAL_W, PHYSICAL_H = 480, 800
CYAN = (0, 255, 180)
RED = (255, 50, 50)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

pygame.font.init()
MAIN_FONT = pygame.font.SysFont("Arial", 40, bold=True)
CHAT_FONT = pygame.font.SysFont("Arial", 30, bold=False)
CLOCK_FONT = pygame.font.SysFont("Courier New", 80, bold=True)

SENSOR_TRIGGER_ENTRY_TIME = 500
SENSOR_TRIGGER_EXIT_TIME = 3000


# STATE DATA: [Base_Height, Gaze_Speed, Radius, Close_Spd, Open_Spd]
STATES = {
    "ACTIVE":     [160, 0.1,  30, 0.5, 0.15], # Was NEUTRAL
    "SQUINTING":  [85,  0.07, 15, 0.4, 0.12], # Was SQUINT
    "SLEEPING":   [8,   0.02, 4,  0.1, 0.1],  # Was SLEEP
    "WAKING":     [140, 0.05, 20, 0.3, 0.1],  # Was CONFUSED
    "CONFUSED":   [140, 0.05, 20, 0.3, 0.1],  # Kept for compatibility if needed, or mapped to WAKING
    "THINKING":   [130, 0.1,  40, 0.3, 0.2],
    "ANGRY":      [120, 0.1,  10, 0.4, 0.2],  # Angry layout
    "SCARED":     [160, 0.2,  10, 0.5, 0.2],  # Scared layout (wide eyes, fast gaze)
    "HAPPY":      [120, 0.1,  20, 0.4, 0.2],  # Happy layout (arched eyes)
    "RAINBOW_EYES": [210, 0.1,  30, 0.5, 0.15], # Generic shape, rainbow fill
    "WINK":       [160, 0.1,  20, 0.5, 0.2],  # Wink (one eye closed)
    "UWU":        [160, 0.1,  20, 0.4, 0.2],  # Uwu face
    "CANVAS":  [0, 0, 0, 0, 0],    # Show Text state
    "CHAT": [0, 0, 0, 0, 0],    # Show Text state
    "CLOCK": [0, 0, 0, 0, 0],   # Show Time state
}

CANVAS_DURATION = 10

# BLUETOOTH CONFIGURATION
BLUETOOTH_NAME = "ekko_bt"

SCHEDULE_FILE_PATH = "/home/ekko/bot_ekko/schedule.json"

# SLEEP_AT and WAKE_AT are now managed by schedule.json


# LOGGING CONFIGURATION
LOG_LEVEL = "INFO"

# SYSTEM MONITORING
SYSTEM_MONITORING_ENABLED = True
SYSTEM_LOG_FILE = "/home/ekko/bot_ekko/system_health.jsonl"
SYSTEM_SAMPLE_RATE = 10.0 # Seconds

# LLM CONFIGURATION
SERVER_CONFIG = {
    "url": "http://192.168.0.2:5000/chat", # Replace with your server IP
    "api_key": None
}
