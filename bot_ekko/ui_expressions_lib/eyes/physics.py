"""
Eye physics rig.

Holds the *current* (animated) geometry of both eyes and lerps it toward the
*target* expression's geometry every frame. Because the morph is generic, a
transition between any two expressions is smooth without per-state code.

Also owns the shared gaze offset (where the eyes are looking, relative to their
base centers) and the blink modulation (a multiplier on eye height).
"""
import pygame
from typing import Optional, Dict, Any

from bot_ekko.core.base import BasePhysicsEngine
from bot_ekko.core.logger import get_logger
from bot_ekko.ui_expressions_lib.eyes.spec import EyeSpec, ExpressionSpec

logger = get_logger("EyeRig")

# Base eye centers in logical space (800x480).
BASE_LX, BASE_LY = 280, 240
BASE_RX, BASE_RY = 520, 240


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class EyeRig(BasePhysicsEngine):
    def __init__(self, state_machine: Any):
        super().__init__()
        self.state_machine = state_machine

        self.base_lx, self.base_ly = BASE_LX, BASE_LY
        self.base_rx, self.base_ry = BASE_RX, BASE_RY

        # Current (animated) geometry. Starts neutral.
        self.cur_left = EyeSpec()
        self.cur_right = EyeSpec()
        self.cur_color = [0.0, 255.0, 180.0]

        # Target expression (set by the adapter each frame).
        self.target: Optional[ExpressionSpec] = None

        # Gaze: target_x/target_y come from BasePhysicsEngine (set_look_at).
        self.gaze_x, self.gaze_y = 0.0, 0.0

        # Blink.
        self.blink_phase = "IDLE"      # IDLE | CLOSING | OPENING
        self.blink_factor = 1.0        # multiplies eye height

    # -- target ---------------------------------------------------------------

    def set_expression(self, spec: ExpressionSpec) -> None:
        self.target = spec

    def trigger_blink(self) -> None:
        if self.blink_phase == "IDLE":
            self.blink_phase = "CLOSING"

    # -- per-frame update -----------------------------------------------------

    def update(self, now: Optional[int] = None) -> None:
        if self.target is not None:
            t = self.target.morph_speed
            self.cur_left = self.cur_left.lerp(self.target.left, t)
            self.cur_right = self.cur_right.lerp(self.target.right, t)
            for i in range(3):
                self.cur_color[i] = _lerp(self.cur_color[i], self.target.color[i], t)

        # Gaze easing toward the desired look point.
        gs = 0.14
        self.gaze_x += (self.target_x - self.gaze_x) * gs
        self.gaze_y += (self.target_y - self.gaze_y) * gs

        self._update_blink()

    def _update_blink(self) -> None:
        if self.blink_phase == "CLOSING":
            self.blink_factor += (0.04 - self.blink_factor) * 0.5
            if self.blink_factor < 0.12:
                self.blink_phase = "OPENING"
        elif self.blink_phase == "OPENING":
            self.blink_factor += (1.0 - self.blink_factor) * 0.3
            if self.blink_factor > 0.97:
                self.blink_factor = 1.0
                self.blink_phase = "IDLE"

    # Backwards-compatible alias (old code/tests call apply_physics()).
    def apply_physics(self) -> None:
        self.update(pygame.time.get_ticks())

    # -- accessors for the renderer ------------------------------------------

    def color(self):
        return (int(self.cur_color[0]), int(self.cur_color[1]), int(self.cur_color[2]))

    def left_center(self):
        return (self.base_lx + self.gaze_x, self.base_ly + self.gaze_y)

    def right_center(self):
        return (self.base_rx + self.gaze_x, self.base_ry + self.gaze_y)

    # -- save / restore -------------------------------------------------------

    def serialize(self) -> Dict[str, Any]:
        return {
            "left": self.cur_left.__dict__.copy(),
            "right": self.cur_right.__dict__.copy(),
            "color": list(self.cur_color),
            "gaze_x": self.gaze_x,
            "gaze_y": self.gaze_y,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "blink_phase": self.blink_phase,
        }

    def restore(self, state: Dict[str, Any]) -> None:
        if not state:
            return
        if "left" in state:
            self.cur_left = EyeSpec(**state["left"])
        if "right" in state:
            self.cur_right = EyeSpec(**state["right"])
        if "color" in state:
            self.cur_color = list(state["color"])
        self.gaze_x = state.get("gaze_x", self.gaze_x)
        self.gaze_y = state.get("gaze_y", self.gaze_y)
        self.target_x = state.get("target_x", self.target_x)
        self.target_y = state.get("target_y", self.target_y)
        self.blink_phase = state.get("blink_phase", "IDLE")


# Backwards-compatible name.
Eyes = EyeRig
