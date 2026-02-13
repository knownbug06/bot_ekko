import sys
import os
import pygame
import time

# Simulate running from mainbot/bot_ekko
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot_ekko.ui_expressions_lib.bmo.expressions import BMOExpressions
from bot_ekko.ui_expressions_lib.bmo.physics import BMOPhysics

# Mock Dependencies
class MockStateMachine:
    pass

def test_bmo_happy_variations():
    print("Testing BMO Happy Variations Render...")
    
    pygame.init()
    surface = pygame.Surface((320, 240))
    
    sm = MockStateMachine()
    physics = BMOPhysics(sm)
    expressions = BMOExpressions(physics, sm)
    
    # 1. Open Eyes (Default)
    print("Rendering Happy (Open Eyes)...")
    expressions.draw_happy(surface, eyes_closed=False)
    pygame.image.save(surface, "bmo_happy_open_eyes.png")
    
    # 2. Closed Eyes
    print("Rendering Happy (Closed Eyes)...")
    expressions.draw_happy(surface, eyes_closed=True)
    pygame.image.save(surface, "bmo_happy_closed_eyes.png")
    
    print("Saved 'bmo_happy_open_eyes.png' and 'bmo_happy_closed_eyes.png'.")
    print("SUCCESS")

if __name__ == "__main__":
    test_bmo_happy_variations()
