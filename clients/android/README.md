# Android offline pose demo

Kotlin + CameraX + MediaPipe Tasks Vision. Pose landmarks are flattened and passed to `libcore_map.so` (same C as Windows/iOS) which returns Core JSON (`backend_id=mediapipe_pose`, `skeleton=coco_17`).

## Setup

1. Copy `models/pose_landmarker_full.task` (from `python scripts/download_pose_landmarker.py`) to `app/src/main/assets/`.
2. Open `clients/android` in Android Studio.
3. Build/run on a device or emulator with a camera.

The C sources are compiled via `app/src/main/cpp/CMakeLists.txt` pointing at `native/core_map/core_map.c`.
