# iOS Visual Pose client

Swift + UIKit + AVFoundation + MediaPipe Tasks Vision. Same workflow as Windows/Android: **list → camera/import → prepare (person box + in/out) → analyze → player overlay + five-chapter report**. Pose landmarks go through `core_map.c` (same C ABI) and draw a COCO-17 skeleton.

This machine that authors the repo may be Windows: **open the project on a Mac** to compile. Do not treat the old `CorePoseDemo` camera logger as the product.

## Build on a Mac

```bash
cd /path/to/visual
python3 scripts/download_pose_landmarker.py
python3 scripts/generate_ios_xcodeproj.py
cd clients/ios && pod install && cd ../..
open clients/ios/VisualPose.xcworkspace   # use the workspace, not the xcodeproj
```

In Xcode:

1. Signing: select your team, bundle id `local.visual.corepose`.
2. Run on a **simulator or device**. The simulator camera is not a skier — Import a clip from Photos/Files.

MediaPipe is installed via CocoaPods (`MediaPipeTasksVision` **0.10.35** — note: 0.10.29 does not exist on CocoaPods; 0.10.35 is the closest release).

Build copies `locales/strings.json`, `content/ski/curriculum.v2.json`, and `models/pose_landmarker_full.task` into the app bundle.

## Product rules

Walk [docs/clients/mobile-parity-checklist.md](../../docs/clients/mobile-parity-checklist.md) before calling iOS done. Short version:

- Camera/Import create **Pending** clips; analysis starts only from Prepare.
- List has **no** back; other pages use a floating back into the list.
- Video is **letterboxed** (contain). Overlay uses the same transform.
- Seek to the in-point, **then** play. Download saves a stamped JPEG; Share uses `UIActivityViewController` (do not also present Safari in the same tap). Chrome icons must match `clients/windows/ui/icons/` (no SF Symbol substitutes).
- Report: 0-score rings are gray `#9E9E9E`; skill tree is a vertical list with a **white dashed** spine; black diamonds get a 1px white stroke.

## Known gap vs Windows

Video **Download** on iOS/Android is a stamped still (JPEG), not a muxed overlay MP4.
