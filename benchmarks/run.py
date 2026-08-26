"""CUDA timing harness for Core research (batch size 1)."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
RESULTS = ROOT / "results"

COCO_FILES = (
    "000000000139.jpg",
    "000000000724.jpg",
    "000000000785.jpg",
)
COCO_BASE = "http://images.cocodataset.org/val2017/"

def _imgsz_for_height(height: int) -> int:
    return ((height + 31) // 32) * 32


def _download_samples() -> list[Path]:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name in COCO_FILES:
        dest = SAMPLES / name
        if not dest.exists():
            url = COCO_BASE + name
            try:
                urllib.request.urlretrieve(url, dest)
            except OSError:
                img = np.zeros((640, 640, 3), dtype=np.uint8)
                img[:] = (40, 80, 120)
                cv2.imwrite(str(dest), img)
        paths.append(dest)
    return paths


def _resize(bgr: np.ndarray, height: int) -> np.ndarray:
    h, w = bgr.shape[:2]
    scale = height / float(h)
    return cv2.resize(bgr, (int(w * scale), height), interpolation=cv2.INTER_LINEAR)


def _gpu_meta() -> dict[str, Any]:
    if not torch.cuda.is_available():
        return {"cuda": False}
    props = torch.cuda.get_device_properties(0)
    return {
        "cuda": True,
        "device_name": torch.cuda.get_device_name(0),
        "total_memory_bytes": int(props.total_memory),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
    }


def _run_resolution(
    model: YOLO,
    frames: list[np.ndarray],
    warmup: int,
    iters: int,
    imgsz: int,
) -> dict[str, Any]:
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()

    for i in range(warmup):
        model.predict(frames[i % len(frames)], verbose=False, device=0, imgsz=imgsz)
    torch.cuda.synchronize()

    latencies_ms: list[float] = []
    for i in range(iters):
        frame = frames[i % len(frames)]
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        model.predict(frame, verbose=False, device=0, imgsz=imgsz)
        torch.cuda.synchronize()
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)

    peak_bytes = int(torch.cuda.max_memory_allocated())
    mean_ms = float(sum(latencies_ms) / len(latencies_ms))
    return {
        "height": int(frames[0].shape[0]),
        "width": int(frames[0].shape[1]),
        "imgsz": imgsz,
        "warmup": warmup,
        "iters": iters,
        "latency_ms_mean": mean_ms,
        "latency_ms_p50": float(sorted(latencies_ms)[len(latencies_ms) // 2]),
        "fps": 1000.0 / mean_ms if mean_ms > 0 else 0.0,
        "peak_memory_bytes": peak_bytes,
        "peak_memory_mib": peak_bytes / (1024 * 1024),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Core vision CUDA micro-benchmark")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="default")
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iters", type=int, default=50)
    args = parser.parse_args(argv)

    if not torch.cuda.is_available():
        print("CUDA is required", file=sys.stderr)
        return 1

    weights = PRESETS[args.preset]
    sample_paths = _download_samples()
    images = [cv2.imread(str(p)) for p in sample_paths]
    if any(im is None for im in images):
        print("failed to load samples", file=sys.stderr)
        return 1

    model = YOLO(weights)
    model.to("cuda")

    payload: dict[str, Any] = {
        "preset": args.preset,
        "weights": weights,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "gpu": _gpu_meta(),
        "batch_size": 1,
        "resolutions": [],
    }

    for height in (720, 1080):
        frames = [_resize(im, height) for im in images]
        imgsz = _imgsz_for_height(height)
        payload["resolutions"].append(
            _run_resolution(model, frames, args.warmup, args.iters, imgsz)
        )

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS / f"{args.preset}-{stamp}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest = RESULTS / f"{args.preset}-latest.json"
    latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
