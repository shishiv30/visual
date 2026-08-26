"""Infer one image and print CoreInferenceResult JSON."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from schemas.core_inference import SourceKind


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Core pose/detect on one image")
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--backend",
        choices=("yolo", "mediapipe"),
        default="yolo",
        help="yolo = CUDA YOLO baseline; mediapipe = offline shared Core",
    )
    parser.add_argument("--weights", default="yolo11n-pose.pt")
    parser.add_argument("--task", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args(argv)

    bgr = cv2.imread(str(args.image))
    if args.backend == "mediapipe":
        from core.mediapipe_engine import MediaPipeEngine

        result = MediaPipeEngine(args.task).infer(bgr, source_kind=SourceKind.IMAGE)
    else:
        from core.engine import CoreEngine

        result = CoreEngine(args.weights, conf_threshold=args.conf).infer(
            bgr, source_kind=SourceKind.IMAGE
        )
    text = result.model_dump_json(indent=2)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result.error is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
