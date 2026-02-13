import random
import math
from collections import deque
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Union

import pygame

from bot_ekko.core.state_registry import StateRegistry
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


class BaseStateHandler:
    """
    Base class for handling state logic, transitions, and context management.
    """
    def __init__(self, render_engine: Any, state_machine: StateMachine):
        """
        Initialize the BaseStateHandler.

        Args:
            render_engine (AbstractRenderEngine): The render engine instance.
            state_machine (StateMachine): The state machine instance.
        """
        self.render_engine = render_engine
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
            StateContext: A snapshot of the current state, time, and physics state.
        """
        physics = self.render_engine.get_physics_state()
        
        # Backwards compatibility: try to extract x/y if available
        x = physics.get("x", 0) if physics else 0
        y = physics.get("y", 0) if physics else 0

        return StateContext(
            state=self.state_machine.get_state(),
            state_entry_time=self.state_entry_time,
            x=x,
            y=y,
            physics_state=physics,
            params=self.current_state_params
        )
    
    def save_state_ctx(self) -> None:
        """
        Saves the current state context to history.
        """
        state_ctx = self.get_current_state_ctx()
        self.state_history.append(state_ctx)
    
    def restore_state_ctx(self) -> None:
        """
        Restores the most recently saved state context from history.
        """
        if self.state_history:
            state_ctx = self.state_history.pop()
            self.set_state(state_ctx.state, params=state_ctx.params)
            self.state_entry_time = state_ctx.state_entry_time
            
            if state_ctx.physics_state:
                self.render_engine.set_physics_state(state_ctx.physics_state)
            else:
                # Backwards compatible restore
                self.render_engine.set_physics_state({"x": state_ctx.x, "y": state_ctx.y})
                
            logger.info(f"Context restored to: {state_ctx.state}")

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
        if not StateRegistry.has_state(new_state):
            logger.warning(f"Attempted to set invalid state: {new_state}")
            return

        # Update params regardless of state change (sometimes we re-set same state with new params)
        self.current_state_params = params

        current_state = self.state_machine.get_state()
        if current_state != new_state:
            self.state_machine.set_state(new_state)
            self.state_entry_time = pygame.time.get_ticks()
            logger.info(f"State transition: {current_state} -> {new_state}, state_entry_time: {self.state_entry_time}")


class StateHandler(BaseStateHandler):
    """
    Default StateHandler mainly for backward compatibility or extension.
    """
    pass
