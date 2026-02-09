import pygame
import math
import random
from bot_ekko.sys_config import STATES, CYAN, RED, WHITE

class EyesExpressions:
    def __init__(self, eyes, state_machine):
        self.eyes = eyes
        self.state_machine = state_machine
    
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
            state_data = STATES.get(self.state_machine.get_state(), STATES["ACTIVE"])
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
