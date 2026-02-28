import pygame
import math
import random
from bot_ekko.sys_config import CYAN, RED, WHITE
from bot_ekko.core.state_registry import StateRegistry

class EyesExpressions:
    def __init__(self, eyes, state_machine):
        self.eyes = eyes
        self.state_machine = state_machine
        
        # Rainbow state cache
        self.rainbow_surf = None
        self.rainbow_layer = None
        self.eyes_mask_layer = None
    
    def draw_uwu_eyes(self, surface, color=CYAN, blush_color=(255, 182, 193)):
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        
        # 1. Draw Eyes (U shape)
        eye_radius = 80
        line_width = 10
        
        # Left Eye (pi to 2pi -> Smile/U)
        l_rect = pygame.Rect(lx - eye_radius, ly - eye_radius - 50, eye_radius*2, eye_radius*2)
        pygame.draw.arc(surface, color, l_rect, math.pi, 2*math.pi, line_width)
        
        # Right Eye
        r_rect = pygame.Rect(rx - eye_radius, ry - eye_radius - 50, eye_radius*2, eye_radius*2)
        pygame.draw.arc(surface, color, r_rect, math.pi, 2*math.pi, line_width)
        
        # 2. Draw Mouth
        center_x = (lx + rx) // 2
        center_y = (ly + ry) // 2 + 60 

        mouth_radius = 40
        # Left 'u' of mouth
        mouth_l_rect = pygame.Rect(center_x - 2*mouth_radius, center_y, 2*mouth_radius, 2*mouth_radius)
        pygame.draw.arc(surface, color, mouth_l_rect, math.pi, 2*math.pi, line_width)
        
        # Right 'u' of mouth
        mouth_r_rect = pygame.Rect(center_x, center_y, 2*mouth_radius, 2*mouth_radius)
        pygame.draw.arc(surface, color, mouth_r_rect, math.pi, 2*math.pi, line_width)
        
        # 3. Draw Blush
        blush_w, blush_h = 90, 40
        blush_offset_y = 60
        
        l_blush = pygame.Rect(lx - blush_w//2 - 50, ly + blush_offset_y, blush_w, blush_h)
        r_blush = pygame.Rect(rx - blush_w//2 + 50, ry + blush_offset_y, blush_w, blush_h)
        
        pygame.draw.ellipse(surface, blush_color, l_blush)
        pygame.draw.ellipse(surface, blush_color, r_blush)

    def draw_rainbow_eyes(self, surface, now):
        w, h = surface.get_size()
        
        if (self.rainbow_surf is None or 
            self.rainbow_layer is None or 
            self.rainbow_layer.get_size() != (w, h)):
            
            # self.create_rainbow_gradient is defined below, verify method name
            self.rainbow_surf = self.create_rainbow_gradient(w, h)
            self.rainbow_layer = pygame.Surface((w, h), pygame.SRCALPHA)
            self.eyes_mask_layer = pygame.Surface((w, h), pygame.SRCALPHA)
            
        offset_x = int((now / 5) % w)
        
        self.rainbow_layer.blit(self.rainbow_surf, (-offset_x, 0))
        self.rainbow_layer.blit(self.rainbow_surf, (w - offset_x, 0))

        self.eyes_mask_layer.fill((0, 0, 0, 0)) # Clear transparent
        self.draw_generic(self.eyes_mask_layer, (255, 255, 255))
        
        self.eyes_mask_layer.blit(self.rainbow_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        surface.blit(self.eyes_mask_layer, (0, 0))

    def draw_angry_eyes(self, surface, color=RED):
        self.draw_slanted_eyes(surface, color, slant_inwards=True)

    def draw_scared_eyes(self, surface, color=WHITE):
        self.draw_slanted_eyes(surface, color, slant_inwards=False)

    def draw_uwu_mouth(self, surface, color=CYAN):
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        
        center_x = (lx + rx) // 2
        center_y = (ly + ry) // 2 + 100 

        radius = 40
        width = 10
        
        left_rect = pygame.Rect(center_x - 2*radius, center_y, 2*radius, 2*radius)
        pygame.draw.arc(surface, color, left_rect, math.pi, 2*math.pi, width)
        
        right_rect = pygame.Rect(center_x, center_y, 2*radius, 2*radius)
        pygame.draw.arc(surface, color, right_rect, math.pi, 2*math.pi, width)

    def create_rainbow_gradient(self, w, h):
        surf = pygame.Surface((w, h))
        import colorsys
        for x in range(w):
            hue = x / w
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            color = (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
            pygame.draw.line(surf, color, (x, 0), (x, h))
        return surf

    def draw_rect_eyes(self, surface, color, top_r=None, bot_r=None):
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        w = 160
        h_l, h_r = int(self.eyes.curr_lh), int(self.eyes.curr_rh)
        
        tr_l, tr_r = top_r, top_r
        br_l, br_r = bot_r, bot_r
        
        if top_r is None or bot_r is None:
            state_data = StateRegistry.get_state_data(self.state_machine.get_state())
            if not state_data:
                state_data = StateRegistry.get_state_data(StateRegistry.ACTIVE)
            
            _, _, radius, _, _ = state_data
            tr_l = tr_r = br_l = br_r = radius
        
        pygame.draw.rect(surface, color, 
            (lx - w//2, ly - h_l//2, w, h_l), 
            border_top_left_radius=tr_l, 
            border_top_right_radius=tr_l,
            border_bottom_left_radius=br_l,
            border_bottom_right_radius=br_l)
            
        pygame.draw.rect(surface, color, 
            (rx - w//2, ry - h_r//2, w, h_r), 
            border_top_left_radius=tr_r, 
            border_top_right_radius=tr_r,
            border_bottom_left_radius=br_r,
            border_bottom_right_radius=br_r)

    def draw_generic(self, surface, color=CYAN):
        self.draw_rect_eyes(surface, color)

    def draw_happy_eyes(self, surface, color=CYAN):
        w = 160
        self.draw_rect_eyes(surface, color, top_r=w//2, bot_r=10)

    def draw_rounded_poly(self, surface, color, points, radius):
        pygame.draw.polygon(surface, color, points)
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            pygame.draw.circle(surface, color, p1, radius)
            pygame.draw.line(surface, color, p1, p2, width=radius * 2) 

    def draw_slanted_eyes(self, surface, color, slant_inwards=True):
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        h_l, h_r = int(self.eyes.curr_lh), int(self.eyes.curr_rh)
        
        slant = 35
        r = 10 
        w = 160
        half_w = w // 2
        
        l_tl_off = 0 if slant_inwards else slant
        l_tr_off = slant if slant_inwards else 0
        
        r_tl_off = slant if slant_inwards else 0
        r_tr_off = 0 if slant_inwards else slant
        
        l_poly = [
            (lx - half_w + r, ly - h_l//2 + l_tl_off + r),      
            (lx + half_w - r, ly - h_l//2 + l_tr_off + r),      
            (lx + half_w - r, ly + h_l//2 - r),                 
            (lx - half_w + r, ly + h_l//2 - r)                  
        ]
        
        r_poly = [
            (rx - half_w + r, ry - h_r//2 + r_tl_off + r),
            (rx + half_w - r, ry - h_r//2 + r_tr_off + r),
            (rx + half_w - r, ry + h_r//2 - r),
            (rx - half_w + r, ry + h_r//2 - r)
        ]
        
        self.draw_rounded_poly(surface, color, l_poly, r)
        self.draw_rounded_poly(surface, color, r_poly, r)

    def draw_sad_eyes(self, surface, color=CYAN, crying=False):
        # Sad eyes slant outwards (Inner corners LOW, Outer corners LOW? No, Inner High, Outer Low makes 'sadder' look?
        # Typically Sad eyes slant DOWN-OUTWARDS (Inner High, Outer Low).
        # Let's reuse slanted logic but verify direction.
        # ANGRY (Inwards=True)  -> Inner Low, Outer High? No, let's re-read slanted logic.
        
        # Slanted Logic:
        # Inwards=True: Left Eye: TopLeft=0, TopRight=Slant. -> Inner Top is HIGHER.
        # Wait, l_tr is Inner for Left Eye?
        # Left Eye: (lx - half_w, ...). Right side of Left Eye is Inner.
        # l_tr_off = slant. So Inner Top is LOWER (y + off).
        # So Inwards=True (ANGRY) -> Inner Top is LOWER. Brow furrows down in middle. Correct.
        
        # SAD: Inner Top should be HIGHER. Outer Top should be LOWER.
        # So Inwards=False?
        # Inwards=False: l_tr_off = 0. l_tl_off = slant.
        # Inner Top (Right side of Left Eye) is HIGHER (0 offset). Outer Top (Left side) is LOWER (+slant offset).
        # This matches SCARED/SAD shape.
        
        self.draw_slanted_eyes(surface, color, slant_inwards=False)
        
        if crying:
            # Draw tears
            lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
            rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
            h_l, h_r = int(self.eyes.curr_lh), int(self.eyes.curr_rh)
            
            # Tear drops
            tear_color = (0, 200, 255) # Cyan-ish blue
            
            # Left Tear
            pygame.draw.circle(surface, tear_color, (lx, ly + h_l//2 + 20), 8)
            pygame.draw.circle(surface, tear_color, (lx - 10, ly + h_l//2 + 40), 6)
            
            # Right Tear
            pygame.draw.circle(surface, tear_color, (rx, ry + h_r//2 + 20), 8)
            pygame.draw.circle(surface, tear_color, (rx + 10, ry + h_r//2 + 40), 6)

    def draw_crying_eyes(self, surface, color=CYAN):
        self.draw_sad_eyes(surface, color, crying=True)

    def draw_excited_eyes(self, surface, color=CYAN):
        # Big wide eyes, maybe with sparkles?
        # Just use Rect Eyes but with large pupils/iris if we had them.
        # Since we just draw rects, let's draw extra stylistic elements.
        
        self.draw_rect_eyes(surface, color)
        
        # Draw "sparkles"
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        
        sparkle_color = WHITE
        
        # Star shape or diamond
        def draw_diamond(cx, cy, size):
            pts = [(cx, cy-size), (cx+size, cy), (cx, cy+size), (cx-size, cy)]
            pygame.draw.polygon(surface, sparkle_color, pts)
            
        draw_diamond(lx - 40, ly - 40, 15)
        draw_diamond(rx + 40, ry - 40, 15)

    def draw_amused_eyes(self, surface, color=CYAN):
        # Arched up like Happy, but maybe squintier?
        # Happy: top_r=w//2, bot_r=10
        # Amused: top_r=w//2, bot_r=30?
        w = 160
        self.draw_rect_eyes(surface, color, top_r=w//2, bot_r=40)

    def draw_surprised_eyes(self, surface, color=CYAN):
        # Wide Ovals or Circles
        # We can simulate this by setting border radius to half width/height
        lx, ly = int(self.eyes.curr_lx), int(self.eyes.curr_ly)
        rx, ry = int(self.eyes.curr_rx), int(self.eyes.curr_ry)
        w = 160
        h_l, h_r = int(self.eyes.curr_lh), int(self.eyes.curr_rh) # These should be large from physics
        
        # Draw ellipses for pure surprise
        l_rect = pygame.Rect(lx - w//2, ly - h_l//2, w, h_l)
        r_rect = pygame.Rect(rx - w//2, ry - h_r//2, w, h_r)
        
        pygame.draw.ellipse(surface, color, l_rect)
        pygame.draw.ellipse(surface, color, r_rect)
        
        # Small pupil in center?
        pygame.draw.circle(surface, (0, 0, 0), (lx, ly), 20)
        pygame.draw.circle(surface, (0, 0, 0), (rx, ry), 20)

    def draw_confused_eyes(self, surface, color=CYAN):
        # One eye raised, one eye normal/squinted
        # Logic handled in Physics (Height), here we just draw rects.
        # But maybe we want different shapes?
        # Let's just use generic rects, physics handles asymmetry.
        self.draw_rect_eyes(surface, color)
