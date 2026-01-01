import unittest
from unittest.mock import MagicMock
from bot_ekko.core.interrupt_manager import InterruptManager, InterruptItem
from bot_ekko.core.command_center import CommandNames

class TestInterruptManager(unittest.TestCase):
    def setUp(self):
        self.mock_state_handler = MagicMock()
        self.mock_command_center = MagicMock()
        self.interrupt_manager = InterruptManager(self.mock_state_handler, self.mock_command_center)
        
        # Default state
        self.mock_state_handler.get_state.return_value = "ACTIVE"

    def test_single_interrupt(self):
        # 1. Trigger Interrupt
        self.interrupt_manager.set_interrupt("test_int", 50, "TEST_STATE")
        
        # Verify Context Saved
        self.mock_state_handler.save_state_ctx.assert_called_once()
        
        # Verify Command Issued
        self.mock_command_center.issue_command.assert_called_with(CommandNames.CHANGE_STATE, {"target_state": "TEST_STATE"})
        
        # 2. Clear Interrupt
        self.interrupt_manager.clear_interrupt("test_int")
        
        # Verify Context Restored
        self.mock_state_handler.restore_state_ctx.assert_called_once()

    def test_priority_overtake(self):
        # 1. Low Priority
        self.interrupt_manager.set_interrupt("low_p", 10, "LOW_STATE")
        self.mock_command_center.issue_command.assert_called_with(CommandNames.CHANGE_STATE, {"target_state": "LOW_STATE"})
        
        # Reset mocks
        self.mock_command_center.reset_mock()
        self.mock_state_handler.reset_mock()
        
        # 2. High Priority overrides
        self.mock_state_handler.get_state.return_value = "LOW_STATE" # Simulate we are in low state
        self.interrupt_manager.set_interrupt("high_p", 90, "HIGH_STATE")
        
        # Should switch to HIGH_STATE
        self.mock_command_center.issue_command.assert_called_with(CommandNames.CHANGE_STATE, {"target_state": "HIGH_STATE"})
        # Should NOT save context again (already interrupted)
        self.mock_state_handler.save_state_ctx.assert_not_called()
        
        # Reset
        self.mock_command_center.reset_mock()
        
        # 3. Clear High Priority -> Should fall back to Low
        self.mock_state_handler.get_state.return_value = "HIGH_STATE"
        self.interrupt_manager.clear_interrupt("high_p")
        
        # Should issue command for LOW_STATE
        self.mock_command_center.issue_command.assert_called_with(CommandNames.CHANGE_STATE, {"target_state": "LOW_STATE"})
        # Should NOT restore context yet
        self.mock_state_handler.restore_state_ctx.assert_not_called()
        
        # 4. Clear Low Priority -> Restore
        self.mock_state_handler.get_state.return_value = "LOW_STATE"
        self.interrupt_manager.clear_interrupt("low_p")
        self.mock_state_handler.restore_state_ctx.assert_called_once()

    def test_lower_priority_does_not_override(self):
        # 1. High First
        self.interrupt_manager.set_interrupt("high_p", 90, "HIGH_STATE")
        self.mock_command_center.reset_mock()
        self.mock_state_handler.reset_mock()
        
        # 2. Low Second
        self.mock_state_handler.get_state.return_value = "HIGH_STATE"
        self.interrupt_manager.set_interrupt("low_p", 10, "LOW_STATE")
        
        # Should NOT switch
        self.mock_command_center.issue_command.assert_not_called()
        
if __name__ == '__main__':
    unittest.main()
