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
| `native/core_map/` | Shared C ABI: BlazePose 33 → Core JSON |
| `clients/windows/` | 离线 PySide6 三界面客户端 |
| `docs/clients/` | 客户端实现规格；[移动端遗漏清单](docs/clients/mobile-parity-checklist.md) |
| `clients/android/` | Offline CameraX + MediaPipe demo |
| `clients/ios/` | Offline AVFoundation + MediaPipe demo |
| `models/` | Shared `pose_landmarker_full.task` (download script) |
| `tests/` | Contract, mapping, blaze map, optional CUDA/MediaPipe smoke tests |

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
