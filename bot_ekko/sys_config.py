import os
from typing import Tuple, Dict, List, Any
import pygame

"""
System Configuration Module
---------------------------
Contains all global constants, configuration paths, and state definitions.
"""

# Dynamic Base Directory
# sys_config.py is in bot_ekko/ (inner), so go up 2 levels to get to root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCREEN_ROTATION = 0

# Display Settings
LOGICAL_W, LOGICAL_H = 800, 480
PHYSICAL_W, PHYSICAL_H = 480, 800

# Colors (R, G, B)
CYAN: Tuple[int, int, int] = (0, 255, 180)
RED: Tuple[int, int, int] = (255, 50, 50)
BLACK: Tuple[int, int, int] = (0, 0, 0)
WHITE: Tuple[int, int, int] = (255, 255, 255)

COLORS = {
    "CYAN": CYAN,
    "RED": RED,
    "BLACK": BLACK,
    "WHITE": WHITE
}

# Fonts
# Must be initialized after pygame.init() usually, but here we assume init calls happen before usage
# or that font module init is sufficient.
pygame.font.init()
MAIN_FONT = pygame.font.SysFont("Arial", 40, bold=True)
CHAT_FONT = pygame.font.SysFont("Arial", 30, bold=False)
CLOCK_FONT = pygame.font.SysFont("Courier New", 80, bold=True)

# Timings (ms)
SENSOR_TRIGGER_ENTRY_TIME = 500
SENSOR_TRIGGER_EXIT_TIME = 3000

# STATE DATA has been moved to ui_expressions_lib/eyes/adapter.py and registered via StateRegistry

CANVAS_DURATION = 10

# BLUETOOTH CONFIGURATION
BLUETOOTH_NAME = "Ekko"

# File Paths
SCHEDULE_FILE_PATH = os.path.join(BASE_DIR, "bot_ekko", "config.json")
DEFAULT_GIF_PATH = os.path.join(BASE_DIR, "bot_ekko", "assets", "anime.gif")

# LOGGING CONFIGURATION
LOG_LEVEL = "INFO"

# SYSTEM MONITORING
SYSTEM_MONITORING_ENABLED = True
SYSTEM_LOG_FILE = os.path.join(BASE_DIR, "system_health.jsonl")
SYSTEM_SAMPLE_RATE = 10.0 # Seconds

# LLM CONFIGURATION
SERVER_CONFIG: Dict[str, Any] = {
    "url": "http://localhost:8000", 
    "api_key": None
}

SENSOR_UPDATE_RATE = 0.1  # seconds


GESTURE_DETECTION_IPC_SOCKET_PATH = "/tmp/ekko_ipc.sock"
GESTURE_DETECTION_MODEL_PATH = os.path.join(BASE_DIR, "gesture_recognizer.task")