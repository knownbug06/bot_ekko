import random
import math
import pygame
from collections import deque
from datetime import datetime
from bot_ekko.config import *
from bot_ekko.modules.effects import EffectsRenderer
from bot_ekko.modules.media_interface import MediaModule
from bot_ekko.core.movements import Looks
from bot_ekko.core.logger import get_logger
from bot_ekko.core.models import StateContext, CommandNames

logger = get_logger("StateHandler")

class StateRenderer:
    def __init__(self, eyes, state_handler, command_center):
        self.eyes = eyes
        self.last_blink = 0
        self.last_mood_change = 0
        self.state_handler = state_handler
        self.command_center = command_center
        self.media_player = MediaModule(self.state_handler)
        
        # Rendering attributes
        self.effects = EffectsRenderer()
        self.particles = []
        self.wake_stage = 0
        
        # State Flags
        self.is_media_playing = False
        self.interrupt_state = False
        
        # Proxies to StateHandler attributes needed for logic/rendering
        self.looks = Looks(self.eyes, state_handler.state_machine)
        self.state_machine = state_handler.state_machine


    def trigger_wake(self):
        """Force wake up sequence."""
        if self.state_handler.get_state() == "SLEEPING":
            logger.info("Triggering WAKING state from SLEEPING")
            self.command_center.issue_command(CommandNames.CHANGE_STATE, {"target_state": "WAKING"})

    def render(self, surface, now, sleep_h, sleep_m, wake_h, wake_m):
        """
        Main update loop for state handling.
        
        Checks schedules, determines the current state, and calls the appropriate 
        specific handler method (e.g., handle_ACTIVE).
        """
        if not self.is_media_playing:
            self._check_schedule(sleep_h, sleep_m, wake_h, wake_m)
        
            current_state = self.state_handler.get_state()
            handler_name = f"handle_{current_state}"
            handler = getattr(self, handler_name, None)
            if handler:
                handler(surface, now, self.state_handler.current_state_params)
            else:
                logger.warning(f"Warning: No handler for state {current_state}")
        else:
            self.media_player.update(surface)

    def _check_schedule(self, sleep_h, sleep_m, wake_h, wake_m):
        now_dt = datetime.now()
        current_total = now_dt.hour * 60 + now_dt.minute
        sleep_total = sleep_h * 60 + sleep_m
        wake_total = wake_h * 60 + wake_m

        if sleep_total > wake_total: # Over midnight
            in_sleep = current_total >= sleep_total or current_total < wake_total
        else: # Same day
            in_sleep = sleep_total <= current_total < wake_total

        current_state = self.state_handler.get_state()
        if in_sleep:
            if current_state != "SLEEPING" and current_state != "WAKING" and not self.interrupt_state:
                logger.info("Triggering SLEEPING state from schedule")
                self.command_center.issue_command(CommandNames.CHANGE_STATE, {"target_state": "SLEEPING"})
        else:
            if current_state == "SLEEPING":
                logger.info("Triggering WAKING state from schedule")
                self.command_center.issue_command(CommandNames.CHANGE_STATE, {"target_state": "WAKING"})

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
                self.command_center.issue_command(CommandNames.CHANGE_STATE, {"target_state": "SQUINTING"})
                self.last_mood_change = now

        # 3. Random Blink
        self.random_blink(surface, now)
        # --- RENDERING ---
        self._draw_generic(surface)

    def handle_SQUINTING(self, surface, now, params=None):
        # --- LOGIC ---
        if now - self.eyes.last_gaze > random.randint(2000, 5000):
            self.eyes.target_x = random.randint(-100, 100)
            self.eyes.target_y = random.randint(-40, 40)
            self.eyes.last_gaze = now
            
        if now - self.last_mood_change > random.randint(2000, 5000):
            logger.info("Triggering ACTIVE state from random mood")
            self.command_center.issue_command(CommandNames.CHANGE_STATE, {"target_state": "ACTIVE"})
            self.last_mood_change = now
            
        # --- RENDERING ---
        self._draw_generic(surface)
    
    def handle_ANGRY(self, surface, now, params=None):
        # --- LOGIC ---
        self.looks.look_center()
        self.random_blink(surface, now)
             
        # --- RENDERING ---
        # Slanted Trapezoids
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        w, h = 160, int(self.eyes.curr_lh)
        slant = 35
        r = 10 # Corner radius
        
        l_poly = [
            (lx - 80 + r, ly - h//2 + r),          # Top Left
            (lx + 80 - r, ly - h//2 + slant + r),  # Top Right (Lower)
            (lx + 80 - r, ly + h//2 - r),          # Bottom Right
            (lx - 80 + r, ly + h//2 - r)           # Bottom Left
        ]
        
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        r_poly = [
            (rx - 80 + r, ry - h//2 + slant + r),  # Top Left (Lower)
            (rx + 80 - r, ry - h//2 + r),          # Top Right
            (rx + 80 - r, ry + h//2 - r),          # Bottom Right
            (rx - 80 + r, ry + h//2 - r)           # Bottom Left
        ]
        
        self._draw_rounded_poly(surface, RED, l_poly, r)
        self._draw_rounded_poly(surface, RED, r_poly, r)

    def handle_SCARED(self, surface, now, params=None):
        # --- LOGIC ---
        # if now - self.eyes.last_gaze > random.randint(500, 1500):
        self.eyes.target_x = random.randint(-40, 40)
        self.eyes.target_y = random.randint(-20, 20)
        self.eyes.last_gaze = now

        self.random_blink(surface, now)
             
        # --- RENDERING ---
        # Reverse Slanted Trapezoids (SCARED: Inner corners UP)
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        h = int(self.eyes.curr_lh)
        slant = 35
        r = 10 # Corner radius
        
        l_poly = [
            (lx - 80 + r, ly - h//2 + slant + r),  # Top Left (Lower/Bigger Y)
            (lx + 80 - r, ly - h//2 + r),          # Top Right (Higher/Smaller Y)
            (lx + 80 - r, ly + h//2 - r),          # Bottom Right
            (lx - 80 + r, ly + h//2 - r)           # Bottom Left
        ]
        
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        r_poly = [
            (rx - 80 + r, ry - h//2 + r),          # Top Left
            (rx + 80 - r, ry - h//2 + slant + r),  # Top Right
            (rx + 80 - r, ry + h//2 - r),          # Bottom Right
            (rx - 80 + r, ry + h//2 - r)           # Bottom Left
        ]
        
        self._draw_rounded_poly(surface, WHITE, l_poly, r)
        self._draw_rounded_poly(surface, WHITE, r_poly, r)

    def handle_HAPPY(self, surface, now, params=None):
        # --- LOGIC ---
        self.looks.look_up()
        self.random_blink(surface, now)

        # --- RENDERING ---
        self._draw_happy_eyes(surface)
        self._draw_uwu_mouth(surface)

    def handle_RAINBOW_EYES(self, surface, now, params=None):
        self.random_blink(surface, now)
        self.looks.look_center()

        # --- RENDERING ---
        # 1. Get Rainbow Surface (lazy init)
        if not hasattr(self, 'rainbow_surf'):
            self.rainbow_surf = self._create_rainbow_gradient(surface.get_width(), surface.get_height())
            
        # 2. Calculate offset
        offset_x = int((now / 5) % surface.get_width()) # Speed factor
        
        # 3. Create the full rainbow output
        rainbow_layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        # Draw two copies to handle wrapping
        rainbow_layer.blit(self.rainbow_surf, (-offset_x, 0))
        rainbow_layer.blit(self.rainbow_surf, (surface.get_width() - offset_x, 0))

        # 4. Create mask (Eyes in White)
        eyes_layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._draw_generic(eyes_layer, (255, 255, 255))
        
        # 5. Mask rainbow with eyes (Multiply)
        eyes_layer.blit(rainbow_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        surface.blit(eyes_layer, (0, 0))

    def handle_WINK(self, surface, now, params=None):
        # --- LOGIC ---
        # Animation Cycle: 4000ms
        # 0-1000: Open (Both Happy)
        # 1000-1200: Closing Right
        # 1200-1400: Closed Right (Hold)
        # 1400-1600: Opening Right
        # 1600-4000: Open (Idle)
        
        cycle_time = (now - self.state_entry_time) % 4000
        
        # Default Targets (Open)
        target_lh = 160
        target_rh = 160
        
        if 1000 < cycle_time < 1200:
            # Closing Right
            target_rh = 20
        elif 1200 <= cycle_time < 1400:
            # Held Closed
            target_rh = 10
        elif 1400 <= cycle_time < 1600:
            # Opening
            target_rh = 160
        
        # Apply physics manually (Lerp)
        speed = 0.2
        self.eyes.curr_lh += (target_lh - self.eyes.curr_lh) * speed
        self.eyes.curr_rh += (target_rh - self.eyes.curr_rh) * speed
        
        self.looks.look_center()
        
        # --- RENDERING ---
        self._draw_happy_eyes(surface)

    def handle_UWU(self, surface, now, params=None):
        # --- LOGIC ---
        self.looks.look_center()
        
        # --- RENDERING ---
        line_color = CYAN
        blush_color = (255, 182, 193) # LightPink
        
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        
        # 1. Draw Eyes (U shape)
        eye_radius = 80
        line_width = 10
        
        # Left Eye (pi to 2pi -> Smile/U)
        l_rect = pygame.Rect(lx - eye_radius, ly - eye_radius - 50, eye_radius*2, eye_radius*2)
        pygame.draw.arc(surface, line_color, l_rect, math.pi, 2*math.pi, line_width)
        
        # Right Eye
        r_rect = pygame.Rect(rx - eye_radius, ry - eye_radius - 50, eye_radius*2, eye_radius*2)
        pygame.draw.arc(surface, line_color, r_rect, math.pi, 2*math.pi, line_width)
        
        # 2. Draw Mouth
        # Center between eyes
        center_x = (lx + rx) // 2
        # Position slightly higher than before
        center_y = (ly + ry) // 2 + 60 

        mouth_radius = 40
        # Left 'u' of mouth
        mouth_l_rect = pygame.Rect(center_x - 2*mouth_radius, center_y, 2*mouth_radius, 2*mouth_radius)
        pygame.draw.arc(surface, line_color, mouth_l_rect, math.pi, 2*math.pi, line_width)
        
        # Right 'u' of mouth
        mouth_r_rect = pygame.Rect(center_x, center_y, 2*mouth_radius, 2*mouth_radius)
        pygame.draw.arc(surface, line_color, mouth_r_rect, math.pi, 2*math.pi, line_width)
        
        # 3. Draw Blush
        # Bigger and lighter
        blush_w, blush_h = 90, 40
        blush_offset_y = 60 # Slightly closer to eyes
        
        l_blush = pygame.Rect(lx - blush_w//2 - 50, ly + blush_offset_y, blush_w, blush_h)
        r_blush = pygame.Rect(rx - blush_w//2 + 50, ry + blush_offset_y, blush_w, blush_h)
        
        pygame.draw.ellipse(surface, blush_color, l_blush)
        pygame.draw.ellipse(surface, blush_color, r_blush)

    def handle_SLEEPING(self, surface, now, params=None):
        # --- LOGIC ---
        self.eyes.target_x = math.sin(now / 1000) * 15
        self.eyes.target_y = 25
        self._update_particles(now)
        
        # --- RENDERING ---
        self._draw_generic(surface)
        self.effects.render_zzz(surface, self.particles)

    def handle_WAKING(self, surface, now, params=None):
        # --- LOGIC ---
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
            self.command_center.issue_command(CommandNames.CHANGE_STATE, {"target_state": "ACTIVE"})
            self.last_mood_change = now
            
        # --- RENDERING ---
        self._draw_generic(surface)

    def handle_INTERFACE(self, surface, now, params=None):
        pass

    def handle_FUNNY(self, surface, now, params=None):
        # Trigger GIF playback if not already playing
        
        if not self.is_media_playing:
            # We want to return to ACTIVE (or schedule default) after this, NOT recurse into FUNNY.
            # So we push ACTIVE to history manually and tell play_gif NOT to save current (FUNNY) state.
            
            # Using 0 for entry time and coordinates as defaults
            fallback_ctx = StateContext(state="ACTIVE", state_entry_time=now, x=0, y=0)
            self.state_handler.state_history.append(fallback_ctx)
        
            # Placeholder path - user should replace this
            self.media_player.play_gif("/home/ekko/bot_ekko/bot_ekko/assets/anime.gif", duration=5.0, save_context=False)
            
        # Ensure media player updates
        if self.is_media_playing:
             self.media_player.update(surface)

    def _draw_happy_eyes(self, surface, color=CYAN):
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        w = 160
        h_l = int(self.eyes.curr_lh)
        h_r = int(self.eyes.curr_rh)
        
        # Left Eye
        pygame.draw.rect(surface, color, 
            (lx - w//2, ly - h_l//2, w, h_l), 
            border_top_left_radius=w//2, 
            border_top_right_radius=w//2,
            border_bottom_left_radius=10,
            border_bottom_right_radius=10)
            
        # Right Eye
        pygame.draw.rect(surface, color, 
            (rx - w//2, ry - h_r//2, w, h_r), 
            border_top_left_radius=w//2, 
            border_top_right_radius=w//2,
            border_bottom_left_radius=10,
            border_bottom_right_radius=10)

    def _draw_uwu_mouth(self, surface, color=CYAN):
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        
        # Center between eyes
        center_x = (lx + rx) // 2
        # Position below eyes
        # Eyes are approx at Y=240, height 160. Bottom is 320.
        center_y = (ly + ry) // 2 + 100 

        radius = 40
        width = 10
        
        # Left 'u'
        # Arc Pi to 2Pi goes Left -> Bottom -> Right. This forms a 'u' shape.
        left_rect = pygame.Rect(center_x - 2*radius, center_y, 2*radius, 2*radius)
        pygame.draw.arc(surface, color, left_rect, math.pi, 2*math.pi, width)
        
        # Right 'u' 
        right_rect = pygame.Rect(center_x, center_y, 2*radius, 2*radius)
        pygame.draw.arc(surface, color, right_rect, math.pi, 2*math.pi, width)

    def _create_rainbow_gradient(self, w, h):
        surf = pygame.Surface((w, h))
        import colorsys
        for x in range(w):
            hue = x / w
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            color = (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
            pygame.draw.line(surf, color, (x, 0), (x, h))
        return surf
        if not self.is_media_playing:
            # Fallback to ACTIVE
            fallback_ctx = StateContext(state="ACTIVE", state_entry_time=now, x=0, y=0)
            self.state_history.append(fallback_ctx)
            
            text = params.get('text', 'Hello!') if params else 'Hello!'
            self.media_player.show_text(text, duration=5.0, save_context=False)
            
        if self.is_media_playing:
            self.media_player.update(surface)

    def _draw_generic(self, surface, color=CYAN):
        state_data = STATES.get(self.state_machine.get_state(), STATES["ACTIVE"])
        _, _, radius, _, _ = state_data
        
        logger.debug(f"Drawing generic eyes for state: {self.state_machine.get_state()}")
        
        # Draw Left Eye
        pygame.draw.rect(surface, color, 
            (int(self.eyes.curr_lx - 80), int(self.eyes.curr_ly - self.eyes.curr_lh//2), 160, int(self.eyes.curr_lh)), 
            border_radius=radius)
        # Draw Right Eye
        pygame.draw.rect(surface, color, 
            (int(self.eyes.curr_rx - 80), int(self.eyes.curr_ry - self.eyes.curr_rh//2), 160, int(self.eyes.curr_rh)), 
            border_radius=radius)

    def _update_particles(self, now):
        if random.random() < 0.03:
            # X, Y, Alpha
            self.particles.append([self.eyes.base_rx + 40, self.eyes.base_ry - 40, 255])
        for p in self.particles[:]:
            p[1] -= 1.2
            p[0] += math.sin(now/500) * 0.5
            p[2] -= 3
            if p[2] <= 0: self.particles.remove(p)

    def _draw_rounded_poly(self, surface, color, points, radius):
        pygame.draw.polygon(surface, color, points)
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            pygame.draw.circle(surface, color, p1, radius)
            pygame.draw.line(surface, color, p1, p2, width=radius * 2)

    

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

        # Instantiate Renderer
        self.renderer = StateRenderer(eyes, self)
    
    def get_state(self):
        return self.state_machine.get_state()
    
    def get_current_state_ctx(self):
        return StateContext(
            state=self.state_machine.get_state(),
            state_entry_time=self.state_entry_time,
            x=self.eyes.target_x,
            y=self.eyes.target_y
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
            self.set_state(state_ctx.state)
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

    @property
    def is_media_playing(self):
        return self.renderer.is_media_playing

    @is_media_playing.setter
    def is_media_playing(self, value):
        self.renderer.is_media_playing = value

    @property
    def interrupt_state(self):
        return self.renderer.interrupt_state

    @interrupt_state.setter
    def interrupt_state(self, value):
        self.renderer.interrupt_state = value
