import random
import math
import pygame
from datetime import datetime
from bot_ekko.config import *
from bot_ekko.modules.effects import EffectsRenderer
from bot_ekko.core.movements import Looks
from bot_ekko.core.logger import get_logger

logger = get_logger("StateHandler")

class StateHandler:
    """Handles ONLY logic, timers, and state decisions."""
    def __init__(self, eyes, state_machine):
        self.eyes = eyes
        self.state_machine = state_machine
        self.last_blink = 0
        self.last_mood_change = 0

        self.looks = Looks(self.eyes, self)
        
        # State logic variables
        self.wake_stage = 0 
        self.wake_timer = 0
        self.particles = [] # For Zzz
        self.effects = EffectsRenderer()

        self.interrupt_state = False
        self.state_entry_time = 0

    def set_state(self, new_state):
        args = []
        if isinstance(new_state, tuple):
             new_state, *args = new_state
        
        current_state = self.state_machine.get_state()
        if current_state != new_state:
            self.state_machine.set_state(new_state)
            self.state_entry_time = pygame.time.get_ticks()
            logger.info(f"State transition: {current_state} -> {new_state}, state_entry_time: {self.state_entry_time}")
        
        if self.state_machine.get_state() == "WAKING":
            self.wake_stage = 0
            self.wake_timer = pygame.time.get_ticks()
            # Mood/State params are handled by body physics now

    def trigger_wake(self):
        """Force wake up sequence."""
        if self.state_machine.get_state() == "SLEEPING":
            logger.info("Triggering WAKING state from SLEEPING")
            self.set_state("WAKING")

    def handle_states(self, surface, now, sleep_h, sleep_m, wake_h, wake_m):
        self._check_schedule(sleep_h, sleep_m, wake_h, wake_m)
        
        current_state = self.state_machine.get_state()
        handler_name = f"handle_{current_state}"
        handler = getattr(self, handler_name, None)
        if handler:
            handler(surface, now)
        else:
            logger.warning(f"Warning: No handler for state {current_state}")

    def _check_schedule(self, sleep_h, sleep_m, wake_h, wake_m):
        now_dt = datetime.now()
        current_total = now_dt.hour * 60 + now_dt.minute
        sleep_total = sleep_h * 60 + sleep_m
        wake_total = wake_h * 60 + wake_m

        if sleep_total > wake_total: # Over midnight
            in_sleep = current_total >= sleep_total or current_total < wake_total
        else: # Same day
            in_sleep = sleep_total <= current_total < wake_total

        current_state = self.state_machine.get_state()
        if in_sleep:
            if current_state != "SLEEPING" and current_state != "WAKING" and not self.interrupt_state:
                logger.info("Triggering SLEEPING state from schedule")
                self.set_state("SLEEPING")
        else:
            if current_state == "SLEEPING":
                logger.info("Triggering WAKING state from schedule")
                self.set_state("WAKING")
    
    def random_blink(self, surface, now):
        if self.eyes.blink_phase == "IDLE" and (now - self.last_blink > random.randint(3000, 9000)):
            self.eyes.blink_phase = "CLOSING"
            self.last_blink = now

    def handle_ACTIVE(self, surface, now):
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
                self.set_state("SQUINTING")
                self.last_mood_change = now

        # 3. Random Blink
        self.random_blink(surface, now)

            
        # --- RENDERING ---
        self._draw_generic(surface)

    def handle_SQUINTING(self, surface, now):
        # --- LOGIC ---
        if now - self.eyes.last_gaze > random.randint(2000, 5000):
            self.eyes.target_x = random.randint(-100, 100)
            self.eyes.target_y = random.randint(-40, 40)
            self.eyes.last_gaze = now
            
        if now - self.last_mood_change > random.randint(2000, 5000):
            logger.info("Triggering ACTIVE state from random mood")
            self.set_state("ACTIVE")
            self.last_mood_change = now
             
        # --- RENDERING ---
        self._draw_generic(surface)
    
    def handle_ANGRY(self, surface, now):
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

    def handle_SCARED(self, surface, now):
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

    def handle_HAPPY(self, surface, now):
        # --- LOGIC ---
        self.looks.look_up()
        self.random_blink(surface, now)

        # --- RENDERING ---
        self._draw_happy_eyes(surface)

    def handle_RAINBOW_EYES(self, surface, now):
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

    def handle_WINK(self, surface, now):
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

    def _create_rainbow_gradient(self, w, h):
        surf = pygame.Surface((w, h))
        import colorsys
        for x in range(w):
            hue = x / w
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            color = (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
            pygame.draw.line(surf, color, (x, 0), (x, h))
        return surf

    def handle_SLEEPING(self, surface, now):
        # --- LOGIC ---
        self.eyes.target_x = math.sin(now / 1000) * 15
        self.eyes.target_y = 25
        self._update_particles(now)
        
        # --- RENDERING ---
        self._draw_generic(surface)
        self.effects.render_zzz(surface, self.particles)

    def handle_WAKING(self, surface, now):
        # --- LOGIC ---
        elapsed = now - self.wake_timer
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
            self.set_state("ACTIVE")
            self.last_mood_change = now
            
        # --- RENDERING ---
        self._draw_generic(surface)

    def handle_INTERFACE(self, surface, now):
        pass

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
