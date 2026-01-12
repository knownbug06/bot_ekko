import unittest
from unittest.mock import MagicMock
from bot_ekko.core.event_manager import EventManager
from bot_ekko.core.models import BluetoothData

class TestEventManagerBT(unittest.TestCase):
    def setUp(self):
        self.mock_sensor_trigger = MagicMock()
        self.mock_command_center = MagicMock()
        self.mock_state_renderer = MagicMock()
        self.mock_state_handler = MagicMock()
        self.mock_interrupt_manager = MagicMock()
        
        # Initial state setup
        self.mock_state_renderer.interrupt_state = False
        
        self.event_manager = EventManager(
            self.mock_sensor_trigger,
            self.mock_command_center,
            self.mock_state_renderer,
            self.mock_state_handler,
            self.mock_interrupt_manager
        )

    def test_bt_command_state_change(self):
        """
        Verify that STATE;ANGRY issues a state change command.
        """
        # Setup BT Data
        bt_data = MagicMock(spec=BluetoothData)
        bt_data.is_connected = True
        bt_data.text = "STATE;ANGRY"
        
        # Act
        self.event_manager.update_bt_events(bt_data)
        
        # Assertions
        # Should issue command
        from bot_ekko.core.models import CommandNames
        self.mock_command_center.issue_command.assert_called_with(CommandNames.CHANGE_STATE, params={"target_state": "ANGRY"})
        
        # Should NOT trigger interrupt
        self.mock_interrupt_manager.set_interrupt.assert_not_called()

    def test_bt_text_interrupt(self):
        """
        Verify that plain text triggers an interrupt.
        """
        bt_data = MagicMock(spec=BluetoothData)
        bt_data.is_connected = True
        bt_data.text = "HELLO"

        self.event_manager.update_bt_events(bt_data)

        self.mock_interrupt_manager.set_interrupt.assert_called_once()
    
if __name__ == '__main__':
    unittest.main()
