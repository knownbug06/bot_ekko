import pygame
from dataclasses import dataclass, field
from typing import Dict, Optional
from bot_ekko.core.command_center import CommandCenter, CommandNames
from bot_ekko.core.state_machine import StateHandler
from bot_ekko.core.logger import get_logger

logger = get_logger("InterruptHandler")

@dataclass
class InterruptItem:
    name: str
    target_state: str
    priority: int
    duration: int
    start_time: int
    params: dict = field(default_factory=dict)

class InterruptHandler:
    def __init__(self, command_center: CommandCenter, state_handler: StateHandler):
        self.command_center = command_center
        self.state_handler = state_handler
        self.active_interrupts: Dict[str, InterruptItem] = {}
        self.is_interrupted = False

    def set_interrupt(self, name: str, duration: int, target_state: str, priority: int = 10, params: dict = None):
        """
        Sets or updates an interrupt.
        """
        current_time = pygame.time.get_ticks()
        item = InterruptItem(
            name=name,
            target_state=target_state,
            priority=priority,
            duration=duration,
            start_time=current_time,
            params=params or {}
        )
        
        self.active_interrupts[name] = item
        logger.info(f"Set interrupt '{name}': {item}")
        self._evaluate_state()

    def update(self):
        """
        Checks for timeouts and updates state matches.
        """
        if not self.active_interrupts:
            return

        current_time = pygame.time.get_ticks()
        expired_names = []
        
        # Check timeouts
        for name, item in self.active_interrupts.items():
            if current_time - item.start_time > item.duration:
                expired_names.append(name)
        
        if expired_names:
            for name in expired_names:
                logger.info(f"Interrupt '{name}' timed out.")
                del self.active_interrupts[name]
            self._evaluate_state()
            
    def _evaluate_state(self):
        """
        Determines the highest priority interrupt and transitions to it.
        """
        if not self.active_interrupts:
            if self.is_interrupted:
                logger.info("No active interrupts. Restoring original state.")
                self.command_center.issue_command(CommandNames.RESTORE_STATE)
                self.is_interrupted = False
            return

        # Find highest priority
        highest = max(self.active_interrupts.values(), key=lambda x: x.priority)
        
        # If we are not currently interrupted, this is the first interrupt. Save history.
        save_history = False
        if not self.is_interrupted:
            save_history = True
            self.is_interrupted = True
            logger.info("Interrupt cycle started. Requesting history save.")
            
        current_state = self.state_handler.get_state()
        
        # Transition if target state differs
        if current_state != highest.target_state:
            logger.info(f"Applying interrupt transition: {highest.name} -> {highest.target_state} (P:{highest.priority})")
            cmd_params = {"target_state": highest.target_state, "save_history": save_history}
            cmd_params.update(highest.params)
            
            self.command_center.issue_command(CommandNames.CHANGE_STATE, params=cmd_params)

    def stop_interrupt(self, name: str):
        if name in self.active_interrupts:
            logger.info(f"Stopping interrupt '{name}' manually.")
            del self.active_interrupts[name]
            self._evaluate_state()
