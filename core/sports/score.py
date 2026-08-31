"""Metric scoring, stage score and the advance rule (design §6).

What changed from v2, in the order §6 lists it:

1. **Count gates.** A ``C``-form metric scores ``100 * (1 - faulty/total)``
   clipped by the allowance, and the report states it the way the curriculum
   does: *"stems in 3 of 22 transitions — the allowance is 2"*. The clipping
   lives in :mod:`core.sports.bands`.
2. **Reliability weighting.** The stage score is a reliability-weighted mean
   over the *gate* metrics, not a flat mean, so a metric measured on a marginal
   view cannot sink the stage. Reliability comes straight from the measurement
   layer and is reported next to every metric.
3. **Asymmetry separately.** Paired metrics keep both sides
   (``left_value`` / ``right_value``) and the weaker side is named on the
   ``asymmetry_index`` row rather than averaged away.
4. **Rubric alongside score.** Every row carries ``not_yet`` / ``pass`` /
   ``strong`` from the band's three thresholds.
5. **Three states.** ``ok`` / ``unknown`` / ``not_applicable`` are distinct and
   ``state`` plus ``reason`` say which. Nothing here ever turns an unmeasured or
   not-applicable metric into a zero — not in a row, not in the stage score.

Decisions beyond §6, stated because they change what "ready" means:

* **An unmeasured gate does not block advancement, but an unmeasured-only stage
  does.** §6 says "every gate metric at pass or better". Read literally, a clip
  filmed face-on could never advance any stage that gates a fore/aft metric,
  because 2D pose cannot see fore/aft in that view at all. The rule applied
  here is v2's (``assess._required_ok``): every *measured* gate metric must
  pass, and at least one gate metric must have been measured. The gates that
  were not measured are listed in the filming chapter, so the reason is visible
  rather than hidden inside a boolean.
* **The v2 confidence taper is kept** (``score * (0.8 + 0.2*confidence)``) so a
  v2 report and a v3 report put comparable numbers on the same clip.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.i18n import t
from core.sports.bands import (
    INJURY_RISK_METRICS,
    INJURY_RISK_SWEEP,
    Evaluation,
    band_for,
    evaluate,
)
from core.sports.curriculum import Curriculum, LevelSpec
from core.sports.metrics import (
    BY_ID,
    REASON_NO_SAMPLES,
    REASON_NO_SCALE,
    REASON_LANDMARK_MISSING,
    REASON_NO_TURNS,
    REASON_NON_FINITE,
    REASON_TOO_FRONTAL,
    REASON_TOO_PROFILE,
    MetricPack,
    MetricValue,
    spec_for,
)
from schemas.stage_report import MetricReport, MetricState, Rubric

#: Weight floor, so a metric with near-zero reliability still counts a little
#: rather than dropping out of the stage score entirely.
RELIABILITY_FLOOR = 0.15

CONF_GATE = 0.35

_RUBRIC = {
    "not_yet": Rubric.NOT_YET,
    "pass": Rubric.PASS,
    "strong": Rubric.STRONG,
    "not_rated": Rubric.NOT_RATED,
}

#: English display names per metric id. Every one is a ``t()`` key; the zh side
#: lives in ``locales/_v3_keys.assess.json``.
METRIC_NAMES: dict[str, str] = {
    "stance_width": "Stance width",
    "stance_width_var": "Stance width change",
    "wedge_angle": "Wedge angle",
    "shin_angle_fore_aft": "Shin angle",
    "hip_over_foot": "Hips over the feet",
    "com_vertical_travel": "Up-and-down movement",
    "edge_angle_proxy": "Edge angle (proxy)",
    "inclination": "Inclination",
    "angulation": "Angulation",
    "banking_index": "Banking share",
    "separation_angle": "Upper-lower separation",
    "upper_body_quiet": "Quiet upper body",
    "knee_valgus": "Knee tracking",
    "turn_rate": "Turn rate",
    "turn_duration_var": "Rhythm evenness",
    "turn_amplitude": "Turn amplitude",
    "turn_shape_index": "Turn shape",
    "edge_change_duration": "Edge-change time",
    "flexion_range": "Knee flex range",
    "flexion_rate": "Knee flex rate",
    "pressure_peak_phase": "Pressure peak in the turn",
    "stem_count": "Stemmed transitions",
    "backseat_count": "Back-seat finishes",
    "rotation_count": "Turns led by the shoulders",
    "braking_count": "Braking turns",
    "asymmetry_index": "Left-right asymmetry",
    "hands_in_view": "Hands in view",
    "pole_touch_rate": "Pole touch per turn",
    "pole_touch_timing": "Pole touch timing",
    "view_azimuth_deg": "Camera angle",
    "view_class": "View",
    "landmark_quality": "Skeleton quality",
    "usable_frame_ratio": "Usable frames",
    "camera_motion": "Camera motion",
    "fps_effective": "Effective frame rate",
    "turn_count": "Turns detected",
}

#: English display names per metric group.
GROUP_NAMES: dict[str, str] = {
    "stance": "Stance and balance",
    "edging": "Edging and steering",
    "rhythm": "Rhythm and turn shape",
    "faults": "Turn faults",
    "poles": "Poles and hands",
    "quality": "Filming quality",
}

#: Why a metric has no number, as display text.
REASON_TEXT: dict[str, str] = {
    REASON_TOO_PROFILE: "Filmed too side-on to measure this.",
    REASON_TOO_FRONTAL: "Filmed too face-on to measure this.",
    REASON_NO_TURNS: "No linked turns were detected in this clip.",
    REASON_NO_SCALE: "The skeleton was too small or incomplete to measure.",
    REASON_NO_SAMPLES: "Not measured in this clip.",
    REASON_NON_FINITE: "Not measured in this clip.",
}

NOT_APPLICABLE_AGE_TEXT = "Not applicable at this age."

#: One display key per joint slug the measurement layer can name; the zh side
#: lives in ``locales/_v3_keys.corefix.json``.
JOINT_NAMES: dict[str, str] = {
    "left_shoulder": "left shoulder",
    "right_shoulder": "right shoulder",
    "left_wrist": "left wrist",
    "right_wrist": "right wrist",
    "left_hip": "left hip",
    "right_hip": "right hip",
    "left_knee": "left knee",
    "right_knee": "right knee",
    "left_ankle": "left ankle",
    "right_ankle": "right ankle",
    "left_heel": "left heel",
    "right_heel": "right heel",
    "left_foot": "left foot",
    "right_foot": "right foot",
}

LANDMARK_MISSING_TEXT = "The {joints} could not be tracked in this clip."


def _joint_list(slugs: str, lang: str) -> str:
    names = [
        t(JOINT_NAMES.get(slug, slug.replace("_", " ")), lang=lang)
        for slug in slugs.split("+")
        if slug
    ]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return t(
        "{head} and {tail}",
        lang=lang,
        head=", ".join(names[:-1]),
        tail=names[-1],
    )


def metric_name(metric_id: str, lang: str) -> str:
    base = metric_id.rsplit("_left", 1)[0].rsplit("_right", 1)[0]
    return t(METRIC_NAMES.get(base, base), lang=lang)


def group_name(group: str, lang: str) -> str:
    return t(GROUP_NAMES.get(group, group), lang=lang)


def reason_text(reason: str | None, lang: str) -> str:
    if not reason:
        return ""
    if reason.startswith("not_applicable_age_band"):
        return t(NOT_APPLICABLE_AGE_TEXT, lang=lang)
    if reason.startswith(f"{REASON_LANDMARK_MISSING}:"):
        return t(
            LANDMARK_MISSING_TEXT,
            lang=lang,
            joints=_joint_list(reason.split(":", 1)[1], lang),
        )
    return t(REASON_TEXT.get(reason, reason), lang=lang)


def standard_text(evaluation: Evaluation, unit: str, lang: str) -> str:
    """The band's standard, localized. Mirrors ``Band.standard`` structurally."""
    text = evaluation.standard
    if not text:
        return ""
    if text.startswith("at most ") and " of " in text:
        head, _, tail = text[len("at most "):].partition(" of ")
        return t("at most {n} of {total}", lang=lang, n=head, total=tail)
    if text.startswith("at least "):
        return t(
            "at least {value}",
            lang=lang,
            value=_with_unit(text[len("at least "):], unit, lang),
        )
    if text.startswith("at most "):
        return t(
            "at most {value}",
            lang=lang,
            value=_with_unit(text[len("at most "):], unit, lang),
        )
    lo, _, hi = text.partition(" to ")
    return t(
        "{lo} to {hi}",
        lang=lang,
        lo=_with_unit(lo, unit, lang),
        hi=_with_unit(hi, unit, lang),
    )


UNIT_SUFFIX = {
    "deg": "°",
    "hz": " Hz",
    "s": " s",
}


def _with_unit(number: str, unit: str, lang: str) -> str:
    suffix = UNIT_SUFFIX.get(unit.lower(), "")
    return f"{number}{suffix}"


def _format_value(item: MetricValue, unit: str, lang: str) -> str:
    """Human-facing value, already unit-converted (schema: ``display``)."""
    if item.text:
        return t(item.text.replace("_", " ").capitalize(), lang=lang)
    if item.value is None:
        return ""
    unit_key = unit.lower()
    if item.form == "C" and item.total_turns:
        return t(
            "{n} of {total} turns",
            lang=lang,
            n=int(item.faulty_turns or 0),
            total=int(item.total_turns),
        )
    if unit_key == "deg":
        return f"{item.value:.0f}°"
    if unit_key == "hz":
        return f"{item.value:.2f} Hz"
    if unit_key == "s":
        return f"{item.value:.2f} s"
    if unit_key in ("fraction", "ratio"):
        return f"{item.value:.2f}"
    if unit_key == "turns":
        return f"{item.value:.0f}"
    return f"{item.value:.2f}"


def _state(item: MetricValue) -> MetricState:
    if item.state == "ok":
        return MetricState.OK
    if item.state == "not_applicable":
        return MetricState.NOT_APPLICABLE
    return MetricState.UNKNOWN


def _paired_values(pack: MetricPack, metric_id: str) -> tuple[float | None, float | None]:
    spec = spec_for(metric_id)
    if spec is None or not spec.per_side:
        return None, None
    return pack.value(f"{metric_id}_left"), pack.value(f"{metric_id}_right")


@dataclass(frozen=True)
class ScoredMetric:
    """A metric row plus what the caller needs to reason about it."""

    report: MetricReport
    evaluation: Evaluation
    reliability: float
    is_gate: bool

    @property
    def measured(self) -> bool:
        return self.report.state == MetricState.OK and self.report.score is not None


def score_metric(
    pack: MetricPack,
    level: LevelSpec,
    metric_id: str,
    lang: str,
    *,
    age_band: str | None = None,
    is_gate: bool = False,
) -> ScoredMetric:
    """Score one metric of one level into a report row."""
    item = pack.get(metric_id)
    spec = BY_ID.get(metric_id) or spec_for(metric_id)
    unit = item.unit if item is not None else (spec.unit if spec else "")
    band = band_for(level.id, metric_id, age_band)
    evaluation = evaluate(band, item)
    left, right = _paired_values(pack, metric_id)
    if item is None:
        report = MetricReport(
            id=metric_id,
            name=metric_name(metric_id, lang),
            group=group_name(spec.group if spec else "", lang),
            state=MetricState.UNKNOWN,
            reason=reason_text(REASON_NO_SAMPLES, lang),
            unit=unit,
            is_gate=is_gate,
        )
        return ScoredMetric(report, evaluation, 0.0, is_gate)
    report = MetricReport(
        id=metric_id,
        name=metric_name(metric_id, lang),
        group=group_name(spec.group if spec else "", lang),
        state=_state(item),
        reason=reason_text(item.reason, lang),
        value=item.value,
        unit=unit,
        display=_format_value(item, unit, lang),
        score=evaluation.score,
        rubric=_RUBRIC.get(evaluation.rubric, Rubric.NOT_RATED),
        reliability=round(float(item.reliability), 3),
        is_gate=is_gate,
        standard=standard_text(evaluation, unit, lang),
        form=item.form,
        per_turn=list(item.per_turn or []),
        faulty_turns=evaluation.faulty_turns
        if evaluation.faulty_turns is not None
        else item.faulty_turns,
        total_turns=evaluation.total_turns
        if evaluation.total_turns is not None
        else item.total_turns,
        evidence_ms=None if item.evidence_ms is None else float(item.evidence_ms),
        left_value=left,
        right_value=right,
    )
    return ScoredMetric(report, evaluation, float(item.reliability), is_gate)


def score_level(
    pack: MetricPack, level: LevelSpec, lang: str
) -> list[ScoredMetric]:
    """Every core metric of a level, in the curriculum's diagnostic order."""
    age_band = getattr(pack.athlete, "age_band", None)
    gates = set(level.gate_metrics)
    rows = [
        score_metric(
            pack,
            level,
            metric_id,
            lang,
            age_band=age_band,
            is_gate=metric_id in gates,
        )
        for metric_id in level.core_metrics
    ]
    asym = _asymmetry_row(pack, level, lang, rows)
    if asym is not None:
        rows.append(asym)
    return rows


def _asymmetry_row(
    pack: MetricPack,
    level: LevelSpec,
    lang: str,
    rows: list[ScoredMetric],
) -> ScoredMetric | None:
    """The separate asymmetry row (§6.3), with the weaker side named.

    Skipped when ``asymmetry_index`` is already one of the level's core metrics
    (``pizza``, the carve levels, ``powder``) — those rows get the side stamped
    on them instead.
    """
    side = weaker_side(pack, level)
    if "asymmetry_index" in level.core_metrics:
        for row in rows:
            if row.report.id == "asymmetry_index":
                row.report.side = side
        return None
    item = pack.get("asymmetry_index")
    if item is None or item.state != "ok":
        return None
    scored = score_metric(
        pack, level, "asymmetry_index", lang, age_band=getattr(pack.athlete, "age_band", None)
    )
    scored.report.side = side
    return scored


def weaker_side(pack: MetricPack, level: LevelSpec) -> str:
    """Which leg scores worse across this level's paired metrics, or ``""``.

    Both sides are scored against the same band and the side with the lower
    mean score is named. A tie, or no paired metric measured, gives ``""``
    rather than picking one.
    """
    age_band = getattr(pack.athlete, "age_band", None)
    totals = {"left": [], "right": []}  # type: dict[str, list[float]]
    for metric_id in level.core_metrics:
        spec = BY_ID.get(metric_id)
        if spec is None or not spec.per_side:
            continue
        band = band_for(level.id, metric_id, age_band)
        for side in ("left", "right"):
            result = evaluate(band, pack.get(f"{metric_id}_{side}"))
            if result.score is not None:
                totals[side].append(result.score)
    if not totals["left"] or not totals["right"]:
        return ""
    left = sum(totals["left"]) / len(totals["left"])
    right = sum(totals["right"]) / len(totals["right"])
    if abs(left - right) < 1.0:
        return ""
    return "left" if left < right else "right"


def stage_score(
    rows: list[ScoredMetric], confidence: float, curriculum: Curriculum
) -> float:
    """Reliability-weighted mean over the gate metrics (§6.2).

    Falls back to the measured core metrics when no gate metric produced a
    value, and to 0.0 when nothing did. The v2 confidence taper is applied last
    so the number stays comparable with a stored 2.1.0 report.

    ``curriculum`` is accepted for symmetry with
    :func:`ready_for_next_stage` — the pass mark lives there, not here, because
    a score is a measurement and the pass mark is a policy.
    """
    _ = curriculum
    gate_rows = [row for row in rows if row.is_gate and row.measured]
    pool = gate_rows or [row for row in rows if row.measured]
    if not pool:
        return 0.0
    weights = [max(row.reliability, RELIABILITY_FLOOR) for row in pool]
    total = sum(weights)
    raw = sum(
        weight * float(row.report.score or 0.0)
        for weight, row in zip(weights, pool)
    ) / total
    return round(raw * (0.8 + 0.2 * max(0.0, min(1.0, confidence))), 1)


def gate_summary(rows: list[ScoredMetric]) -> tuple[int, int, list[str]]:
    """``(passed, measured, unmeasured_ids)`` over the gate metrics."""
    gates = [row for row in rows if row.is_gate]
    measured = [row for row in gates if row.measured]
    passed = sum(1 for row in measured if row.evaluation.passing)
    unmeasured = [row.report.id for row in gates if not row.measured]
    return passed, len(measured), unmeasured


def injury_flags(
    rows: list[ScoredMetric],
    *,
    pack: MetricPack | None = None,
    level: LevelSpec | None = None,
) -> list[str]:
    """Failing metrics that carry the design's ``injury-risk`` flag (§6).

    Back-seat (``hip_over_foot``, ``backseat_count``) and banking
    (``banking_index``) are the two the design names.

    ``rows`` only ever covers ``level.core_metrics``, so on the stages that do
    not list an injury-risk metric — ``skid_short``, the ``carve_*`` rungs and
    the ``mogul_*`` rungs — the block silently did not apply and a skier deep in
    the back seat could advance. §6 states the rule unconditionally, so when
    ``pack`` and ``level`` are supplied every injury-risk metric that has no row
    is evaluated straight off the pack against this stage's band and flagged
    when its rubric is ``not_yet``. An unmeasured or not-applicable metric
    evaluates to ``not_rated`` and therefore never blocks, matching the
    module-level rule for gates. Behaviour is unchanged when they are omitted.
    """
    flagged = [
        row.report.id
        for row in rows
        if row.report.id in INJURY_RISK_METRICS
        and row.measured
        and not row.evaluation.passing
    ]
    # Fore/aft is dangerous at every stage, so it is swept everywhere. Banking is
    # only a hazard once the skier is actually carrying edge angle, and on a
    # wedge rung the index is a ratio of two noise-level angles — so it blocks
    # advancement only on the stages that list it as a core metric, where the
    # rows above already cover it.
    if pack is None or level is None:
        return flagged
    core = set(level.core_metrics)
    age_band = getattr(pack.athlete, "age_band", None)
    for metric_id in sorted(INJURY_RISK_SWEEP):
        if metric_id in flagged or metric_id in core:
            continue
        evaluation = evaluate(
            band_for(level.id, metric_id, age_band), pack.get(metric_id)
        )
        if evaluation.rubric == "not_yet":
            flagged.append(metric_id)
    return flagged


def weakest(rows: list[ScoredMetric]) -> ScoredMetric | None:
    """Lowest-scoring measured gate metric, else lowest-scoring measured metric."""
    gates = [row for row in rows if row.is_gate and row.measured]
    pool = gates or [row for row in rows if row.measured]
    if not pool:
        return None
    return min(pool, key=lambda row: float(row.report.score or 0.0))


def ready_for_next_stage(
    rows: list[ScoredMetric],
    *,
    confidence: float,
    score: float,
    curriculum: Curriculum,
    pack: MetricPack | None = None,
    level: LevelSpec | None = None,
) -> bool:
    """The §6 advance rule, made explicit.

    ``confidence >= 0.35`` and ``score >= pass_score`` and every measured gate
    metric at ``pass`` or better (with at least one measured) and no
    injury-risk fault flagged.

    ``pack`` / ``level`` make the injury-risk block unconditional even on a
    stage whose ``core_metrics`` list no injury-risk metric; see
    :func:`injury_flags`. Omitting them keeps the previous behaviour.
    """
    if confidence < CONF_GATE or score < curriculum.pass_score:
        return False
    passed, measured, _ = gate_summary(rows)
    if measured == 0 or passed != measured:
        return False
    return not injury_flags(rows, pack=pack, level=level)
