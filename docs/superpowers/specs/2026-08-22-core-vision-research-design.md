# Core vision research — design spec

Date: 2026-08-22  
Phase: core research only (no app, no client)

## Goal

Compare mainstream open-source vision stacks for a future action-tracking product. Decide a **default inference backend** and one **contrast backend**, then freeze a versioned Core I/O schema that later app layers can consume.

## Constraints

- Host: Windows + NVIDIA GPU (measured on RTX 5090 Laptop, 24 GB).
- Batch size 1; resolutions 720p and 1080p.
- Do not lock product capabilities before numbers exist. Schema stays extensible (empty arrays allowed).
- No HTTP service in this phase.

## Decision weights (fixed)

| Criterion | Weight |
| --- | --- |
| Latency / FPS at 1080p, batch 1 | 30 |
| Peak VRAM | 15 |
| Windows + CUDA install reproducibility | 20 |
| Structured outputs (bbox, keypoints, track id) | 20 |
| License for later commercial apps | 10 |
| Swap cost (ONNX / unified tensors) | 5 |

Scores are 1–5. Weighted total is out of 5.

## Success criteria

1. Landscape covers pose, detection, tracking, segmentation, and CUDA runtimes.
2. Benchmarks produce JSON under `benchmarks/results/` with latency, FPS, and peak memory.
3. `docs/research/selection.md` names default + contrast backends with the matrix filled.
4. `schemas/core-inference.v0.json` matches `docs/research/api-draft.md`.

## Conclusions (filled after measurement)

- Default: Ultralytics YOLO11n-pose (PyTorch CUDA). ~102 FPS at 1080p batch 1, ~95 MiB peak on RTX 5090 Laptop.
- Contrast: YOLO11n detect. ~107 FPS at 1080p; boxes only.
- Schema: `schemas/core-inference.v0.json` / `schemas/core_inference.py`.

## Non-goals

Skiing (or any sport) scoring, real-time overlay UI, multi-camera calibration, 3D mesh reconstruction.
