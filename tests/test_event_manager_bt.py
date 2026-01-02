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
        
        # Initial state setup
        self.mock_state_renderer.interrupt_state = False
        
        self.event_manager = EventManager(
            self.mock_sensor_trigger,
            self.mock_command_center,
            self.mock_state_renderer,
            self.mock_state_handler
        )

    def test_bt_command_permanent_state_change(self):
        """
        Verification Test:
        Desired Behavior: BT Command should NOT save context and should set interrupt=False (or clear it).
        """
        # Setup BT Data
        bt_data = MagicMock(spec=BluetoothData)
        bt_data.is_connected = True
        bt_data.text = "ANGRY"
        
        # Act
        self.event_manager.update_bt_events(bt_data)
        
        # Assertions for the FIXED behavior
        # Should NOT save context
        self.mock_state_handler.save_state_ctx.assert_not_called()
        
        # Should set interrupt_state = False
        self.assertFalse(self.mock_state_renderer.interrupt_state)

if __name__ == '__main__':
    unittest.main()
