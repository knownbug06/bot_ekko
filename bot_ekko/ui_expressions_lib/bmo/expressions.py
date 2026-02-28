import pygame
import math
from bot_ekko.core.state_registry import StateRegistry

# Colors
BMO_TEAL = (106, 191, 163)
BMO_DARK = (20, 40, 30) # Almost black, dark green
BMO_BLUSH = (255, 180, 180)
BMO_MOUTH_INNER = (50, 20, 20) # Dark red/brown for mouth interior
BMO_TEETH = (240, 240, 250)    # Off-white
BMO_TONGUE = (200, 100, 100)   # Pinkish red

# Configurable Sizes
EYE_RADIUS = 25
MOUTH_WIDTH = 80
MOUTH_HEIGHT = 60
SMILE_WIDTH = 100
SMILE_HEIGHT = 50

class BMOExpressions:
    def __init__(self, physics, state_machine):
        self.physics = physics
        self.state_machine = state_machine
        
    def _draw_background(self, surface):
        surface.fill(BMO_TEAL)
        
    def _draw_eyes(self, surface):
        """Draw simple dot eyes based on physics position."""
        lx, ly = int(self.physics.curr_lx), int(self.physics.curr_ly)
        rx, ry = int(self.physics.curr_rx), int(self.physics.curr_ry)
        
        radius = EYE_RADIUS
        
        # Blink logic handled by physics blink_progress (0.0 open, 1.0 closed)
        blink = self.physics.blink_progress
        
        # Left Eye
        if blink < 1.0:
            h = int(radius * 2 * (1.0 - blink))
            if h < 2: h = 2
            pygame.draw.ellipse(surface, BMO_DARK, (lx - radius, ly - h//2, radius*2, h))
        else:
             pygame.draw.line(surface, BMO_DARK, (lx - radius, ly), (lx + radius, ly), 3)

        # Right Eye
        if blink < 1.0:
            h = int(radius * 2 * (1.0 - blink))
            if h < 2: h = 2
            pygame.draw.ellipse(surface, BMO_DARK, (rx - radius, ry - h//2, radius*2, h))
        else:
             pygame.draw.line(surface, BMO_DARK, (rx - radius, ry), (rx + radius, ry), 3)

    def _draw_eyes_happy_closed(self, surface):
        lx, ly = int(self.physics.curr_lx), int(self.physics.curr_ly)
        rx, ry = int(self.physics.curr_rx), int(self.physics.curr_ry)
        radius = EYE_RADIUS
        
        # Draw Inverted U for closed happy eyes
        # Left Arg
        rect_l = pygame.Rect(lx - radius, ly - radius, radius*2, radius*2)
        pygame.draw.arc(surface, BMO_DARK, rect_l, 0, math.pi, 3)
        
        # Right Arc
        rect_r = pygame.Rect(rx - radius, ry - radius, radius*2, radius*2)
        pygame.draw.arc(surface, BMO_DARK, rect_r, 0, math.pi, 3)

    def _draw_eyes_angry(self, surface):
        lx, ly = int(self.physics.curr_lx), int(self.physics.curr_ly)
        rx, ry = int(self.physics.curr_rx), int(self.physics.curr_ry)
        radius = EYE_RADIUS
        
        # Draw slanted eyebrows / angry eyes
        # Left Eye - slanted down right
        pygame.draw.line(surface, BMO_DARK, (lx - radius, ly - radius + 10), (lx + radius, ly + 5), 5)
        pygame.draw.circle(surface, BMO_DARK, (lx, ly + 5), radius - 5)

        # Right Eye - slanted down left
        pygame.draw.line(surface, BMO_DARK, (rx - radius, ly + 5), (rx + radius, ly - radius + 10), 5)
        pygame.draw.circle(surface, BMO_DARK, (rx, ry + 5), radius - 5)


    def _draw_mouth_smile(self, surface):
        center_x = (self.physics.curr_lx + self.physics.curr_rx) // 2
        # Move mouth relative to eye center
        eye_y_center = (self.physics.curr_ly + self.physics.curr_ry) // 2
        center_y = int(eye_y_center + 60) # 60px below eyes
        
        w = SMILE_WIDTH
        h = SMILE_HEIGHT
        rect = pygame.Rect(center_x - w//2, center_y - h//2, w, h)
        pygame.draw.arc(surface, BMO_DARK, rect, math.pi, 2*math.pi, 5)

    def _draw_mouth_open(self, surface):
        center_x = (self.physics.curr_lx + self.physics.curr_rx) // 2
        # Move mouth relative to eye center
        eye_y_center = (self.physics.curr_ly + self.physics.curr_ry) // 2
        center_y = int(eye_y_center + 60)
        
        # Dimensions
        w = MOUTH_WIDTH
        h = MOUTH_HEIGHT
        
        # 1. Mouth Interior (D-Shape)
        # Rect with rounded bottom corners
        mouth_rect = pygame.Rect(center_x - w//2, center_y - h//2, w, h)
        pygame.draw.rect(surface, BMO_MOUTH_INNER, mouth_rect, 
                         border_bottom_left_radius=20, 
                         border_bottom_right_radius=20)
                         
        # 2. Teeth (Top)
        # Small curve or rect at the top
        teeth_h = 10
        teeth_rect = pygame.Rect(center_x - w//2 + 5, center_y - h//2, w - 10, teeth_h)
        pygame.draw.rect(surface, BMO_TEETH, teeth_rect, 
                         border_bottom_left_radius=5, 
                         border_bottom_right_radius=5)
                         
        # 3. Tongue (Bottom)
        # Ellipse at the bottom, clipped by the D-shape?
        # Simpler: Just draw a flattened ellipse/arc at the bottom of the mouth
        tongue_w = 30
        tongue_h = 20
        tongue_rect = pygame.Rect(center_x - tongue_w//2, center_y + h//2 - tongue_h + 2, tongue_w, tongue_h)
        pygame.draw.ellipse(surface, BMO_TONGUE, tongue_rect)

    def _draw_mouth_frown(self, surface):
        center_x = (self.physics.curr_lx + self.physics.curr_rx) // 2
        eye_y_center = (self.physics.curr_ly + self.physics.curr_ry) // 2
        center_y = int(eye_y_center + 70) # Frown sits a bit lower
        
        w = SMILE_WIDTH
        h = SMILE_HEIGHT
        rect = pygame.Rect(center_x - w//2, center_y, w, h)
        pygame.draw.arc(surface, BMO_DARK, rect, 0, math.pi, 5)

    def _draw_mouth_line(self, surface):
        center_x = (self.physics.curr_lx + self.physics.curr_rx) // 2
        eye_y_center = (self.physics.curr_ly + self.physics.curr_ry) // 2
        center_y = int(eye_y_center + 60)
        
        w = SMILE_WIDTH
        start = (center_x - w//2, center_y)
        end = (center_x + w//2, center_y)
        pygame.draw.line(surface, BMO_DARK, start, end, 5)

    def _draw_mouth_amused(self, surface):
        center_x = (self.physics.curr_lx + self.physics.curr_rx) // 2
        eye_y_center = (self.physics.curr_ly + self.physics.curr_ry) // 2
        center_y = int(eye_y_center + 60)
        
        # Smirk - tilted line or curve
        w = SMILE_WIDTH
        h = SMILE_HEIGHT // 2
        rect = pygame.Rect(center_x - w//2, center_y - h, w, h*2)
        pygame.draw.arc(surface, BMO_DARK, rect, 3.4, 6.0, 5)

    def _draw_mouth_surprised(self, surface, large=False):
        center_x = (self.physics.curr_lx + self.physics.curr_rx) // 2
        eye_y_center = (self.physics.curr_ly + self.physics.curr_ry) // 2
        center_y = int(eye_y_center + 70)
        
        radius = 15 if not large else 25
        pygame.draw.circle(surface, BMO_DARK, (center_x, center_y), radius, 5)

    def _draw_mouth_angry(self, surface, open_mouth=False):
        center_x = (self.physics.curr_lx + self.physics.curr_rx) // 2
        eye_y_center = (self.physics.curr_ly + self.physics.curr_ry) // 2
        center_y = int(eye_y_center + 70)
        
        w = SMILE_WIDTH
        
        if open_mouth:
             # Shouting mouth
            h = 40
            rect = pygame.Rect(center_x - w//2, center_y - h//2, w, h)
            pygame.draw.rect(surface, BMO_MOUTH_INNER, rect, border_radius=10)
            pygame.draw.rect(surface, BMO_DARK, rect, 3, border_radius=10)
            # Tongue
            pygame.draw.ellipse(surface, BMO_TONGUE, (center_x - 15, center_y + 5, 30, 15))
        else:
            # Gritted teeth / zigzag
            start_x = center_x - w//2
            for i in range(0, w, 10):
                pygame.draw.line(surface, BMO_DARK, (start_x + i, center_y), (start_x + i + 5, center_y + 10), 3)
                pygame.draw.line(surface, BMO_DARK, (start_x + i + 5, center_y + 10), (start_x + i + 10, center_y), 3)


    def draw_default(self, surface):
        self._draw_background(surface)
        self._draw_eyes(surface)
        self._draw_mouth_smile(surface)

    def draw_happy(self, surface, eyes_closed=False):
        self._draw_background(surface)
        if eyes_closed:
            self._draw_eyes_happy_closed(surface)
        else:
            self._draw_eyes(surface)
        self._draw_mouth_open(surface)

    def draw_sad(self, surface, mouth_open=False):
        self._draw_background(surface)
        self._draw_eyes(surface)
        if mouth_open:
            # Small open 'o' for sighing/sadness
            self._draw_mouth_surprised(surface, large=False)
        else:
            self._draw_mouth_frown(surface)

    def draw_angry(self, surface, mouth_open=False):
        self._draw_background(surface)
        self._draw_eyes_angry(surface)
        self._draw_mouth_angry(surface, open_mouth=mouth_open)

    def draw_amused(self, surface, mouth_open=False):
        self._draw_background(surface)
        if mouth_open:
            self._draw_eyes_happy_closed(surface)
            self._draw_mouth_smile(surface)
        else:
            self._draw_eyes(surface)
            self._draw_mouth_amused(surface)
            
    def draw_surprised(self, surface, mouth_open=False):
        self._draw_background(surface)
        self._draw_eyes(surface)
        self._draw_mouth_surprised(surface, large=mouth_open)


    def draw_neutral(self, surface):
        self._draw_background(surface)
        self._draw_eyes(surface)
        self._draw_mouth_line(surface)
