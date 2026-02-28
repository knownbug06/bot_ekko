import pygame
import random
from typing import Dict, Any, Optional

from bot_ekko.core.base_renderer import BaseStateRenderer
from bot_ekko.core.state_registry import StateRegistry
from bot_ekko.core.models import CommandNames
from bot_ekko.core.logger import get_logger
from bot_ekko.ui_expressions_lib.bmo.physics import BMOPhysics
from bot_ekko.ui_expressions_lib.bmo.expressions import BMOExpressions
from bot_ekko.core.movements import BaseMovements

logger = get_logger("MainAdapter")

# BMO Configuration Data
# [Gaze_Speed, Close_Spd, Open_Spd]
BMO_STATE_DATA = {
    StateRegistry.ACTIVE:     [0.1, 0.2, 0.2],
    StateRegistry.HAPPY:      [0.1, 0.2, 0.2],
    StateRegistry.SAD:        [0.05, 0.1, 0.1],
    StateRegistry.ANGRY:      [0.1, 0.3, 0.3],
    StateRegistry.SLEEPING:   [0.0, 0.1, 0.1],
    StateRegistry.WAKING:     [0.05, 0.2, 0.2],
    StateRegistry.AMUSED:     [0.1, 0.2, 0.2],
    StateRegistry.SURPRISED:  [0.05, 0.4, 0.4],
    # Fill others with defaults
}

class MainAdapter(BaseStateRenderer):
    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.state_machine = state_machine
        self.state_handler = None
        self.command_center = None
        
        # Init Components
        self.physics = BMOPhysics(self.state_machine)
        self.expressions = BMOExpressions(self.physics, self.state_machine)
        self.movements = BaseMovements(self.physics)
        
        self.last_blink = 0
        self.last_gaze = 0
        self.last_mood_change = 0 # Track last smile time
        
        # Register States
        self._register_states()
        
    def _register_states(self):
        logger.info("Registering BMO States...")
        # Register specific BMO data
        for state, data in BMO_STATE_DATA.items():
            StateRegistry.register_state(state, data)
            
        # Ensure all other known states have at least default data
        # If StateRegistry has keys with None, fill them
        default_data = [0.1, 0.2, 0.2]
        
        # We can Iterate known constants from StateRegistry class if we want, 
        # but for now let's just ensure critical ones.
        # Actually StateRegistry._data keys are available if we access strictly, 
        # but the class doesn't expose keys list publically in the method I wrote. 
        # I'll rely on on-demand fallback in physics if data is missing, 
        # OR I can register defaults for everything I missed.
        pass

    def set_dependencies(self, state_handler, command_center):
        self.state_handler = state_handler
        self.command_center = command_center

    def update(self, now: int) -> None:
        super().update(now)
        self.physics.apply_physics()

    def render(self, surface: pygame.Surface, now: int) -> None:
        super().render(surface, now)

    def handle_fallback(self, surface: pygame.Surface, now: int):
        self.expressions.draw_default(surface)

    def random_blink(self, surface, now):
        if self.physics.blink_phase == "IDLE" and (now - self.last_blink > random.randint(3000, 9000)):
            self.physics.blink_phase = "CLOSING"
            self.last_blink = now

    def handle_ACTIVE(self, surface: pygame.Surface, now: int, params=None):
        # 1. Random Gaze
        if now - self.last_gaze > random.randint(5000, 10000):
            self.physics.target_x = random.randint(-40, 40)
            self.physics.target_y = random.randint(-40, 40)
            self.last_gaze = now

        # 2. Random Blink
        self.random_blink(surface, now)

        # 3. Random Mood (Smile)
        if now - self.last_mood_change > random.randint(8000, 15000):
            if random.random() > 0.6:
                logger.info("Triggering HAPPY state (Smiling) from random mood")
                
                # Randomly pick a variant: "closed_eyes" or "open_eyes"
                variant = "closed_eyes" if random.random() > 0.5 else "open_eyes"
                
                self.command_center.issue_command(CommandNames.CHANGE_STATE, params={
                    "target_state": StateRegistry.HAPPY,
                    "variant": variant
                })
                self.last_mood_change = now

        self.expressions.draw_default(surface)
        
    def handle_HAPPY(self, surface: pygame.Surface, now: int, params=None):
        eyes_closed = False
        if params and params.get("variant") == "closed_eyes":
            eyes_closed = True
            
        # Return to ACTIVE after random duration (2-5s)
        # We check entry time of state
        if self.state_handler:
             elapsed = now - self.state_handler.state_entry_time
             if elapsed > random.randint(2000, 5000):
                 if random.random() > 0.05: # Small chance per frame once duration passed? No, deterministic once time passed.
                     logger.info("Triggering ACTIVE state from HAPPY (Done smiling)")
                     self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": StateRegistry.ACTIVE})
                     self.last_mood_change = now

        self.expressions.draw_happy(surface, eyes_closed=eyes_closed)

    def handle_SAD(self, surface: pygame.Surface, now: int, params=None):
        mouth_open = False
        if params and params.get("variant") == "mouth_open":
             mouth_open = True
        # Randomly sigh (open mouth) every ~5 seconds
        elif (int(now / 1000) % 5 == 0): 
             mouth_open = True
             
        self.expressions.draw_sad(surface, mouth_open=mouth_open)
        
    def handle_CRYING(self, surface: pygame.Surface, now: int, params=None):
         self.expressions.draw_sad(surface, mouth_open=True) # Crying usually open mouth? Or add tears later
         
    def handle_ANGRY(self, surface: pygame.Surface, now: int, params=None):
        mouth_open = False
        if params and params.get("variant") == "shouting":
             mouth_open = True
        # Randomly shout/grit teeth
        elif (int(now / 800) % 4 == 0):
             mouth_open = True
             
        self.expressions.draw_angry(surface, mouth_open=mouth_open)

    def handle_AMUSED(self, surface: pygame.Surface, now: int, params=None):
        mouth_open = False
        if params and params.get("variant") == "laughing":
             mouth_open = True
        
        self.expressions.draw_amused(surface, mouth_open=mouth_open)

    def handle_SURPRISED(self, surface: pygame.Surface, now: int, params=None):
        large = False
        if params and params.get("variant") == "very_surprised":
             large = True
             
        self.expressions.draw_surprised(surface, mouth_open=large)

        
    def handle_SQUINTING(self, surface: pygame.Surface, now: int, params=None):
        self.expressions.draw_neutral(surface)

    def handle_SLEEPING(self, surface: pygame.Surface, now: int, params=None):
        self.physics.blink_phase = "CLOSING" 
        self.physics.blink_progress = 1.0
        self.expressions.draw_neutral(surface)


    def get_physics_state(self) -> Dict[str, Any]:
        return {
            "lx": self.physics.curr_lx,
            "ly": self.physics.curr_ly,
            "rx": self.physics.curr_rx,
            "ry": self.physics.curr_ry,
            "blink": self.physics.blink_progress
        }

    def set_physics_state(self, state: Dict[str, Any]) -> None:
        if not state: return
        self.physics.curr_lx = state.get("lx", self.physics.base_lx)
        self.physics.curr_ly = state.get("ly", self.physics.base_ly)
        self.physics.curr_rx = state.get("rx", self.physics.base_rx)
        self.physics.curr_ry = state.get("ry", self.physics.base_ry)
        self.physics.blink_progress = state.get("blink", 0.0)
