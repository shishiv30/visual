"""Download the shared offline Pose Landmarker .task (same file for Win/iOS/Android)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
DEST = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_full.task"


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {URL}")
    urllib.request.urlretrieve(URL, DEST)
    print(f"wrote {DEST} ({DEST.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
