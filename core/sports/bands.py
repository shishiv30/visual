"""Per-stage metric bands: the numbers the classifier and the scorer read.

Design §5 calls for ``membership(metric, L.band[metric])`` and §6 for
``band = level.band[metric], possibly overridden by age band``. The v3
curriculum bundle (``content/ski/curriculum.v3.json``) carries ``core_metrics``
and ``gate_metrics`` per level but **no bands**: only the 39 legacy checkpoints
carry a single ``Threshold`` each. This module is therefore the band table, and
it is code rather than content on purpose — every number here is a calibration
choice that has to be reviewable next to the formula it is calibrated against
(``core.sports.metrics.build_series``), not translatable content.

Shape of a band
---------------

One band is a trapezoid plus a rubric, expressed with four ascending support
points and a strong region:

``fail_lo`` .. ``pass_lo`` .. ``pass_hi`` .. ``fail_hi``

* ``membership`` is 1 inside ``[pass_lo, pass_hi]``, ramps linearly to 0 at
  ``fail_lo`` / ``fail_hi``, and is 0 outside. This is what makes a value
  sitting between two stages contribute partially to both (§5), which is what
  makes the runner-up and the separating metric meaningful.
* ``rubric`` is ``strong`` inside the strong region, ``pass`` inside the pass
  region, ``not_yet`` otherwise — the curriculum's three-level rubric (§6.4).
* ``score`` keeps v2's piecewise shape (0 at the fail edge, 60 at the pass
  edge, 100 at the strong edge), so a stored v2 report and a v3 report put the
  same number on the same skiing.

Count (``C``) bands are different in kind: they carry an allowance as a
*fraction of the turns actually measured* plus an absolute floor, because the
curriculum phrases these gates as "20 consecutive turns, at most 2 faulty"
(≈10%) and a clip with six turns must not inherit an allowance sized for
twenty.

Calibration notes
-----------------

All ratios are in the v3 denominators (§3.2): stance and fore/aft over **leg
length**, valgus over **shank length**. Reading a v2 threshold across means
dividing by ~3, since hip width is ~0.36 leg lengths — e.g. v2's parallel
stance ``between 0.65 and 1.12`` hip widths becomes ``0.22 .. 0.37`` leg
lengths, which is what the parallel band below says.

Frequencies are true Hz. v2's thresholds were on a ~2x inflated scale
(``signals.py:266``), so they are **not** carried across; the numbers here are
physical (a beginner wedge turn takes 3-5 s, short turns 1-2 s).

Profile overrides
-----------------

Only the two the design sanctions by name (§2.3) exist:

1. ``stance_width`` is not penalized for ``age-3-6`` / ``age-7-12`` — a wide
   stance is mechanically correct at that leg length. Implemented as a widening
   of the upper edge only, and recorded in ``ProfileSummary.effects`` so it is
   never silent.
2. Carving metrics are *not applicable* below ``age-13-17``; that is handled in
   the measurement layer (``metrics.carving_applicable``) and in the tree, and
   is never expressed as a pass.

An override may only widen a pass region, never narrow one and never move a
pass edge in the passing direction: :func:`band_for` asserts it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from core.sports.profile import AGE_3_6, AGE_7_12

Kind = Literal["gte", "lte", "between", "count"]
Reading = Literal["signed", "magnitude"]

INF = math.inf

#: Score at the pass edge, matching v2's ``_piecewise`` and the curriculum's
#: ``checkpoint_pass``.
PASS_SCORE = 60.0
#: Ceiling applied to a count metric that blew its allowance, so a failed gate
#: can never read as a pass however few turns were faulty in relative terms.
COUNT_FAIL_CEILING = 55.0
#: Floor applied to a count metric inside its allowance, for the mirror reason.
COUNT_PASS_FLOOR = 65.0
#: How far past the allowance (as a fraction of turns) membership decays to 0.
COUNT_MEMBERSHIP_SPAN = 0.35


@dataclass(frozen=True)
class Band:
    """One metric's standard at one stage."""

    kind: Kind
    fail_lo: float = -INF
    pass_lo: float = -INF
    pass_hi: float = INF
    fail_hi: float = INF
    strong_lo: float = -INF
    strong_hi: float = INF
    #: ``count`` only: allowance as a fraction of measured turns, and its floor.
    allow_ratio: float = 0.10
    min_allowance: int = 2
    reading: Reading = "signed"

    # -- construction ---------------------------------------------------
    @staticmethod
    def gte(fail: float, pass_: float, strong: float, *, reading: Reading = "signed") -> Band:
        """Higher is better: 0 at ``fail``, pass at ``pass_``, 100 at ``strong``."""
        return Band(
            "gte",
            fail_lo=fail,
            pass_lo=pass_,
            pass_hi=INF,
            fail_hi=INF,
            strong_lo=strong,
            strong_hi=INF,
            reading=reading,
        )

    @staticmethod
    def lte(strong: float, pass_: float, fail: float, *, reading: Reading = "signed") -> Band:
        """Lower is better: 100 at ``strong``, pass at ``pass_``, 0 at ``fail``."""
        return Band(
            "lte",
            fail_lo=-INF,
            pass_lo=-INF,
            pass_hi=pass_,
            fail_hi=fail,
            strong_lo=-INF,
            strong_hi=strong,
            reading=reading,
        )

    @staticmethod
    def between(
        fail_lo: float,
        pass_lo: float,
        pass_hi: float,
        fail_hi: float,
        *,
        reading: Reading = "signed",
    ) -> Band:
        """A window: strong is the middle half of the pass region."""
        mid = 0.5 * (pass_lo + pass_hi)
        quarter = 0.25 * (pass_hi - pass_lo)
        return Band(
            "between",
            fail_lo=fail_lo,
            pass_lo=pass_lo,
            pass_hi=pass_hi,
            fail_hi=fail_hi,
            strong_lo=mid - quarter,
            strong_hi=mid + quarter,
            reading=reading,
        )

    @staticmethod
    def count(allow_ratio: float = 0.10, min_allowance: int = 2) -> Band:
        """At most ``allow_ratio`` of the measured turns faulty, floor included."""
        return Band("count", allow_ratio=allow_ratio, min_allowance=min_allowance)

    # -- reading --------------------------------------------------------
    def read(self, value: float | None) -> float | None:
        """Apply the band's reading convention to a raw metric value.

        ``magnitude`` exists because three metrics are signed oscillations whose
        whole-clip aggregate is a *median of a signed series* and therefore sits
        near zero for symmetric skiing (``separation_angle``,
        ``pole_touch_timing``, ``asymmetry_index``). §4 gates the *amount* of
        separation, so the amount is what is compared.
        """
        if value is None:
            return None
        return abs(value) if self.reading == "magnitude" else value

    def allowance(self, total: int) -> int:
        """Faulty-turn allowance for a clip with ``total`` measured turns."""
        if total <= 0:
            return self.min_allowance
        return max(self.min_allowance, int(math.ceil(self.allow_ratio * total)))

    # -- membership, rubric, score --------------------------------------
    def membership(
        self, value: float | None, *, faulty: int | None = None, total: int | None = None
    ) -> float | None:
        """Trapezoidal membership in ``[0, 1]``, or ``None`` when unmeasured.

        The plateau is the **strong** region and the ramps run out to the fail
        edges, so a value barely inside the pass region contributes partially
        rather than fully. Ramping to the pass edge instead was tried first and
        makes the classifier degenerate: on a clean clip a dozen levels all
        reach ``fit = 1.0``, separation collapses to zero and every report comes
        out ambiguous. Peaking on the strong region is what gives §5's
        "contributes partially to both" any discriminating power.
        """
        if self.kind == "count":
            if faulty is None or not total:
                return None
            allowed = self.allowance(total)
            ratio = float(faulty) / float(total)
            edge = (allowed / float(total)) + COUNT_MEMBERSHIP_SPAN
            if faulty == 0:
                return 1.0
            if ratio >= edge:
                return 0.0
            return _ramp(ratio, edge, 0.0)
        raw = self.read(value)
        if raw is None:
            return None
        if self.strong_lo <= raw <= self.strong_hi:
            return 1.0
        if raw < self.strong_lo:
            if raw <= self.fail_lo:
                return 0.0
            return _ramp(raw, self.fail_lo, self.strong_lo)
        if raw >= self.fail_hi:
            return 0.0
        return _ramp(raw, self.fail_hi, self.strong_hi)

    def rubric(
        self, value: float | None, *, faulty: int | None = None, total: int | None = None
    ) -> str:
        """``strong`` / ``pass`` / ``not_yet``, or ``not_rated`` when unmeasured."""
        if self.kind == "count":
            if faulty is None or not total:
                return "not_rated"
            if faulty == 0:
                return "strong"
            return "pass" if faulty <= self.allowance(total) else "not_yet"
        raw = self.read(value)
        if raw is None:
            return "not_rated"
        if self.strong_lo <= raw <= self.strong_hi:
            return "strong"
        if self.pass_lo <= raw <= self.pass_hi:
            return "pass"
        return "not_yet"

    def score(
        self, value: float | None, *, faulty: int | None = None, total: int | None = None
    ) -> float | None:
        """0-100, keeping v2's piecewise shape (design §6)."""
        if self.kind == "count":
            if faulty is None or not total:
                return None
            allowed = self.allowance(total)
            base = 100.0 * (1.0 - float(faulty) / float(total))
            if faulty > allowed:
                return round(min(base, COUNT_FAIL_CEILING), 1)
            return round(max(base, COUNT_PASS_FLOOR) if faulty else 100.0, 1)
        raw = self.read(value)
        if raw is None:
            return None
        if self.kind == "gte":
            return _piecewise(raw, self.fail_lo, self.pass_lo, self.strong_lo)
        if self.kind == "lte":
            return _piecewise(-raw, -self.fail_hi, -self.pass_hi, -self.strong_hi)
        # between: v2's shape — full marks at the centre, 60 at the edges.
        lo, hi = self.pass_lo, self.pass_hi
        if lo <= raw <= hi:
            mid = 0.5 * (lo + hi)
            span = max((hi - lo) / 2.0, 1e-6)
            return round(100.0 - 40.0 * abs(raw - mid) / span, 1)
        if raw < lo:
            width = max(lo - self.fail_lo, 1e-6)
            return round(max(0.0, 60.0 * (1.0 - (lo - raw) / width)), 1)
        width = max(self.fail_hi - hi, 1e-6)
        return round(max(0.0, 60.0 * (1.0 - (raw - hi) / width)), 1)

    def standard(self, *, total: int | None = None) -> str:
        """Plain-language statement of the standard, for the report.

        English only: the caller runs it through ``core.i18n.t`` with the
        numbers substituted, which is why the shape is a format string.
        """
        if self.kind == "count":
            return f"at most {self.allowance(total or 0)} of {total or 0}"
        if self.kind == "gte":
            return f"at least {_num(self.pass_lo)}"
        if self.kind == "lte":
            return f"at most {_num(self.pass_hi)}"
        return f"{_num(self.pass_lo)} to {_num(self.pass_hi)}"

    def widened_high(self, delta: float) -> Band:
        """Copy with the upper edges pushed out — the only override allowed."""
        if delta <= 0.0 or self.kind == "count":
            return self
        return Band(
            self.kind,
            fail_lo=self.fail_lo,
            pass_lo=self.pass_lo,
            pass_hi=self.pass_hi + delta if self.pass_hi != INF else INF,
            fail_hi=self.fail_hi + delta if self.fail_hi != INF else INF,
            strong_lo=self.strong_lo,
            strong_hi=self.strong_hi + delta if self.strong_hi != INF else INF,
            allow_ratio=self.allow_ratio,
            min_allowance=self.min_allowance,
            reading=self.reading,
        )


def _ramp(value: float, zero_at: float, one_at: float) -> float:
    span = one_at - zero_at
    if not math.isfinite(span) or abs(span) < 1e-12:
        return 0.0
    return max(0.0, min(1.0, (value - zero_at) / span))


def _piecewise(value: float, lo: float, mid: float, hi: float) -> float:
    """v2's ``assess._piecewise``: 0 at ``lo``, 60 at ``mid``, 100 at ``hi``."""
    if value <= lo:
        return 0.0
    if value >= hi:
        return 100.0
    if value < mid:
        return round(60.0 * (value - lo) / max(mid - lo, 1e-6), 1)
    return round(60.0 + 40.0 * (value - mid) / max(hi - mid, 1e-6), 1)


def _num(value: float) -> str:
    if value in (INF, -INF):
        return "any"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# the table
# ---------------------------------------------------------------------------

#: Fallback band per metric: "competent recreational skiing" for that quantity.
DEFAULTS: dict[str, Band] = {
    # stance and balance
    "stance_width": Band.between(0.14, 0.22, 0.40, 0.58),
    "stance_width_var": Band.lte(0.03, 0.10, 0.22),
    "wedge_angle": Band.lte(3.0, 8.0, 20.0),
    "ski_wedge_angle": Band.lte(3.0, 8.0, 20.0),
    "ski_parallelism": Band.gte(0.70, 0.85, 1.0),
    "shin_angle_fore_aft": Band.between(-2.0, 5.0, 25.0, 38.0),
    "hip_over_foot": Band.between(-0.15, -0.05, 0.12, 0.25),
    "com_vertical_travel": Band.gte(0.02, 0.06, 0.16),
    # edging and steering
    "edge_angle_proxy": Band.gte(5.0, 12.0, 28.0),
    "inclination": Band.gte(3.0, 8.0, 22.0),
    "angulation": Band.gte(3.0, 8.0, 20.0),
    "banking_index": Band.lte(0.35, 0.60, 0.85),
    "separation_angle": Band.gte(4.0, 10.0, 26.0, reading="magnitude"),
    "upper_body_quiet": Band.lte(2.5, 7.0, 14.0),
    "knee_valgus": Band.lte(0.10, 0.30, 0.60),
    # rhythm and turn shape
    "turn_rate": Band.gte(0.08, 0.18, 0.40),
    "turn_duration_var": Band.lte(0.08, 0.25, 0.50),
    "turn_amplitude": Band.gte(5.0, 10.0, 28.0),
    "turn_shape_index": Band.gte(0.22, 0.35, 0.58),
    "edge_change_duration": Band.lte(0.15, 0.35, 0.70),
    "flexion_range": Band.gte(6.0, 15.0, 32.0),
    "flexion_rate": Band.gte(0.20, 0.45, 0.95),
    "pressure_peak_phase": Band.between(0.15, 0.32, 0.70, 0.88),
    # per-turn faults
    "stem_count": Band.count(0.10, 2),
    "backseat_count": Band.count(0.15, 2),
    "rotation_count": Band.count(0.15, 2),
    "braking_count": Band.count(0.10, 2),
    "asymmetry_index": Band.lte(0.30, 0.80, 2.00, reading="magnitude"),
    # poles and hands
    "hands_in_view": Band.gte(0.30, 0.55, 0.85),
    "pole_touch_rate": Band.gte(0.30, 0.70, 0.95),
    "pole_touch_timing": Band.lte(0.10, 0.25, 0.50, reading="magnitude"),
}

#: Per-level overrides. Only what differs from :data:`DEFAULTS` is listed, so a
#: reviewer reads the table as "what this stage asks that is special".
OVERRIDES: dict[str, dict[str, Band]] = {
    "pizza_glide": {
        # v2 `cp_pg_stance` between 1.15 and 2.5 hip widths, /3 (§3.2).
        "stance_width": Band.between(0.30, 0.40, 0.85, 1.10),
        "wedge_angle": Band.gte(2.0, 10.0, 25.0),
        "ski_wedge_angle": Band.gte(2.0, 10.0, 25.0),
        "knee_valgus": Band.lte(0.15, 0.40, 0.75),
    },
    "pizza": {
        "stance_width": Band.between(0.28, 0.38, 0.80, 1.05),
        # Foot-index noise can read 8-10 deg on parallel skis; real wedge turns
        # sit well above 12 deg in a quarter view.
        "wedge_angle": Band.gte(5.0, 12.0, 22.0),
        "ski_wedge_angle": Band.gte(5.0, 12.0, 22.0),
        "turn_rate": Band.gte(0.06, 0.15, 0.32),
        "turn_amplitude": Band.gte(5.0, 10.0, 26.0),
        "turn_shape_index": Band.gte(0.20, 0.32, 0.55),
        # A beginner steers with the hips; a big torso lead is the fault here.
        "separation_angle": Band.lte(6.0, 16.0, 34.0, reading="magnitude"),
        "asymmetry_index": Band.lte(0.35, 1.00, 2.20, reading="magnitude"),
    },
    "sideslip": {
        # v2 `cp_ss_edge` between 5 and 25 degrees.
        "edge_angle_proxy": Band.between(2.0, 5.0, 25.0, 40.0),
        # v2 `cp_ss_quiet` at most 6 degrees of separation sway.
        "upper_body_quiet": Band.lte(2.5, 6.0, 12.0),
        # A sideslip is a quiet body: vertical travel is a fault, not a virtue.
        "com_vertical_travel": Band.lte(0.03, 0.08, 0.18),
        "flexion_range": Band.gte(4.0, 10.0, 25.0),
    },
    "wedge_christie": {
        # The wedge must fall through the turn, so the median sits low but
        # nonzero, and the *variation* is the real gate.
        "wedge_angle": Band.between(1.0, 3.0, 16.0, 30.0),
        "ski_wedge_angle": Band.between(1.0, 3.0, 16.0, 30.0),
        "stance_width_var": Band.gte(0.02, 0.06, 0.14),
        "knee_valgus": Band.lte(0.12, 0.35, 0.68),
    },
    "parallel": {
        "stance_width": Band.between(0.14, 0.22, 0.37, 0.55),
        "turn_shape_index": Band.gte(0.25, 0.38, 0.60),
        "banking_index": Band.lte(0.40, 0.70, 0.95),
    },
    "dynamic_parallel": {
        "flexion_range": Band.gte(8.0, 18.0, 35.0),
        "com_vertical_travel": Band.gte(0.03, 0.07, 0.18),
        # v2 `cp_dp_pressure` between 0.35 and 0.7 of the arc.
        "pressure_peak_phase": Band.between(0.15, 0.35, 0.70, 0.88),
        # v2 `cp_dp_pole` at least 0.8 touches per turn.
        "pole_touch_rate": Band.gte(0.35, 0.80, 0.95),
        # v2 `cp_dp_rhythm` CV at most 0.2.
        "turn_duration_var": Band.lte(0.08, 0.20, 0.45),
    },
    "firm_snow": {
        "edge_angle_proxy": Band.gte(6.0, 12.0, 26.0),
        # v2 `cp_fs_edgechange` at most 0.35 s between edges.
        "edge_change_duration": Band.lte(0.14, 0.35, 0.70),
        "turn_shape_index": Band.gte(0.30, 0.42, 0.65),
    },
    "skid_short": {
        "turn_rate": Band.gte(0.35, 0.55, 0.85),
        "separation_angle": Band.gte(6.0, 14.0, 30.0, reading="magnitude"),
        "flexion_range": Band.gte(8.0, 15.0, 30.0),
        "pole_touch_rate": Band.gte(0.20, 0.50, 0.85),
    },
    "carve_long": {
        "edge_angle_proxy": Band.gte(8.0, 15.0, 30.0),
        "turn_shape_index": Band.gte(0.35, 0.48, 0.70),
        "asymmetry_index": Band.lte(0.30, 0.80, 1.80, reading="magnitude"),
    },
    "carve_medium": {
        "edge_angle_proxy": Band.gte(10.0, 18.0, 34.0),
        "banking_index": Band.lte(0.32, 0.55, 0.82),
        "angulation": Band.gte(4.0, 10.0, 22.0),
        "turn_shape_index": Band.gte(0.35, 0.48, 0.70),
        "turn_rate": Band.between(0.25, 0.33, 0.55, 0.75),
        "asymmetry_index": Band.lte(0.30, 0.80, 1.80, reading="magnitude"),
    },
    "carve_short": {
        "edge_angle_proxy": Band.gte(12.0, 22.0, 38.0),
        "banking_index": Band.lte(0.30, 0.52, 0.80),
        "angulation": Band.gte(5.0, 12.0, 24.0),
        "turn_shape_index": Band.gte(0.35, 0.48, 0.70),
        "turn_rate": Band.gte(0.45, 0.60, 0.90),
        "edge_change_duration": Band.lte(0.10, 0.25, 0.55),
        "separation_angle": Band.gte(6.0, 14.0, 30.0, reading="magnitude"),
        "asymmetry_index": Band.lte(0.30, 0.80, 1.80, reading="magnitude"),
    },
    "steeps": {
        "turn_rate": Band.gte(0.35, 0.50, 0.80),
        "edge_change_duration": Band.lte(0.12, 0.30, 0.60),
        # v2 `cp_st_separation` at least 25 degrees of separation.
        "separation_angle": Band.gte(10.0, 25.0, 38.0, reading="magnitude"),
        # v2 `cp_st_braking` at most 3 braking turns.
        "braking_count": Band.count(0.15, 3),
    },
    "mogul_absorb": {
        # v2 `cp_mg_amp` at least 30 degrees of knee travel.
        "flexion_range": Band.gte(15.0, 30.0, 55.0),
        # v2 `cp_mg_freq` 0.7 Hz on the inflated scale, ~0.35 Hz true (§3.3).
        "flexion_rate": Band.gte(0.20, 0.40, 0.90),
        "com_vertical_travel": Band.gte(0.04, 0.10, 0.22),
        # v2 `cp_mg_quiet`: bumps allow more sway than a groomed run.
        "upper_body_quiet": Band.lte(3.0, 8.0, 16.0),
    },
    "mogul_fallline": {
        "flexion_range": Band.gte(15.0, 30.0, 55.0),
        "flexion_rate": Band.gte(0.25, 0.50, 1.00),
        "com_vertical_travel": Band.gte(0.04, 0.10, 0.22),
        "upper_body_quiet": Band.lte(3.0, 8.0, 16.0),
        "turn_rate": Band.gte(0.45, 0.70, 1.10),
        "pressure_peak_phase": Band.between(0.10, 0.25, 0.65, 0.85),
    },
    "powder": {
        # §4: a narrower band than the piste stages.
        "stance_width": Band.between(0.08, 0.13, 0.34, 0.50),
        # v2 `cp_pw_travel` at least 0.1 leg lengths of travel.
        "com_vertical_travel": Band.gte(0.04, 0.10, 0.20),
        "flexion_rate": Band.between(0.15, 0.25, 0.70, 1.00),
        # v2 `cp_pw_shape` between 0.4 and 0.75.
        "turn_shape_index": Band.between(0.30, 0.40, 0.75, 0.92),
        "asymmetry_index": Band.lte(0.30, 0.90, 2.00, reading="magnitude"),
    },
}

#: Age-band widenings, §2.3. The only entry the design sanctions.
AGE_WIDENINGS: dict[str, dict[str, float]] = {
    AGE_3_6: {"stance_width": 0.18},
    AGE_7_12: {"stance_width": 0.12},
}

#: Human-facing note for each widening, as an English display key.
AGE_WIDENING_NOTE = (
    "A wide stance is mechanically correct at this age; "
    "stance width is not penalized."
)

#: Metrics whose failure carries the design's ``injury-risk`` flag (§6).
INJURY_RISK_METRICS = frozenset(
    {"hip_over_foot", "backseat_count", "banking_index"}
)

#: The subset swept at *every* stage, whether or not the stage lists it.
#:
#: Being in the back seat is a knee-injury mechanism on a green run as much as on
#: a black one, so those two are checked unconditionally. ``banking_index`` is
#: deliberately not here: banking only loads the knee once there is real edge
#: angle to bank on, and on a wedge rung the index divides one noise-level angle
#: by another. It therefore blocks advancement only where a stage names it.
INJURY_RISK_SWEEP = frozenset({"hip_over_foot", "backseat_count"})


def band_for(level_id: str, metric_id: str, age_band: str | None = None) -> Band | None:
    """Band for one metric at one stage, with the age override applied.

    Returns ``None`` for a metric with no band, which the scorer reports as a
    measured value with ``rubric = not_rated`` — a number with no standard, not
    a failure.
    """
    base = OVERRIDES.get(level_id, {}).get(metric_id) or DEFAULTS.get(metric_id)
    if base is None:
        return None
    delta = AGE_WIDENINGS.get(age_band or "", {}).get(metric_id)
    if not delta:
        return base
    # The §2.3 policy (an override may widen, never tighten) is structural in
    # :meth:`Band.widened_high` and guarded by ``tests/test_curriculum_v3.py``;
    # asserting it here could not fail and vanished under ``python -O`` anyway.
    return base.widened_high(delta)


@dataclass(frozen=True)
class Evaluation:
    """A band applied to one measured value."""

    membership: float | None
    rubric: str
    score: float | None
    standard: str
    faulty_turns: int | None = None
    total_turns: int | None = None
    allowance: int | None = None

    @property
    def passing(self) -> bool:
        return self.rubric in ("pass", "strong")


NOT_RATED = Evaluation(None, "not_rated", None, "")


def evaluate(band: Band | None, item: object) -> Evaluation:
    """Apply a band to a ``MetricValue``-shaped object.

    Duck-typed on ``state`` / ``value`` / ``faulty_turns`` / ``total_turns`` so
    this module stays free of imports from the measurement layer. A metric that
    is ``unknown`` or ``not_applicable`` evaluates to :data:`NOT_RATED`: it
    never becomes a zero (schema rule, design §6.5).
    """
    if band is None or item is None:
        return NOT_RATED
    if str(getattr(item, "state", "")) != "ok":
        return NOT_RATED
    value = getattr(item, "value", None)
    faulty = getattr(item, "faulty_turns", None)
    total = getattr(item, "total_turns", None)
    if band.kind == "count":
        # The measurement layer puts the faulty count in `value` as well; the
        # explicit pair is authoritative when present.
        if faulty is None and value is not None:
            faulty = int(round(float(value)))
        if not total:
            return NOT_RATED
        return Evaluation(
            membership=band.membership(value, faulty=faulty, total=total),
            rubric=band.rubric(value, faulty=faulty, total=total),
            score=band.score(value, faulty=faulty, total=total),
            standard=band.standard(total=total),
            faulty_turns=faulty,
            total_turns=total,
            allowance=band.allowance(total),
        )
    if value is None:
        return NOT_RATED
    return Evaluation(
        membership=band.membership(value),
        rubric=band.rubric(value),
        score=band.score(value),
        standard=band.standard(),
        faulty_turns=faulty,
        total_turns=total,
    )


def age_effects(age_band: str | None) -> list[str]:
    """English notes describing every widening applied for this age band."""
    if not age_band or age_band not in AGE_WIDENINGS:
        return []
    return [AGE_WIDENING_NOTE]
