import sys
import os
import pygame

# Simulate running from mainbot/bot_ekko
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot_ekko.ui_expressions_lib.eyes.adapter import EyesExpressionAdapter

class MockStateMachine:
    pass

def test_eyes_init():
    print("Testing EyesExpressionAdapter Initialization...")
    pygame.init()
    try:
        adapter = EyesExpressionAdapter(MockStateMachine())
        # Check if scheduler exists
        if hasattr(adapter, 'scheduler'):
            print("SUCCESS: EyesExpressionAdapter initialized with scheduler.")
        else:
            print("FAILURE: EyesExpressionAdapter missing scheduler attribute.")
            sys.exit(1)
    except Exception as e:
        print(f"FAILURE: Initialization crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_eyes_init()
