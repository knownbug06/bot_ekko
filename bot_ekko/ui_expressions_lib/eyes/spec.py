"""
Declarative expression specification for the eyes render engine.

An expression is described entirely by data (see expressions.json) instead of a
positional list + a bespoke draw method. Each eye is a shape (rounded rect by
default) plus four eyelid coverage fractions. The *difference* between the inner
and outer lid coverage is what produces human emotion:

    angry    -> top inner lids low  (brows furrow toward the nose)   \\  //
    sad      -> top outer lids low  (brows droop outward)            //  \\
    happy    -> bottom lids raised  (cheeks push up, crescent eyes)  \\__//
    sleepy   -> both top lids low   (half-closed)

Geometry is animated by lerping the *current* EyeSpec toward the *target*
expression's EyeSpec every frame (see physics.EyeRig), so transitions between
any two expressions are smooth automatically.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields, asdict
from typing import Dict, Any, Optional, Tuple, List

from bot_ekko.core.logger import get_logger

logger = get_logger("EyesSpec")

EXPRESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expressions.json")


@dataclass
class EyeSpec:
    """Geometry of a single eye. All values are in logical pixels except lid_*
    which are fractions [0, 1] of the eye height covered by a (black) eyelid."""
    width: float = 170.0
    height: float = 170.0
    radius: float = 55.0            # corner radius (clamped to fit at render time)
    offset_x: float = 0.0           # static per-eye offset from its base center
    offset_y: float = 0.0
    lid_top_inner: float = 0.0      # nose-side top lid coverage
    lid_top_outer: float = 0.0      # temple-side top lid coverage
    lid_bottom_inner: float = 0.0
    lid_bottom_outer: float = 0.0
    shape: str = "rect"             # rect | ellipse | arc | heart | ring

    def lerp(self, target: "EyeSpec", t: float) -> "EyeSpec":
        """Linear-interpolate every numeric field toward `target` by factor t.
        Shape snaps to the target (shapes can't blend)."""
        return EyeSpec(
            width=_lerp(self.width, target.width, t),
            height=_lerp(self.height, target.height, t),
            radius=_lerp(self.radius, target.radius, t),
            offset_x=_lerp(self.offset_x, target.offset_x, t),
            offset_y=_lerp(self.offset_y, target.offset_y, t),
            lid_top_inner=_lerp(self.lid_top_inner, target.lid_top_inner, t),
            lid_top_outer=_lerp(self.lid_top_outer, target.lid_top_outer, t),
            lid_bottom_inner=_lerp(self.lid_bottom_inner, target.lid_bottom_inner, t),
            lid_bottom_outer=_lerp(self.lid_bottom_outer, target.lid_bottom_outer, t),
            shape=target.shape,
        )


@dataclass
class ExpressionSpec:
    """A complete, named facial expression."""
    name: str
    left: EyeSpec = field(default_factory=EyeSpec)
    right: EyeSpec = field(default_factory=EyeSpec)
    color: Tuple[int, int, int] = (0, 255, 180)
    gaze: str = "wander"            # wander | jitter | sway | scan | center | up | down | left | right | up_right | up_left | away
    blink: str = "normal"           # normal | slow | fast | none
    morph_speed: float = 0.18       # how fast we lerp toward this expression
    effects: Tuple[str, ...] = ()   # tears, sparkles, blush, zzz, mouth, sweat, pupils
    auto_next: Optional[str] = None # auto-transition to this state...
    auto_after_ms: int = 0          # ...after this many ms in the expression


_EYE_FIELDS = {f.name for f in fields(EyeSpec)}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _build_eye(base: Dict[str, Any], override: Dict[str, Any]) -> EyeSpec:
    merged = {k: v for k, v in base.items() if k in _EYE_FIELDS}
    merged.update({k: v for k, v in override.items() if k in _EYE_FIELDS})
    return EyeSpec(**merged)


def load_expressions(path: str = EXPRESSIONS_FILE) -> Dict[str, ExpressionSpec]:
    """Parse expressions.json into a {NAME: ExpressionSpec} library."""
    with open(path, "r") as f:
        raw = json.load(f)

    defaults = raw.get("defaults", {})
    library: Dict[str, ExpressionSpec] = {}

    for name, cfg in raw.get("expressions", {}).items():
        name = name.upper()
        # Geometry: defaults <- expression-level <- per-eye override.
        base_geo = {**defaults, **cfg}
        left = _build_eye(base_geo, cfg.get("left", {}))
        right = _build_eye(base_geo, cfg.get("right", {}))

        color = cfg.get("color", defaults.get("color", [0, 255, 180]))
        library[name] = ExpressionSpec(
            name=name,
            left=left,
            right=right,
            color=tuple(color),
            gaze=cfg.get("gaze", defaults.get("gaze", "wander")),
            blink=cfg.get("blink", defaults.get("blink", "normal")),
            morph_speed=cfg.get("morph_speed", defaults.get("morph_speed", 0.18)),
            effects=tuple(cfg.get("effects", [])),
            auto_next=cfg.get("auto_next"),
            auto_after_ms=cfg.get("auto_after_ms", 0),
        )

    logger.info(f"Loaded {len(library)} eye expressions from {os.path.basename(path)}")
    return library
