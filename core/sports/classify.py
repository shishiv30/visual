"""Stage classification: the §5 scored-candidate classifier, plus the v2 ladder.

v2 was one hand-written if-ladder over 14 whole-clip signals, first match wins
(``assess.classify``). It is kept verbatim here as :func:`classify_legacy` so
the two can be run side by side on the same clip and a disagreement is visible
rather than silent (design §5, "Backward compatibility").

:func:`classify_v3` is the replacement. Every level that a camera can judge is
scored, so the report can name the runner-up and the metric that separated it —
which is the whole point of chapter 2, "Why this stage".

Weights, gates and formulas are §5 verbatim::

    s(L)              = 0.55*fit + 0.30*gate + 0.15*prior
    separation_factor = clamp((s1 - s2) / 0.15, 0.4, 1.0)
    confidence        = s1 * quality_factor * separation_factor
    ambiguous         = confidence < 0.35

Decisions this module had to make where §5 is silent, each of them stated here
because they change what the report asserts:

* **``turn_count`` is not a hard gate.** §5 step 1 lists it with the quality
  gates, but ``pizza_glide`` is a straight glide and ``sideslip`` is a slip: a
  clip with zero segmented turns is a perfectly assessable clip for those
  stages. Zero turns therefore suppresses the turn-dependent metrics (the
  measurement layer already does that with ``no_turns_segmented``) and raises a
  *filming* note, rather than voiding the report. Landmark quality, usable-frame
  ratio and body scale remain hard gates.
* **``fit`` averages only the metrics that produced a value**, since an
  unmeasured metric has no membership and must not be read as a zero. The
  penalty for unmeasurable evidence lands on ``gate`` instead, where an
  unknown gate metric counts as not passed — so a stage whose gates the clip
  could not see loses to one whose gates it could.
* **Age-band exclusion is expressed as a rejected candidate**, never as a low
  score: a level the curriculum marks ``not_applicable`` for this athlete's age
  band keeps its row (so the report can say why) but is removed from the
  argmax.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.sports.bands import band_for, evaluate
from core.sports.curriculum import Curriculum, LevelSpec
from core.sports.history import StageHistory
from core.sports.metrics import MetricPack
from core.sports.scene import SceneContext
from core.sports.signals import FeaturePack
from schemas.stage_report import Candidate, Classification

# --- §5 constants -----------------------------------------------------------

W_FIT = 0.55
W_GATE = 0.30
W_PRIOR = 0.15
SEPARATION_SPAN = 0.15
SEPARATION_FLOOR = 0.40
CONF_GATE = 0.35

# --- quality gates (§5 step 1) ---------------------------------------------

MIN_FRAMES = 6
MIN_LANDMARK_QUALITY = 0.20
MIN_USABLE_FRAME_RATIO = 0.40
#: Below this many turns the rhythm and count metrics are not trustworthy; a
#: filming note, not a blocker.
MIN_TURNS_FOR_RHYTHM = 4

REASON_TOO_FEW_FRAMES = "too_few_frames"
REASON_LOW_QUALITY = "low_landmark_quality"
REASON_FEW_USABLE_FRAMES = "few_usable_frames"
REASON_NO_BODY_SCALE = "no_body_scale"
REASON_NOTHING_MEASURED = "no_measurable_metrics"
REASON_NO_CANDIDATES = "no_candidate_stage"
REASON_NOT_APPLICABLE_AGE = "not_applicable_age_band"
REASON_SCENE_MISSING = "scene_fact_missing"

#: Quality-factor reference points. Landmark quality of 0.7 and 80% usable
#: frames are treated as "as good as it gets"; a single-plane view can only see
#: half of the catalog, so it costs 20%.
QUALITY_REF = 0.70
USABLE_REF = 0.80
VIEW_PENALTY_SINGLE_PLANE = 0.80

#: Slope-band ordinals for the terrain-consistency prior.
_BAND_ORDINAL = {"green": 0, "blue": 1, "black": 2, "double-black": 3}
#: The slope band each level's terrain implies.
_TERRAIN_BAND = {
    "green": "green",
    "blue": "blue",
    "park": "blue",
    "red": "black",
    "black": "black",
    "mogul": "black",
    "offpiste": "black",
    "any": "",
}
#: When terrain_type is explicitly set, full-tier levels outside this set are
#: excluded from candidates — piste metrics should not compete with mogul metrics
#: when the user has told us the terrain is mogul, etc.
_TERRAIN_TYPE_LEVEL_TERRAINS: dict[str, frozenset[str]] = {
    "mogul": frozenset({"mogul", "any"}),
    "piste": frozenset({"green", "blue", "red", "black", "double-black", "any"}),
    "park": frozenset({"park", "any"}),
    "offpiste": frozenset({"offpiste", "any"}),
}

PRIOR_NEUTRAL = 0.50
#: §5: "previously passed levels raise adjacent levels". Implemented as a
#: *relative* shift — the next rung is raised and the rung already passed is
#: lowered — because that is what makes a progression report progress: a skier
#: who has passed `parallel` is, by definition, no longer working on `parallel`.
#: Without the second half, a level whose core metrics a good skier satisfies
#: perfectly (`parallel` is a subset of every carve level) wins forever.
PRIOR_ADJACENT = 0.40
PRIOR_PASSED_PENALTY = 0.30
PRIOR_TERRAIN_MATCH = 0.15
PRIOR_TERRAIN_STEP = 0.12


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


@dataclass(frozen=True)
class CandidateScore:
    """Internal working row; projected onto the schema's ``Candidate``."""

    level: LevelSpec
    fit: float
    gate: float
    prior: float
    score: float
    memberships: dict[str, float]
    measured: int
    rejected_reason: str = ""

    @property
    def eligible(self) -> bool:
        return not self.rejected_reason


def candidate_levels(
    curriculum: Curriculum, scene: SceneContext | None
) -> list[LevelSpec]:
    """§5 step 2: every ``full`` level, plus ``scene`` levels the scene allows.

    ``catalog`` levels are never candidates — that is what the tier means — and
    neither is an out-of-scope level.

    When ``terrain_type`` is explicitly provided, full-tier levels whose
    ``level.terrain`` falls outside the terrain track are also excluded —
    piste metrics must not compete with mogul metrics when the user has said
    the terrain is a mogul run.
    """
    terrain_type = getattr(scene, "terrain_type", None) if scene else None
    terrain_type_val = getattr(terrain_type, "value", None) if terrain_type else None
    allowed_terrains = _TERRAIN_TYPE_LEVEL_TERRAINS.get(terrain_type_val) if terrain_type_val else None

    out: list[LevelSpec] = []
    for level_id in curriculum.level_ids:
        level = curriculum.levels.get(level_id)
        if level is None or not level.in_scope:
            continue
        tier = level.tier or "full"
        if tier == "catalog":
            continue
        if tier == "scene":
            if scene is None or not scene.requires_satisfied(level.requires_scene):
                continue
        elif allowed_terrains is not None and level.terrain not in allowed_terrains:
            continue
        out.append(level)
    return out


def missing_scene_facts(
    curriculum: Curriculum, scene: SceneContext | None
) -> list[str]:
    """Scene facts a ``scene``-tier level wanted and never got.

    Reported in ``SceneSummary.missing`` so the report can say *why* a stage was
    not even considered, instead of silently dropping it. Only genuinely
    *unknown* facts are listed: a snow surface the user did supply, which simply
    is not hardpack, is not missing information — it is information that rules
    the stage out.
    """
    out: list[str] = []
    for level_id in curriculum.level_ids:
        level = curriculum.levels.get(level_id)
        if level is None or (level.tier or "full") != "scene":
            continue
        if scene is not None and scene.requires_satisfied(level.requires_scene):
            continue
        for token in level.requires_scene:
            fact = token.split(":", 1)[0]
            known = scene is not None and getattr(scene, fact, None) is not None
            if not known and fact not in out:
                out.append(fact)
    return out


def _age_excluded(level: LevelSpec, age_band: str | None) -> bool:
    """Whether the curriculum marks this level not applicable at this age."""
    if not age_band:
        return False
    for note in level.profile_notes:
        if note.id == age_band and note.status == "not_applicable":
            return True
    return False


def _memberships(
    pack: MetricPack, level: LevelSpec, age_band: str | None
) -> tuple[dict[str, float], int]:
    """Membership per core metric, and how many produced a value."""
    out: dict[str, float] = {}
    for metric_id in level.core_metrics:
        band = band_for(level.id, metric_id, age_band)
        result = evaluate(band, pack.get(metric_id))
        if result.membership is None:
            continue
        out[metric_id] = float(result.membership)
    return out, len(out)


#: How much of ``fit`` survives when none of the level's core metrics could be
#: measured. See :func:`_fit`.
FIT_COVERAGE_FLOOR = 0.5


def _fit(memberships: dict[str, float], core_count: int) -> float:
    """Mean membership, discounted by how much of the core set was measured.

    §5 defines ``fit`` as the plain mean over the level's core metrics, which
    silently rewards a level whose one measurable metric happens to sit in band
    over a level whose whole core set was measured and mostly sits in band. The
    coverage discount — half the weight on the mean, half on the fraction of the
    core set that produced a value — removes that. It never invents a number for
    an unmeasured metric, which is the rule it has to respect.
    """
    if not memberships or core_count <= 0:
        return 0.0
    mean = sum(memberships.values()) / len(memberships)
    coverage = len(memberships) / float(core_count)
    return mean * (FIT_COVERAGE_FLOOR + (1.0 - FIT_COVERAGE_FLOOR) * coverage)


def _gate_ratio(
    pack: MetricPack, level: LevelSpec, age_band: str | None
) -> float:
    """Fraction of this level's gate metrics at ``pass`` or better.

    An unknown gate metric counts as not passed: the clip did not show it, so
    the stage it gates cannot claim it.
    """
    gates = level.gate_metrics
    if not gates:
        return 0.0
    passed = 0
    for metric_id in gates:
        band = band_for(level.id, metric_id, age_band)
        if evaluate(band, pack.get(metric_id)).passing:
            passed += 1
    return passed / float(len(gates))


def _prior(
    level: LevelSpec,
    pack: MetricPack,
    curriculum: Curriculum,
    history: StageHistory | None,
) -> float:
    """§5 step 4: profile, history and scene-consistency prior in ``[0, 1]``."""
    prior = PRIOR_NEUTRAL
    if history is not None and not history.is_empty:
        passed = history.passed_levels()
        adjacent: set[str] = set()
        for lid in passed:
            spec = curriculum.levels.get(lid)
            if spec is not None:
                adjacent.update(spec.next_levels)
        prereq = set(level.prerequisites.levels)
        if level.id not in passed and (
            level.id in adjacent or (prereq and prereq <= passed)
        ):
            prior += PRIOR_ADJACENT
        if level.id in passed:
            prior -= PRIOR_PASSED_PENALTY
    scene = pack.scene
    band = getattr(getattr(scene, "slope_band", None), "value", None)
    expected = _TERRAIN_BAND.get(level.terrain, "")
    if band and expected:
        distance = abs(
            _BAND_ORDINAL.get(expected, 0) - _BAND_ORDINAL.get(str(band), 0)
        )
        prior += (
            PRIOR_TERRAIN_MATCH if distance == 0 else -PRIOR_TERRAIN_STEP * distance
        )
    return _clamp(prior)


def quality_factor(pack: MetricPack) -> float:
    """Global clip-quality multiplier on confidence (§5 step 5)."""
    quality = _clamp(pack.landmark_quality / QUALITY_REF)
    usable = _clamp(pack.usable_frame_ratio / USABLE_REF)
    view_class = str(getattr(getattr(pack.view, "view_class", ""), "value", ""))
    view = 1.0 if view_class == "quarter" else VIEW_PENALTY_SINGLE_PLANE
    return _clamp(quality * usable * view)


def unusable_reason(pack: MetricPack) -> str:
    """§5 step 1. Empty string means the clip is worth classifying."""
    if pack.n_frames < MIN_FRAMES:
        return REASON_TOO_FEW_FRAMES
    if pack.scale is None or not pack.scale.ok:
        return REASON_NO_BODY_SCALE
    if pack.landmark_quality < MIN_LANDMARK_QUALITY:
        return REASON_LOW_QUALITY
    if pack.usable_frame_ratio < MIN_USABLE_FRAME_RATIO:
        return REASON_FEW_USABLE_FRAMES
    return ""


def _separating_metric(
    top: CandidateScore, other: CandidateScore
) -> str:
    """Metric with the largest membership gap between two candidates.

    Only metrics both levels actually measured are eligible: a metric one level
    does not care about is not what separated them, it is just absent.
    """
    shared = set(top.memberships) & set(other.memberships)
    pool = shared or (set(top.memberships) | set(other.memberships))
    best_id = ""
    best_gap = -1.0
    for metric_id in sorted(pool):
        gap = abs(
            top.memberships.get(metric_id, 0.0) - other.memberships.get(metric_id, 0.0)
        )
        if gap > best_gap:
            best_gap = gap
            best_id = metric_id
    return best_id


def score_candidates(
    pack: MetricPack,
    curriculum: Curriculum,
    history: StageHistory | None = None,
) -> list[CandidateScore]:
    """Every candidate scored, best first. Rejected rows keep their reason."""
    age_band = getattr(pack.athlete, "age_band", None)
    rows: list[CandidateScore] = []
    for level in candidate_levels(curriculum, pack.scene):
        memberships, measured = _memberships(pack, level, age_band)
        fit = _fit(memberships, len(level.core_metrics))
        gate = _gate_ratio(pack, level, age_band)
        prior = _prior(level, pack, curriculum, history)
        rejected = ""
        if _age_excluded(level, age_band):
            rejected = REASON_NOT_APPLICABLE_AGE
            prior = 0.0
        elif not memberships:
            rejected = REASON_NOTHING_MEASURED
        rows.append(
            CandidateScore(
                level=level,
                fit=fit,
                gate=gate,
                prior=prior,
                score=W_FIT * fit + W_GATE * gate + W_PRIOR * prior,
                memberships=memberships,
                measured=measured,
                rejected_reason=rejected,
            )
        )
    rows.sort(key=lambda row: (row.eligible, row.score), reverse=True)
    return rows


def _row_to_candidate(
    row: CandidateScore, name: str, separating: tuple[str, str] = ("", "")
) -> Candidate:
    return Candidate(
        stage_id=row.level.id,
        stage_name=name,
        score=round(row.score, 4),
        fit=round(row.fit, 4),
        gate_ratio=round(row.gate, 4),
        prior=round(row.prior, 4),
        tier=row.level.tier or "full",
        separating_metric_id=separating[0],
        separating_metric_name=separating[1],
        rejected_reason=row.rejected_reason,
    )


def classify_v3(
    pack: MetricPack,
    curriculum: Curriculum,
    history: StageHistory | None = None,
    *,
    name_for: object = None,
    max_candidates: int = 4,
) -> Classification:
    """Classify one clip (design §5).

    ``name_for`` is an optional ``(level_id) -> str`` used to fill the display
    names; ``core`` cannot know the caller's language, so ``assess`` passes its
    own localizer in.
    """
    resolve = name_for if callable(name_for) else (lambda level_id: level_id)
    blocked = unusable_reason(pack)
    if blocked:
        return Classification(
            method="unusable", confidence=0.0, unusable_reason=blocked
        )
    rows = score_candidates(pack, curriculum, history)
    eligible = [row for row in rows if row.eligible]
    if not eligible:
        reason = (
            REASON_NOTHING_MEASURED
            if rows
            else REASON_NO_CANDIDATES
        )
        return Classification(
            method="unusable",
            confidence=0.0,
            unusable_reason=reason,
            candidates=[
                _row_to_candidate(row, str(resolve(row.level.id)))
                for row in rows[:max_candidates]
            ],
        )
    top = eligible[0]
    runner = eligible[1] if len(eligible) > 1 else None
    separation = top.score - (runner.score if runner is not None else 0.0)
    separation_factor = _clamp(
        separation / SEPARATION_SPAN, SEPARATION_FLOOR, 1.0
    )
    factor = quality_factor(pack)
    confidence = _clamp(top.score * factor * separation_factor)
    ambiguous = confidence < CONF_GATE
    keep = 2 if ambiguous else max_candidates
    shown = eligible[:keep]
    rejected_rows = [row for row in rows if not row.eligible]
    if not ambiguous:
        # Keep the age-excluded rows visible: "not applicable at this age" is
        # information the report must show, not a candidate silently dropped.
        shown = shown + [
            row
            for row in rejected_rows
            if row.rejected_reason == REASON_NOT_APPLICABLE_AGE
        ][:2]
    candidates: list[Candidate] = []
    for row in shown:
        separating = ("", "")
        if row is not top:
            # The display name is deliberately left empty: this module has no
            # ``lang`` and must not put a raw metric id in a name field, or the
            # ports render ``turn_shape_index``. The localizing caller
            # (``assess.assess_clip``) fills it from ``score.metric_name``.
            separating = (_separating_metric(top, row), "")
        candidates.append(
            _row_to_candidate(row, str(resolve(row.level.id)), separating)
        )
    return Classification(
        method="scored_candidates",
        chosen_id=top.level.id,
        confidence=round(confidence, 4),
        separation=round(separation, 4),
        quality_factor=round(factor, 4),
        candidates=candidates,
        ambiguous=ambiguous,
    )


def separating_metric_id(classification: Classification) -> str:
    """The runner-up's separating metric, or ``""``. Convenience for chapter 2."""
    for candidate in classification.candidates[1:]:
        if candidate.separating_metric_id:
            return candidate.separating_metric_id
    return ""


# ---------------------------------------------------------------------------
# v2 ladder, kept for comparison (design §5, last paragraph)
# ---------------------------------------------------------------------------

UNKNOWN = "unknown"
SYS_CATEGORY = "unknown"
LEGACY_QUALITY_GATE = 0.2


def classify_legacy(pack: FeaturePack) -> tuple[str, str, float]:
    """The v2 if-ladder, moved here unchanged from ``assess.classify``.

    Strong mogul (large knee absorb) wins first. Carve-like angulation on a
    narrow stance is checked before soft mogul so groomed green-piste carving
    is not swallowed by knee rhythm alone. Soft mogul requires wide stance.

    Kept so the two classifiers can be compared on the same fixtures; the v2
    thresholds are on v2's denominators and its inflated frequency scale, so
    the numbers here must not be reused for v3 bands.
    """
    if pack.n < 4 or pack.quality < LEGACY_QUALITY_GATE:
        return SYS_CATEGORY, UNKNOWN, 0.0

    def _mogul_stage() -> tuple[str, str, float]:
        stage = "mogul_absorb"
        if pack.fall_line < 0.85 and pack.knee_flex_freq > 1.1:
            stage = "mogul_fallline"
        return "alpine_moguls", stage, min(1.0, 0.45 + pack.knee_flex_freq / 4.0)

    # Strong mogul: clear bump absorption (real mogul clips ~amp 70+).
    if pack.knee_flex_amp > 50.0 and pack.knee_flex_freq > 0.8:
        return _mogul_stage()
    # Carve / angulated piste before soft mogul (green-piste false positives).
    if pack.inward_lean >= 0.18 and pack.stance_width < 1.2:
        if pack.turn_freq >= 0.45:
            return "alpine_piste", "carve_short", 0.5
        if pack.turn_freq >= 0.32:
            return "alpine_piste", "carve_medium", 0.5
        return "alpine_piste", "carve_long", 0.5
    # Soft mogul: medium knee work with wide projected stance.
    if (
        pack.knee_flex_amp > 35.0
        and pack.knee_flex_freq > 0.6
        and pack.stance_width >= 1.2
    ):
        return _mogul_stage()
    # Pizza / glide: wide stance without mogul-like knee rhythm.
    if pack.stance_width >= 1.2 and pack.knee_flex_freq <= 0.6:
        conf = min(1.0, 0.4 + (pack.stance_width - 1.2))
        if pack.turn_freq < 0.18:
            return "alpine_piste", "pizza_glide", conf
        return "alpine_piste", "pizza", conf
    if (
        pack.stance_width_std >= 0.22
        and pack.stance_width >= 0.95
        and pack.inward_lean < 0.18
    ):
        return "alpine_piste", "wedge_christie", 0.55
    if pack.stance_width < 1.1 and pack.turn_freq >= 0.45:
        return "alpine_piste", "skid_short", 0.5
    if pack.stance_width < 1.1:
        return "alpine_piste", "parallel", 0.55
    return SYS_CATEGORY, UNKNOWN, 0.25


