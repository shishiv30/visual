# Visual Pose — App Feature Specification

**Version:** 3.0.0  
**Platforms:** Windows (PC), iOS, Android  
**Update policy:** Update this document first before changing any platform's code. All three clients must implement features from this spec — divergence from it is a bug.

---

## 1. App Overview

Visual Pose is an **offline ski coaching app**. It uses the MediaPipe Pose Landmarker model to detect body landmarks in video or images of skiers, then runs a sports-science pipeline to diagnose the skier's technique level and generate a personalized 12-chapter coaching report.

**Everything runs on-device.** No internet connection or server is required after install.

### Workflow (4 screens)

```
List  →  Capture/Import  →  Prepare  →  Player + Report
```

1. **List** — Library of all clips (pending/processing/done)
2. **Capture/Import** — Record via camera or import a video/image file
3. **Prepare** — Draw a person bounding box, trim in/out, fill athlete profile, set scene
4. **Player** — Letterboxed playback with skeleton overlay + 12-chapter report below

### Local data root

```
{app_data}/library/{clip_id}/
  clip.mp4       # normalized video (or clip.jpg for images)
  thumb.jpg      # 128×72 JPEG thumbnail
  meta.json      # ClipMeta — status, seeds, athlete, scene
  analysis.json  # ClipAnalysis — per-frame COCO-17 + BlazePose 33 keypoints
  stage_report.json  # StageReport v3.0.0 — full 12-chapter report
  frame_feedback.json  # per-frame like/unlike/skeleton votes
  report_correction.json  # manual stage correction (optional)
```

---

## 2. Shared Content Assets

All three clients bundle these files (Android: Gradle copy task; iOS: build script; Windows: read from repo):

| Asset | Path | Description |
|---|---|---|
| Curriculum | `content/ski/curriculum.v3.json` | 16 level specs; checkpoints, drills, prerequisites |
| Knowledge pack | `content/ski/knowledge/kb.v1.json` | Bilingual coaching content per stage (tutorial/faults/drills/terrain/equipment) |
| Metrics registry | `content/ski/knowledge/metrics.json` | Metric definitions and display names |
| Signals | `content/ski/knowledge/signals.json` | Signal extraction definitions |
| Body | `content/ski/knowledge/body.json` | Body landmark reference |
| Expert | `content/ski/knowledge/expert.json` | Expert rules |
| Locales | `locales/strings.json` | ~800 i18n keys, 9 languages: en, zh, es, fr, de, it, ja, ko, pt |
| Pose model | `models/pose_landmarker_full.task` | MediaPipe Pose Landmarker Full |

**Do not ship `curriculum.v2.json` as the runtime curriculum.** Keep it only for reading old stored reports.

---

## 3. Data Schemas

### 3.1 ClipMeta (`meta.json`)

```
clip_id           string    Unique clip identifier (UUID)
created_at        string    ISO 8601 timestamp
display_name      string    "MM/DD/YYYY-HH:mm"
duration_ms       int       Full video duration in ms (0 for images)
width, height     int       Frame dimensions
fps               float     Source frame rate
kind              enum      "video" | "image"
status            enum      "pending" | "processing" | "done"
seeds             list      Person bounding boxes: [{t_ms, norm_box: {x,y,w,h}}]
play_start_ms     int       Analysis/playback window start (ms), default 0
play_end_ms       int|null  Analysis/playback window end (ms), null = full duration
athlete_key       string    Key into athletes.json (athlete profile)
scene             object    SceneContext (terrain_type, slope_band, snow_surface, ...)
```

### 3.2 ClipAnalysis (`analysis.json`)

```
schema_version    "1.0.0"
clip_id           string
fps               float     Effective analysis fps
frame_count       int
frames            list      Per-frame entries:
  t_ms            int       Timestamp in ms
  coco17          list      17 COCO keypoints: [{x,y,score}] in pixel coords
  blaze33         list      33 BlazePose joints: [{x,y,z,score}] normalized [0,1]
  bbox            object    {x,y,w,h} in pixel coords
```

### 3.3 StageReport (`stage_report.json`) — schema v3.0.0

Top-level fields:

| Field | Type | Chapter |
|---|---|---|
| schema_version | "3.0.0" | — |
| clip_id | string | — |
| category_id, stage_id | string | — |
| category_name, stage_name | string | — |
| confidence | float 0–1 | Ch 1, 2 |
| ready_for_next_stage | bool | Ch 1 |
| score_0_100 | float | Ch 1 |
| posture | {stability, coordination, control, balance} each float 0–100 | Ch 1 |
| classification | Classification object | Ch 2 |
| metrics | list[MetricReport] | Ch 3 |
| turns | TurnSummary | Ch 4 |
| keypoints | list[KeypointResult] | Ch 5 |
| tree | list[TreeNodeV3] | Ch 6 |
| tree_path | list[TreeNode] (legacy 2.1.0) | Ch 6 fallback |
| knowledge_ref | {kb_stage, pack_version, level_id} | Ch 7–11 |
| knowledge_focus | {fault_ids, drill_ids, skill_ids, weakest_metric_id} | Ch 7–11 |
| score_series | list[{t_ms, score}] | Ch 1 timeline |
| next_level_ids, next_level_names | list[string] | Ch 6 |
| next_plans | list[LevelPlan] | Ch 6 |
| session_plan | list[DrillPayload] | Ch 8 |
| weakest_checkpoint_id | string | Ch 5 |
| terrain_id, terrain_name, terrain_desc | string | Ch 1, 10 |
| stage_focus, training_focus, how_to_advance | string | Ch 1 |
| filming | list[FilmingIssue] | Ch 12 |
| film_steps | list[string] | Ch 12 |
| disclaimer | string | Ch 12 |
| heuristic_not_fis_carve | bool | Ch 12 |
| scene | SceneSummary | Ch 2 |
| profile_summary | ProfileSummary | Ch 11 |
| kb_stage | string | Ch 7–11 (fallback) |

**Classification object:**
```
method, chosen_id, confidence, separation, quality_factor
ambiguous          bool   True if confidence < gate → "Possible stage" chip
unusable_reason    string Non-empty if clip could not be scored
candidates         list:
  stage_id, stage_name
  score, fit, gate_ratio, prior
  separating_metric_id, separating_metric_name
  rejected_reason
```

**MetricReport:**
```
id, name, group
state         "ok" | "unknown" | "not_applicable"
rubric        "not_yet" | "pass" | "strong" | "not_rated"
is_gate       bool
value, display, unit, standard
score         float|null  (null when state != ok)
reliability   float 0–1
left_value, right_value  float|null
faulty_turns, total_turns  int|null
evidence_ms   int|null
per_turn      list[{index, value, flag}]
```

**TurnSummary:**
```
count, left_count, right_count
mean_duration_s   float|null
duration_cv       float|null  (rhythm variation coefficient)
fault_counts      {metric_id: count}
turns             list[TurnRecord]:
  index, side ("L"|"R"), t_start_ms, t_end_ms, duration_s
  amplitude_deg   float|null
  flags           list[string]
```

**TreeNodeV3:**
```
id, name, kb_stage, tier, branch
state     "completed" | "current" | "inferred" | "available" | "locked" | "not_applicable"
score_best    float|null
gates_passed  bool|null
locked_reason, inferred_reason  string
depth         int
parents, children  list[string]  (stage ids)
```

**KeypointResult:**
```
id, name
status        "pass" | "fail" | "unknown"
score         float|null
good, bad     string  (coaching text)
evidence_ms   int|null
drills        list[DrillPayload]
faulty_turns, total_turns  int|null
allowance     float|null
```

**FilmingIssue:**
```
code      string
message   string
severity  "info" | "warn" | "blocker"
```

### 3.4 FrameFeedback (`frame_feedback.json`)

```
entries   list:
  t_ms          int
  pose_index    int
  stage_vote    string  "like" | "unlike" | null
  skeleton_ok   bool
```

### 3.5 ReportCorrection (`report_correction.json`)

```
corrected_stage_id   string
timestamp            string ISO 8601
```

---

## 4. Screen Specifications

### Screen 1: List

**Top bar:**
- Camera button (left) — navigate to Capture/camera mode
- Import button (left) — open file picker
- Language selector (right) — switch language live; re-renders all strings

**Clip card (per clip):**
- Thumbnail 128×72, rounded card background
- Display name `MM/DD/YYYY-HH:mm`
- Duration `m:ss` (video) or `--` (image)
- Status chip: Pending / Processing (with spinner) / Done
- "Possible stage" ambiguity chip when `classification.ambiguous == true`
- Buttons (right side):
  - **Report** — shown only when Done and stage_report.json exists → opens Player
  - **Reanalyze** — clears analysis + report, sets status = Pending, opens Prepare
  - **Delete** — confirmation dialog → removes clip directory

**Navigation:**
- Tap Pending card → Prepare
- Tap Processing card → info dialog ("Clip is still being analyzed")
- Tap Done card → Player

**Loading overlay:** full-screen spinner shown during import ("Importing…") and analysis ("Analyzing pose…")

---

### Screen 2: Capture

**Camera mode:**
- Live camera preview (back camera preferred, fallback to front)
- Record button → toggles recording; writes temp video file
- Max recording duration enforced to 120s (auto-stop)
- On stop → ingest recorded file, navigate to List

**Import mode:**
- Import button → file picker
- Accepted formats: `.mp4 .mov .avi .mkv .webm .m4v .jpg .jpeg .png .webp .bmp`
- **If video duration > 120s → show Trim Dialog before ingesting**
- After import (or trim confirmation) → IngestWorker runs in background thread

**Trim Dialog (shown only when video > 120s):**
- Title: "Trim video"
- Range slider: select in_ms and out_ms; max window = 120s
- Video total duration shown for reference
- Confirm → ingest with play_start_ms = in_ms, play_end_ms = out_ms
- Cancel → abort import, return to List

**IngestWorker:**
- Normalize: max long-edge 720px, 30fps, H.264, no audio (Windows uses ffmpeg; mobile reads frames directly)
- Extract thumbnail frame → thumb.jpg (128×72 JPEG)
- Write meta.json with status = PENDING, play_start_ms, play_end_ms

**Camera permission denial UI:** shown if permission refused; offers "Grant permission" retry button

---

### Screen 3: Prepare

**Person box canvas (SeedCanvasView):**
- Displays current video frame
- Touch-draw bounding box around the person to track
- Multiple seeds at different timestamps allowed
- Each saved seed shown as a green diamond on the timeline

**Timeline strip (TimelineStripView):**
- Filmstrip thumbnails
- Draggable playhead — seek to any frame
- Blue in/out trim edges — set logical analysis window (does NOT re-encode the file)
- Pinch-zoom on the strip
- Green/purple diamond markers at seeded frames

**Athlete profile form:**
- Saved profile picker — select or create a profile (auto-fills fields)
- Name (text field, required)
- Birthday (date picker) — used for age band: age-3-6 / age-7-12 / age-13-17 / adult
- Height cm (spin box 50–250)
- Gender: Unspecified / Female / Male / Other
- Weight kg (spin box 20–200)
- Ski length cm (spin box 80–220)

**Scene context form (optional):**
- Terrain type: Groomed piste / Mogul run / Terrain park / Off-piste / Not sure
- Slope band: Green / Blue / Black / Double black / Not sure
- Snow surface: Corduroy / Packed / Hardpack / Ice / Soft / Powder / Crud / Slush / Not sure

**Start analysis button:**
- Requires: ≥1 person seed box drawn + athlete name + measurements filled
- On press: saves seeds + athlete + scene to meta.json, sets status = PROCESSING, starts AnalysisWorker

---

### Screen 4: Player + Report

**Video canvas:**
- Letterbox contain-fit (no crop, black bars), aspect-ratio preserving
- Min height 160dp, max 360dp

**PoseOverlayView:**
- COCO-17 skeleton drawn on every frame (orange bones, red joints)
- Green detection bounding box
- Minimum visibility threshold 0.3 — landmarks below are not drawn

**Chrome toolbar (auto-hides 3s during playback, shows on tap):**
- Play / Pause
- Frame locator — copies JSON to clipboard: `{clip_id, video_frame, t_ms, pose_index, blaze33}`
- Speed: 0.5× / 0.75× / 1× / 1.25× / 1.5× / 2×
- Like (per-frame stage vote, persisted to frame_feedback.json)
- Unlike (per-frame negative vote)
- Bad skeleton (flags skeleton quality for that frame)
- Download — exports stamped JPEG (skeleton overlay burned in) via system save dialog
- Share — system share sheet + upload URL menu (YouTube / TikTok / X / Facebook / Weibo / Bilibili)

**Timeline strip (player mode):**
- Thumbnails with purple/green keyframe dots
- Seekable white playhead
- In/out range shown as purple bars (display only, no trim in player)

**TurnStripView:**
- Horizontal coloured bar: deep purple = left turns, light purple = right turns
- Tappable to seek to that turn's start time

**ScoreTimelineView:**
- Line chart of score_series (frame-by-frame score, 0–100)
- Tappable to seek

**Level & next step header (first card in the scrollable report, ahead of Ch 1):**
- Own card, first thing in the scroll — anchors "what level am I at" and "what's next" so it's the first thing read, ahead of the rest of the report's detail
- Stage name/icon (mirrors Ch 1's stage row) + confidence chip
- Single top-priority next step: the first entry of `next_level_names`, or `how_to_advance` text when no next level is applicable — tapping/clicking scrolls to Chapter 6 (Skill tree)
- Hidden when no report is loaded, same as the chapters

**Report panel (scrollable):**
- Header card above, then the 12-chapter report — see §5

**Correction dialog:**
- "Correct result" button in Ch 1 → shows correction dialog
- User selects the correct stage from a list
- Saves to report_correction.json

---

## 5. Report: 12 Chapters

All chapter titles and UI strings come from `locales/strings.json` via `I18n.t()`. Chapters with no data are hidden.

| # | ID | Title (i18n key) | Default | Content |
|---|---|---|---|---|
| 1 | summary | "Summary" | Expanded | Stage name + trophy icon (also anchored by the header card above the report, see §4); terrain + suggested trail rating; pass/fail gate message; score ring (0–100, heuristic); confidence ring; 4 posture rings (stability / coordination / control / balance); ScoreTimelineView; "Correct result" button |
| 2 | why_stage | "Why this stage" | Expanded | Classification candidates (top 2): fit %, gate %, prior %, score %; quality chips (view angle / camera motion / snow / slope / terrain / fps); scene missing facts |
| 3 | core_metrics | "Core metrics" | Expanded | Legend: "Gate metrics decide advancement; diagnostic metrics explain the skiing." Per metric card: name, Gate/Diagnostic label, rubric chip (Pass/Not yet/Strong/Not rated), score ring, left/right values, faulty-turn count, evidence-time seek link |
| 4 | turns | "Turn-by-turn" | Expanded | Turn count (left / right); mean duration; rhythm CV; TurnStripView; per-turn detail rows with seek links |
| 5 | checkpoints | "Checkpoints" | Expanded | Weakest checkpoint card (if not passed); per-checkpoint: score ring, Pass/Not yet chip, good/bad coaching text, faulty-turn count, evidence-time seek link, drill lines |
| 6 | skill_tree | "Skill tree" | Expanded | Vertical tree (white dashed connector); node states: completed = filled purple, current = light purple, inferred = medium purple, available = grey, locked = dark grey; next stage names shown as individual chips, with the top-priority one (`next_level_names[0]`) marked "Recommended next" in accent color; full LevelPlan cards with drills/venues for every next stage, with the plan matching the recommended stage shown first and visually distinguished — all next stages/plans remain visible, only the ordering/emphasis changes. Side branches (moguls/off-piste/park/race off the piste spine) are collapsible: only the branch containing the current stage is expanded by default, every other branch starts collapsed behind a "{Branch} · N stages" disclosure row, tap to expand/collapse — the piste spine itself is never collapsed |
| 7 | tutorial | "Stage tutorial" | **Collapsed** | From kb.v1.json: goal, why it matters, skills with name/description/cues/misconceptions (ordered by knowledge_focus.skill_ids if set) |
| 8 | drills | "Drills" | **Collapsed** | From kb.v1.json ordered by knowledge_focus.drill_ids: name, purpose, setup, steps, dose (max 8 drills) |
| 9 | faults | "Faults and fixes" | **Collapsed** | From kb.v1.json ordered by knowledge_focus.fault_ids: name, looks like, symptom, injury risk, fix cues (max 8 faults) |
| 10 | terrain | "Terrain and venue" | **Collapsed** | Terrain name/desc from report; terrain entities and tactics from kb.v1.json |
| 11 | equipment | "Equipment" | **Collapsed** | Equipment entities from kb.v1.json; profile effects (age band, ski length band, effects list) |
| 12 | filming | "Filming and disclaimer" | Expanded | Disclaimer text; carve heuristic note (if applicable); FilmingIssue cards with severity prefix (⚠ blocker / ! warn / • info); film_steps checklist |

Chapters 7–11 are collapsible: tap the chapter title to expand/collapse.  
Empty chapters (no data) are hidden entirely.

---

## 6. Import Flow (Step by Step)

1. User taps **Camera** or **Import** on List screen
2. **Camera path:** live preview → Record → auto-stop after 120s or user stops → temp file written → ingest with play_start_ms = 0, play_end_ms = null
3. **File import path:** file picker → user selects file
4. **If video duration > 120s:** Trim Dialog shown → user selects in/out window (≤120s) → confirm
5. **IngestWorker** (background thread):
   - Copy file to `library/{clip_id}/clip.mp4` (or `clip.jpg`)
   - Extract metadata (duration, dimensions, fps)
   - Write thumbnail → `thumb.jpg`
   - Write `meta.json` (status = PENDING, play_start_ms, play_end_ms)
6. Navigate to List → clip appears as **Pending**
7. User taps Pending card → Prepare screen

---

## 7. Analysis Flow (Step by Step)

1. User opens **Prepare**: seeks video, draws person bounding box(es), fills athlete form, optionally sets scene
2. "Start analysis" pressed:
   - Saves seeds, athlete, scene → `meta.json` (status = PROCESSING)
   - Starts AnalysisWorker in background thread; loading overlay shown
3. **AnalysisWorker:**
   - Open media with MediaPipe PoseLandmarker (GPU → CPU fallback)
   - For video: iterate every **2nd frame** in [play_start_ms, play_end_ms], max 120s:
     - Use nearest seed mark to anchor person bounding box (ROI)
     - Between seeds: color-histogram person tracking to reidentify across frames
     - Run MediaPipe inference on ROI crop
     - Collect COCO-17 keypoints + BlazePose-33 joints per frame
   - Post-process: fill low-confidence frame gaps (≤400ms gap), EMA-smooth bounding boxes
   - Write → `analysis.json`
4. **Assess pipeline:**
   - `SportsSignals.extractFeatures()` → FeaturePack (stance width, knee flex, inward lean, backseat, turn frequency, …)
   - `Turns.segment()` → TurnSegmentation (left/right turns, t_start_ms/t_end_ms)
   - `MetricPackBuilder.build()` → MetricPack (per-metric scores from LevelBands)
   - `ClassifyV3.classify()` → Classification (candidate stages, fit, gate ratio, prior, ambiguity)
   - `SkillTree.buildTree()` → list[TreeNodeV3]
   - Assemble → `StageReport` v3.0.0
   - Write → `stage_report.json`
5. `meta.json` status = **DONE** → List auto-refreshes → user taps Report or Done card → Player

---

## 8. Key Algorithms

### Person Tracking
Multi-seed color histogram ROI tracker:
- User places seed boxes at specific timestamps in Prepare
- At each seeded timestamp, the person box is known exactly
- Between seeds: build a color histogram of the person crop, then search nearby frames using histogram similarity (`compareHist`) to reidentify the person
- `ClipRange.nearestSeed(t_ms)` — returns the nearest seed for any frame
- `PersonRoi` — handles histogram build and search

### Frame Stride
Every **2nd frame** is processed (stride = 2). At 30fps this gives ~15 pose estimates per second. Capped at `MAX_MS = 120,000ms`.

### Pose Mapping
BlazePose 33 joints → COCO-17 keypoints via the shared native `core_map` C library (`libcore_map.so` / `core_map.dylib` / `core_map.dll`). The JNI/FFI bridge calls `fromBlaze33(json_in) → json_out`.

### Turn Segmentation
Hip-X oscillation analysis: detect left–right direction changes in the hip joint's horizontal position. Produces a list of `TurnSegment` (side, t_start_ms, t_end_ms, amplitude_deg).

### ClassifyV3
For each candidate stage in curriculum.v3.json:
- **Fit**: LevelBands fuzzy membership score for all metrics in this stage
- **Gate ratio**: fraction of gate metrics that pass
- **Prior**: stage history for this athlete + terrain adjacency weight
- **Quality gate**: minimum usable frame fraction required
- Combined score → ranked candidates; ambiguous when top-2 confidence gap < threshold

### Posture
Four composite scores from FeaturePack + keypoint results:
- **Stability**: lateral balance and weight transfer consistency
- **Coordination**: upper-lower body timing
- **Control**: edge angle management
- **Balance**: fore-aft weight distribution

### Skill Tree
Depth-first build from curriculum.v3.json dependency graph. Node states:
- `completed` — athlete has passed this level (from StageHistory)
- `current` — diagnosed level for this clip
- `inferred` — implied complete by passing a downstream level
- `available` — prerequisites met, ready to attempt
- `locked` — prerequisites not met
- `not_applicable` — excluded for this athlete (age/terrain)

---

## 9. Platform Parity Matrix

| Feature | PC (Windows) | iOS | Android |
|---|---|---|---|
| 4-screen workflow | ✅ | ✅ | ✅ |
| Video import (file picker) | ✅ | ✅ | ✅ |
| Live camera recording | ✅ | ✅ | ✅ |
| **Trim dialog for >120s video** | ✅ | ✅ | ✅ (added) |
| MediaPipe pose analysis | ✅ | ✅ | ✅ |
| COCO-17 skeleton overlay | ✅ | ✅ | ✅ |
| 12-chapter report | ✅ | ❌ (5 chapters) | ✅ |
| Turn-by-turn (ch 4) | ✅ | ❌ | ✅ |
| Collapsible ch 7–11 | ✅ | ❌ | ✅ |
| Knowledge pack (ch 7–11) | ✅ | ❌ | ✅ |
| Skill tree (ch 6) | ✅ | ✅ (basic) | ✅ |
| Correction dialog | ✅ | ❌ | ✅ |
| Frame feedback | ✅ | ✅ | ✅ |
| "Possible stage" chip | ✅ | ❌ | ✅ |
| 9-language i18n | ✅ | partial | ✅ |
| Athlete profiles | ✅ | ✅ | ✅ |
| Scene context form | ✅ | ❌ | ✅ |
| Speed selector (6 speeds) | ✅ | ✅ | ✅ |
| Download JPEG | ✅ | ✅ | ✅ |
| Download MP4 (overlay) | ✅ | ❌ | ❌ deferred |
| Share sheet + upload URLs | ✅ | ✅ | ✅ |
| Scene inference hints (Prepare) | ✅ | ❌ | ❌ deferred |
| Processing cancel button | ✅ | ❌ | ❌ deferred |
| Optical-flow camera motion | ✅ | ❌ | ❌ deferred |

**Deferred (Phase 4):** overlay MP4 export, optical-flow camera_motion, scene_infer hints, processing cancel, lite landmarker option.

---

## 10. i18n Rules

- All user-visible strings come from `locales/strings.json` via the platform i18n helper (`I18n.t(key)` on Android/iOS, `i18n.t(key)` on Windows)
- The English string IS the key — do not use separate en keys
- Language can be switched at runtime — all rendered text must re-render from strings when language changes
- `strings.json` schema_version 2.0.0; approximately 800+ keys; 9 languages
- New features: add keys to `strings.json` first, then use `I18n.t()` in all clients

---

## 11. Design Tokens

| Token | Value | Usage |
|---|---|---|
| CARD | `#1A2433` | Card background |
| PAPER | `#F5F5F5` | Body text on dark cards |
| TITLE | `#9E9E9E` | Secondary / metadata text |
| DEEP_PURPLE | `#5E35B1` | Primary brand color |
| LIGHT_PURPLE | `#CE93D8` | Accent, current-level node |
| WATERMELON | `#E94B6A` | Error / fail |
| LINK | `#4FC3F7` | Tappable seek links |
| SPACE_CHAPTER | 36dp | Between report chapters |
| SPACE_PANEL | 24dp | Between cards within a chapter |
| SPACE_TEXT | 16dp | Between text lines |
| PAGE_INSET | 12dp | Card internal padding |

---

## 12. References

- PC client: [`clients/windows/`](../clients/windows/)
- iOS client: [`clients/ios/`](../clients/ios/)
- Android client: [`clients/android/`](../clients/android/)
- Stage report schema: [`schemas/stage_report.py`](../schemas/stage_report.py)
- Curriculum: [`content/ski/curriculum.v3.json`](../content/ski/curriculum.v3.json)
- Desktop ↔ Android parity: [`docs/clients/desktop-android-parity-v3.md`](clients/desktop-android-parity-v3.md)
- v3 design spec: [`docs/superpowers/specs/2026-08-30-ski-report-v3-design.md`](superpowers/specs/2026-08-30-ski-report-v3-design.md)
