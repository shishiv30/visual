# core_map

C99 shared library: BlazePose 33 landmarks → Core JSON (`backend_id=mediapipe_pose`).

```powershell
cmake -S native/core_map -B native/core_map/build
cmake --build native/core_map/build --config Release
python -m pytest tests/test_blaze_map.py
```

ABI: `core_map_from_blaze33` / `core_map_free` in `core_map.h`.
