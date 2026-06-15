"""
Eyes render-engine adapter (config-driven).

The bulk of the work is generic: `update()` picks the ExpressionSpec for the
current state, drives behaviour (gaze / blink / auto-transition) from that spec,
and `render()` draws it with the generic renderer. Adding an expression is a
data change in expressions.json - no handler needed here.

Only the media/text states (CANVAS, CHAT, CLOCK) keep bespoke handlers because
they render through the MediaInterface instead of the eye rig.
"""
import math
import random
from datetime import datetime
from typing import Dict, Any, Optional

import pygame

from bot_ekko.core.base import BaseStateRenderer
from bot_ekko.core.state_registry import StateRegistry
from bot_ekko.core.models import CommandNames
from bot_ekko.core.logger import get_logger
from bot_ekko.modules.effects import EffectsRenderer
from bot_ekko.modules import audio_vis, llm_state
from bot_ekko.sys_config import (
    CYAN, LOGICAL_W, LOGICAL_H, MAIN_FONT, CANVAS_DURATION, DEFAULT_GIF_PATH,
)

from bot_ekko.ui_expressions_lib.eyes.physics import EyeRig
from bot_ekko.ui_expressions_lib.eyes.expressions import EyesRenderer
from bot_ekko.ui_expressions_lib.eyes.spec import load_expressions

logger = get_logger("MainAdapter")

# Named gaze directions -> (x, y) offset from base eye center.
GAZE_DIRECTIONS = {
    "center": (0, 0), "up": (0, -50), "down": (0, 55),
    "left": (-90, 0), "right": (90, 0),
    "up_right": (70, -45), "up_left": (-70, -45), "away": (-80, -40),
}

BLINK_INTERVALS = {
    "normal": (3000, 9000),
    "slow": (6000, 13000),
    "fast": (1200, 3000),
}

# States rendered by the MediaInterface rather than the eye rig.
MEDIA_STATES = {
    StateRegistry.CANVAS, StateRegistry.CHAT, StateRegistry.CLOCK,
    StateRegistry.LISTENING, StateRegistry.DISPLAY_TEXT,
}

# Waveform bar layout constants
_BAR_COUNT = 40
_BAR_W = 10
_BAR_GAP = 5
_BAR_MAX_H = 180
_BAR_MIN_H = 4
_WAVE_TOTAL_W = _BAR_COUNT * (_BAR_W + _BAR_GAP) - _BAR_GAP


class MainAdapter(BaseStateRenderer):
    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.state_machine = state_machine

        self.rig = EyeRig(state_machine)
        self.renderer = EyesRenderer(self.rig, state_machine)
        self.effects = EffectsRenderer()
        self.media_player = None

        # Load the declarative expression library and register every expression
        # as a valid state so CommandCenter.set_state() will accept it.
        self.library = load_expressions()
        for name, spec in self.library.items():
            StateRegistry.register_state(name, spec)

        # Behaviour timers.
        self.last_blink = 0
        self.last_gaze = 0

        # Prime the rig with a neutral expression.
        if StateRegistry.ACTIVE in self.library:
            self.rig.set_expression(self.library[StateRegistry.ACTIVE])

    def set_media_player(self, media_player):
        self.media_player = media_player

    # -- per-frame update -----------------------------------------------------

    def update(self, now: int) -> None:
        self._check_schedule(now)

        state = self.state_handler.get_state().upper() if self.state_handler else StateRegistry.ACTIVE
        spec = self.library.get(state)
        if spec:
            self.rig.set_expression(spec)
            self._drive_gaze(spec, now)
            self._drive_blink(spec, now)
            self._drive_auto_transition(state, spec, now)

        self.rig.update(now)

    def _drive_gaze(self, spec, now):
        mode = spec.gaze
        if mode == "wander":
            if now - self.last_gaze > random.randint(4000, 9000):
                self.rig.target_x = random.randint(-100, 100)
                self.rig.target_y = random.randint(-40, 40)
                self.last_gaze = now
        elif mode == "jitter":
            if now - self.last_gaze > random.randint(150, 400):
                self.rig.target_x = random.randint(-25, 25)
                self.rig.target_y = random.randint(-20, 20)
                self.last_gaze = now
        elif mode == "sway":
            import math
            self.rig.target_x = math.sin(now / 1000.0) * 15
            self.rig.target_y = 25
        elif mode == "scan":
            import math
            self.rig.target_x = math.sin(now / 700.0) * 90
            self.rig.target_y = 0
        elif mode in GAZE_DIRECTIONS:
            self.rig.target_x, self.rig.target_y = GAZE_DIRECTIONS[mode]

    def _drive_blink(self, spec, now):
        interval = BLINK_INTERVALS.get(spec.blink)
        if not interval:
            return
        if self.rig.blink_phase == "IDLE" and now - self.last_blink > random.randint(*interval):
            self.rig.trigger_blink()
            self.last_blink = now

    def _drive_auto_transition(self, state, spec, now):
        if not (spec.auto_next and self.command_center and self.state_handler):
            return
        elapsed = now - self.state_handler.state_entry_time
        if elapsed >= spec.auto_after_ms:
            target = spec.auto_next.upper()
            if target != state:
                self.command_center.issue_command(
                    CommandNames.CHANGE_STATE, params={"target_state": target}
                )

    # -- rendering ------------------------------------------------------------

    def render(self, surface: pygame.Surface, now: int) -> None:
        if not self.state_handler:
            return
        state = self.state_handler.get_state().upper()
        params = self.state_handler.current_state_params

        if state in MEDIA_STATES:
            handler = getattr(self, f"handle_{state}", None)
            if handler:
                handler(surface, now, params=params)
            return

        spec = self.library.get(state, self.library.get(StateRegistry.ACTIVE))
        self.renderer.draw(surface, now, effects=spec.effects if spec else ())

    def handle_fallback(self, surface: pygame.Surface, now: int):
        self.renderer.draw_generic(surface)

    # -- save / restore -------------------------------------------------------

    def get_physics_state(self) -> Dict[str, Any]:
        return self.rig.serialize()

    def set_physics_state(self, state: Dict[str, Any]) -> None:
        self.rig.restore(state)

    # -- media / text states --------------------------------------------------

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

    def handle_CHAT(self, surface, now, params=None):
        is_loading = False
        text = ""
        if params:
            is_loading = params.get("is_loading", False)
            text = params.get("text", "")

        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2

        if is_loading:
            self.effects.render_loading_dots(surface, center_x, center_y, now)
        elif text and self.media_player:
            try:
                from bot_ekko.sys_config import CHAT_FONT
                font = CHAT_FONT
            except ImportError:
                font = MAIN_FONT
            surf = self.media_player._render_wrapped_text(text, font, CYAN, LOGICAL_W - 40)
            rect = surf.get_rect(center=(center_x, center_y))
            surface.blit(surf, rect)

    @staticmethod
    def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list:
        lines = []
        for paragraph in text.replace('\r\n', '\n').split('\n'):
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current = ""
            for word in words:
                test = (current + " " + word).strip() if current else word
                if font.size(test)[0] <= max_width:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
        return lines

    def handle_DISPLAY_TEXT(self, surface, now, params=None):
        surface.fill((0, 0, 0))
        cx = surface.get_width() // 2
        cy = surface.get_height() // 2

        state = llm_state.get_state()
        text = state["text"]
        is_done = state["is_done"]
        error = state["error"]

        if error:
            err_surf = MAIN_FONT.render("something went wrong :(", True, (255, 80, 80))
            surface.blit(err_surf, err_surf.get_rect(center=(cx, cy)))
            return

        try:
            from bot_ekko.sys_config import CHAT_FONT
            font = CHAT_FONT
        except ImportError:
            font = MAIN_FONT

        if not text:
            # Still waiting for first token — show loading dots
            self.effects.render_loading_dots(surface, cx, cy - 20, now)
            thinking_surf = font.render("thinking...", True, (*CYAN, 160))
            surface.blit(thinking_surf, thinking_surf.get_rect(centerx=cx, top=cy + 20))
            return

        # Render word-wrapped response text
        margin_x, margin_y = 50, 40
        line_h = font.get_linesize() + 4
        max_w = surface.get_width() - margin_x * 2
        max_lines = (surface.get_height() - margin_y * 2) // line_h

        lines = self._wrap_text(text, font, max_w)

        # If more lines than fit, show the last N (tail-follows like a terminal)
        visible = lines[-max_lines:] if len(lines) > max_lines else lines
        y = margin_y
        for line in visible:
            surf = font.render(line, True, CYAN)
            surface.blit(surf, (margin_x, y))
            y += line_h

        # Blinking cursor while streaming
        if not is_done and (now // 400) % 2 == 0:
            cursor = font.render("▋", True, CYAN)
            surface.blit(cursor, (margin_x + font.size(visible[-1] if visible else "")[0] + 2, y - line_h))

    def handle_LISTENING(self, surface, now, params=None):
        surface.fill((0, 0, 0))
        rms_values = audio_vis.get_snapshot()

        cx = surface.get_width() // 2
        cy = surface.get_height() // 2
        x_start = cx - _WAVE_TOTAL_W // 2

        for i, rms in enumerate(rms_values):
            # Smooth with a tiny sine shimmer so silent bars aren't completely flat
            shimmer = math.sin(now * 0.003 + i * 0.4) * 0.015
            height = max(_BAR_MIN_H, int((_BAR_MAX_H * (rms + shimmer))))
            x = x_start + i * (_BAR_W + _BAR_GAP)
            rect = pygame.Rect(x, cy - height // 2, _BAR_W, height)

            # Fade alpha: older bars (left) dimmer, current bar (right) full brightness
            alpha = int(80 + 175 * (i / _BAR_COUNT))
            color = (*CYAN, alpha)

            bar_surf = pygame.Surface((_BAR_W, height), pygame.SRCALPHA)
            bar_surf.fill(color)
            surface.blit(bar_surf, (rect.x, rect.y))

        label = MAIN_FONT.render("listening...", True, (*CYAN, 160))
        surface.blit(label, label.get_rect(centerx=cx, top=cy + _BAR_MAX_H // 2 + 16))

    def handle_CLOCK(self, surface, now, params=None):
        if not self.media_player:
            return
        from bot_ekko.sys_config import CLOCK_FONT

        current_time = datetime.now().strftime("%I:%M %p")
        if current_time.startswith("0"):
            current_time = current_time[1:]

        if not self.media_player.is_playing or self.media_player.current_text != current_time:
            self.media_player.show_text(current_time, duration=60.0, save_context=False, font=CLOCK_FONT)
        self.media_player.update(surface)


# Backwards-compatible alias (older tests import EyesExpressionAdapter).
EyesExpressionAdapter = MainAdapter
