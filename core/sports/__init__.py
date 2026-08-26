"""Offline alpine stage assessment from BlazePose 33."""

from core.sports.assess import assess_clip
from core.sports.curriculum import CURRICULUM_PATH, load_curriculum
from core.sports.translator import loc

__all__ = ["assess_clip", "CURRICULUM_PATH", "load_curriculum", "loc"]
