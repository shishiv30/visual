# Core inference API draft (v0)

Contract for later app layers. Independent of Ultralytics. JSON Schema: [`schemas/core-inference.v0.json`](../../schemas/core-inference.v0.json). Pydantic: [`schemas/core_inference.py`](../../schemas/core_inference.py).

`schema_version` is `0.1.0`. Unused tasks return **empty arrays**, not omitted keys.

## Input (conceptual)

The process that calls Core supplies:

- raster (`image` or `video_frame`)
- `timestamp_ms`
- pixel `width` / `height`
- optional `camera_intrinsics` `{fx, fy, cx, cy}`

This phase does not define an HTTP route.

## Output

Top-level object `CoreInferenceResult`:

- `detections[]` — `class_name`, `confidence`, `bbox_xyxy` (pixel xyxy), optional `track_id`
- `poses[]` — `skeleton: coco_17`, 17 named keypoints `{name, x, y, z?, confidence}`, `score`, optional `detection_index`
- `tracks[]` — `track_id` + `detection_index` (empty until ByteTrack is wired)
- `classifications[]` / `segments[]` — reserved
- `model_meta` — `backend_id`, `model_name`, `latency_ms`, `device`
- `error` — null or `{code, message}` with `NO_PERSON` | `LOW_CONFIDENCE` | `GPU_OOM` | `INVALID_INPUT`

`backend_id` values in this repo:

- `yolo11n-pose` / `yolo11n` — Windows CUDA YOLO (desktop baseline, not shipped on phone)
- `mediapipe_pose` — offline MediaPipe Pose Landmarker on Windows / iOS / Android (see [blazepose-coco17.md](blazepose-coco17.md))

Default YOLO backend fills `detections` (person) and `poses`. Contrast `yolo11n` fills `detections` only. MediaPipe fills the same COCO-17 fields after BlazePose mapping.

## COCO-17 names (fixed order)

nose, left_eye, right_eye, left_ear, right_ear, left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist, left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle

Coordinates are in the **original frame** pixel space after letterbox inversion (backend responsibility).
