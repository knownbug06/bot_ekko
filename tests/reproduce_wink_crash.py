import unittest
from unittest.mock import MagicMock
import pygame
from bot_ekko.core.state_renderer import StateRenderer

class TestWinkCrash(unittest.TestCase):
    def test_wink_does_not_crash(self):
        # Mocks
        eyes = MagicMock()
        state_handler = MagicMock()
        command_center = MagicMock()
        
        # Setup specific mock attributes needed by StateRenderer init and logic
        state_handler.state_machine = MagicMock()
        state_handler.state_entry_time = 1000 # Mock time
        
        renderer = StateRenderer(eyes, state_handler, command_center)
        
        # Test
        try:
            surface = MagicMock()
            renderer.handle_WINK(surface, 2000) # 2000 > 1000, so 1000ms elapsed
        except AttributeError as e:
            self.fail(f"handle_WINK crashed with AttributeError: {e}")
        except Exception as e:
            self.fail(f"handle_WINK crashed with unexpected exception: {e}")

if __name__ == '__main__':
    unittest.main()
