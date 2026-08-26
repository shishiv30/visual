# BlazePose 33 → COCO-17 (offline Core)

Shared by Windows / iOS / Android. MediaPipe Pose Landmarker emits **33** BlazePose landmarks. Core `poses[].skeleton` stays **`coco_17`**. Mapping lives in [`native/core_map/`](../../native/core_map/) (C ABI) with a Python twin in [`core/blaze_map.py`](../../core/blaze_map.py).

`model_meta.backend_id` for this path: **`mediapipe_pose`**.

## Landmark indices

MediaPipe BlazePose (Tasks Pose Landmarker):

| i | Name |
| --- | --- |
| 0 | nose |
| 1 | left_eye_inner |
| 2 | left_eye |
| 3 | left_eye_outer |
| 4 | right_eye_inner |
| 5 | right_eye |
| 6 | right_eye_outer |
| 7 | left_ear |
| 8 | right_ear |
| 9 | mouth_left |
| 10 | mouth_right |
| 11 | left_shoulder |
| 12 | right_shoulder |
| 13 | left_elbow |
| 14 | right_elbow |
| 15 | left_wrist |
| 16 | right_wrist |
| 17–22 | hands (unused for COCO-17) |
| 23 | left_hip |
| 24 | right_hip |
| 25 | left_knee |
| 26 | right_knee |
| 27 | left_ankle |
| 28 | right_ankle |
| 29–32 | heels / foot index (unused) |

COCO-17 order (Core `keypoints[]`):

| COCO i | Name | Blaze i |
| --- | --- | --- |
| 0 | nose | 0 |
| 1 | left_eye | 2 |
| 2 | right_eye | 5 |
| 3 | left_ear | 7 |
| 4 | right_ear | 8 |
| 5 | left_shoulder | 11 |
| 6 | right_shoulder | 12 |
| 7 | left_elbow | 13 |
| 8 | right_elbow | 14 |
| 9 | left_wrist | 15 |
| 10 | right_wrist | 16 |
| 11 | left_hip | 23 |
| 12 | right_hip | 24 |
| 13 | left_knee | 25 |
| 14 | right_knee | 26 |
| 15 | left_ankle | 27 |
| 16 | right_ankle | 28 |

Index table in code: `{0,2,5,7,8,11,12,13,14,15,16,23,24,25,26,27,28}`.

## Coordinates and confidence

- Input to `core_map_from_blaze33`: per person **33 × 4** floats `(x, y, z, visibility)` in **pixel** space (`x` in `[0,width]`, `y` in `[0,height]`).
- Callers (Python / JNI / Swift) convert MediaPipe normalized landmarks: `x_px = x * width`, `y_px = y * height`.
- COCO keypoint `confidence` = Blaze `visibility` clamped to `[0, 1]`.
- Person `detections[].bbox_xyxy` = axis-aligned box of mapped keypoints with `visibility >= 0.1`, clipped to the frame. `confidence` = mean of the 17 visibilities.
- Person dropped if mean visibility `< 0.25` (`LOW_CONFIDENCE` if every person is dropped; `NO_PERSON` if `num_people == 0`).
- `tracks`, `classifications`, `segments` are empty arrays.

## Offline model

Same file on all three clients (checksum must match):

`models/pose_landmarker_full.task`

Download: [pose_landmarker_full.task](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task)

```powershell
python scripts/download_pose_landmarker.py
```
