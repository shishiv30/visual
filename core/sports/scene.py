"""Scene facts a clip cannot supply on its own (design §2.2).

``snow_surface`` and ``slope_band`` come from the user at Prepare time; ``view``
and ``camera_motion`` are filled in by the measurement layer, not by the user;
``fps_effective`` is computed as source fps ÷ frame stride.

Scene is optional. Every field defaults to ``None`` and a missing scene never
raises: it simply moves the ``scene``-tier levels (``firm_snow``, ``steeps``,
``powder``) out of the classifier's candidate set, which the report then says
out loud. Pure and client-independent — no imports from ``clients/``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class SnowSurface(str, Enum):
    CORDUROY = "corduroy"
    PACKED = "packed"
    HARDPACK = "hardpack"
    ICE = "ice"
    SOFT = "soft"
    POWDER = "powder"
    CRUD = "crud"
    SLUSH = "slush"


class SlopeBand(str, Enum):
    GREEN = "green"
    BLUE = "blue"
    BLACK = "black"
    DOUBLE_BLACK = "double-black"


class TerrainType(str, Enum):
    PISTE = "piste"
    MOGUL = "mogul"
    PARK = "park"
    OFFPISTE = "offpiste"


class ViewClass(str, Enum):
    PROFILE = "profile"
    QUARTER = "quarter"
    FRONTAL = "frontal"


class CameraMotion(str, Enum):
    STATIC = "static"
    PANNING = "panning"
    FOLLOW = "follow"


#: Surfaces that satisfy the `firm_snow` gate (design §4).
FIRM_SNOW_SURFACES: tuple[SnowSurface, ...] = (SnowSurface.HARDPACK, SnowSurface.ICE)
#: Surfaces that satisfy the `powder` gate (design §4).
POWDER_SURFACES: tuple[SnowSurface, ...] = (SnowSurface.SOFT, SnowSurface.POWDER)
#: Slope bands that satisfy the `steeps` gate (design §4).
STEEP_SLOPE_BANDS: tuple[SlopeBand, ...] = (SlopeBand.BLACK, SlopeBand.DOUBLE_BLACK)

#: `requires_scene` token lists for the three scene-tier levels in design §1.2.
REQUIRES_FIRM_SNOW: tuple[str, ...] = ("snow_surface:hardpack|ice",)
REQUIRES_STEEPS: tuple[str, ...] = ("slope_band:black|double-black",)
REQUIRES_POWDER: tuple[str, ...] = ("snow_surface:soft|powder",)
REQUIRES_MOGUL: tuple[str, ...] = ("terrain_type:mogul",)
REQUIRES_PARK: tuple[str, ...] = ("terrain_type:park",)

_SURFACE_ALIASES = {"groomed": "corduroy", "hard-pack": "hardpack", "boilerplate": "ice"}
_BAND_ALIASES = {
    "double_black": "double-black",
    "doubleblack": "double-black",
    "double black": "double-black",
}
_TERRAIN_ALIASES: dict[str, str] = {
    "groomed": "piste",
    "on-piste": "piste",
    "moguls": "mogul",
    "bumps": "mogul",
    "freestyle": "park",
    "off-piste": "offpiste",
    "backcountry": "offpiste",
    "powder": "offpiste",
}
_UNKNOWN_WORDS = frozenset({"", "none", "null", "unknown", "not sure", "not_sure"})


def _clean(value: object) -> str:
    raw = getattr(value, "value", value)
    if raw is None:
        return ""
    text = str(raw).strip().lower()
    return text.rsplit(".", 1)[-1] if "." in text else text


def _parse(enum_cls: type[Enum], value: object, aliases: dict[str, str]) -> Enum | None:
    if isinstance(value, enum_cls):
        return value
    text = _clean(value)
    if text in _UNKNOWN_WORDS:
        return None
    text = aliases.get(text, text)
    try:
        return enum_cls(text)
    except ValueError:
        return None


def parse_snow_surface(value: object) -> SnowSurface | None:
    """Tolerant parse; anything unrecognized becomes ``None``."""
    return _parse(SnowSurface, value, _SURFACE_ALIASES)  # type: ignore[return-value]


def parse_slope_band(value: object) -> SlopeBand | None:
    """Tolerant parse; anything unrecognized becomes ``None``."""
    return _parse(SlopeBand, value, _BAND_ALIASES)  # type: ignore[return-value]


def parse_terrain_type(value: object) -> TerrainType | None:
    """Tolerant parse; anything unrecognized becomes ``None``."""
    return _parse(TerrainType, value, _TERRAIN_ALIASES)  # type: ignore[return-value]


def parse_view(value: object) -> ViewClass | None:
    return _parse(ViewClass, value, {})  # type: ignore[return-value]


def parse_camera_motion(value: object) -> CameraMotion | None:
    return _parse(CameraMotion, value, {})  # type: ignore[return-value]


@dataclass(frozen=True)
class SceneContext:
    """What we know about the snow, the slope, the framing and the sample rate."""

    snow_surface: SnowSurface | None = None
    slope_band: SlopeBand | None = None
    terrain_type: TerrainType | None = None
    view: ViewClass | None = None
    camera_motion: CameraMotion | None = None
    fps_effective: float | None = None

    @property
    def is_empty(self) -> bool:
        """True when nothing about the scene is known."""
        return (
            self.snow_surface is None
            and self.slope_band is None
            and self.terrain_type is None
            and self.view is None
            and self.camera_motion is None
        )

    def requires_satisfied(self, requires: list[str] | tuple[str, ...] | None) -> bool:
        """Whether this scene meets every token in a level's ``requires_scene``.

        A token is either a bare field name (``"snow_surface"`` — the field must
        be known) or a field name with the allowed values after a colon
        (``"snow_surface:hardpack|ice"``). An empty or missing requirement list
        is satisfied by definition, which is what ``full``-tier levels carry.
        Unknown field names, unknown values and a missing scene all return
        ``False``; nothing here raises.
        """
        if not requires:
            return True
        if isinstance(requires, str):
            requires = (requires,)
        for token in requires:
            if not self._token_satisfied(token):
                return False
        return True

    def _token_satisfied(self, token: object) -> bool:
        text = str(token or "").strip()
        if not text:
            return False
        field, _, allowed = text.partition(":")
        current = _SCENE_FIELDS.get(field.strip().lower())
        if current is None:
            return False
        value = getattr(self, current, None)
        if value is None:
            return False
        if not allowed.strip():
            return True
        wanted = {
            part.strip().lower()
            for chunk in allowed.split("|")
            for part in chunk.split(",")
            if part.strip()
        }
        return _clean(value) in wanted

    def with_fps_effective(self, fps_effective: float | None) -> SceneContext:
        """Copy carrying a computed sample rate."""
        return replace(self, fps_effective=_positive_fps(fps_effective))

    def to_dict(self) -> dict:
        """JSON-ready block; enum members become their string values."""
        return {
            "snow_surface": None if self.snow_surface is None else self.snow_surface.value,
            "slope_band": None if self.slope_band is None else self.slope_band.value,
            "terrain_type": None if self.terrain_type is None else self.terrain_type.value,
            "view": None if self.view is None else self.view.value,
            "camera_motion": (
                None if self.camera_motion is None else self.camera_motion.value
            ),
            "fps_effective": self.fps_effective,
        }

    @classmethod
    def from_dict(
        cls, data: object, *, fps_effective: float | None = None
    ) -> SceneContext:
        """Build from a stored scene block. ``None``/garbage gives an empty scene.

        An explicit ``fps_effective`` argument wins over any stored value, since
        the pipeline knows the stride it actually sampled with.
        """
        payload = data if isinstance(data, dict) else {}
        stored_fps = _positive_fps(payload.get("fps_effective"))
        chosen = _positive_fps(fps_effective)
        return cls(
            snow_surface=parse_snow_surface(payload.get("snow_surface")),
            slope_band=parse_slope_band(payload.get("slope_band")),
            terrain_type=parse_terrain_type(payload.get("terrain_type")),
            view=parse_view(payload.get("view")),
            camera_motion=parse_camera_motion(payload.get("camera_motion")),
            fps_effective=chosen if chosen is not None else stored_fps,
        )


_SCENE_FIELDS = {
    "snow_surface": "snow_surface",
    "slope_band": "slope_band",
    "terrain_type": "terrain_type",
    "view": "view",
    "camera_motion": "camera_motion",
}


def _positive_fps(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if out != out or out <= 0.0 or out == float("inf"):
        return None
    return out
