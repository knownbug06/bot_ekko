from dataclasses import dataclass, field
from typing import Dict, Optional, List
from bot_ekko.core.logger import get_logger
from bot_ekko.core.command_center import CommandCenter, CommandNames
from bot_ekko.core.state_machine import StateHandler
import heapq

logger = get_logger("InterruptManager")

@dataclass(order=True)
class InterruptItem:
    priority: int
    name: str = field(compare=False)
    target_state: str = field(compare=False)
    params: dict = field(compare=False, default=None)

class InterruptManager:
    """
    Manages state interrupts based on priority.
    
    Higher integer = Higher priority.
    Example Priorities:
    - 10: Idle behaviors (Background)
    - 30: Distance Sensor
    - 50: Proximity Sensor
    - 90: Critical Battery / Error
    """
    def __init__(self, state_handler: StateHandler, command_center: CommandCenter):
        self.state_handler = state_handler
        self.command_center = command_center
        
        # Dictionary to track active interrupts by name: {name: InterruptItem}
        self.active_interrupts: Dict[str, InterruptItem] = {}
        
        # Track if we are currently handling an interrupt to manage context
        self.is_interrupted = False

    def set_interrupt(self, name: str, priority: int, target_state: str, params: dict = None):
        """
        Activates or updates an interrupt.
        """
        # Create new item
        new_item = InterruptItem(priority, name, target_state, params)
        
        # Check if this specific interrupt is already active and identical?
        # Actually, we just update it.
        if name in self.active_interrupts:
            if self.active_interrupts[name] == new_item:
                return # No change
            logger.info(f"Updating interrupt '{name}': {new_item}")
        else:
            logger.info(f"New interrupt set '{name}': {new_item}")

        self.active_interrupts[name] = new_item
        self._evaluate_state()

    def clear_interrupt(self, name: str):
        """
        Removes an interrupt by name.
        """
        if name in self.active_interrupts:
            logger.info(f"Clearing interrupt '{name}'")
            del self.active_interrupts[name]
            self._evaluate_state()

    def _evaluate_state(self):
        """
        Determines the highest priority interrupt and transitions to it.
        If no interrupts remain, restores the previous state.
        """
        if not self.active_interrupts:
            if self.is_interrupted:
                self._restore_original_state()
            return

        # Find highest priority interrupt
        # heap is min-heap, so we need max. Just iterate, it's small list.
        highest_priority_item = max(self.active_interrupts.values(), key=lambda x: x.priority)
        
        current_state = self.state_handler.get_state()
        
        # If we are not yet interrupted, save context first
        if not self.is_interrupted:
            self.state_handler.save_state_ctx()
            self.is_interrupted = True
            logger.info("Interrupt cycle started. Context saved.")

        # Transition if needed
        # We check if we are already in the target state of the highest priority interrupt
        # This allows switching between different interrupts (e.g. Distance -> Proximity)
        if current_state != highest_priority_item.target_state:
             logger.info(f"Applying interrupt: {highest_priority_item.name} -> {highest_priority_item.target_state}")
             cmd_params = {"target_state": highest_priority_item.target_state}
             if highest_priority_item.params:
                 # We merge interrupt params (like {'param': {'text': 'HELLO'}}) into the command
                 # But issue_command expects a single dict for params. 
                 # The StateHandler stores this entire dict as current_state_params.
                 cmd_params.update(highest_priority_item.params)
                 
             self.command_center.issue_command(CommandNames.CHANGE_STATE, cmd_params)

    def _restore_original_state(self):
        """
        Restores state from before any interrupts began.
        """
        if self.is_interrupted:
            logger.info("No active interrupts. Restoring original context.")
            self.state_handler.restore_state_ctx()
            self.is_interrupted = False
