import sys
import os
import pygame

# Simulate running from mainbot/bot_ekko
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot_ekko.ui_expressions_lib.bmo.expressions import BMOExpressions
from bot_ekko.ui_expressions_lib.bmo.physics import BMOPhysics

# Mock Dependencies
class MockStateMachine:
    pass

def test_bmo_happy_render():
    print("Testing BMO Happy Expressions Render...")
    
    pygame.init()
    # Create an invisible surface
    surface = pygame.Surface((320, 240))
    
    sm = MockStateMachine()
    physics = BMOPhysics(sm)
    expressions = BMOExpressions(physics, sm)
    
    # Render Happy
    print("Rendering Happy Expression...")
    expressions.draw_happy(surface)
    
    # Save to file for manual inspection if needed
    pygame.image.save(surface, "bmo_happy_test.png")
    print("Saved 'bmo_happy_test.png' relative to current directory.")
    
    print("SUCCESS: Render completed without error.")

if __name__ == "__main__":
    test_bmo_happy_render()
