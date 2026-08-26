# Benchmarks

Thin harness: load a model, time warm-up + steady inference, write JSON. Not a product pipeline.

## Environment recorded on 2026-08-22

- GPU: NVIDIA GeForce RTX 5090 Laptop GPU, 24463 MiB
- Driver: 592.02
- Python: 3.12.12
- PyTorch: 2.11.0+cu128

## Samples

Images are downloaded once into `benchmarks/samples/` from the public COCO 2017 val set (person-centric files):

- `000000000139.jpg`
- `000000000724.jpg`
- `000000000785.jpg`

If download fails, the harness synthesizes solid-color frames at the target resolution so timing still runs.

## Run

```powershell
python -m pip install -r benchmarks/requirements.txt
python benchmarks/run.py --preset default
python benchmarks/run.py --preset contrast
```

`--preset default` → `yolo11n-pose.pt`  
`--preset contrast` → `yolo11n.pt`  

Both run 720p and 1080p, batch size 1, with Ultralytics `imgsz` equal to the target height so the two resolutions are not both folded to 640. 10 warm-up + 50 timed iterations, then write `benchmarks/results/<preset>-<timestamp>.json`.

Peak CUDA memory uses `torch.cuda.max_memory_allocated` after a reset at the start of each resolution.
