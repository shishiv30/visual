# Ski Report v3 — Stage Model, Classification, Metrics and Report Layout

Status: design, for review before implementation
Date: 2026-08-30
Supersedes: the stage model implied by `content/ski/curriculum.v2.json` (schema 2.1.0)

## 0. Why v3

v2 works but has four structural limits, all visible in the code rather than in the output:

1. **The stage ladder is the app's own invention**, ten levels deep, and does not line up with any
   teaching system. There is no sideslip rung, no rhythm/pole rung, no firm-snow rung, and no
   steeps rung — so a skier who fails on ice or in the fall line has nowhere to land.
2. **Classification is a hand-written if-ladder** over 14 whole-clip signals
   (`core/sports/assess.py:42-91`). It has no notion of a turn, so it cannot express the one thing
   every teaching system gates on: *how many of these turns were clean*.
3. **The athlete profile is collected and then ignored.** `AthleteProfile`
   (`clients/windows/store/athletes.py:24`) carries birthday, gender, height_cm, weight_kg,
   ski_cm; it is snapshotted onto `ClipMeta` and never reaches `assess_clip`. Every threshold is
   therefore implicitly calibrated to adult proportions, and a child is measured against them.
4. **The report ends where coaching should begin.** Five chapters, all diagnosis, no curriculum:
   no tutorial for the stage, no drills with a dose, no terrain guidance, no equipment guidance.

v3 rebuilds the stage model on the 16-stage bilingual curriculum now living in the wiki
(`wiki/interests/skiing/curriculum/`, 81 measurable gates), adds turn segmentation so gates can be
expressed as *N of M turns*, makes the profile a first-class input, and extends the report to carry
the curriculum content for the skier's own stage.

---

## 1. Stage model

### 1.1 Two ladders, one bridge

The wiki curriculum has 16 stages (`st-01`…`st-16`). The app has 14 level ids, 10 in scope. v3
keeps the existing app ids — stored reports, three ported client decoders and the test suite all
key off them — and adds a `kb_stage` bridge field plus six new levels.

Every level gains an **observability tier**, which is the honest statement of what a camera can
and cannot judge:

| Tier | Meaning | Consequence in the report |
|---|---|---|
| `full` | Classifiable and scorable from the clip alone | Auto-detected, scored, gated |
| `scene` | Needs one scene fact the clip cannot supply (snow surface, slope band) | Auto-detected only when the user or the pipeline supplies it; otherwise offered as "possible stage" |
| `catalog` | Real rung of the progression, not observable in a clip | Appears in the skill tree and the knowledge chapters; never auto-detected, never scored |

### 1.2 The v3 ladder

| App level id | Name | `kb_stage` | Tier | Category | Terrain | Next |
|---|---|---|---|---|---|---|
| `first_slide` | First slide and equipment | `st-01` | catalog | alpine_piste | green | pizza_glide |
| `pizza_glide` | Wedge glide | `st-02` | full | alpine_piste | green | pizza |
| `pizza` | Wedge turns | `st-03` | full | alpine_piste | green | sideslip |
| `sideslip` | Sideslip and edge release | `st-04` | full | alpine_piste | green | wedge_christie |
| `wedge_christie` | Wedge christie | `st-05` | full | alpine_piste | green | parallel |
| `parallel` | Parallel skiing | `st-06` | full | alpine_piste | blue | dynamic_parallel |
| `dynamic_parallel` | Dynamic parallel: rhythm and poles | `st-07` | full | alpine_piste | blue | skid_short, carve_long, firm_snow |
| `firm_snow` | Firm snow and ice | `st-08` | scene | alpine_piste | blue | skid_short, carve_long |
| `skid_short` | Short skidded turns | `st-09` | full | alpine_piste | blue | mogul_absorb, steeps |
| `carve_long` | Long-radius carve | `st-10` | full | alpine_piste | blue | carve_medium |
| `carve_medium` | Medium-radius carve | `st-10` | full | alpine_piste | red | carve_short |
| `carve_short` | Short-radius carve | `st-11` | full | alpine_piste | red | — |
| `steeps` | Steeps | `st-12` | scene | alpine_piste | black | powder |
| `mogul_absorb` | Mogul absorption | `st-13` | full | alpine_moguls | mogul | mogul_fallline |
| `mogul_fallline` | Mogul fall-line | `st-13` | full | alpine_moguls | black | powder |
| `powder` | Powder and soft snow | `st-14` | scene | alpine_offpiste | offpiste | trees |
| `trees` | Crud, trees and complex terrain | `st-15` | catalog | alpine_offpiste | offpiste | specialization |
| `specialization` | Specialization and self-coaching | `st-16` | catalog | alpine_piste | any | — |

Retained catalog-only levels: `ollie`, `park`, `gates`, `switch` (unchanged, `in_scope: false`).
New category `alpine_offpiste`, new terrain `offpiste`, new venue `venue_offpiste`.

Six new assessable-or-scene rungs — `sideslip`, `dynamic_parallel`, `firm_snow`, `steeps`,
`powder` — plus two catalog bookends (`first_slide`, `specialization`) and `trees`.

### 1.3 Per-stage structure definition

Each level in `content/ski/curriculum.v3.json` gains the fields marked **new**:

```
level:
  id, category_id, terrain, venue_ids[]          # as v2
  name, desc                                     # Localized, as v2
  in_scope                                       # as v2
  heuristic_not_fis_carve                        # as v2
  checkpoints[]                                  # as v2, now metric-backed (§4)
  next_levels[]                                  # as v2
  session_drills[]                               # as v2
  kb_stage            NEW  "st-06"               # bridge to the wiki curriculum
  tier                NEW  full | scene | catalog
  requires_scene      NEW  ["snow_surface"] | ["slope_band"] | []
  core_metrics[]      NEW  ordered metric ids, most diagnostic first (§4)
  gate_metrics[]      NEW  subset that must pass to advance
  prerequisites       NEW  {levels[], checkpoints[]}
  profile_notes[]     NEW  adaptation overlay ids that apply (age-7-12, phys-female-adult, …)
  kb_refs             NEW  {tutorial, drills[], faults[], venue, equipment}
```

`tier`, `core_metrics` and `kb_refs` are what the new report chapters read. `prerequisites` makes
the skill tree honest: a rung is *reachable* only when its prerequisite checkpoints have been
passed at least once in this athlete's history.

---

## 2. Inputs: skeleton, scene, profile

### 2.1 Skeleton (unchanged source, wider use)

BlazePose-33 in image pixels, 2D, per-landmark visibility. v3 starts using landmarks the current
code ignores: elbows 13/14, heels 29/30, foot_index 31/32 beyond a presence counter, and per-side
values instead of pooling both legs into one list (`core/sports/signals.py:134-148`).

### 2.2 Scene (new)

`SceneContext`, supplied by the user at Prepare time and/or weakly inferred:

| Field | Source | Used for |
|---|---|---|
| `snow_surface` | user pick: corduroy / packed / hardpack / ice / soft / powder / crud / slush | gates `firm_snow`, `powder`; threshold band selection |
| `slope_band` | user pick: green / blue / black / double-black, or inferred from the hip trajectory's descent rate | gates `steeps`; terrain plausibility |
| `view` | inferred: azimuth estimate + framing quality (§3.1) | gating lateral metrics, confidence |
| `camera_motion` | inferred: static / panning / follow | invalidates `turn_freq`, `fall_line` when follow |
| `fps_effective` | computed: source fps ÷ frame stride | **fixes the 2× frequency bug** (`signals.py:266`) |

Scene is optional. A missing `snow_surface` does not block the report; it moves `firm_snow` and
`powder` out of the candidate set and says so.

### 2.3 Profile (new — collected today, unused today)

`AthleteProfile` → `assess_clip`. Derived quantities:

```
age_years        = (clip_date - birthday) / 365.25
age_band         = age-3-6 | age-7-12 | age-13-17 | age-18-39 | age-40-59 | age-60plus
height_m, mass_kg
leg_len_m        ≈ 0.53 * height_m          # anthropometric estimate, used only as a prior
px_per_m         = observed_body_span_px / expected_body_span_m
bmi              = mass_kg / height_m²      # equipment guidance only, never a score input
ski_len_ratio    = ski_cm / (height_m*100)  # equipment chapter
```

Profile affects exactly three things, and nothing else:

1. **Normalization** — see §3.2. This is the main win: metrics become size-invariant.
2. **Threshold band selection** — a threshold may carry per-age-band overrides, mirroring the
   curriculum's adaptation overlays. Example: a wide stance is *mechanically correct* for
   `age-3-6`/`age-7-12` (high centre of mass relative to leg length), so `stance_width` is not
   penalized there; carving gates are marked not-applicable below `age-13-17` because bending a
   ski requires mass.
3. **Equipment guidance** — ski length band, boot flex band, and the "check the rental skis have
   edges" note for children, in the equipment chapter.

**Policy, taken verbatim from the curriculum's adaptation policy:** a profile may change the
normalization, the applicable threshold band, or the guidance. It may never silently lower a pass
standard. Where a gate is not applicable to a band, the report says *not applicable at this age*
rather than awarding a pass. Sex is used only for equipment fit guidance and for the injury-risk
note; it never changes a score.

---

## 3. Measurement layer

### 3.1 View and quality gating (new)

Every lateral metric in v2 divides by `hip_w = |x_lhip − x_rhip|`, which collapses toward zero in a
profile view and makes `stance_width`, `inward_lean`, `knee_valgus` explode
(`core/sports/signals.py:113`). v3 estimates the view first:

```
shoulder_w_px, hip_w_px, torso_len_px, leg_len_px      # medians over usable frames
aspect          = hip_w_px / leg_len_px
azimuth_deg     ≈ asin(clamp(aspect / aspect_frontal, 0, 1))    # 0° = pure profile, 90° = face-on
view_class      = profile | quarter | frontal
```

`aspect_frontal` is the athlete's expected frontal ratio from the profile prior, so the estimate is
scale-free. Lateral metrics are computed only when `azimuth_deg ≥ 25°`; below that they are
returned as `None` with reason `view_too_profile`, which the report shows as a filming note instead
of a bad score. This replaces the current situation where a profile clip silently produces
nonsense.

### 3.2 Normalization (rewritten)

| Quantity | v2 denominator | v3 denominator | Why |
|---|---|---|---|
| stance width | hip width | **leg length** | Stance scales with leg length, not pelvis width; hip width also collapses with view angle |
| lateral CoM offset | hip width | **leg length** | same |
| knee valgus | hip width | **knee-to-ankle length** | local to the segment being measured |
| fore/aft | torso length | **shin length + explicit shin angle** | torso length is the wrong ruler and divides by 1e-3 when shoulders are missing (`signals.py:168`) |
| vertical travel | — | **leg length** | new metric |
| all angles | — | degrees | already scale-free |

Where `px_per_m` is available and the view is `quarter` or `frontal`, distances are additionally
reported in centimetres for the report's benefit. Scores always use the ratio form.

### 3.3 Turn segmentation (new — the enabling change)

Gates in the curriculum are phrased as *"20 consecutive turns, at most 2 faulty"*. v2 cannot count
turns. v3 segments them:

```
1. build the steering signal  θ(t) = signed angle of (hip_mid → ankle_mid) relative to
   the smoothed path tangent, low-pass filtered at 2 Hz
2. turn boundaries = zero crossings of θ with hysteresis, minimum turn duration 0.35 s
3. reject boundary pairs whose amplitude is below 8°  (traverse, not a turn)
4. label each turn L/R, and split it into phases by |θ|:
      transition  = ±15% of the boundary window
      initiation  = boundary → 1/3 of the arc
      shaping     = middle third            (pressure peak expected here)
      finish      = last third
5. emit Turn[] with t_start, t_end, side, amplitude_deg, duration_s, phase boundaries
```

Everything in §4 then exists in three forms: whole-clip robust statistic, per-turn series, and
**count-of-faulty-turns**, which is what the gates actually compare. `fps_effective` is used
throughout, fixing the 2× error.

Cross-check: `core/sports/dtw.py` already implements banded DTW and is currently dead code
(`tests/test_ski_stage.py:288` only). With turns segmented, DTW becomes usable for turn-shape
comparison against a stage template; that is deliberately **out of scope for v3** and noted as a
follow-up.

### 3.4 Metric catalog (new)

Metrics are the v3 replacement for v2's 14 signals. Existing ids are kept where the definition is
unchanged; the rest are new. `A` = whole-clip aggregate, `T` = per-turn, `C` = count of faulty
turns.

**Stance and balance**

| id | Definition | Unit | Forms | Replaces |
|---|---|---|---|---|
| `stance_width` | ankle separation ÷ leg length, median | ratio | A,T | v2 same name, new denominator |
| `stance_width_var` | IQR of the above | ratio | A | `stance_width_std` |
| `wedge_angle` | angle between the two foot vectors (ankle→foot_index) | deg | A,T | new |
| `shin_angle_fore_aft` | shank vector vs image vertical, signed | deg | A,T | replaces `backseat` |
| `hip_over_foot` | horizontal hip-to-ankle offset ÷ leg length, at the transition | ratio | A,T,C | new — this is the real fore/aft gate |
| `com_vertical_travel` | hip_y range within a turn ÷ leg length | ratio | A,T | new |

**Edging and steering**

| id | Definition | Unit | Forms | Replaces |
|---|---|---|---|---|
| `edge_angle_proxy` | shank vector vs slope normal, view-corrected | deg | A,T | new |
| `inclination` | shoulder-mid to ankle-mid line vs vertical | deg | A,T | part of v2 `inward_lean` |
| `angulation` | inclination minus hip-to-shoulder line angle | deg | A,T | the other half of `inward_lean` |
| `banking_index` | inclination ÷ (inclination + angulation) | ratio | A,T | new — separates banking from angulation |
| `separation_angle` | signed shoulder-line minus pelvis-line yaw | deg | A,T | signed version of `upper_quiet` |
| `upper_body_quiet` | std of separation_angle | deg | A | v2 `upper_quiet`, now in degrees |
| `knee_valgus` | knee-to-ankle horizontal offset ÷ shank length | ratio | A,T | v2 same, new denominator |

**Rhythm and turn shape**

| id | Definition | Unit | Forms | Replaces |
|---|---|---|---|---|
| `turn_rate` | turns per second from segmentation | Hz | A | v2 `turn_freq`, correct fps |
| `turn_duration_var` | CV of turn duration | ratio | A | new — rhythm consistency |
| `turn_amplitude` | mean steering amplitude per turn | deg | A,T | new |
| `turn_shape_index` | shaping-phase duration ÷ total turn duration | ratio | A,T | new — C-shape vs Z-shape |
| `edge_change_duration` | transition window length | s | A,T | new |
| `flexion_range` | knee flexion p90−p10 | deg | A,T | v2 `knee_flex_amp` |
| `flexion_rate` | knee flexion cycles per second | Hz | A | v2 `knee_flex_freq`, correct fps |
| `pressure_peak_phase` | where in the turn flexion is deepest, 0=initiation 1=finish | ratio | A,T | new — detects park-and-ride |

**Faults counted per turn**

| id | Definition | Forms |
|---|---|---|
| `stem_count` | turns whose transition window shows `wedge_angle` above the band | C |
| `backseat_count` | turns whose finish shows `hip_over_foot` behind the band | C |
| `rotation_count` | turns where `separation_angle` leads the skis into the turn | C |
| `braking_count` | turns whose `turn_shape_index` collapses at the finish | C |
| `asymmetry_index` | mean signed L−R difference across paired metrics ÷ pooled sd | A |

**Pole and hands**

| id | Definition | Unit | Forms |
|---|---|---|---|
| `hands_in_view` | fraction of frames with both wrists forward of the hip line | ratio | A |
| `pole_touch_rate` | detected wrist-velocity spikes near transitions ÷ turns | ratio | A |
| `pole_touch_timing` | mean offset of the spike from the transition | s | A,T |

**Quality and scene**

`view_azimuth_deg`, `view_class`, `landmark_quality`, `usable_frame_ratio`, `camera_motion`,
`fps_effective`, `turn_count`. These are never scored; they gate everything else and drive the
filming chapter.

Roughly 34 metrics against v2's 14, and every one of them is a quantity the curriculum's gates
actually name.

---

## 4. Per-stage core metrics and gates

Derived from the wiki curriculum's `assessment.criteria[]`, keeping only what a camera can judge.
`gate` marks the metrics that must pass to advance; the rest are diagnostic.

| Level | `kb_stage` | Core metrics (ordered) | Gates |
|---|---|---|---|
| `pizza_glide` | st-02 | stance_width, wedge_angle, shin_angle_fore_aft, knee_valgus, hip_over_foot | stance_width, wedge_angle, hip_over_foot |
| `pizza` | st-03 | turn_rate, turn_amplitude, stance_width, separation_angle, turn_shape_index, asymmetry_index | turn_rate, turn_shape_index, asymmetry_index |
| `sideslip` | st-04 | edge_angle_proxy, upper_body_quiet, com_vertical_travel, flexion_range, hip_over_foot | edge_angle_proxy, upper_body_quiet |
| `wedge_christie` | st-05 | wedge_angle (must fall through the turn), stance_width_var, knee_valgus, separation_angle | wedge_angle, stance_width_var |
| `parallel` | st-06 | **stem_count**, stance_width, turn_shape_index, hip_over_foot, banking_index, hands_in_view, backseat_count | stem_count, turn_shape_index, hip_over_foot |
| `dynamic_parallel` | st-07 | flexion_range, com_vertical_travel, pressure_peak_phase, pole_touch_rate, pole_touch_timing, turn_duration_var | pressure_peak_phase, pole_touch_rate, turn_duration_var |
| `firm_snow` | st-08 | edge_angle_proxy, edge_change_duration, turn_shape_index, braking_count, upper_body_quiet | edge_change_duration, braking_count *(requires `snow_surface ∈ {hardpack, ice}`)* |
| `skid_short` | st-09 | turn_rate, turn_duration_var, separation_angle, flexion_range, pole_touch_rate, upper_body_quiet | turn_rate, turn_duration_var, separation_angle |
| `carve_long` | st-10 | edge_angle_proxy, banking_index, angulation, turn_shape_index, stance_width, asymmetry_index | edge_angle_proxy, banking_index, turn_shape_index |
| `carve_medium` | st-10 | as carve_long + turn_rate | + turn_rate |
| `carve_short` | st-11 | as carve_medium + edge_change_duration, separation_angle | + edge_change_duration |
| `steeps` | st-12 | turn_rate, edge_change_duration, separation_angle, com_vertical_travel, braking_count | separation_angle, braking_count *(requires `slope_band ∈ {black, double-black}`)* |
| `mogul_absorb` | st-13 | flexion_range, flexion_rate, com_vertical_travel, upper_body_quiet, hands_in_view | flexion_range, com_vertical_travel, upper_body_quiet |
| `mogul_fallline` | st-13 | as mogul_absorb + turn_rate, pressure_peak_phase | + turn_rate |
| `powder` | st-14 | stance_width (narrower band), com_vertical_travel, flexion_rate, turn_shape_index, asymmetry_index | com_vertical_travel, turn_shape_index *(requires `snow_surface ∈ {soft, powder}`)* |

`first_slide`, `trees`, `specialization` and the four park/race/switch levels carry no metrics by
design; their chapter content comes from the knowledge base only.

---

## 5. Classification algorithm

v2: one if-ladder, first match wins, whole-clip signals only. v3: scored candidates.

```
1. GATE      usable_frame_ratio, landmark_quality, turn_count, view_class
             → below gate: return an "unusable clip" report with a filming chapter
2. CANDIDATES from tier: all `full` levels, plus `scene` levels whose requires_scene is satisfied
3. FEATURE    compute the metric catalog (§3.4) with profile normalization (§3.2)
4. SCORE      for each candidate level L:
                 fit(L)  = mean over L.core_metrics of membership(metric, L.band[metric])
                 gate(L) = fraction of L.gates passed
                 prior(L)= profile and history prior:
                           - age band applicability (carving levels ≥ age-13-17)
                           - previously passed levels raise adjacent levels
                           - scene consistency (slope_band vs L.terrain)
                 s(L)    = 0.55*fit + 0.30*gate + 0.15*prior
5. SELECT     L* = argmax s(L)
              confidence = s(L*) * quality_factor * separation_factor
                 separation_factor = clamp((s(L*) - s(L2)) / 0.15, 0.4, 1.0)
6. GUARD      if confidence < 0.35 → report the top 2 candidates as "possible stage" with the
              discriminating metric named, rather than asserting one
```

`membership()` is a trapezoid over the metric's band for that level, so a metric sitting between
two stages contributes partially to both instead of hard-switching. This is what makes the new
"Why this stage" chapter possible: the report can show the two closest levels and the metric that
separated them.

Backward compatibility: the v2 ladder is kept as `classify_legacy` and run alongside in tests, so a
disagreement on the existing fixtures is visible rather than silent.

---

## 6. Scoring algorithm

Per metric:

```
band            = level.band[metric], possibly overridden by age band
raw             = metric value (ratio / deg / Hz / count)
score_0_100     = piecewise(raw, band)              # v2 `_continuous_score` shape, kept
reliability     = f(landmark_quality, view_azimuth, sample_count, metric noise class)
rubric          = not_yet | pass | strong            # from the band's three thresholds
```

Changes from v2:

1. **Count gates.** For `C`-form metrics the score is `100 * (1 − faulty/total)` clipped by the
   allowance, and the report states it the way the curriculum does: *"stems in 3 of 22 transitions —
   the allowance is 2"*.
2. **Reliability weighting.** Stage score is a reliability-weighted mean of gate metrics rather
   than a flat mean, so a metric measured on a marginal view cannot sink the stage. Reliability is
   reported next to each metric.
3. **Asymmetry is scored separately**, not averaged away. Both legs are computed independently and
   the weaker side is named.
4. **Rubric alongside score.** Each metric carries `not_yet/pass/strong`, mirroring the
   curriculum's three-level rubric, so the report can say what "good enough" means.
5. **Not-applicable is a distinct state**, separate from zero and from unknown: `n/a (age band)`,
   `unknown (view too profile)`, `0 (measured, failing)`.

Advance rule, unchanged in spirit and now explicit: `ready_for_next_stage` requires confidence
≥ 0.35, stage score ≥ `pass_score`, **every gate metric at `pass` or better**, and no
`injury-risk` fault flagged (back-seat and banking are the two that carry that flag).

---

## 7. Report layout

Twelve chapters, replacing five. Chapters 1-6 are diagnosis, 7-11 are the knowledge base, 12 is
housekeeping. This ordering is the user requirement: measurement first, curriculum last.

| # | Chapter | Source | Notes |
|---|---|---|---|
| 1 | Summary | report | Stage, score ring, confidence, four posture rings, terrain badge — stage name also anchored by a "Level & next step" header card, first in the scrollable report ahead of this chapter (added on top of v3, readability follow-up) |
| 2 | Why this stage | classifier | Top-2 candidates, the separating metric, view/scene/quality badges |
| 3 | Core metrics | metrics | Per-stage ordered metrics: value, unit, score ring, rubric, reliability, evidence link |
| 4 | Turn-by-turn | segmentation | Turn count, L/R symmetry, per-turn strip chart, faulty-turn callouts |
| 5 | Checkpoints | curriculum | Gate list with the *N of M* phrasing and the pass standard |
| 6 | Skill tree | curriculum | Completed / current / next, with locked reasons (§8); the top-priority next level (`next_level_names[0]`) is marked "Recommended next" and its plan card sorts first, but every next level and plan card stays visible |
| 7 | Stage tutorial | knowledge base | Goal, why it matters, key skills with cues and misconceptions |
| 8 | Drills | knowledge base | Name, purpose, steps, dose, success indicator; the ones targeting the weakest metric first |
| 9 | Faults and fixes | knowledge base | Matched to the skier's own failing metrics, not the generic list |
| 10 | Terrain and venue | knowledge base | What terrain this stage needs, what to avoid, snow/timing guidance |
| 11 | Equipment | knowledge base + profile | Ski length band from height/weight, boot flex band, tune spec where relevant |
| 12 | Filming and disclaimer | report | Filming faults found in this clip, then the mandatory disclaimer |

Chapters 7-11 are **data, not prose written by the app**: they are rendered from a knowledge pack
imported from the wiki curriculum (§9), already bilingual, already coach-reviewed.

Layout consequences for the desktop client:

- `report_panel.py` currently hard-codes `_ch1.._ch5` with five `_fill_*` methods, and
  `tests/test_report_panel.py:130` asserts exactly five. v3 makes the chapter list data-driven:
  a `CHAPTERS` tuple of `(id, title_key, fill_fn)` iterated to build the panel, so adding a
  chapter is one tuple entry.
- The panel already owns a `QScrollArea` (`report_panel.py:98`), so length is not a new problem;
  chapters 7-11 are collapsed by default (`ReportChapter` gains a `collapsible` flag) so the
  diagnosis stays above the fold.
- Existing style rules are unchanged and binding: 32px gray chapter titles with no numeric prefix,
  `#1A2433` cards with 12px radius, 36/24/16 spacing, one paragraph per label, full-width panels,
  `t("English key")` for every string, pointer cursor via the event filter, dark palette only.

---

## 8. Skill tree

v2's `_tree_path` (`assess.py:439`) walks parents, then follows `next_levels[0]` forward — a single
line, no branches, and each node carries only `{id, name, current}`. v3:

```
TreeNode:
  id, name, kb_stage, tier
  state: completed | current | available | locked | not_applicable
  score_best        best stage score ever recorded for this athlete on this level
  gates_passed      "3/5"
  locked_reason     e.g. "needs sideslip gate ac-04-01", "carving needs age 13+"
  branch            piste | moguls | offpiste | park | race
```

- `completed` — passed on some earlier clip (from the athlete's report history in the store).
- `current` — the classifier's pick for this clip.
- `available` — prerequisites satisfied, not yet passed.
- `locked` — prerequisites unmet, with the reason named.
- `not_applicable` — excluded by age band, with the reason named.

The tree renders the **whole** progression, branches included, not just the spine: the piste line
plus the mogul and off-piste branches, with catalog rungs shown greyed. This is the user
requirement that the skill tree cover completed, current and future stages.

History source: `clients/windows/store/library.py` gains `list_reports_for_athlete(athlete_key)`;
the store already snapshots `athlete_key` onto `ClipMeta` (`library.py:51-52`).

**Readability follow-up (post-v3):** `next_level_names` used to render as a single joined
`"Next stage: A · B"` label with no way to tell which stage to prioritize. It now renders as
individual chips, with `next_level_names[0]` styled distinctly ("Recommended next", accent color)
and its matching `next_plans` entry sorted to the top — this is presentation-only, no `TreeNode`
schema change. See `docs/app-spec.md` §4/§5 for the current, canonical description.

The tree itself was, per §8, rendering the **whole** progression including every branch, which on
a curriculum with several side branches made the current stage hard to find. Side branches
(`branch != "piste"`) are now collapsible, defaulting to collapsed except the one branch that
contains the `current` node — a disclosure row ("{Branch} · N stages") replaces the branch's rows
when collapsed. The piste spine is always fully shown; this only affects side branches, and is
presentation-only (no `TreeNodeV3` schema change, no change to `order_tree_rows`'s row ordering).

---

## 9. Knowledge pack import

The curriculum lives in a different repo. v3 imports a compact pack rather than vendoring the whole
dataset:

```
scripts/import_ski_knowledge.py \
    --source ../llm-wiki/wiki/interests/skiing/curriculum/build/curriculum.{lang}.json \
    --out content/ski/knowledge/kb.v1.json
```

The pack keeps, per `kb_stage`, both languages: goal, why_it_matters, core_question, 6 skills
(name, description, why, 2 cues, misconceptions), 7 drills (name, purpose, steps, dose,
success_indicator), 6 faults (name, symptom, root_causes, diagnosis_test, fix cues + drill ids),
terrain guidance, and the `aux_refs` slices of the equipment / terrain-and-venues / snow modules.
It drops what the app cannot use: assessment protocols (the app measures instead), fitness,
lessons, injury prose, and the adaptation overlays beyond the ids the app already applies.

Estimated pack size: ~180 KB per language, versus 815 KB for the full bundle. Provenance
(`source_version`, `imported_at`, `gate_ids`) is recorded in the pack so a stale pack is detectable.

**i18n**: pack strings are pre-translated content, not UI copy, so they live in the pack rather than
in `locales/strings.json`. Chapter titles, labels and units remain `t("English key")` keys and go
through the copy-coach + translator review the repo requires.

---

## 10. Compatibility and rollout

**Schema.** `StageReport` goes to `3.0.0`, additively: every v2 field is kept and still populated.
New optional blocks: `metrics[]`, `turns`, `classification`, `tree[]` (replacing `tree_path`, which
is kept as a projection), `knowledge`, `scene`, `profile_summary`. `load_stage_report`
(`library.py:144`) already force-rewrites `schema_version`; v3 extends that migration to fill new
blocks with `None` so old stored reports still open.

**The three ported implementations.** `assess` exists three times — Python, `Assess.swift`,
`Assess.kt` — with no shared fixtures, so a threshold change silently diverges between desktop and
phone. v3 adds `tests/fixtures/stage_report/*.json`: recorded `ClipAnalysis` inputs plus expected
`StageReport` outputs, consumed by the Python tests now and by the Swift/Kotlin test targets when
those are updated. This is the guard the repo currently lacks.

**Order of work, as instructed.**

1. Core: metrics, turn segmentation, classifier, scoring, schema v3, knowledge pack. Python only.
2. Desktop report template: data-driven chapters, chapters 2/3/4 and 7-11, richer skill tree.
3. Verify on macOS: `python -m pytest`, then launch and walk a clip end to end. Note that macOS
   needs `VISUAL_LIBRARY`/`VISUAL_PREFS` set because the store paths default to Windows
   `AppData` (`store/library.py:70-77`, `store/prefs.py:12-19`) — fix that as part of this work.
4. Confirm Windows: no macOS-only conditionals added, the two existing ones untouched
   (`capture_page.py:127` darwin camera block, `mediapipe_engine.py:69-73` darwin CPU delegate),
   no path or DPI assumptions changed. Run the suite on Windows before commit.
5. Only then iOS: `StageReport.swift`, `Assess.swift`, `ReportPanelView.swift` chapter list,
   `Theme.swift` tokens, new chart views, then re-run `scripts/generate_ios_xcodeproj.py`.
6. Android and Windows verification on the other machine after the commit, per the plan.

**Known bugs to fix on the way through** (all found during the survey, all currently shipping):

| Bug | Location | Effect |
|---|---|---|
| Frequencies are ~2× true Hz | `signals.py:266` uses source fps with stride-2 sampling | every rhythm threshold is on an inflated scale |
| `backseat` divides by 1e-3 | `signals.py:168` when shoulders are missing | ratio blows up ~1000× |
| Language never reloads | `prefs.py:36` writes `"language"`, `:26` reads `"Language"` | saved language silently ignored |
| Store paths are Windows-only | `library.py:70-77`, `prefs.py:12-19` | macOS run needs env vars |
| `dtw.py` is dead code | referenced only by a test | no template comparison happens |
| `stage_focus` / `training_focus` / `how_to_advance` never populated | `stage_report.py:60-61` | dead v1 fields rendered as empty |

---

## 11. Out of scope for v3

DTW turn-shape matching against stage templates; automatic snow-surface classification from pixels;
slope-angle estimation from a single uncalibrated camera beyond the coarse band; 3D pose or
`pose_world_landmarks`; multi-skier analysis; anything beyond the resort boundary (the curriculum
itself puts sidecountry out of scope and requires avalanche training, and the app must not imply
otherwise).
