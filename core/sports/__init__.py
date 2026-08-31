"""Offline alpine stage assessment from BlazePose 33.

Lazy for the same reason as ``core/__init__.py``: eagerly importing ``assess``
here created an import cycle for anything that only wanted the curriculum or the
metric registry (``schemas`` → ``core.sports.scene`` → ``core.sports`` → assess),
and pulled the whole scoring stack into a caller that just needed a data file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.sports.curriculum import CURRICULUM_PATH, load_curriculum

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from core.sports.assess import assess_clip
    from core.sports.translator import loc

__all__ = ["assess_clip", "CURRICULUM_PATH", "load_curriculum", "loc"]

_LAZY = {
    "assess_clip": ("core.sports.assess", "assess_clip"),
    "loc": ("core.sports.translator", "loc"),
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
