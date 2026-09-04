# Ski Board Overlay — Offline Algorithm Research

Status: draft (follow-up to pose-proxy overlay)
Date: 2026-08-31
Builds on: [`2026-08-31-ski-cv-optimization-research.md`](2026-08-31-ski-cv-optimization-research.md) §5 (Track B)

## 1. Problem statement

Users expect **two cyan ski axes under the skeleton feet**. Current playback uses a **pose proxy** (Blaze33 knee→ankle→foot_index) when `models/ski/segment.onnx` is absent.

**Observed failures (production):**

| Symptom | Root cause |
|---|---|
| Boards not under feet | MediaPipe foot_index / heel are **boot-top landmarks**, not ski tips; 2D projection collapses board length |
| Boards misaligned with body | Shank direction ≠ ski axis in quarter-view and follow-cam; no ground plane |
| Low / unstable detection | Heel landmarks noisy; profile view; occlusion; proxy conf gate hides lines |
| Re-analyze does not fix | ONNX model not shipped; stored `ski.source=pose` was misleading |

**Conclusion:** Pose proxy is acceptable for **interim wedge metrics (P1a/B0)** only. It is **not** a stable overlay or coach-facing geometry source.

---

## 2. Requirements (unchanged)

| Requirement | Notes |
|---|---|
| Fully offline | ONNX Runtime on Windows CPU/DirectML; later CoreML / NNAPI |
| Cross-platform logic | Geometry in `core/sports/`; no UI-only math |
| Target clip | Quarter-view piste, 720p, single skier, bbox from existing pipeline |
| Honest accuracy | Stage classification ±5° wedge MAE; not FIS edge scoring |
| Latency budget | < 30 ms / frame @ 720p crop on mid laptop CPU |
| Model size | < 5 MB preferred; < 35 MB acceptable for SAM-class fallback |

---

## 3. Option matrix (offline)

| ID | Method | Input | Output | Stability | Size / speed | Fit |
|---|---|---|---|---|---|---|
| **B1** | Tiny U-Net / MobileNet encoder | RGB crop + bbox | 2 ski masks → PCA tip/tail | **High** (trained on skis) | ~2–5 MB, fast | **Primary (spec P1b)** |
| **B1+** | B1 + temporal median (5-frame) | mask series | smoothed tip/tail | High | negligible | P2 (partially done for pose) |
| **B2** | MobileSAM / SAM-ViT-B (quantized) | crop + **point prompts** (ankles, toes) | masks → PCA | Medium–high | 10–72 MB, 50–200 ms | Offline analyze OK; heavy for mobile |
| **B3** | SkipClick (2025) | image + clicks/bbox | mask | Medium–high on snow | TBD; real-time interactive | Same team as WSESeg; winter domain |
| **B4** | Direct tip/tail keypoints (Ludwig WACVW’23 ViT) | RGB | 4 keypoints | Medium (ski-jump pretrain) | ~5–15 MB | Needs fine-tune on piste clips |
| **B5** | Classical edge / color in foot ROI | crop below ankle | line fit | **Low** on white/grey snow | trivial | Reject |
| **B0** | Pose proxy (current) | Blaze33 | synthetic axis | **Low** for overlay | zero | Metrics fallback only; **hide in UI** |

---

## 4. Recommended path

### Phase 1 — Stop showing bad overlay (immediate)

1. **UI policy:** draw ski overlay only when `ski.source == "segment"` OR `ski_detect_ok` from segmentation with conf ≥ threshold.
2. Pose proxy remains for **`ski_wedge_angle` fallback metrics** when board detect fails; do not render as ski lines.
3. Optional chip: «Ski outline unavailable — re-run with board model» (i18n).

This avoids false confidence while the model is missing.

### Phase 2 — Ship segmentation MVP (4–6 weeks, already specced)

Already scaffolded in repo:

| Asset | Path |
|---|---|
| Geometry | `core/sports/ski_geometry.py` |
| Detect hook | `core/sports/ski_detect.py` |
| Baseline script | `scripts/ski_baseline_wseseg.py` |
| Annotation schema | `content/ski/annotations/schema.json` |
| Runbook | `2026-08-31-p1b-wseseg-baseline-runbook.md` |

**Steps:**

1. Download **WSESeg** ([github.com/Schorob/wseseg](https://github.com/Schorob/wseseg)) → `data/ski/wseseg/` (gitignored).
2. Run `evaluate-masks` → confirm **mask → PCA wedge** MAE on alpine ski class.
3. Train **MobileNetV3-Small + U-Net decoder** (2-class: left/right ski) on WSESeg «Skis (misc)» masks.
4. Export **`models/ski/segment.onnx`**; wire existing `_run_segmentation()` in `ski_detect.py`.
5. Label **50–100 frames** from library clips (`b97c92dd` parallel + one pizza clip) → fine-tune / calibrate conf threshold.
6. Acceptance: quarter-view MAE < 5° vs tip/tail labels; parallel clip false pizza = 0.

**Pose-guided mask assignment (improves split):**

- After connected components, assign left/right by nearest ankle (Blaze33 27/28) — already in spec §5.3.
- Reject frame when `view_too_profile` (existing azimuth gate in metrics).

### Phase 3 — Optional upgrades (if B1 insufficient)

| If… | Then… |
|---|---|
| Grey boards on white snow | Add contrast augment; fine-tune on self clips; avoid pure edge detectors |
| Follow-cam motion blur | Temporal mask union over 3 frames before PCA |
| B1 MAE > 5° on labels | Try **SkipClick** ([arxiv:2501.07960](https://arxiv.org/abs/2501.07960)) on WSESeg + SHSeg skier masks |
| Need faster labeling | MobileSAM with ankle clicks for coach correction UI (P3 B3 loop) |
| Jump-specific geometry | Ludwig tip/tail ViT — fine-tune last layers on piste labels only |

---

## 5. Datasets (offline)

| Dataset | Content | Use |
|---|---|---|
| **WSESeg** (CBMI 2024) | 7452 equipment instance masks; 2 ski classes | Pretrain segmenter; PCA baseline |
| **SHSeg** (SkipClick 2025) | 534 skier masks on SkiTB frames | Generalization test (athlete vs equipment) |
| **SkiTB** | Bounding boxes, multi-cam ski video | Hard cases, follow-cam |
| **Self clips** | 50–100 tip/tail JSON (`annotations/schema.json`) | Fine-tune + acceptance |
| **Ludwig ski-jump** | tip/tail + sparse masks | Architecture reference, not domain match |

---

## 6. Architecture (target)

```
RGB frame + skier bbox
        │
        ├─► MediaPipe pose (existing)
        │
        └─► segment.onnx (crop bbox + 8% pad)
                 │
                 ├─► left/right masks (CC + ankle assign)
                 │
                 └─► ski_geometry.mask_axis_endpoints
                          │
                          ├─► analysis.json ski {tip,tail,source:segment}
                          ├─► overlay draw (cyan)
                          └─► metrics ski_wedge_angle / ski_parallelism
```

Pose proxy **does not** feed overlay when `segment.onnx` missing.

---

## 7. Evaluation plan

| Test | Command / fixture |
|---|---|
| Geometry unit | `pytest tests/test_ski_geometry.py` |
| Mask baseline | `python scripts/ski_baseline_wseseg.py evaluate-masks …` |
| Label MAE | `score-labels` on `data/ski/self_clips/*/annotations.json` |
| Parallel regression | clip `b97c92dd` — no pizza false positive |
| Overlay visual | Player + export_overlay on 3 labeled frames |
| Profile gate | Drop ski detect when azimuth < 25° |

Report template: `benchmarks/ski/wseseg_baseline.json` (extend with `self_clip_mae`).

---

## 8. References

| Ref | Topic |
|---|---|
| Schön et al., CBMI 2024 — [WSESeg](https://arxiv.org/abs/2407.09288) | Equipment segmentation dataset |
| Schön et al., 2025 — [SkipClick](https://arxiv.org/abs/2501.07960) | Winter-sports interactive segmentation |
| Ludwig et al., WACVW 2023 | Ski tip/tail keypoints with sparse masks |
| Fohrmann et al., Sensors 2019 | Monocular ski + body orientation (±3.8° lean) |
| Zhang et al., MobileSAM | ONNX-friendly prompted segmentation |
| Dunnhofer & Micheloni, SkiTB 2024 | Ski video benchmark |

---

## 9. Decision

| Question | Answer |
|---|---|
| Can pose proxy ever be «stable enough» for overlay? | **No** for quarter-view coach UI |
| What is the minimum viable offline solution? | **WSESeg-trained tiny segmenter + PCA tip/tail** (P1b) |
| What to do until model ships? | **Hide pose overlay**; keep skeleton; show unavailable hint |
| Next engineering task | Download WSESeg → baseline MAE → train ONNX → label 50 frames |
