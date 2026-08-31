"""Clip coaching report filled from curriculum JSON.

Schema 3.0.0 (ski report v3, design doc
``docs/superpowers/specs/2026-08-30-ski-report-v3-design.md``).

v3 is **additive**: every 2.1.0 field is still present and still populated, so a
client that only understands 2.1.0 keeps rendering the same five chapters. The
new blocks are all optional:

``classification``   why this stage was chosen, and what came second
``metrics``          the per-stage metric catalog with rubric and reliability
``turns``            turn segmentation summary, so gates can read "N of M"
``tree``             the whole skill tree with per-node state, not just a path
``knowledge_ref``    which knowledge-pack stage the tutorial chapters render
``knowledge_focus``  the faults and drills selected from this skier's own metrics
``scene``            the scene facts used, and which were missing
``profile_summary``  what the athlete profile changed
``filming``          filming problems detected in this clip

Design rules that this schema encodes deliberately:

* A metric is never a bare number. ``state`` separates "measured and failing"
  from "could not measure" from "not applicable at this age", and ``reason``
  says which. Reports must not show 0 for something that was not measured.
* A profile may change normalization, threshold band, or guidance. It may never
  silently lower a pass standard, so ``MetricReport.state`` carries
  ``not_applicable`` rather than an awarded pass.
* Knowledge content is referenced, not embedded: the pack ships with every
  client and is far larger than a report. Only the *selection* derived from this
  skier's metrics is stored.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "3.0.0"


class KeypointStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class MetricState(str, Enum):
    """Why a metric has (or has not) a value. Never collapse these to 0."""

    OK = "ok"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class Rubric(str, Enum):
    """Three-level rubric, mirroring the curriculum's own gate wording."""

    NOT_YET = "not_yet"
    PASS = "pass"
    STRONG = "strong"
    NOT_RATED = "not_rated"


class NodeState(str, Enum):
    COMPLETED = "completed"
    CURRENT = "current"
    INFERRED = "inferred"
    AVAILABLE = "available"
    LOCKED = "locked"
    NOT_APPLICABLE = "not_applicable"


class KeypointResult(BaseModel):
    id: str
    name: str = ""
    status: KeypointStatus
    score: float | None = None
    value: float | None = None
    evidence_ms: float | None = None
    good: str
    bad: str
    drills: list[dict]
    #: v3: the metric id this checkpoint reads, when it is metric-backed.
    metric_id: str = ""
    #: v3: "3 of 22" style evidence for count-form gates.
    faulty_turns: int | None = None
    total_turns: int | None = None
    allowance: int | None = None


class TreeNode(BaseModel):
    """2.1.0 shape. Kept as a projection of ``StageReport.tree``."""

    id: str
    name: str
    current: bool = False


class TreeNodeV3(BaseModel):
    """One rung of the whole progression, with its state for this athlete."""

    id: str
    name: str
    kb_stage: str = ""
    tier: str = "full"
    branch: str = "piste"
    state: NodeState = NodeState.LOCKED
    score_best: float | None = None
    gates_passed: str = ""
    locked_reason: str = ""
    inferred_reason: str = ""
    depth: int = 0
    parents: list[str] = Field(default_factory=list)
    children: list[str] = Field(default_factory=list)


class FrameScorePoint(BaseModel):
    t_ms: float
    score: float


class PostureScores(BaseModel):
    """Heuristic coach composites 0–100 (not lab SI metrics)."""

    stability: float = 0.0
    coordination: float = 0.0
    control: float = 0.0
    balance: float = 0.0


class MetricReport(BaseModel):
    """One measured metric as the report renders it."""

    id: str
    name: str = ""
    group: str = ""
    state: MetricState = MetricState.UNKNOWN
    reason: str = ""
    value: float | None = None
    unit: str = ""
    #: Human-facing value, already formatted and unit-converted (e.g. "42 cm").
    display: str = ""
    score: float | None = None
    rubric: Rubric = Rubric.NOT_RATED
    reliability: float = 0.0
    is_gate: bool = False
    #: Plain-language statement of the standard, e.g. "at most 2 of 20".
    standard: str = ""
    form: str = "A"
    per_turn: list[float | None] = Field(default_factory=list)
    faulty_turns: int | None = None
    total_turns: int | None = None
    evidence_ms: float | None = None
    #: "left" / "right" when this row is one side of a paired metric.
    side: str = ""
    #: Paired-side scores, when the metric is measured per leg.
    left_value: float | None = None
    right_value: float | None = None


class TurnRecord(BaseModel):
    index: int
    side: str = ""
    t_start_ms: float = 0.0
    t_end_ms: float = 0.0
    duration_s: float = 0.0
    amplitude_deg: float = 0.0
    #: Fault ids that fired on this turn, e.g. ["stem_count", "backseat_count"].
    flags: list[str] = Field(default_factory=list)


class TurnSummary(BaseModel):
    count: int = 0
    left_count: int = 0
    right_count: int = 0
    mean_duration_s: float | None = None
    duration_cv: float | None = None
    turns: list[TurnRecord] = Field(default_factory=list)
    #: Faulty-turn tallies keyed by fault metric id.
    fault_counts: dict[str, int] = Field(default_factory=dict)


class Candidate(BaseModel):
    """One stage the classifier considered."""

    stage_id: str
    stage_name: str = ""
    score: float = 0.0
    fit: float = 0.0
    gate_ratio: float = 0.0
    prior: float = 0.0
    tier: str = "full"
    #: Filled on runners-up: which metric separated this from the pick.
    separating_metric_id: str = ""
    separating_metric_name: str = ""
    rejected_reason: str = ""


class Classification(BaseModel):
    """Why this stage, and how sure."""

    method: Literal["scored_candidates", "legacy_ladder", "unusable"] = "scored_candidates"
    chosen_id: str = ""
    confidence: float = 0.0
    separation: float = 0.0
    quality_factor: float = 1.0
    candidates: list[Candidate] = Field(default_factory=list)
    #: True when confidence fell below the gate and the report offers options.
    ambiguous: bool = False
    unusable_reason: str = ""


class SceneSummary(BaseModel):
    snow_surface: str = ""
    slope_band: str = ""
    view_class: str = ""
    view_azimuth_deg: float | None = None
    camera_motion: str = ""
    fps_effective: float | None = None
    #: Scene facts a candidate stage needed but did not get.
    missing: list[str] = Field(default_factory=list)


class ProfileSummary(BaseModel):
    """What the profile changed. Guidance only — never a score change."""

    age_band: str = ""
    age_years: float | None = None
    sex: str = ""
    height_cm: float | None = None
    weight_kg: float | None = None
    ski_cm: float | None = None
    is_complete: bool = False
    #: Human-facing notes: normalization used, bands overridden, stages excluded.
    effects: list[str] = Field(default_factory=list)
    #: Adaptation overlay ids applied, e.g. ["age-7-12", "phys-female-adult"].
    overlays: list[str] = Field(default_factory=list)


class KnowledgeRef(BaseModel):
    """Which knowledge-pack entry the tutorial chapters render."""

    kb_stage: str = ""
    pack_version: str = ""
    level_id: str = ""


class KnowledgeFocus(BaseModel):
    """The slice of the knowledge pack chosen from this skier's own metrics."""

    #: Fault ids from the pack, ordered by how badly this skier failed them.
    fault_ids: list[str] = Field(default_factory=list)
    #: Drill ids to run first, targeting the weakest gate metric.
    drill_ids: list[str] = Field(default_factory=list)
    #: Skill ids the weakest metrics map to.
    skill_ids: list[str] = Field(default_factory=list)
    weakest_metric_id: str = ""
    weakest_metric_name: str = ""


class FilmingIssue(BaseModel):
    code: str
    message: str = ""
    severity: Literal["info", "warn", "blocker"] = "info"


class StageReport(BaseModel):
    schema_version: Literal["3.0.0"] = "3.0.0"
    clip_id: str
    category_id: str
    stage_id: str
    category_name: str
    stage_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    ready_for_next_stage: bool
    disclaimer: str

    # --- 2.1.0 fields, still populated ---
    stage_focus: str = ""
    training_focus: str = ""
    how_to_advance: str = ""
    score_0_100: float = 0.0
    terrain_id: str = ""
    terrain_name: str = ""
    terrain_desc: str = ""
    weakest_checkpoint_id: str = ""
    next_level_ids: list[str] = Field(default_factory=list)
    next_level_names: list[str] = Field(default_factory=list)
    next_plans: list[dict] = Field(default_factory=list)
    session_plan: list[dict] = Field(default_factory=list)
    tree_path: list[TreeNode] = Field(default_factory=list)
    film_steps: list[str] = Field(default_factory=list)
    keypoints: list[KeypointResult]
    score_series: list[FrameScorePoint] = Field(default_factory=list)
    heuristic_not_fis_carve: bool = False
    posture: PostureScores | None = None

    # --- v3 blocks, all optional ---
    kb_stage: str = ""
    tier: str = "full"
    classification: Classification | None = None
    metrics: list[MetricReport] = Field(default_factory=list)
    turns: TurnSummary | None = None
    tree: list[TreeNodeV3] = Field(default_factory=list)
    knowledge_ref: KnowledgeRef | None = None
    knowledge_focus: KnowledgeFocus | None = None
    scene: SceneSummary | None = None
    profile_summary: ProfileSummary | None = None
    filming: list[FilmingIssue] = Field(default_factory=list)

    def gate_metrics(self) -> list[MetricReport]:
        """Metrics that decide advancement, in report order."""
        return [m for m in self.metrics if m.is_gate]

    def measured_metrics(self) -> list[MetricReport]:
        """Metrics that actually produced a value."""
        return [m for m in self.metrics if m.state == MetricState.OK]
