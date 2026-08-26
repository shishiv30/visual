# Windows 客户端

离线三界面：列表 / 拍摄-上传 / 播放叠加骨骼。规格见 [`docs/clients/windows-client.md`](../../docs/clients/windows-client.md)。

## 依赖

- Python 3.12+
- [ffmpeg](https://ffmpeg.org/) 在 PATH 中（没有则回退 OpenCV 转码，兼容性较差）
- `models/pose_landmarker_full.task`：`python scripts/download_pose_landmarker.py`
- 拍摄/上传后条目为 **待定**；点击后进入准备页：进度条定位、多帧拖框、逻辑入/出点，确认才分析
- 处理完毕后再点条目查看 overlay
- **刷新** 会清分析结果、框选和逻辑区间并回到待定
- 新导入视频高度 > 720 会按比例压到 720p（已入库 1080 片需重新导入）
- 骨骼更稳：在跳变附近再框 1–2 次，裁掉无关头尾后再分析；进度条 `f`/`p` 可对出错帧

```powershell
cd d:\AI\visual
python -m pip install -r clients/windows/requirements.txt
python -m pip install -r requirements-mediapipe.txt
python scripts/download_pose_landmarker.py
python -m clients.windows.app
```

库目录：`%LOCALAPPDATA%\visual\library\`（可用 `VISUAL_LIBRARY` 覆盖）。
