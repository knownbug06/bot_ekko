import random
import math
import pygame
from datetime import datetime
from bot_ekko.config import CYAN, RED, STATES
from bot_ekko.modules.effects import EffectsRenderer

class StateHandler:
    """Handles ONLY logic, timers, and state decisions."""
    def __init__(self, eyes, state_machine):
        self.eyes = eyes
        self.state_machine = state_machine
        self.last_blink = 0
        self.last_mood_change = 0
        
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
        
        if self.state_machine.get_state() == "WAKING":
            self.wake_stage = 0
            self.wake_timer = pygame.time.get_ticks()
            # Mood/State params are handled by body physics now

    def trigger_wake(self):
        """Force wake up sequence."""
        if self.state_machine.get_state() == "SLEEPING":
            self.set_state("WAKING")

    def handle_states(self, surface, now, sleep_h, sleep_m, wake_h, wake_m):
        self._check_schedule(sleep_h, sleep_m, wake_h, wake_m)
        
        current_state = self.state_machine.get_state()
        handler_name = f"handle_{current_state}"
        handler = getattr(self, handler_name, None)
        if handler:
            handler(surface, now)
        else:
            print(f"Warning: No handler for state {current_state}")

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
                 self.set_state("SLEEPING")
        else:
            if current_state == "SLEEPING":
                self.set_state("WAKING")

    def handle_PROXIMITY(self, surface, now):
        self.eyes.target_x = random.randint(-100, 100)
        self.eyes.target_y = random.randint(-40, 40)
        self.eyes.last_gaze = now
        self.random_blink(surface, now)
        self._draw_generic(surface)
    
    # def handle_DISTANCE(self, surface, now):
    #     self.eyes.target_x = random.randint(-100, 100)
    #     self.eyes.target_y = random.randint(-40, 40)
    #     self.eyes.last_gaze = now
    #     self.random_blink(surface, now)
    #     self._draw_generic(surface)
    
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
             self.set_state("ACTIVE")
             self.last_mood_change = now
             
        # --- RENDERING ---
        self._draw_generic(surface)
    
    def handle_ANGRY(self, surface, now):
        # --- LOGIC ---
        if now - self.eyes.last_gaze > random.randint(1000, 3000):
            self.eyes.target_x = random.randint(-80, 80)
            self.eyes.target_y = random.randint(-30, 30)
            self.eyes.last_gaze = now

        if now - self.last_mood_change > random.randint(10000, 20000):
             self.set_state("ACTIVE")
             self.last_mood_change = now
             
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
        w, h = 160, int(self.eyes.curr_lh)
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
        
        WHITE = (255, 255, 255)
        self._draw_rounded_poly(surface, WHITE, l_poly, r)
        self._draw_rounded_poly(surface, WHITE, r_poly, r)

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
            self.set_state("ACTIVE")
            self.last_mood_change = now
            
        # --- RENDERING ---
        self._draw_generic(surface)

    def handle_INTERFACE(self, surface, now):
        pass

    def _draw_generic(self, surface):
        state_data = STATES.get(self.state_machine.get_state(), STATES["ACTIVE"])
        _, _, radius, _, _ = state_data
        # Draw Left Eye
        pygame.draw.rect(surface, CYAN, 
            (int(self.eyes.curr_lx - 80), int(self.eyes.curr_ly - self.eyes.curr_lh//2), 160, int(self.eyes.curr_lh)), 
            border_radius=radius)
        # Draw Right Eye
        pygame.draw.rect(surface, CYAN, 
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
