# Performance (this machine)

Recorded 2026-08-22. Raw JSON: `benchmarks/results/default-latest.json`, `benchmarks/results/contrast-latest.json`.

## Host

| Item | Value |
| --- | --- |
| GPU | NVIDIA GeForce RTX 5090 Laptop GPU (24 GB) |
| Driver | 592.02 |
| PyTorch | 2.11.0+cu128 |
| CUDA runtime (PyTorch) | 12.8 |
| Ultralytics | 8.4.126 |
| Protocol | batch 1; 10 warm-up + 50 timed; `imgsz` aligned to 32 (736 / 1088 for 720 / 1080 request) |
| Inputs | three COCO val2017 JPEGs resized so height is 720 or 1080 |

## Results

| Preset | Weights | Height | Mean ms | p50 ms | FPS | Peak MiB |
| --- | --- | --- | --- | --- | --- | --- |
| default | yolo11n-pose.pt | 720 | 7.04 | 7.00 | 142 | 67 |
| default | yolo11n-pose.pt | 1080 | 9.82 | 9.85 | 102 | 95 |
| contrast | yolo11n.pt | 720 | 6.70 | 6.65 | 149 | 66 |
| contrast | yolo11n.pt | 1080 | 9.31 | 9.26 | 107 | 94 |

Pose head costs about 0.3–0.5 ms versus detect-only at the same `imgsz` on this GPU. Both stay above 100 FPS at 1080p batch 1, with peak allocation under 100 MiB (model + activations; not counting the full CUDA context).

## Interpretation

On this laptop GPU, nano YOLO is not the latency bottleneck for a single 1080p stream. Selection is driven by **output completeness** (pose vs boxes), **install path**, and **AGPL**, not by FPS. TensorRT was not measured; it is the next optimization if a smaller GPU becomes the target.
