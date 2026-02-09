import random
import math
import pygame
from datetime import datetime
from typing import Dict, Any, Optional

from bot_ekko.ui_expressions_lib.eyes.expressions import EyesExpressions
from bot_ekko.core.render_engine import AbstractRenderEngine
from bot_ekko.ui_expressions_lib.eyes.physics import Eyes
from bot_ekko.core.logger import get_logger
from bot_ekko.core.models import CommandNames, StateContext
from bot_ekko.sys_config import *
from bot_ekko.modules.effects import EffectsRenderer
from bot_ekko.core.scheduler import Scheduler

logger = get_logger("EyesExpressionAdapter")

class EyesExpressionAdapter(AbstractRenderEngine):
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.state_handler = None
        self.command_center = None
        
        # Initialize internal components
        self.eyes = Eyes(self.state_machine)
        self.expressions = EyesExpressions(self.eyes, self.state_machine)
        
        # Rendering attributes
        self.effects = EffectsRenderer()
        self.particles = []
        self.wake_stage = 0
        
        self.last_blink = 0
        self.last_mood_change = 0
        
        # Scheduler
        self.scheduler = Scheduler(SCHEDULE_FILE_PATH)
        
        self.media_player = None 

        # Rainbow state cache
        self.rainbow_surf = None
        self.rainbow_layer = None
        self.eyes_mask_layer = None

    def set_dependencies(self, state_handler, command_center):
        self.state_handler = state_handler
        self.command_center = command_center

    def set_media_player(self, media_player):
        self.media_player = media_player

    def update(self, now: int) -> None:
        """Update physics and scheduler."""
        self._check_schedule(now)
        self.eyes.apply_physics()

    def render(self, surface: pygame.Surface, now: int) -> None:
        """Main render loop."""
        current_state = self.state_handler.get_state().upper()
        handler_name = f"handle_{current_state}"
        handler = getattr(self, handler_name, None)
        
        if handler:
            handler(surface, now, params=self.state_handler.current_state_params)
        else:
            logger.warning(f"Warning: No handler for state {current_state}")
            # Fallback to standard eyes if no specific handler
            self.expressions.draw_generic(surface)

    def get_physics_state(self) -> Dict[str, Any]:
        """Return current eyes state."""
        return {
            "x": self.eyes.target_x,
            "y": self.eyes.target_y,
            "curr_lx": self.eyes.curr_lx,
            "curr_ly": self.eyes.curr_ly,
            "curr_rx": self.eyes.curr_rx,
            "curr_ry": self.eyes.curr_ry,
            "curr_lh": self.eyes.curr_lh,
            "curr_rh": self.eyes.curr_rh,
            "blink_phase": self.eyes.blink_phase
        }

    def set_physics_state(self, state: Dict[str, Any]) -> None:
        """Restore eyes state."""
        if not state:
            return
            
        self.eyes.target_x = state.get("x", 0)
        self.eyes.target_y = state.get("y", 0)
        self.eyes.curr_lx = state.get("curr_lx", self.eyes.base_lx)
        self.eyes.curr_ly = state.get("curr_ly", self.eyes.base_ly)
        self.eyes.curr_rx = state.get("curr_rx", self.eyes.base_rx)
        self.eyes.curr_ry = state.get("curr_ry", self.eyes.base_ry)
        self.eyes.curr_lh = state.get("curr_lh", 160.0)
        self.eyes.curr_rh = state.get("curr_rh", 160.0)
        self.eyes.blink_phase = state.get("blink_phase", "IDLE")

    # --- Scheduler Logic (Moved from StateRenderer) ---
    def _check_schedule(self, now):
        # Grace period on startup (2 seconds) to ensure we start in ACTIVE/Initial state
        if now < 2000:
            return

        current_state = self.state_handler.get_state()
        if current_state == "CHAT":
            return

        now_dt = datetime.now()
        
        result = self.scheduler.get_target_state(now_dt, current_state)

        if result:
            target_state, params = result
            
            # Prepare params with source tracking
            cmd_params = params.copy() if params else {}
            cmd_params["_source"] = "scheduler"
            cmd_params["target_state"] = target_state
            
            # Scheduler says we should be in target_state
            if current_state != target_state:
                logger.info(f"Triggering {target_state} state from schedule with params: {params}")
                self.command_center.issue_command(CommandNames.CHANGE_STATE, params=cmd_params)
        else:
            # No active schedule
            # Check if we are currently in a state triggered by the scheduler
            current_params = self.state_handler.current_state_params or {}
            
            # Helper to handle case where params might be flattened or nested (defensive)
            source = current_params.get("_source") if isinstance(current_params, dict) else None
            
            if source == "scheduler":
                if current_state == "SLEEPING":
                     logger.info("Triggering WAKING state (Schedule ended)")
                     self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": "WAKING"})
                else:
                     logger.info(f"Reverting to ACTIVE from {current_state} (Schedule ended)")
                     self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": "ACTIVE"})

    # --- Render Handlers (Moved from StateRenderer) ---

    def random_blink(self, surface, now):
        if self.eyes.blink_phase == "IDLE" and (now - self.last_blink > random.randint(3000, 9000)):
            self.eyes.blink_phase = "CLOSING"
            self.last_blink = now

    def handle_ACTIVE(self, surface, now, params=None):
        # --- LOGIC ---
        # 1. Random Gaze
        if now - self.eyes.last_gaze > random.randint(5000, 10000):
            self.eyes.target_x = random.randint(-100, 100)
            self.eyes.target_y = random.randint(-40, 40)
            self.eyes.last_gaze = now

        # 2. Random Mood (Squint)
        if now - self.last_mood_change > random.randint(5000, 12000):
            if random.random() > 0.6:
                logger.info("Triggering SQUINTING state from random mood")
                self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": "SQUINTING"})
                self.last_mood_change = now

        # 3. Random Blink
        self.random_blink(surface, now)
        # --- RENDERING ---
        self.expressions.draw_generic(surface)

    def handle_SQUINTING(self, surface, now, params=None):
        # --- LOGIC ---
        if now - self.eyes.last_gaze > random.randint(2000, 5000):
            self.eyes.target_x = random.randint(-100, 100)
            self.eyes.target_y = random.randint(-40, 40)
            self.eyes.last_gaze = now
            
        if now - self.last_mood_change > random.randint(2000, 5000):
            logger.info("Triggering ACTIVE state from random mood")
            self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": "ACTIVE"})
            self.last_mood_change = now
            
        # --- RENDERING ---
        self.expressions.draw_generic(surface)
    
    def handle_CANVAS(self, surface, now, params=None):
        if self.media_player and self.media_player.is_playing:
            self.media_player.update(surface)
            return

        if self.media_player:
            interrupt_name = params.get('interrupt_name') if params else None
            text = None
            if params and 'param' in params and isinstance(params['param'], dict):
                 text = params['param'].get('text')
            
            duration = params.get("duration", CANVAS_DURATION) if params else CANVAS_DURATION
            
            if text:
                self.media_player.show_text(text, duration=duration, save_context=False, interrupt_name=interrupt_name)
            else:
                gif_path = params.get("media_path", DEFAULT_GIF_PATH) if params else DEFAULT_GIF_PATH
                self.media_player.play_gif(gif_path, duration=duration, save_context=False, interrupt_name=interrupt_name)
    
    def handle_ANGRY(self, surface, now, params=None):
        # --- LOGIC ---
        self.eyes.look_center()
        self.random_blink(surface, now)
             
        # --- RENDERING ---
        self.expressions.draw_slanted_eyes(surface, color=RED, slant_inwards=True)

    def handle_SCARED(self, surface, now, params=None):
        # --- LOGIC ---
        self.eyes.target_x = random.randint(-40, 40)
        self.eyes.target_y = random.randint(-20, 20)
        self.eyes.last_gaze = now

        self.random_blink(surface, now)
             
        # --- RENDERING ---
        self.expressions.draw_slanted_eyes(surface, color=WHITE, slant_inwards=False)

    def handle_HAPPY(self, surface, now, params=None):
        # --- LOGIC ---
        self.eyes.look_up()
        self.random_blink(surface, now)

        # --- RENDERING ---
        self.expressions.draw_happy_eyes(surface)
        self.expressions.draw_uwu_mouth(surface)

    def handle_RAINBOW_EYES(self, surface, now, params=None):
        self.random_blink(surface, now)
        self.eyes.look_center()

        # --- RENDERING ---
        w, h = surface.get_size()
        
        if (self.rainbow_surf is None or 
            self.rainbow_layer is None or 
            self.rainbow_layer.get_size() != (w, h)):
            
            logger.debug("Initializing Rainbow Surfaces")
            self.rainbow_surf = self.expressions.create_rainbow_gradient(w, h)
            self.rainbow_layer = pygame.Surface((w, h), pygame.SRCALPHA)
            self.eyes_mask_layer = pygame.Surface((w, h), pygame.SRCALPHA)
            
        offset_x = int((now / 5) % w)
        
        self.rainbow_layer.blit(self.rainbow_surf, (-offset_x, 0))
        self.rainbow_layer.blit(self.rainbow_surf, (w - offset_x, 0))

        self.eyes_mask_layer.fill((0, 0, 0, 0)) # Clear transparent
        self.expressions.draw_generic(self.eyes_mask_layer, (255, 255, 255))
        
        self.eyes_mask_layer.blit(self.rainbow_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        surface.blit(self.eyes_mask_layer, (0, 0))

    def handle_CHAT(self, surface, now, params=None):
        # --- LOGIC ---
        # No eye logic needed for chat-only screen
        
        # --- RENDERING ---
        is_loading = False
        text = ""
        
        if params:
            is_loading = params.get("is_loading", False)
            text = params.get("text", "")

        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2 

        if is_loading:
            self.effects.render_loading_dots(surface, center_x, center_y, now)
        elif text:
            try:
                from bot_ekko.sys_config import CHAT_FONT
                font = CHAT_FONT
            except ImportError:
                font = MAIN_FONT
             
            # assuming media_player exposes this util or we duplicate/move it
            if self.media_player:   
                surf = self.media_player._render_wrapped_text(text, font, CYAN, LOGICAL_W - 40)
                rect = surf.get_rect(center=(center_x, center_y))
                surface.blit(surf, rect)

    def handle_WINK(self, surface, now, params=None):
        cycle_time = (now - self.state_handler.state_entry_time) % 4000
        
        target_lh = 160
        target_rh = 160
        
        if 1000 < cycle_time < 1200:
            target_rh = 20
        elif 1200 <= cycle_time < 1400:
            target_rh = 10
        elif 1400 <= cycle_time < 1600:
            target_rh = 160
        
        speed = 0.2
        self.eyes.curr_lh += (target_lh - self.eyes.curr_lh) * speed
        self.eyes.curr_rh += (target_rh - self.eyes.curr_rh) * speed
        
        self.eyes.look_center()
        
        self.expressions.draw_happy_eyes(surface)

    def handle_UWU(self, surface, now, params=None):
        self.eyes.look_center()
        
        line_color = CYAN
        blush_color = (255, 182, 193) # LightPink
        
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        
        eye_radius = 80
        line_width = 10
        
        l_rect = pygame.Rect(lx - eye_radius, ly - eye_radius - 50, eye_radius*2, eye_radius*2)
        pygame.draw.arc(surface, line_color, l_rect, math.pi, 2*math.pi, line_width)
        
        r_rect = pygame.Rect(rx - eye_radius, ry - eye_radius - 50, eye_radius*2, eye_radius*2)
        pygame.draw.arc(surface, line_color, r_rect, math.pi, 2*math.pi, line_width)
        
        center_x = (lx + rx) // 2
        center_y = (ly + ry) // 2 + 60 

        mouth_radius = 40
        mouth_l_rect = pygame.Rect(center_x - 2*mouth_radius, center_y, 2*mouth_radius, 2*mouth_radius)
        pygame.draw.arc(surface, line_color, mouth_l_rect, math.pi, 2*math.pi, line_width)
        
        mouth_r_rect = pygame.Rect(center_x, center_y, 2*mouth_radius, 2*mouth_radius)
        pygame.draw.arc(surface, line_color, mouth_r_rect, math.pi, 2*math.pi, line_width)
        
        blush_w, blush_h = 90, 40
        blush_offset_y = 60
        
        l_blush = pygame.Rect(lx - blush_w//2 - 50, ly + blush_offset_y, blush_w, blush_h)
        r_blush = pygame.Rect(rx - blush_w//2 + 50, ry + blush_offset_y, blush_w, blush_h)
        
        pygame.draw.ellipse(surface, blush_color, l_blush)
        pygame.draw.ellipse(surface, blush_color, r_blush)

    def handle_SLEEPING(self, surface, now, params=None):
        self.eyes.target_x = math.sin(now / 1000) * 15
        self.eyes.target_y = 25
        self._update_particles(now)
        
        self.expressions.draw_generic(surface)
        self.effects.render_zzz(surface, self.particles)

    def handle_WAKING(self, surface, now, params=None):
        elapsed = now - self.state_handler.state_entry_time
        if elapsed < 1500: # Stage 0: Jitter
            self.wake_stage = 0
            self.eyes.target_x = random.randint(-25, 25)
            self.eyes.target_y = random.randint(-25, 25)
            if random.random() > 0.7: self.eyes.blink_phase = "CLOSING"
        elif elapsed < 4000: # Stage 1: Confusion
            self.wake_stage = 1
            self.eyes.target_x = -50
            self.eyes.curr_lh, self.eyes.curr_rh = 140, 60 
        else: # Stage 2: Fully Awake
            logger.info("Triggering ACTIVE state from WAKING")
            self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": "ACTIVE"})
            self.last_mood_change = now
            
        self.expressions.draw_generic(surface)

    def handle_INTERFACE(self, surface, now, params=None):
        pass

    def handle_FUNNY(self, surface, now, params=None):
        if self.media_player and not self.media_player.is_playing:
            fallback_ctx = StateContext(state="ACTIVE", state_entry_time=now, x=0, y=0)
            self.state_handler.state_history.append(fallback_ctx)
            self.media_player.play_gif(DEFAULT_GIF_PATH, duration=5.0, save_context=False)
            
        if self.media_player and self.media_player.is_playing:
             self.media_player.update(surface)
    
    def handle_CLOCK(self, surface, now, params=None):
        if not self.media_player:
            return

        current_time = datetime.now().strftime("%I:%M %p") 
        if current_time.startswith("0"):
            current_time = current_time[1:] 
            
        from bot_ekko.sys_config import CLOCK_FONT
        
        target_text = current_time.capitalize()
        if not self.media_player.is_playing or self.media_player.current_text != target_text:
             self.media_player.show_text(current_time, duration=60.0, save_context=False, font=CLOCK_FONT)
             
        self.media_player.update(surface)

    # --- Drawing Helpers (Delegated to EyesExpressions) ---
    def _update_particles(self, now):
        if random.random() < 0.03:
            # X, Y, Alpha
            self.particles.append([self.eyes.base_rx + 40, self.eyes.base_ry - 40, 255])
        for p in self.particles[:]:
            p[1] -= 1.2
            p[0] += math.sin(now/500) * 0.5
            p[2] -= 3
            if p[2] <= 0: self.particles.remove(p)
