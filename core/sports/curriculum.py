"""Load versioned ski curriculum JSON."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

CURRICULUM_PATH = (
    Path(__file__).resolve().parents[2] / "content" / "ski" / "curriculum.v2.json"
)


class Localized(BaseModel):
    zh: str
    en: str


class Threshold(BaseModel):
    op: Literal["gte", "lte", "between"]
    value: float
    hi: float | None = None


class Drill(BaseModel):
    id: str
    name: Localized
    desc: Localized
    training: list[Localized]
    venue_ids: list[str] = Field(default_factory=list)


class CheckpointSpec(BaseModel):
    id: str
    name: Localized
    desc: Localized
    body: list[str]
    required: bool = True
    signal: str
    threshold: Threshold
    heuristic_not_fis_carve: bool = False
    drills: list[str] = Field(default_factory=list)


class LevelSpec(BaseModel):
    id: str
    category_id: str
    in_scope: bool = True
    heuristic_not_fis_carve: bool = False
    name: Localized
    desc: Localized
    checkpoints: list[str] = Field(default_factory=list)
    next_levels: list[str] = Field(default_factory=list)
    session_drills: list[str] = Field(default_factory=list)
    terrain: str = "green"
    venue_ids: list[str] = Field(default_factory=list)


class TerrainSpec(BaseModel):
    id: str
    name: Localized
    desc: Localized


class VenueSpec(BaseModel):
    id: str
    terrain: str
    name: Localized
    desc: Localized
    tips: Localized


class Curriculum(BaseModel):
    schema_version: Literal["2.1.0"]
    disclaimer: Localized
    pass_score: float = 75.0
    checkpoint_pass: float = 60.0
    sys_drill: str
    categories: dict[str, Localized]
    terrains: dict[str, TerrainSpec]
    venues: dict[str, VenueSpec]
    level_ids: list[str]
    catalog_level_ids: list[str] = Field(default_factory=list)
    drills: dict[str, Drill]
    checkpoints: dict[str, CheckpointSpec]
    levels: dict[str, LevelSpec]

    @model_validator(mode="after")
    def ids_match_keys(self) -> Curriculum:
        for key, drill in self.drills.items():
            if drill.id != key:
                raise ValueError(f"drill id mismatch {key}")
        for key, spec in self.checkpoints.items():
            if spec.id != key:
                raise ValueError(f"checkpoint id mismatch {key}")
        for key, spec in self.levels.items():
            if spec.id != key:
                raise ValueError(f"level id mismatch {key}")
        for key, spec in self.terrains.items():
            if spec.id != key:
                raise ValueError(f"terrain id mismatch {key}")
        for key, spec in self.venues.items():
            if spec.id != key:
                raise ValueError(f"venue id mismatch {key}")
        if self.sys_drill not in self.drills:
            raise ValueError("sys_drill missing")
        for spec in self.checkpoints.values():
            for did in spec.drills:
                if did not in self.drills:
                    raise ValueError(f"{spec.id} unknown drill {did}")
        for spec in self.levels.values():
            for cid in spec.checkpoints:
                if cid not in self.checkpoints:
                    raise ValueError(f"{spec.id} unknown checkpoint {cid}")
            for nid in spec.next_levels:
                if nid not in self.levels:
                    raise ValueError(f"{spec.id} unknown next {nid}")
            for did in spec.session_drills:
                if did not in self.drills:
                    raise ValueError(f"{spec.id} unknown session drill {did}")
            if spec.terrain not in self.terrains:
                raise ValueError(f"{spec.id} unknown terrain")
            for vid in spec.venue_ids:
                if vid not in self.venues:
                    raise ValueError(f"{spec.id} unknown venue {vid}")
        return self


@lru_cache(maxsize=1)
def load_curriculum(path: Path | None = None) -> Curriculum:
    target = path or CURRICULUM_PATH
    return Curriculum.model_validate_json(target.read_text(encoding="utf-8"))


def level_by_id(cur: Curriculum, level_id: str) -> LevelSpec | None:
    return cur.levels.get(level_id)


def category_name(cur: Curriculum, category_id: str) -> Localized | None:
    return cur.categories.get(category_id)
