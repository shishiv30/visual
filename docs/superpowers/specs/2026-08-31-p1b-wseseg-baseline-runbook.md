# P1b — WSESeg baseline and self-clip annotation runbook

Companion to [`2026-08-31-ski-cv-optimization-research.md`](2026-08-31-ski-cv-optimization-research.md).

## Goal

Validate that **mask → PCA axis → ski wedge angle** is stable enough to replace foot-index wedge on quarter-view clips, before training a tiny segmenter.

Target: MAE < 5° vs coach tip/tail labels on 50–100 frames.

---

## Step 1 — WSESeg dataset

1. Obtain WSESeg (CBMI 2024, 7452 alpine/jump ski instance masks).
2. Extract to **`data/ski/wseseg/`** (gitignored; not committed).
3. Expected layout:

```
data/ski/wseseg/
  images/          # or frames/
  masks/           # per-instance or per-image combined masks
  meta.json        # optional index
```

If download URL requires paper contact, document the resolved path in this folder’s `meta.json` locally.

---

## Step 2 — Baseline script (to implement)

**File:** [`scripts/ski_baseline_wseseg.py`](../../scripts/ski_baseline_wseseg.py)

```bash
# Smoke: PCA wedge on one mask pair
python scripts/ski_baseline_wseseg.py \
  --wseseg-dir data/ski/wseseg \
  --limit 20 \
  --report benchmarks/ski/wseseg_baseline.json

# Export frames from library clip for manual tip/tail labeling
python scripts/ski_baseline_wseseg.py \
  --export-clip "%LOCALAPPDATA%/visual/library/<clip-uuid>/clip.mp4" \
  --export-count 30 \
  --export-dir data/ski/self_clips/<clip-uuid>/frames
```

**Script responsibilities:**

| Subcommand | Action |
|---|---|
| `evaluate-masks` | Load WSESeg masks → `core.sports.ski_geometry.compute_ski_wedge_from_combined_mask` → wedge stats |
| `export-frames` | Sample N frames from clip mp4 → PNG + `manifest.json` |
| `score-labels` | Compare tip/tail JSON annotations → MAE vs PCA or model |

---

## Step 3 — Geometry module (to implement)

**File:** [`core/sports/ski_geometry.py`](../../core/sports/ski_geometry.py)

Pure numpy (no OpenCV):

- `mask_axis_endpoints(mask) -> SkiAxis`
- `split_connected_masks(mask) -> list[mask]`
- `ski_wedge_angle_deg(left, right) -> float`
- `ski_parallelism(wedge_deg) -> float`
- `compute_ski_wedge_from_combined_mask(mask) -> SkiWedge | None`

**Tests:** [`tests/test_ski_geometry.py`](../../tests/test_ski_geometry.py) — synthetic rectangles at known angles.

---

## Step 4 — Self-clip annotation

**Schema:** [`content/ski/annotations/schema.json`](../../content/ski/annotations/schema.json)

**Workflow:**

1. Pick 2–3 library clips: at least one **parallel** (e.g. `b97c92dd`), one **pizza**, one ambiguous if available.
2. Export ~15–30 frames each (quarter view, board visible).
3. Label in any tool (Label Studio, CVAT, or simple HTML canvas); export to JSON matching schema.
4. Store under `data/ski/self_clips/<clip_id>/annotations.json` (gitignored).

**Minimum fields per frame:**

```json
{
  "frame_index": 42,
  "skis": {
    "left":  { "tip": [120, 400], "tail": [140, 520] },
    "right": { "tip": [280, 395], "tail": [260, 515] }
  }
}
```

**Coach stage label** on the file root: `"stage_label": "parallel"`.

---

## Step 5 — Acceptance checklist

- [ ] WSESeg baseline runs on ≥20 mask pairs without crash
- [ ] Wedge angle distribution: alpine masks mostly >10° for wedge-like poses (sanity)
- [ ] Self labels: ≥50 frames across parallel + pizza
- [ ] PCA-from-mask MAE vs labels documented in `benchmarks/ski/wseseg_baseline.json`
- [ ] If MAE > 8°: proceed to tiny U-Net on WSESeg; if MAE < 5° on clean frames: integrate `ski_wedge_angle` into metrics (feature flag)

---

## Step 6 — Next code integration (after baseline)

1. Add `ski_detect.py` + ONNX model path under `models/ski/` (gitignored weights).
2. Register `ski_wedge_angle`, `ski_parallelism`, `ski_detect_ok` in `content/ski/knowledge/metrics.json`.
3. Wire analyze pipeline optional pass in `clients/windows/pipeline/analyze.py`.
4. Curriculum + `bands.py` gate on `ski_wedge_angle` when `ski_detect_ok`.

---

## References

- WSESeg: https://doi.org/10.1109/cbmi62980.2024.10859243
- Ludwig WACVW 2023 tip/tail keypoints
- Fohrmann Sensors 2019 board orientation
