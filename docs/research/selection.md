# Selection matrix

Weights from [2026-08-22-core-vision-research-design.md](../superpowers/specs/2026-08-22-core-vision-research-design.md). Scores 1–5. **Measured rows** use this machine’s 1080p batch-1 numbers in [performance.md](performance.md).

## Candidates scored

| ID | Backend | Why it is in the matrix |
| --- | --- | --- |
| A | Ultralytics YOLO11n-pose (PyTorch CUDA) | Single pass: person box + 17 keypoints |
| B | Ultralytics YOLO11n detect (PyTorch CUDA) | Detection-only contrast; tracking-friendly boxes |
| C | MediaPipe Pose | Client-first, Apache-2.0, weaker CUDA server story |
| D | MMPose RTMPose + separate detector | Accuracy-oriented Apache stack; heavier Windows install |
| E | ViTPose via Transformers | Hub-native research baseline |

## Scores

| Criterion (weight) | A YOLO11n-pose | B YOLO11n-det | C MediaPipe | D RTMPose stack | E ViTPose |
| --- | --- | --- | --- | --- | --- |
| Latency 1080p 30% | 5 (measured) | 5 (measured) | 3 (CPU-class; not CUDA default) | 3 (install not run here) | 2 (expected slower) |
| Peak VRAM 15% | 5 (measured) | 5 (measured) | 4 (CPU RAM) | 3 | 2 |
| Win+CUDA repro 20% | 5 | 5 | 4 | 2 | 4 |
| Structured I/O 20% | 5 (box+kpts) | 4 (box only) | 4 (kpts, weak box) | 5 | 4 |
| License 10% | 2 (AGPL-3.0) | 2 (AGPL-3.0) | 5 (Apache-2.0) | 5 (Apache-2.0) | 5 |
| Swap cost 5% | 4 (ONNX export) | 4 | 2 (graph not YOLO-shaped) | 3 | 3 |
| **Weighted / 5** | **4.55** | **4.35** | **3.70** | **3.35** | **3.15** |

Weighted example for A: `0.3*5 + 0.15*5 + 0.2*5 + 0.2*5 + 0.1*2 + 0.05*4 = 4.55`.

## Recommendation

- **Default backend:** Ultralytics **YOLO11n-pose** on PyTorch CUDA. Highest score, one model fills Core `detections` + `poses`, and this host already runs `torch 2.11+cu128`.
- **Contrast backend:** Ultralytics **YOLO11n** detect. Same install and tensor layout; isolates detector cost vs pose head. Use when app only needs boxes + ByteTrack.
- **License fork:** if a commercial app cannot take AGPL, re-run the matrix with **RTMPose + RTMDet (Apache)** or MediaPipe as default; do not ship Ultralytics weights without an enterprise license.

First Core version should expose pose+detect fields and treat `tracks` as optional (ByteTrack in a later increment).
