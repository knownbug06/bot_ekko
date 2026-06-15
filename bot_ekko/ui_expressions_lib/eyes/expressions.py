"""
Generic, data-driven eye renderer.

A single code path draws *any* expression from its EyeSpec geometry:
  - the eyeball is a shape (rect / ellipse / arc / heart / ring), and
  - emotion comes from black "eyelid" polygons slicing the eyeball at an angle.

Adding a new expression therefore never touches this file - it only needs a new
entry in expressions.json. Effects (tears, sparkles, blush, ...) are procedural
and stateless (driven by `now`), so they cost nothing to keep around.
"""
import math
import colorsys

import pygame

from bot_ekko.sys_config import CYAN, RED, WHITE, BLACK, MAIN_FONT
from bot_ekko.ui_expressions_lib.eyes.spec import EyeSpec

PINK = (255, 150, 190)
TEAR = (90, 180, 255)


def _clampi(v, lo, hi):
    return max(lo, min(hi, int(v)))


class EyesRenderer:
    def __init__(self, rig, state_machine):
        self.rig = rig
        self.state_machine = state_machine
        # Cached rainbow gradient (built lazily, reused across frames).
        self._rainbow_grad = None
        self._rainbow_size = None

    # -- public entry point ---------------------------------------------------

    def draw(self, surface, now, effects=()):
        color = self.rig.color()
        lcx, lcy = self.rig.left_center()
        rcx, rcy = self.rig.right_center()
        blink = self.rig.blink_factor

        if "rainbow" in effects:
            self._draw_rainbow(surface, now, blink)
        else:
            self._draw_eye(surface, lcx, lcy, self.rig.cur_left, color, blink, "left", now)
            self._draw_eye(surface, rcx, rcy, self.rig.cur_right, color, blink, "right", now)

        for fx in effects:
            fn = getattr(self, f"_fx_{fx}", None)
            if fn:
                fn(surface, now, (lcx, lcy), (rcx, rcy), color)

    # Compatibility shim for legacy callers / fallback rendering.
    def draw_generic(self, surface, color=CYAN):
        lcx, lcy = self.rig.left_center()
        rcx, rcy = self.rig.right_center()
        self._draw_eye(surface, lcx, lcy, self.rig.cur_left, color, self.rig.blink_factor, "left", 0)
        self._draw_eye(surface, rcx, rcy, self.rig.cur_right, color, self.rig.blink_factor, "right", 0)

    # -- single eye -----------------------------------------------------------

    def _draw_eye(self, surface, cx, cy, eye: EyeSpec, color, blink, side, now):
        w = eye.width
        h = max(2.0, eye.height * blink)

        shape = eye.shape
        if shape == "arc":
            self._shape_arc(surface, cx, cy, w, h, color)
            return
        if shape == "heart":
            self._shape_heart(surface, cx, cy, w, eye.height, color)
            return
        if shape == "ring":
            self._shape_ring(surface, cx, cy, w, color, now)
            return

        x = cx - w / 2
        y = cy - h / 2
        if shape == "ellipse":
            pygame.draw.ellipse(surface, color, (x, y, w, h))
        else:  # rect (default)
            r = _clampi(min(eye.radius, w / 2, h / 2), 0, 999)
            pygame.draw.rect(surface, color, (x, y, w, h), border_radius=r)

        self._draw_lids(surface, x, y, w, h, eye, side)

    def _draw_lids(self, surface, x, y, w, h, eye: EyeSpec, side):
        """Overpaint black trapezoids to emulate eyelids. The inner/outer slant
        is what reads as anger / sadness / sleepiness / happiness."""
        if side == "left":
            t_left, t_right = eye.lid_top_outer, eye.lid_top_inner
            b_left, b_right = eye.lid_bottom_outer, eye.lid_bottom_inner
        else:
            t_left, t_right = eye.lid_top_inner, eye.lid_top_outer
            b_left, b_right = eye.lid_bottom_inner, eye.lid_bottom_outer

        if max(t_left, t_right) > 0.01:
            pygame.draw.polygon(surface, BLACK, [
                (x - 2, y - 2), (x + w + 2, y - 2),
                (x + w + 2, y + t_right * h), (x - 2, y + t_left * h),
            ])
        if max(b_left, b_right) > 0.01:
            pygame.draw.polygon(surface, BLACK, [
                (x - 2, y + h + 2), (x + w + 2, y + h + 2),
                (x + w + 2, y + h - b_right * h), (x - 2, y + h - b_left * h),
            ])

    # -- special shapes -------------------------------------------------------

    def _shape_arc(self, surface, cx, cy, w, h, color):
        """Upward smile arc (closed happy eye, ^_^)."""
        thickness = max(10, int(h * 0.22))
        rect = pygame.Rect(int(cx - w / 2), int(cy - h * 0.55), int(w), int(h * 1.5))
        pygame.draw.arc(surface, color, rect, math.pi, 2 * math.pi, thickness)

    def _shape_heart(self, surface, cx, cy, w, h, color):
        lobe = w * 0.27
        ly = cy - h * 0.12
        pygame.draw.circle(surface, color, (int(cx - w * 0.22), int(ly)), int(lobe))
        pygame.draw.circle(surface, color, (int(cx + w * 0.22), int(ly)), int(lobe))
        pygame.draw.polygon(surface, color, [
            (cx - w * 0.49, ly), (cx + w * 0.49, ly), (cx, cy + h * 0.45),
        ])

    def _shape_ring(self, surface, cx, cy, w, color, now):
        pulse = (math.sin(now / 150.0) + 1) / 2
        outer = int(w * 0.4)
        inner = int(w * 0.12 + w * 0.2 * pulse)
        pygame.draw.circle(surface, color, (int(cx), int(cy)), outer, 6)
        pygame.draw.circle(surface, color, (int(cx), int(cy)), inner)

    # -- effects (procedural, stateless) -------------------------------------

    def _fx_mouth(self, surface, now, lc, rc, color):
        cx = (lc[0] + rc[0]) / 2
        cy = max(lc[1], rc[1]) + 150
        rect = pygame.Rect(int(cx - 45), int(cy - 40), 90, 80)
        pygame.draw.arc(surface, color, rect, math.pi, 2 * math.pi, 8)

    def _fx_blush(self, surface, now, lc, rc, color):
        for (cx, cy), dx in ((lc, -55), (rc, 55)):
            pygame.draw.ellipse(surface, PINK, (int(cx + dx - 45), int(cy + 55), 90, 36))

    def _fx_tears(self, surface, now, lc, rc, color):
        drop = (now % 1400) / 1400.0
        for cx, cy in (lc, rc):
            ty = cy + 90 + drop * 120
            pygame.draw.circle(surface, TEAR, (int(cx), int(ty)), 9)
            pygame.draw.circle(surface, TEAR, (int(cx), int(cy + 80)), 6)

    def _fx_sparkles(self, surface, now, lc, rc, color):
        blink = 0.6 + 0.4 * math.sin(now / 200.0)
        size = int(13 * blink)
        for (cx, cy), dx in ((lc, -55), (rc, 55)):
            self._diamond(surface, int(cx + dx), int(cy - 55), size)

    def _fx_sweat(self, surface, now, lc, rc, color):
        drop = (now % 1600) / 1600.0
        cx, cy = rc
        pygame.draw.circle(surface, TEAR, (int(cx + 95), int(cy - 70 + drop * 60)), 10)

    def _fx_pupils(self, surface, now, lc, rc, color):
        for cx, cy in (lc, rc):
            pygame.draw.circle(surface, BLACK, (int(cx), int(cy)), 24)

    def _fx_zzz(self, surface, now, lc, rc, color):
        cx, cy = rc
        for i in range(3):
            phase = ((now / 1000.0) + i * 0.6) % 1.8
            alpha = max(0, 255 - int(phase * 150))
            size = 24 + int(phase * 14)
            z = pygame.font.SysFont("Arial", size, bold=True).render("Z", True, color)
            z.set_alpha(alpha)
            surface.blit(z, (int(cx + 70 + phase * 25), int(cy - 70 - phase * 45)))

    def _diamond(self, surface, cx, cy, size):
        pygame.draw.polygon(surface, WHITE, [
            (cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy),
        ])

    # -- rainbow fill ---------------------------------------------------------

    def _draw_rainbow(self, surface, now, blink):
        w, h = surface.get_size()
        if self._rainbow_grad is None or self._rainbow_size != (w, h):
            self._rainbow_grad = self._build_rainbow(w, h)
            self._rainbow_size = (w, h)

        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        color = (255, 255, 255)
        lcx, lcy = self.rig.left_center()
        rcx, rcy = self.rig.right_center()
        self._draw_eye(mask, lcx, lcy, self.rig.cur_left, color, blink, "left", now)
        self._draw_eye(mask, rcx, rcy, self.rig.cur_right, color, blink, "right", now)

        offset = int((now / 5) % w)
        scroll = pygame.Surface((w, h))
        scroll.blit(self._rainbow_grad, (-offset, 0))
        scroll.blit(self._rainbow_grad, (w - offset, 0))

        mask.blit(scroll, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        surface.blit(mask, (0, 0))

    def _build_rainbow(self, w, h):
        surf = pygame.Surface((w, h))
        for x in range(w):
            rgb = colorsys.hsv_to_rgb(x / w, 1.0, 1.0)
            pygame.draw.line(surf, (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)), (x, 0), (x, h))
        return surf


# Backwards-compatible name.
EyesExpressions = EyesRenderer
