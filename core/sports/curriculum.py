"""Load versioned ski curriculum JSON."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from core.sports.knowledge import metric_ids

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content" / "ski"
CURRICULUM_V2_PATH = CONTENT_DIR / "curriculum.v2.json"
CURRICULUM_V3_PATH = CONTENT_DIR / "curriculum.v3.json"

# v3 is the runtime bundle: `assess.assess_clip` classifies against the v3
# stage model (tier / core_metrics / gate_metrics / prerequisites) and the v2
# bundle is kept only for reading stored reports and for comparison in tests.
CURRICULUM_PATH = CURRICULUM_V3_PATH

#: Scene facts a `scene`-tier level may require (design doc §2.2).
SCENE_FACTS = ("snow_surface", "slope_band", "terrain_type")


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
    """A gate. v2 rows carry ``signal``, v3 rows carry ``metric`` (§3.4)."""

    id: str
    name: Localized
    desc: Localized
    body: list[str]
    required: bool = True
    signal: str | None = None
    metric: str | None = None
    threshold: Threshold
    heuristic_not_fis_carve: bool = False
    drills: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def one_measurement_source(self) -> CheckpointSpec:
        if bool(self.signal) == bool(self.metric):
            raise ValueError(f"{self.id} needs exactly one of signal / metric")
        return self


class Prerequisites(BaseModel):
    levels: list[str] = Field(default_factory=list)
    checkpoints: list[str] = Field(default_factory=list)


class ProfileNote(BaseModel):
    """One adaptation overlay's status for a level (§2.3)."""

    id: str
    status: Literal["applies", "not_applicable"]
    note: Localized | None = None


class KbRefs(BaseModel):
    """Slices of the imported knowledge pack this level renders from (§9)."""

    tutorial: str | None = None
    drills: list[str] = Field(default_factory=list)
    faults: list[str] = Field(default_factory=list)
    venue: str | None = None
    equipment: str | None = None


class ExclusionRule(BaseModel):
    """Reject candidate levels when all ``when`` metric conditions hold."""

    when: dict[str, float]
    reject_levels: list[str]
    reason: str

    @model_validator(mode="after")
    def when_keys_are_metric_ops(self) -> ExclusionRule:
        for key in self.when:
            if not any(key.endswith(suffix) for suffix in ("_lte", "_gte")):
                raise ValueError(f"exclusion rule when key needs _lte/_gte suffix: {key}")
        return self


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
    # v3 (§1.3). Defaulted so the shipped 2.1.0 bundle still validates; a 3.x
    # bundle is checked for completeness by `Curriculum.v3_stage_model`.
    kb_stage: str = ""
    tier: Literal["full", "scene", "catalog"] | None = None
    requires_scene: list[str] = Field(default_factory=list)
    core_metrics: list[str] = Field(default_factory=list)
    gate_metrics: list[str] = Field(default_factory=list)
    prerequisites: Prerequisites = Field(default_factory=Prerequisites)
    profile_notes: list[ProfileNote] = Field(default_factory=list)
    kb_refs: KbRefs = Field(default_factory=KbRefs)


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
    schema_version: Literal["2.1.0", "3.0.0"]
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
    exclusion_rules: list[ExclusionRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def exclusion_rules_resolve(self) -> Curriculum:
        for rule in self.exclusion_rules:
            for level_id in rule.reject_levels:
                if level_id not in self.levels:
                    raise ValueError(f"exclusion rule unknown level {level_id}")
        return self

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

    @model_validator(mode="after")
    def v3_stage_model(self) -> Curriculum:
        """Structural rules the v3 stage model adds (design doc §1.3, §4)."""
        if self.schema_version != "3.0.0":
            return self
        known_metrics = metric_ids()
        for spec in self.levels.values():
            if not spec.kb_stage:
                raise ValueError(f"{spec.id} missing kb_stage")
            if spec.tier is None:
                raise ValueError(f"{spec.id} missing tier")
            for mid in (*spec.core_metrics, *spec.gate_metrics):
                if mid not in known_metrics:
                    raise ValueError(f"{spec.id} unknown metric {mid}")
            if not set(spec.gate_metrics) <= set(spec.core_metrics):
                raise ValueError(f"{spec.id} gate_metrics not a subset of core_metrics")
            if spec.tier == "catalog" and (spec.core_metrics or spec.gate_metrics):
                raise ValueError(f"catalog {spec.id} must carry no metrics")
            if spec.tier == "scene" and not spec.requires_scene:
                raise ValueError(f"scene {spec.id} must declare requires_scene")
            if spec.tier != "scene" and spec.requires_scene:
                raise ValueError(f"{spec.id} requires_scene only valid for scene tier")
            for token in spec.requires_scene:
                # "snow_surface" or "snow_surface:hardpack|ice" (§1.3, §4)
                if token.split(":", 1)[0] not in SCENE_FACTS:
                    raise ValueError(f"{spec.id} unknown scene fact {token}")
            for lid in spec.prerequisites.levels:
                if lid not in self.levels:
                    raise ValueError(f"{spec.id} unknown prerequisite level {lid}")
            for cid in spec.prerequisites.checkpoints:
                if cid not in self.checkpoints:
                    raise ValueError(f"{spec.id} unknown prerequisite checkpoint {cid}")
        for spec in self.checkpoints.values():
            if spec.metric and spec.metric not in known_metrics:
                raise ValueError(f"{spec.id} unknown metric {spec.metric}")
        return self


@lru_cache(maxsize=1)
def load_curriculum(path: Path | None = None) -> Curriculum:
    target = path or CURRICULUM_PATH
    return Curriculum.model_validate_json(target.read_text(encoding="utf-8"))


def level_by_id(cur: Curriculum, level_id: str) -> LevelSpec | None:
    return cur.levels.get(level_id)


def category_name(cur: Curriculum, category_id: str) -> Localized | None:
    return cur.categories.get(category_id)
