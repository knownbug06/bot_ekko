import unittest
from unittest.mock import MagicMock, patch
import sys
import pygame
from collections import deque

# Add project root to path
sys.path.append("/home/ekko/bot_ekko")

from bot_ekko.core.state_center import StateHandler, StateRenderer
from bot_ekko.core.models import StateContext

class TestStateCenter(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_eyes = MagicMock()
        self.mock_eyes.target_x = 0
        self.mock_eyes.target_y = 0
        self.mock_eyes.curr_lx = 100
        self.mock_eyes.curr_ly = 100
        self.mock_eyes.curr_rx = 200
        self.mock_eyes.curr_ry = 100
        self.mock_eyes.curr_lh = 50
        self.mock_eyes.curr_rh = 50
        self.mock_eyes.blink_phase = "IDLE"
        self.mock_eyes.last_gaze = 0
        
        self.mock_state_machine = MagicMock()
        self.mock_state_machine.get_state.return_value = "ACTIVE"
        
        self.mock_command_center = MagicMock()
        self.mock_media_player = MagicMock()

        # Mock Pygame
        pygame.init = MagicMock()
        pygame.time.get_ticks = MagicMock(return_value=1000)
        
    def test_state_handler_initialization(self):
        """Test that StateHandler initializes with all required attributes."""
        # Mock StateRenderer to avoid recursion or complex setup during init
        with patch('bot_ekko.core.state_center.StateRenderer') as MockRenderer:
            handler = StateHandler(self.mock_eyes, self.mock_state_machine)
            
            # Check attributes
            self.assertTrue(hasattr(handler, 'eyes'))
            self.assertTrue(hasattr(handler, 'state_machine'))
            self.assertTrue(hasattr(handler, 'state_history'))
            self.assertTrue(hasattr(handler, 'media_player'))
            self.assertTrue(hasattr(handler, 'renderer')) # New
            
            # Check initial values
            self.assertIsNone(handler.media_player) # Initially None
            self.assertIsInstance(handler.state_history, deque)
            self.assertEqual(handler.get_state(), "ACTIVE")
            
            MockRenderer.assert_called()

    def test_state_handler_delegation(self):
        """Test that handle_states delegates to renderer."""
        with patch('bot_ekko.core.state_center.StateRenderer') as MockRenderer:
            handler = StateHandler(self.mock_eyes, self.mock_state_machine)
            mock_renderer_instance = MockRenderer.return_value
            
            mock_surface = MagicMock()
            handler.handle_states(mock_surface, 1000, 22, 0, 8, 0)
            
            mock_renderer_instance.handle_states.assert_called_once_with(mock_surface, 1000, 22, 0, 8, 0)



    def test_state_renderer_initialization(self):
        """Test that StateRenderer initializes with all required attributes."""
        mock_state_handler = MagicMock()
        mock_state_handler.state_machine = MagicMock()
        
        renderer = StateRenderer(self.mock_eyes, mock_state_handler, self.mock_command_center, self.mock_media_player)
        
        # Check attributes
        self.assertTrue(hasattr(renderer, 'eyes'))
        self.assertTrue(hasattr(renderer, 'state_handler'))
        self.assertTrue(hasattr(renderer, 'command_center'))
        self.assertTrue(hasattr(renderer, 'media_player'))
        # self.assertTrue(hasattr(renderer, 'is_media_playing')) # Accessed via handler now
        # New attributes moved from Handler
        self.assertTrue(hasattr(renderer, 'effects'))
        self.assertTrue(hasattr(renderer, 'particles'))
        self.assertTrue(hasattr(renderer, 'looks'))
        self.assertTrue(hasattr(renderer, 'state_machine'))
        self.assertTrue(hasattr(renderer, 'wake_stage'))
        
    def test_state_renderer_handle_active(self):
        """Test that handle_ACTIVE calls _draw_generic and doesn't crash on attribute access."""
        mock_state_handler = MagicMock()
        mock_state_handler.get_state.return_value = "ACTIVE"
        
        renderer = StateRenderer(self.mock_eyes, mock_state_handler, self.mock_command_center, self.mock_media_player)
        
        # Mock methods to isolate testing
        renderer._draw_generic = MagicMock()
        renderer.random_blink = MagicMock()
        
        mock_surface = MagicMock()
        now = 2000
        
        renderer.handle_ACTIVE(mock_surface, now)
        
        renderer._draw_generic.assert_called_once_with(mock_surface)
        renderer.random_blink.assert_called_once_with(mock_surface, now)

    def test_handle_states_with_media_playing(self):
        """Test that handle_states delegates to media_player when is_media_playing is True."""
        mock_handler = MagicMock()
        mock_handler.is_media_playing = True
        mock_handler.media_player = self.mock_media_player
        
        renderer = StateRenderer(self.mock_eyes, mock_handler, self.mock_command_center, self.mock_media_player)
        
        mock_surface = MagicMock()
        # Time args: now=1000, sleep=22:00, wake=8:00
        renderer.handle_states(mock_surface, 1000, 22, 0, 8, 0)
        
        self.mock_media_player.update.assert_called_once_with(mock_surface)

    def test_state_handler_save_restore_context(self):
        """Test save_state_ctx and restore_state_ctx."""
        handler = StateHandler(self.mock_eyes, self.mock_state_machine)
        
        # Set some state
        handler.state_entry_time = 1234
        self.mock_eyes.target_x = 10
        self.mock_eyes.target_y = 20
        self.mock_state_machine.get_state.return_value = "ACTIVE"
        
        # Save context
        handler.save_state_ctx()
        self.assertEqual(len(handler.state_history), 1)
        saved_ctx = handler.state_history[0]
        self.assertEqual(saved_ctx.state, "ACTIVE")
        self.assertEqual(saved_ctx.x, 10)
        
        # Change state
        self.mock_state_machine.get_state.return_value = "INTERFACE"
        handler.set_state("INTERFACE") # This calls state_machine.set_state
        
        # Restore context
        handler.restore_state_ctx()
        
        # Assertions
        # restore_state_ctx calls self.set_state(saved_ctx.state), which uses self.state_machine.set_state
        # We need to verify that set_state was called with the restored state
        self.mock_state_machine.set_state.assert_called_with("ACTIVE")
        self.assertEqual(handler.eyes.target_x, 10)
        self.assertEqual(handler.eyes.target_y, 20)
        self.assertEqual(handler.state_entry_time, 1234)

if __name__ == '__main__':
    unittest.main()
