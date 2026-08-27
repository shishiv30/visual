# Visual Pose iOS Implementation Plan

> **For agentic workers:** Implement task-by-task. Windows cannot run `xcodebuild`; write sources and XCTest anyway.

**Goal:** Ship a UIKit Visual Pose iOS app that matches Windows/Android workflow, then review [mobile-parity-checklist.md](../../clients/mobile-parity-checklist.md).

**Architecture:** Four pages in `RootViewController`. Logic ports Android Kotlin. MediaPipe + `core_map` C. Letterbox overlay math. No WebView.

**Tech Stack:** Swift 5.9, iOS 16, UIKit, AVFoundation, MediaPipeTasksVision 0.10.29, `native/core_map`.

## Global Constraints

- Product source: `docs/windows-product.md`
- Copy: `I18n.t("English key")` from bundled `strings.json`
- Colors/spacing: `Theme.swift` tokens matching Android `ReportTheme`
- Icons: desktop SVG paths, never SF Symbols for chrome
- Overlay: `OverlayMath.contain`, `MIN_VIS = 0.3`
- Download ≠ Share; share must not race `openURL`

---

### Task 1: Core logic + Xcode project

**Files:** `clients/ios/VisualPose/**`, `clients/ios/VisualPose.xcodeproj`, tests under `VisualPoseTests/`

Port Android: I18n, OverlayMath, ClipRange, TimelineMath, Library, Athletes, PlayerExport, SkillTree layout, ReportTheme.

### Task 2: Analysis pipeline

Port Curriculum, SportsMath, SportsSignals, Posture, PersonRoi, PoseFilter, PoseTrack, CoreJson, AnalysisJson, PoseMapper, PoseEngine, VideoPose, Assess, StageReport, FrameFeedback.

### Task 3: UI pages

List, Capture, Prepare (seed canvas + filmstrip + athlete form), Player (chrome, overlay, report), loading overlay, floating back.

### Task 4: Parity review

Walk the checklist; document remaining gaps in `clients/ios/README.md`.
