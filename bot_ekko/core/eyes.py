import pygame
from bot_ekko.config import STATES

class Eyes:
    """Handles ONLY the math of moving and drawing."""
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.base_lx, self.base_ly = 280, 240
        self.base_rx, self.base_ry = 520, 240
        
        self.curr_lx, self.curr_ly = self.base_lx, self.base_ly
        self.curr_rx, self.curr_ry = self.base_rx, self.base_ry
        
        self.target_x, self.target_y = 0, 0
        self.curr_lh, self.curr_rh = 160.0, 160.0 
        
        self.blink_phase = "IDLE" # IDLE, CLOSING, OPENING
        self.last_gaze = 0

    def apply_physics(self):
        # Unpack state data.
        current_state = self.state_machine.get_state()
        state_data = STATES.get(current_state, STATES["ACTIVE"])
        base_h, gaze_speed, _, close_spd, open_spd = state_data
        
        # --- GAZE MOVEMENT ---
        dest_lx, dest_ly = self.base_lx + self.target_x, self.base_ly + self.target_y
        dest_rx, dest_ry = self.base_rx + self.target_x, self.base_ry + self.target_y
        
        self.curr_lx += (dest_lx - self.curr_lx) * gaze_speed
        self.curr_ly += (dest_ly - self.curr_ly) * gaze_speed
        self.curr_rx += (dest_rx - self.curr_rx) * gaze_speed
        self.curr_ry += (dest_ry - self.curr_ry) * gaze_speed
        
        # --- BLINK & HEIGHT PHYSICS ---
        # If we are in WAKING state (was CONFUSED), we skip standard height physics 
        if current_state != "WAKING":
            if self.blink_phase == "CLOSING":
                self.curr_lh += (10 - self.curr_lh) * close_spd
                self.curr_rh += (10 - self.curr_rh) * close_spd
                if self.curr_lh < 15: self.blink_phase = "OPENING"
            else:
                self.curr_lh += (base_h - self.curr_lh) * open_spd
                self.curr_rh += (base_h - self.curr_rh) * open_spd
                if abs(self.curr_lh - base_h) < 2: self.blink_phase = "IDLE"

    def set_look_at(self, x, y):
        """Manually set where the eyes should look."""
        self.target_x = x
        self.target_y = y
        self.last_gaze = pygame.time.get_ticks()
