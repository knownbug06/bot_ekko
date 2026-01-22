import random
import math
import pygame
from datetime import datetime
from bot_ekko.sys_config import *
from bot_ekko.modules.effects import EffectsRenderer
from bot_ekko.modules.media_interface import MediaModule
from bot_ekko.core.movements import Looks
from bot_ekko.core.logger import get_logger
from bot_ekko.core.models import StateContext, CommandNames
from bot_ekko.core.scheduler import Scheduler

logger = get_logger("StateRenderer")

class StateRenderer:
    def __init__(self, eyes, state_handler, command_center, interrupt_manager=None):
        self.eyes = eyes
        self.last_blink = 0
        self.last_mood_change = 0
        self.interrupt_manager = interrupt_manager
        self.state_handler = state_handler
        self.command_center = command_center
        
        # self.media_player = MediaModule(self.interrupt_manager, self.command_center)
        self.media_player = None
        # self.media_player.start()
        
        # Rendering attributes
        self.effects = EffectsRenderer()
        self.particles = []
        self.wake_stage = 0
        
        # Scheduler
        self.scheduler = Scheduler(SCHEDULE_FILE_PATH)
        
        # Proxies to StateHandler attributes needed for logic/rendering
        self.looks = Looks(self.eyes, state_handler.state_machine)
        self.state_machine = state_handler.state_machine
        
        # Cache for Rainbow state
        self.rainbow_surf = None
        self.rainbow_layer = None
        self.eyes_mask_layer = None


    def trigger_wake(self):
        """Force wake up sequence."""
        if self.state_handler.get_state() == "SLEEPING":
            logger.info("Triggering WAKING state from SLEEPING")
            self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": "WAKING"})

    def render(self, surface, now):
        """
        Main update loop for state handling.
        
        Checks schedules, determines the current state, and calls the appropriate 
        specific handler method (e.g., handle_ACTIVE).
        """
        self._check_schedule(now)
    
        current_state = self.state_handler.get_state().upper()
        handler_name = f"handle_{current_state}"
        handler = getattr(self, handler_name, None)
        if handler:
            handler(surface, now, params=self.state_handler.current_state_params)
        else:
            logger.warning(f"Warning: No handler for state {current_state}")

    def _check_schedule(self, now):
        # Grace period on startup (2 seconds) to ensure we start in ACTIVE/Initial state
        if now < 2000:
            return

        current_state = self.state_handler.get_state()
        if current_state == "CHAT":
            return

        now_dt = datetime.now()
        current_state = self.state_handler.get_state()
        
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
        self._draw_generic(surface)

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
        self._draw_generic(surface)
    
    def handle_CANVAS(self, surface, now, params=None):
        # Dispatch to media player update if running
        if self.media_player.is_playing:
            self.media_player.update(surface)
            return

        # Start media if not running
        # The parameter structure coming from EventManager -> InterruptManager -> Here is:
        # events: {"param": {"text": "HELLO"}, "interrupt_name": "canvas"}
        # interrupt manager merges this into the command params.
        # So 'params' here will contain: {'target_state': 'CANVAS', 'param': {'text': 'HELLO'}, 'interrupt_name': 'canvas'}
        
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
        self.looks.look_center()
        self.random_blink(surface, now)
             
        # --- RENDERING ---
        # ANGRY: Inner corners are LOWER (Slant Down-Inwards)
        self._draw_slanted_eyes(surface, color=RED, slant_inwards=True)

    def handle_SCARED(self, surface, now, params=None):
        # --- LOGIC ---
        self.eyes.target_x = random.randint(-40, 40)
        self.eyes.target_y = random.randint(-20, 20)
        self.eyes.last_gaze = now

        self.random_blink(surface, now)
             
        # --- RENDERING ---
        # SCARED: Inner corners are HIGHER (Slant Up-Inwards)
        self._draw_slanted_eyes(surface, color=WHITE, slant_inwards=False)

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
        w, h = surface.get_size()
        
        # 1. Lazy Init / Resize Check
        if (self.rainbow_surf is None or 
            self.rainbow_layer is None or 
            self.rainbow_layer.get_size() != (w, h)):
            
            logger.debug("Initializing Rainbow Surfaces")
            self.rainbow_surf = self._create_rainbow_gradient(w, h)
            self.rainbow_layer = pygame.Surface((w, h), pygame.SRCALPHA)
            self.eyes_mask_layer = pygame.Surface((w, h), pygame.SRCALPHA)
            
        # 2. Calculate offset
        offset_x = int((now / 5) % w)
        
        # 3. Draw Rainbow Pattern (Tile it)
        # We reuse self.rainbow_layer to avoid creation cost, but we need to clear/blit
        # Actually, blitting a chaotic full fill doesn't need clear.
        self.rainbow_layer.blit(self.rainbow_surf, (-offset_x, 0))
        self.rainbow_layer.blit(self.rainbow_surf, (w - offset_x, 0))

        # 4. Draw Eyes Mask
        self.eyes_mask_layer.fill((0, 0, 0, 0)) # Clear transparent
        self._draw_generic(self.eyes_mask_layer, (255, 255, 255))
        
        # 5. Mask rainbow with eyes (Multiply)
        # We want to show Rainbow WHERE Eyes are White.
        # Blit Rainbow onto Eyes with MULTIPLY? No, that keeps intersection.
        # Eyes are White (255), Background Transp (0).
        # White * Rainbow = Rainbow. Transp * Rainbow = Transp.
        self.eyes_mask_layer.blit(self.rainbow_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        surface.blit(self.eyes_mask_layer, (0, 0))

    def handle_CHAT(self, surface, now, params=None):
        """
        Permanent chat state.
        
        States:
        - Loading: params['is_loading'] == True. Show "Thinking..." or animation.
        - Result: params['text'] present. Show text.
        """
        # --- LOGIC ---
        # No eye logic needed for chat-only screen
        
        # --- RENDERING ---
        # No eye drawing
        
        is_loading = False
        text = ""
        
        if params:
            is_loading = params.get("is_loading", False)
            text = params.get("text", "")

        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2 # Centered vertically since no eyes

        if is_loading:
            self.effects.render_loading_dots(surface, center_x, center_y, now)
        elif text:
            try:
                from bot_ekko.sys_config import CHAT_FONT
                font = CHAT_FONT
            except ImportError:
                font = MAIN_FONT
                
            surf = self.media_player._render_wrapped_text(text, font, CYAN, LOGICAL_W - 40)
            rect = surf.get_rect(center=(center_x, center_y))
            surface.blit(surf, rect)

    def handle_WINK(self, surface, now, params=None):
        # --- LOGIC ---
        # Animation Cycle: 4000ms
        # 0-1000: Open (Both Happy)
        # 1000-1200: Closing Right
        # 1200-1400: Closed Right (Hold)
        # 1400-1600: Opening Right
        # 1600-4000: Open (Idle)
        
        cycle_time = (now - self.state_handler.state_entry_time) % 4000
        
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
            self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": "ACTIVE"})
            self.last_mood_change = now
            
        # --- RENDERING ---
        self._draw_generic(surface)

    def handle_INTERFACE(self, surface, now, params=None):
        pass

    def handle_FUNNY(self, surface, now, params=None):
        # Trigger GIF playback if not already playing
        
        if not self.media_player.is_playing:
            # We want to return to ACTIVE (or schedule default) after this, NOT recurse into FUNNY.
            # So we push ACTIVE to history manually and tell play_gif NOT to save current (FUNNY) state.
            
            # Using 0 for entry time and coordinates as defaults
            fallback_ctx = StateContext(state="ACTIVE", state_entry_time=now, x=0, y=0)
            self.state_handler.state_history.append(fallback_ctx)
        
            # Placeholder path - user should replace this
            self.media_player.play_gif(DEFAULT_GIF_PATH, duration=5.0, save_context=False)
            
        # Ensure media player updates
        if self.media_player.is_playing:
             self.media_player.update(surface)
    
    def handle_CLOCK(self, surface, now, params=None):
        # --- LOGIC ---
        
        current_time = datetime.now().strftime("%I:%M %p") # 12-hour format e.g., 01:20 PM
        if current_time.startswith("0"):
            current_time = current_time[1:] # Strip leading zero
            
        # Ensure Media Player is showing the correct time
        # We give it a long duration so it doesn't self-stop; Scheduler controls state exit.
        
        from bot_ekko.sys_config import CLOCK_FONT
        
        target_text = current_time.capitalize()
        # Check text AND font (we can't easily check font, but text change is enough trigger usually)
        # Or just force update if text matches but maybe font is wrong? 
        # Simpler: If text changes, update. 
        if not self.media_player.is_playing or self.media_player.current_text != target_text:
             self.media_player.show_text(current_time, duration=60.0, save_context=False, font=CLOCK_FONT)
             
        # --- RENDERING ---
        self.media_player.update(surface)


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

    def _draw_rect_eyes(self, surface, color, top_r=None, bot_r=None):
        """
        Generic helper to draw rounded rectangular eyes.
        If top_r/bot_r are None, uses state configuration (generic).
        If provided, overrides (e.g. for Happy eyes).
        """
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        w = 160
        h_l, h_r = int(self.eyes.curr_lh), int(self.eyes.curr_rh)
        
        tr_l, tr_r = top_r, top_r
        br_l, br_r = bot_r, bot_r
        
        # Default to Config if not specified
        if top_r is None or bot_r is None:
            state_data = STATES.get(self.state_machine.get_state(), STATES["ACTIVE"])
            _, _, radius, _, _ = state_data
            tr_l = tr_r = br_l = br_r = radius
        
        # Left Eye
        pygame.draw.rect(surface, color, 
            (lx - w//2, ly - h_l//2, w, h_l), 
            border_top_left_radius=tr_l, 
            border_top_right_radius=tr_l,
            border_bottom_left_radius=br_l,
            border_bottom_right_radius=br_l)
            
        # Right Eye
        pygame.draw.rect(surface, color, 
            (rx - w//2, ry - h_r//2, w, h_r), 
            border_top_left_radius=tr_r, 
            border_top_right_radius=tr_r,
            border_bottom_left_radius=br_r,
            border_bottom_right_radius=br_r)

    def _draw_generic(self, surface, color=CYAN):
        self._draw_rect_eyes(surface, color)

    def _draw_happy_eyes(self, surface, color=CYAN):
        w = 160
        self._draw_rect_eyes(surface, color, top_r=w//2, bot_r=10)

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

    def _draw_slanted_eyes(self, surface, color, slant_inwards=True):
        """
        Draws slanted eyes for ANGRY (slant_inwards=True) or SCARED (slant_inwards=False).
        """
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        h_l, h_r = int(self.eyes.curr_lh), int(self.eyes.curr_rh)
        
        slant = 35
        r = 10 # Corner radius
        w = 160
        half_w = w // 2
        
        # Calculate offsets based on slant direction
        # If slant_inwards (ANGRY): Outer corners High, Inner corners Low (+slant)
        # If !slant_inwards (SCARED): Outer corners Low (+slant), Inner corners High
        
        # Left Eye (Inner is Right side)
        # Right Eye (Inner is Left side)
        
        l_tl_off = 0 if slant_inwards else slant
        l_tr_off = slant if slant_inwards else 0
        
        r_tl_off = slant if slant_inwards else 0
        r_tr_off = 0 if slant_inwards else slant
        
        l_poly = [
            (lx - half_w + r, ly - h_l//2 + l_tl_off + r),      # Top Left
            (lx + half_w - r, ly - h_l//2 + l_tr_off + r),      # Top Right
            (lx + half_w - r, ly + h_l//2 - r),                 # Bottom Right
            (lx - half_w + r, ly + h_l//2 - r)                  # Bottom Left
        ]
        
        r_poly = [
            (rx - half_w + r, ry - h_r//2 + r_tl_off + r),      # Top Left
            (rx + half_w - r, ry - h_r//2 + r_tr_off + r),      # Top Right
            (rx + half_w - r, ry + h_r//2 - r),                 # Bottom Right
            (rx - half_w + r, ry + h_r//2 - r)                  # Bottom Left
        ]
        
        self._draw_rounded_poly(surface, color, l_poly, r)
        self._draw_rounded_poly(surface, color, r_poly, r)
