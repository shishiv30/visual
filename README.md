# visual

Computer vision research workspace for motion tracking and analysis.

Research docs plus a runnable **Core** engine: YOLO11n-pose → versioned `CoreInferenceResult`. App plugins and client UI are still out of scope.

## Layout

| Path | Role |
| --- | --- |
| `docs/research/` | Landscape, selection matrix, API draft, measured performance |
| `docs/superpowers/specs/` | Phase design spec |
| `benchmarks/` | Thin CUDA timing harness |
| `schemas/` | Versioned Core JSON Schema / Pydantic |
| `core/` | Inference engine and CLI (YOLO + MediaPipe) |
| `content/ski/knowledge/kb.v1.json` | Bilingual ski knowledge pack (16 `kb_stage`s + module slices) imported from the wiki curriculum by `scripts/import_ski_knowledge.py`; `--check` verifies it is current |
| `native/core_map/` | Shared C ABI: BlazePose 33 → Core JSON |
| `clients/windows/` | 离线 PySide6 三界面客户端 |
| `docs/clients/` | 客户端实现规格；[移动端遗漏清单](docs/clients/mobile-parity-checklist.md) |
| `clients/android/` | Offline CameraX + MediaPipe demo |
| `clients/ios/` | Offline AVFoundation + MediaPipe demo |
| `models/` | Shared `pose_landmarker_full.task` (download script) |
| `tests/` | Contract, mapping, blaze map, optional CUDA/MediaPipe smoke tests |

## Running the clients (for testing)

### Desktop

Note: currently Windows-only (PySide6, `%LOCALAPPDATA%` paths, `.ps1` scripts).

```powershell
cd d:\AI\visual
python -m pip install -r clients/windows/requirements.txt
python -m pip install -r requirements-mediapipe.txt
python scripts/download_pose_landmarker.py
python -m clients.windows.app
```

Requires `ffmpeg` in PATH. Library data stored at `%LOCALAPPDATA%\visual\library\` (override with `VISUAL_LIBRARY`). See [clients/windows/README.md](clients/windows/README.md) for full details.

### Android

Build + install on a connected device:

```powershell
cd d:\AI\visual
python scripts/download_pose_landmarker.py
powershell -File scripts/build_android_apk.ps1
```

Or run on an emulator:

```powershell
cd d:\AI\visual
powershell -File scripts/run_android_emulator.ps1
```

Manual install / logs / pushing a test clip:

```powershell
adb install -r clients\android\app\build\outputs\apk\debug\app-debug.apk
adb logcat -s CorePose:I *:E
adb push path\to\ski.mp4 /sdcard/Download/ski.mp4
```

Alternative: open `clients/android` in Android Studio and run. Prerequisites: JDK 17, Android SDK API 35, NDK 28.1+, `adb`/`ANDROID_HOME`. See [clients/android/README.md](clients/android/README.md) for full details.

### iOS

```bash
cd /path/to/visual
python3 scripts/download_pose_landmarker.py
python3 scripts/generate_ios_xcodeproj.py
cd clients/ios && pod install && cd ../..
open clients/ios/VisualPose.xcworkspace   # use the workspace, not the xcodeproj
```

Then in Xcode: set signing team, bundle id `local.visual.corepose`, run on simulator or device (simulator has no camera — import a test clip via Photos/Files instead). See [clients/ios/README.md](clients/ios/README.md) for full details.

## Quick start (Core)

```powershell
python -m pip install -r benchmarks/requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest
python -m core.cli benchmarks\samples\000000000139.jpg --out result.json
python scripts/download_pose_landmarker.py
python -m core.cli benchmarks\samples\000000000139.jpg --backend mediapipe
python -m pip install -r clients/windows/requirements.txt
python -m clients.windows.app
```

## Quick start (benchmarks)

Requires Python 3.12+, NVIDIA GPU, and CUDA-enabled PyTorch.

```powershell
python -m pip install -r benchmarks/requirements.txt
python benchmarks/run.py --preset default
```

See [benchmarks/README.md](benchmarks/README.md).
