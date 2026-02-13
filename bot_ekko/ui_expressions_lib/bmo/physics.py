import pygame
import random
from typing import Any, Tuple
from bot_ekko.core.state_registry import StateRegistry
from bot_ekko.core.logger import get_logger
from bot_ekko.core.base import BasePhysicsEngine

logger = get_logger("BMOPhysics")

class BMOPhysics(BasePhysicsEngine):
    """
    Handles physics for BMO's facial features.
    """
    
    def __init__(self, state_machine: Any):
        self.state_machine = state_machine
        
        # Screen dimensions (Logical)
        self.width = 800
        self.height = 480
        
        # Base positions
        self.base_lx = 280
        self.base_ly = 200
        self.base_rx = 520
        self.base_ry = 200
        
        # Current positions
        self.curr_lx, self.curr_ly = float(self.base_lx), float(self.base_ly)
        self.curr_rx, self.curr_ry = float(self.base_rx), float(self.base_ry)
        
        # Eye sizes (Radius)
        self.base_r = 15.0
        self.curr_r = self.base_r
        
        # Mouth properties
        self.mouth_width = 100.0
        self.mouth_height = 10.0
        self.mouth_y_offset = 150 # Below eyes center
        
        # Mouth properties
        self.mouth_width = 100.0
        self.mouth_height = 10.0
        self.mouth_y_offset = 150 # Below eyes center
        
        # Movement targets
        super().__init__()
        
        # Blink state
        self.blink_phase = "IDLE" # IDLE, CLOSING, OPENING
        self.blink_progress = 0.0 # 0.0 (Open) to 1.0 (Closed)
        
        self.last_gaze = 0

    def apply_physics(self) -> None:
        """
        Updates physics state. Called every frame.
        """
        current_state = self.state_machine.get_state()
        state_data = StateRegistry.get_state_data(current_state)
        
        # Default fallback values if data missing or formatted differently
        # BMO Data Format: [Gaze_Speed, Blink_Open_Spd, Blink_Close_Spd]
        
        gaze_speed = 0.1
        close_spd = 0.2
        open_spd = 0.2
        
        if state_data:
            if len(state_data) == 3:
                gaze_speed, close_spd, open_spd = state_data
            elif len(state_data) >= 5:
                # Fallback for old/Eyes format: [Base_Height, Gaze_Speed, Radius, Close_Spd, Open_Spd]
                _, gaze_speed, _, close_spd, open_spd = state_data[:5]
        
        # --- GAZE PHYSICS ---
        dest_lx = self.base_lx + self.target_x
        dest_ly = self.base_ly + self.target_y
        dest_rx = self.base_rx + self.target_x
        dest_ry = self.base_ry + self.target_y
        
        self.curr_lx += (dest_lx - self.curr_lx) * gaze_speed
        self.curr_ly += (dest_ly - self.curr_ly) * gaze_speed
        self.curr_rx += (dest_rx - self.curr_rx) * gaze_speed
        self.curr_ry += (dest_ry - self.curr_ry) * gaze_speed
        
        # --- BLINK PHYSICS ---
        if self.blink_phase == "CLOSING":
            self.blink_progress += close_spd
            if self.blink_progress >= 1.0:
                self.blink_progress = 1.0
                self.blink_phase = "OPENING"
                
        elif self.blink_phase == "OPENING":
            self.blink_progress -= open_spd
            if self.blink_progress <= 0.0:
                self.blink_progress = 0.0
                self.blink_phase = "IDLE"
    

