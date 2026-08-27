# Visual Pose iOS client — design

**Date:** 2026-08-27  
**Status:** Approved to implement as sources-on-Windows (no local Xcode).  
**Product source:** Windows PySide6; mobile pitfalls in [mobile-parity-checklist.md](../../clients/mobile-parity-checklist.md).

## Goal

Replace the live-camera demo in `clients/ios` with the same four-page Visual Pose app as Android: **list → capture/import → prepare → analyze → player + five-chapter report**. Native UIKit only. After UI lands, walk the parity checklist.

## Approach chosen

**UIKit + UIView, port Android modules 1:1** (not SwiftUI, not expanding `PoseViewController`).

| Option | Trade-off |
|--------|-----------|
| **UIKit port (chosen)** | Matches Android custom views (letterbox overlay, filmstrip, skill tree). Heavier files, fewer SwiftUI layout surprises. |
| SwiftUI + UIViewRepresentable | List/forms nicer; player/overlay/filmstrip still need UIView. Hybrid cost without product gain. |
| Grow the camera demo | Fastest to a skeleton overlay; never becomes the product. |

## Architecture

```
clients/ios/VisualPose.xcodeproj
clients/ios/VisualPose/          # app + logic (Swift)
clients/ios/VisualPoseTests/     # XCTest for OverlayMath, ClipRange, I18n, Library, PlayerExport, SkillTree
native/core_map                  # C via bridging header (existing Package.swift still valid)
```

- **RootViewController** hosts four pages (no UINavigationController back on list). Capture / prepare / player get a floating back (44×44, 12pt inset, safe area).
- **Logic** ports Android Kotlin (`I18n`, `Library`, `Athletes`, `ClipRange`, `OverlayMath`, `Assess`, …) using `JSONSerialization` instead of `org.json`.
- **Pose:** MediaPipe Tasks Vision 0.10.29 via SPM; landmarks × width/height → `core_map_from_blaze33`; GPU then CPU fallback (simulator prefers CPU).
- **Ingest:** `AVAssetExportSession` (≤720p, 30fps, ≤120s, no audio). Images JPEG height 720.
- **Player:** `AVPlayer` + overlay UIView sharing **contain/letterbox** math. Seek to in-point **then** play. Paused frame via `AVAssetImageGenerator` (zero tolerance).
- **Download:** save stamped JPEG (UIActivity / Files). Video overlay MP4 is a known gap unless mux is added later — README must say JPEG still.
- **Share:** platform menu then `UIActivityViewController` with image + URL as extra text. Do **not** present Safari in the same turn.
- **Resources (copy at build):** `locales/strings.json`, `content/ski/curriculum.v2.json`, `models/pose_landmarker_full.task`, desktop SVG paths as `UIBezierPath` (not SF Symbols).
- **i18n:** English key catalog; `UserDefaults` language; no hardcoded UI copy.

## Out of scope

Compiling or installing from this Windows machine. Muxed overlay MP4. WeChat/TikTok/YouTube SDKs. WebView.

## Test

XCTest for pure logic (same cases as Android unit tests). UI verification on Mac: walk [mobile-parity-checklist.md](../../clients/mobile-parity-checklist.md) sections 1–9.
