import unittest
from unittest.mock import MagicMock, patch
import pygame
import sys

# Add project root to path
sys.path.append("/home/ekko/bot_ekko")

from bot_ekko.modules.media_interface import InterfaceModule

class TestInterfaceModule(unittest.TestCase):
    def setUp(self):
        # Mock pygame stuff
        pygame.font.init()
        pygame.font.SysFont = MagicMock()
        pygame.display.get_init = MagicMock(return_value=True)
        
        self.interface = InterfaceModule()

    def test_set_text_duration(self):
        with patch('pygame.time.get_ticks') as mock_ticks:
            mock_ticks.return_value = 1000
            self.interface.set_text("Hello", duration=500)
            
            self.assertTrue(self.interface.active)
            self.assertEqual(self.interface.media_start_time, 1000)
            self.assertEqual(self.interface.media_duration, 500)
            self.assertEqual(self.interface.content_type, "TEXT")

    def test_update_expiration(self):
        with patch('pygame.time.get_ticks') as mock_ticks:
            # Start
            mock_ticks.return_value = 1000
            self.interface.set_text("Hello", duration=500)
            
            # Still valid
            mock_ticks.return_value = 1200
            is_active = self.interface.update()
            self.assertTrue(is_active)
            self.assertTrue(self.interface.active)
            
            # Expired
            mock_ticks.return_value = 1600
            is_active = self.interface.update()
            self.assertFalse(is_active)
            self.assertFalse(self.interface.active)
            self.assertIsNone(self.interface.content_type)

    def test_infinite_duration(self):
        with patch('pygame.time.get_ticks') as mock_ticks:
            mock_ticks.return_value = 1000
            self.interface.set_text("Forever", duration=None)
            
            mock_ticks.return_value = 999999
            is_active = self.interface.update()
            self.assertTrue(is_active)
            self.assertTrue(self.interface.active)

    def test_clear(self):
        self.interface.set_text("test")
        self.interface.clear()
        self.assertFalse(self.interface.active)
        self.assertIsNone(self.interface.content_type)

if __name__ == '__main__':
    unittest.main()
