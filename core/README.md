# Core

Runtime that turns a BGR frame into `CoreInferenceResult` (see `schemas/`).

Default backend: Ultralytics YOLO11n-pose on CUDA when available.

Offline multi-client backend: MediaPipe Pose Landmarker (`--backend mediapipe`) plus `native/core_map` (BlazePose 33 → COCO-17 JSON). Same `.task` file is used on Windows / Android / iOS.

## Run one image

```powershell
python -m pip install -r benchmarks/requirements.txt
python -m core.cli path\to\image.jpg --out result.json
python -m pip install -r requirements-mediapipe.txt
python scripts/download_pose_landmarker.py
python -m core.cli path\to\image.jpg --backend mediapipe --out result-mp.json
```

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

CPU tests cover schema + tensor mapping. The CUDA smoke test loads `yolo11n-pose.pt` and is skipped when no GPU is present.
