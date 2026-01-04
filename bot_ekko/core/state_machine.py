import random
import math
import pygame
from collections import deque
from datetime import datetime
from bot_ekko.sys_config import *
from bot_ekko.modules.effects import EffectsRenderer
from bot_ekko.modules.media_interface import MediaModule
from bot_ekko.core.movements import Looks
from bot_ekko.core.logger import get_logger
from bot_ekko.core.models import StateContext, CommandNames

logger = get_logger("StateHandler")


class StateMachine:
    def __init__(self, initial_state="ACTIVE"):
        self.state = initial_state
    
    def set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
    
    def get_state(self):
        return self.state



class StateHandler:
    """
    Handles state logic, transitions, and rendering delegation for the robot's eyes.

    This class manages the lifecycle of different emotional and functional states 
    (e.g., ACTIVE, SLEEPING, INTERFACE), handling both the logic updates 
    (movement, blinking) and the rendering calls.
    """
    def __init__(self, eyes, state_machine):
        self.eyes = eyes
        self.state_machine = state_machine
        self.state_entry_time = 0
    
        self.state_history = deque(maxlen=5)
        self.current_state_params = None
        self.is_media_playing = False
    
    def get_state(self):
        return self.state_machine.get_state()
    
    def get_current_state_ctx(self):
        return StateContext(
            state=self.state_machine.get_state(),
            state_entry_time=self.state_entry_time,
            x=self.eyes.target_x,
            y=self.eyes.target_y,
            params=self.current_state_params
        )
    
    def save_state_ctx(self):
        """
        Saves the current state context (state, entry time, eye position) to history.
        
        This is typically used before interrupting the current state with a temporary 
        priority state (like a sensor trigger or interface overlay).
        """
        state_ctx = self.get_current_state_ctx()
        self.state_history.append(state_ctx)
    
    def restore_state_ctx(self):
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

    def set_state(self, new_state, params=None):
        """
        Transitions to a new state.
        
        Args:
            new_state (str): The name of the target state (must verify against config.STATES).
            params (dict, optional): Parameters to pass to the state handler. Defaults to None.
        """
        args = []
        if isinstance(new_state, tuple):
             new_state, *args = new_state
        
        # Update params regardless of state change (sometimes we re-set same state with new params)
        self.current_state_params = params

        current_state = self.state_machine.get_state()
        if current_state != new_state:
            self.state_machine.set_state(new_state)
            self.state_entry_time = pygame.time.get_ticks()
            logger.info(f"State transition: {current_state} -> {new_state}, state_entry_time: {self.state_entry_time}")
        
        # Mood/State params are handled by body physics now
