import unittest
from unittest.mock import MagicMock, patch
import pygame
import sys

# Add project root to path
sys.path.append("/home/ekko/bot_ekko")

from bot_ekko.core.state_center import StateHandler
from bot_ekko.modules.media_interface import InterfaceModule

class TestStateHandlerInterface(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_eyes = MagicMock()
        self.mock_state_machine = MagicMock()
        
        # Mock pygame stuff
        pygame.time.get_ticks = MagicMock(return_value=1000)
        pygame.font.init()
        pygame.font.SysFont = MagicMock()
        
        # Instantiate StateHandler
        self.handler = StateHandler(self.mock_eyes, self.mock_state_machine)
        
        # Mock the interface module interacting with it
        self.handler.interface = MagicMock()

    def test_handle_INTERFACE_PLAY_GIF_active(self):
        # Setup: Interface returns True (active)
        self.handler.interface.update.return_value = True
        
        mock_surface = MagicMock()
        self.handler.handle_INTERFACE_PLAY_GIF(mock_surface, 1000)
        
        # Check: Render called, Restore NOT called
        self.handler.interface.render.assert_called_with(mock_surface)
        self.handler.state_machine.set_state.assert_not_called() 
        # Note: restore_state_ctx calls set_state internally if history exists.
        # We need to ensure logic flow. Since I can't easily mock history pop empty check, 
        # I'll rely on checking restore_state_ctx behavior or mocking it.
        
    def test_handle_INTERFACE_PLAY_GIF_expired(self):
        # Setup: Interface returns False (expired)
        self.handler.interface.update.return_value = False
        self.handler.restore_state_ctx = MagicMock()
        
        mock_surface = MagicMock()
        self.handler.handle_INTERFACE_PLAY_GIF(mock_surface, 1000)
        
        # Check: Render NOT called, Restore called
        self.handler.interface.render.assert_not_called()
        self.handler.restore_state_ctx.assert_called_once()

if __name__ == '__main__':
    unittest.main()
