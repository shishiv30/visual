# iOS offline pose demo

Swift + AVFoundation + MediaPipeTasksVision. Landmarks (pixel space) go through `core_map_from_blaze33` and come back as Core JSON (`backend_id=mediapipe_pose`).

## Xcode

1. New iOS App target using the sources under `clients/ios/CorePoseDemo/`.
2. Add `native/core_map/core_map.c` + `core_map.h` to the target (or the local Swift package in `native/core_map/Package.swift`).
3. Set Objective-C bridging header to `CorePoseDemo-Bridging-Header.h`.
4. SPM: `https://github.com/google-ai-edge/mediapipe-samples` is not required; use CocoaPod/SPM `MediaPipeTasksVision` 0.10.x.
5. Copy `models/pose_landmarker_full.task` into the app bundle.

Same `.task` checksum as Windows and Android.
