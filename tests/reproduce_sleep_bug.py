import unittest
from unittest.mock import MagicMock
from bot_ekko.core.models import StateContext
from bot_ekko.core.state_machine import StateHandler, StateMachine

class TestSleepBugReproduction(unittest.TestCase):
    def setUp(self):
        self.mock_eyes = MagicMock()
        self.mock_eyes.target_x = 0
        self.mock_eyes.target_y = 0
        
        self.state_machine = StateMachine()
        self.state_handler = StateHandler(self.mock_eyes, self.state_machine)

    def test_params_lost_after_restore(self):
        # 1. Enter SLEEPING state with scheduler source
        initial_params = {"_source": "scheduler", "target_state": "SLEEPING"}
        self.state_handler.set_state("SLEEPING", params=initial_params)
        
        # Verify initial state
        self.assertEqual(self.state_handler.get_state(), "SLEEPING")
        self.assertEqual(self.state_handler.current_state_params, initial_params)
        
        # 2. Save Context (Simulate Interrupt Manager about to override)
        self.state_handler.save_state_ctx()
        
        # 3. Change State (Simulate Interrupt, e.g., Sensor Trigger)
        interrupt_params = {"trigger": "sensor"}
        self.state_handler.set_state("SQUINTING", params=interrupt_params)
        
        self.assertEqual(self.state_handler.get_state(), "SQUINTING")
        self.assertEqual(self.state_handler.current_state_params, interrupt_params)
        
        # 4. Restore Context (Simulate Interrupt passing)
        self.state_handler.restore_state_ctx()
        
        # 5. Verify restored state and PARAMS
        self.assertEqual(self.state_handler.get_state(), "SLEEPING")
        
        # THIS IS THE BUG: params should be restored to initial_params
        # Currently, StateContext does not save params, so restoration sets them to None (default in set_state)
        # or keeps the old ones (if not cleared, but set_state usually clears if passed None? distinct from previous logic)
        # Let's see what happens.
        
        print(f"Restored params: {self.state_handler.current_state_params}")
        
        # If the bug exists, this assertion will fail because current_state_params will be None or incorrect
        self.assertEqual(self.state_handler.current_state_params, initial_params, 
                         "Params should be restored to preserve scheduler source")

if __name__ == '__main__':
    unittest.main()
