# Open-source vision landscape

Survey date: 2026-08-22. Task groups are separate from framework names. Windows + NVIDIA CUDA is the deployment assumption.

## Pose / skeleton

| Stack | Typical models | Output | License | Windows/CUDA | Swap as backend |
| --- | --- | --- | --- | --- | --- |
| MediaPipe Pose / Holistic | BlazePose | 33 2D/world landmarks | Apache-2.0 | CPU/GPU via MediaPipe; Windows OK, not TensorRT-first | Good for client-side; weaker as server CUDA default |
| MMPose / RTMPose | RTMPose-t/s/m, RTMW | COCO 17 or whole-body keypoints | Apache-2.0 | Strong Linux+CUDA; Windows via mim is heavier | Excellent accuracy; higher install cost |
| Ultralytics YOLO-Pose | YOLO11n/s-pose | bbox + 17 COCO kpts | AGPL-3.0 (or Ultralytics enterprise) | First-class `pip` + PyTorch CUDA | Best Windows velocity |
| ViTPose (HF Transformers) | ViTPose-base/large | Heatmap keypoints | Apache-2.0 (check weights) | Transformers + CUDA; larger VRAM | Research-grade; slower ops |
| MoveNet | Thunder / Lightning | 17 kpts | Apache-2.0 (TF) | TF/TFLite; CUDA secondary | Mobile-oriented |

## Detection

| Stack | Typical models | Output | License | Windows/CUDA | Swap as backend |
| --- | --- | --- | --- | --- | --- |
| Ultralytics YOLO | YOLO11n/s/m detect | xyxy, cls, conf | AGPL-3.0 / enterprise | Excellent | High |
| MMDetection | RTMDet, Faster R-CNN | same | Apache-2.0 | Heavy but complete | Medium |
| RT-DETR | rtdetr-l/x | xyxy | Apache-2.0 (Paddle/Ultralytics ports) | Ultralytics port is easiest on Windows | Medium |
| HF object detection | DETR, YOLOS | boxes | Apache-2.0 typically | Easy install; not always fastest | Medium |

## Tracking (multi-person / temporal)

| Stack | Notes | License | Windows |
| --- | --- | --- | --- |
| ByteTrack | ID association on detector boxes; standard for sports video | MIT | Detector-agnostic |
| BoT-SORT | ByteTrack + camera motion / ReID option | AGPL or MIT depending on fork | Heavier than ByteTrack |
| Ultralytics `track=True` | Wraps ByteTrack / BoT-SORT | Same as Ultralytics | One-liner on Windows |

Tracking is not a standalone backbone: it consumes detections (and optionally embeddings).

## Segmentation (scene option)

| Stack | Output | License | Fit |
| --- | --- | --- | --- |
| SAM / SAM2 | Prompts → masks | Apache-2.0 | Interactive, not real-time default |
| FastSAM | Fast approx SAM | AGPL | Speed over quality |
| YOLO-seg | Instance masks + classes | AGPL | Same family as YOLO detect/pose |

## Inference runtimes (Windows + NVIDIA)

| Runtime | Role | Notes |
| --- | --- | --- |
| PyTorch CUDA | Training + first-party inference | This machine: `2.11.0+cu128` on RTX 5090 Laptop |
| ONNX Runtime CUDA EP | Portable export target | Best swap layer after a PyTorch winner |
| TensorRT | Lowest latency | Engine rebuild per GPU/arch; Blackwell (50-series) needs recent TRT |
| OpenCV DNN | CPU/CUDA baseline | Useful as a floor, not SOTA pose |

Hugging Face Hub is a **weight catalog**, not a runtime. Prefer Hub checkpoints that export to ONNX.

## Community latency (order of magnitude, 1080p batch 1, not this machine)

| Family | Typical FPS class |
| --- | --- |
| YOLO11n detect/pose | tens–100+ FPS on modern NVIDIA |
| RTMPose-s + YOLO detect two-stage | tens of FPS |
| ViTPose-base | often < real-time at 1080p |
| MediaPipe Pose | real-time on CPU; GPU path varies |
| SAM ViT-H | far from real-time |

## Implications for Core

A product that later needs **person box + COCO-17 skeleton + track id** can start from one YOLO family (detect or pose) plus ByteTrack. Two-stage MMPose remains the accuracy contrast if AGPL is unacceptable and Apache stacks are required.
