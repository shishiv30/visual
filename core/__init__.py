"""Core inference engines.

The engine imports are lazy on purpose. ``core.engine`` pulls in torch and
ultralytics, which are only needed for the YOLO backend; the desktop client runs
the MediaPipe backend, and the whole report layer
(``core.sports.*`` → curriculum, metrics, scoring) needs neither. Importing them
eagerly here meant that reading a curriculum file loaded a deep-learning runtime,
which slowed app start and made the report path unimportable in any environment
without torch.

``from core import CoreEngine`` still works exactly as before, via PEP 562.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from schemas.core_inference import CoreInferenceResult

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from core.engine import CoreEngine
    from core.mediapipe_engine import MediaPipeEngine

__all__ = ["CoreEngine", "CoreInferenceResult", "MediaPipeEngine"]

_LAZY = {
    "CoreEngine": ("core.engine", "CoreEngine"),
    "MediaPipeEngine": ("core.mediapipe_engine", "MediaPipeEngine"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = target
    from importlib import import_module

    return getattr(import_module(module_name), attr)


def __dir__() -> list[str]:
    return sorted(__all__)
