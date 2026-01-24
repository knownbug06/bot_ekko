import random
import math
from collections import deque
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Union

import pygame

from bot_ekko.sys_config import STATES
from bot_ekko.core.movements import Looks
from bot_ekko.core.logger import get_logger
from bot_ekko.core.models import StateContext

logger = get_logger("StateHandler")


class StateMachine:
    """
    Manages the current state of the robot.
    """
    def __init__(self, initial_state: str = "ACTIVE"):
        self.state = initial_state
    
    def set_state(self, new_state: str) -> None:
        """
        Updates the current state.
        
        Args:
            new_state (str): The new state to transition to.
        """
        if self.state != new_state:
            self.state = new_state
    
    def get_state(self) -> str:
        """
        Returns the current state.
        
        Returns:
            str: The current state name.
        """
        return self.state


class StateHandler:
    """
    Handles state logic, transitions, and context management for the robot's eyes.

    This class manages the lifecycle of different emotional and functional states 
    (e.g., ACTIVE, SLEEPING, INTERFACE), handling both the logic updates 
    and maintaining state history for context restoration.
    """
    def __init__(self, eyes: Any, state_machine: StateMachine):
        """
        Initialize the StateHandler.

        Args:
            eyes (Eyes): The eyes controller instance.
            state_machine (StateMachine): The state machine instance.
        """
        self.eyes = eyes
        self.state_machine = state_machine
        self.state_entry_time = 0
    
        self.state_history: deque = deque(maxlen=5)
        self.current_state_params: Optional[Dict[str, Any]] = None
        self.is_media_playing = False
    
    def get_state(self) -> str:
        """
        Get the current state from the state machine.
        
        Returns:
            str: Current state name.
        """
        return self.state_machine.get_state()
    
    def get_current_state_ctx(self) -> StateContext:
        """
        Capture the current state context.
        
        Returns:
            StateContext: A snapshot of the current state, time, eye position, and params.
        """
        return StateContext(
            state=self.state_machine.get_state(),
            state_entry_time=self.state_entry_time,
            x=self.eyes.target_x,
            y=self.eyes.target_y,
            params=self.current_state_params
        )
    
    def save_state_ctx(self) -> None:
        """
        Saves the current state context (state, entry time, eye position) to history.
        
        This is typically used before interrupting the current state with a temporary 
        priority state (like a sensor trigger or interface overlay).
        """
        state_ctx = self.get_current_state_ctx()
        self.state_history.append(state_ctx)
    
    def restore_state_ctx(self) -> None:
        """
        Restores the most recently saved state context from history.
        
        This returns the robot to the previous state after an interruption.
        """
        if self.state_history:
            state_ctx = self.state_history.pop()
            self.set_state(state_ctx.state, params=state_ctx.params)
            self.state_entry_time = state_ctx.state_entry_time
            self.eyes.target_x = state_ctx.x
            self.eyes.target_y = state_ctx.y
            logger.info(f"Context restored to: {state_ctx}")

    def set_state(self, new_state: Union[str, Tuple], params: Optional[Dict[str, Any]] = None) -> None:
        """
        Transitions to a new state.
        
        Args:
            new_state (Union[str, Tuple]): The name of the target state (must verify against config.STATES),
                                           or a tuple where the first element is the state name.
            params (dict, optional): Parameters to pass to the state handler. Defaults to None.
        """
        args = []
        if isinstance(new_state, tuple):
             new_state, *args = new_state
        
        # Verify state validity
        if new_state not in STATES:
            logger.warning(f"Attempted to set invalid state: {new_state}")
            return

        # Update params regardless of state change (sometimes we re-set same state with new params)
        self.current_state_params = params

        current_state = self.state_machine.get_state()
        if current_state != new_state:
            self.state_machine.set_state(new_state)
            self.state_entry_time = pygame.time.get_ticks()
            logger.info(f"State transition: {current_state} -> {new_state}, state_entry_time: {self.state_entry_time}")
        
        # Mood/State params are handled by body physics now
