# Visual Pose — Windows 产品说明

本文档以 Windows PySide6 客户端（[`clients/windows`](../clients/windows)）为产品源。文案键均为英文显示原文，经 `t("English key")` 翻译。色值：表面 `#121212`，主色 `BLUE`=`#5E35B1`，再分析 `#8E24AA`，删除 `#E94B6A`，通过/菱形浅紫 `#CE93D8`，纸色 `#F5F5F5`。

应用窗口标题：`Visual Pose — Windows`。四页叠在 `QStackedWidget` 中，默认 **列表**。

---

## 1. 一共四个界面

| 页 | 类 | 何时出现 |
|----|----|----------|
| 列表 List | `ListPage` | 启动首页；拍摄/导入完成后；分析入队后；任意页点返回 |
| 拍摄 Capture | `CapturePage` | 点 Camera；点 Import 时也会先切到此页再弹出文件框 |
| 准备 Prepare | `PreparePage` | 点 **Pending** 卡片，或点 **Reanalyze** |
| 播放+报告 Player | `PlayerPage` | 点 **Done** 卡片，或点 **Report**（二者进入同一页） |

列表 **没有** 返回键。拍摄 / 准备 / 播放左上角各有一颗 **浮动返回**（44×44，距边 12px，半透明深底，白箭头 `Back`），一律回到列表。

---

## 2. 界面跳转

```
列表
  ├ Camera ──► 拍摄（摄像头）── 停止录像并入库 ──► 列表（Pending）
  ├ Import ──► 拍摄页（隐藏预览条）── 文件框
  │              ├ 取消 ──► 列表
  │              └ 成功 ──► 列表（Pending）
  │              └ 视频 >120s ──► Trim 对话框 ── 入库或取消
  ├ 点 Pending 卡片 ──► 准备
  │                      ├ 浮动返回 ──► 列表
  │                      └ Start analysis ──► 列表（Processing，后台分析）
  ├ 点 Processing 卡片 ──► 仅弹窗，留在列表
  │     文案：Processing / This clip is still processing. Play it when it is done.
  ├ 点 Done 卡片 ──► 播放+报告
  ├ Report（仅 Done 且已有 stage_report.json）──► 播放+报告（与点卡片相同）
  ├ Reanalyze（Processing 时隐藏）──► 清空分析/报告/框选 ──► 准备
  └ Delete ──► 确认后删本地文件；若正在播放或准备该片则回列表
播放 / 拍摄 浮动返回 ──► 列表
```

拍摄或导入 **不会自动分析**。入库后状态为 Pending，用户必须打开准备页画人框、填档案、点 Start analysis。

分析中：列表卡片转圈；整窗遮罩 `Analyzing pose…`。导入中遮罩 `Uploading and loading…`。

失败时状态芯片为 `{status} (failed, retry)`，点击仍按枚举状态走（仍为 processing 则继续拦截）。

---

## 3. 列表页

**顶栏（左→右）**

| 控件 | 位置 | 颜色 | 文案键 | 行为 |
|------|------|------|--------|------|
| Camera | 左 | `#5E35B1` 底、白图标字 | `Camera` | 打开拍摄 |
| Import | Camera 右侧 | 同 Camera | `Import` | 打开导入 |
| Language 标签 | 右 | 浅字 | `Language` | 仅标签 |
| 语言下拉 | 最右 | 深色框 | 显示 English / 中文 / … | 切换语言并重绘全部页；播放页会按新语言重算报告文案 |

**卡片（上→下滚动，间距 24px）**

左：圆角缩略图 128×72（无图时 `No preview`）。中：标题 `MM/dd/yyyy-HH:mm`、时长 `m:ss`（图片 `--`）、状态芯片。右：操作按钮。

| 状态 | 芯片颜色 | 行点击 | Report | Reanalyze | Delete | 转圈 |
|------|----------|--------|--------|-----------|--------|------|
| Pending | `#9E9E9E` | 准备 | 隐藏 | 显示 | 始终 | 否 |
| Processing | `#CE93D8` | 弹窗拦截 | 隐藏 | 隐藏 | 始终 | 是 |
| Done 无报告文件 | `#CE93D8` | 播放 | 隐藏 | 显示 | 始终 | 否 |
| Done 有 `stage_report.json` | `#CE93D8` | 播放 | **显示** → 播放 | 显示 | 始终 | 否 |

- Report：`#5E35B1`，键 `Report`
- Reanalyze：`#8E24AA`，键 `Reanalyze`（清 `analysis.json`、`stage_report.json`、人框与逻辑出入点，状态改 Pending）
- Delete：`#E94B6A`，键 `Delete`；确认 `Delete this clip and its local files? This cannot be undone.`

点按钮不会同时触发卡片点击。

---

## 4. 拍摄页

预览铺满；底栏 **Record / Stop**（默认紫底，无额外着色）| **Import…**（`#5E35B1`）。浮动返回在左上。

| 控件 | 文案键 | 行为 |
|------|--------|------|
| Record / Stop | `Record` / `Stop` | 录像；停止后规范化入库为 Pending |
| Import… | `Import…` | 选视频或图片入库 |
| 预览空闲 | `Camera preview` | 实时画面 |
| 无权限 | `Camera permission required` 等 | 引导授权 |
| 浮动返回 | `Back` | 若在录则先停，关摄像头，回列表 |

从列表点 Import 时：预览、Record、Import…、返回均隐藏，只走文件框。视频超过 2 分钟弹出 `Trim video (max 2 minutes)`（In / Out 滑条，OK / Cancel）。

---

## 5. 准备页

自上而下：**画面（居中信箱）→ 当前时间 `m:ss / m:ss` → 胶片时间轴 → 运动员表单 → Start analysis → 区间说明**。浮动返回左上。桌面另有一条操作提示（手机版已按产品要求去掉）。

| 控件 | 文案键 | 行为 |
|------|--------|------|
| 画布 | 绿框 | 拖拽画人框；同一帧再画覆盖；不同时刻可多框（绿菱形） |
| 时间轴 | — | 点胶片寻帧；拖 **蓝/紫** 入出点裁逻辑区间（不改原文件）；点绿菱形跳到已存框；Shift+滚轮 / 捏合缩放 |
| Saved profile | `Saved profile` / `New profile` | 载入本地 `athletes.json` |
| Name \| Birthday | `Name` / `Birthday` / `MM/dd/yyyy` | 两列 |
| Height \| Gender | `Height` / ` cm` / `Gender` / `Unspecified` `Female` `Male` `Other` | |
| Weight \| Ski length | `Weight` / ` kg` / `Ski length` | |
| Start analysis | `Start analysis` | 至少一框 + 姓名身高体重板长；否则 `No box` 或 `Athlete info required` |
| 区间 | `In {lo:.1f}s → out {hi:.1f}s (logical, original file unchanged)` | 只读 |

图片片段：隐藏时间轴。成功后状态 Processing，回列表排队。

---

## 6. 播放+报告页（与截图一致）

页面 **不是** 整页滚动。垂直两段（间距 `SPACE_CHAPTER` 36px，页边距 12px）：

1. **上半固定：** 视频舞台 + 底栏浮动控件 + 其下胶片条  
2. **下半滚动：** 报告，从章节标题 **Summary** 起滚  

浮动返回仍叠在整页左上。

### 6.1 视频

- 信箱（完整帧，不裁切铺满）。
- 叠加：COCO-17 **橙色** 骨骼、**红色** 关节点、检测框 **绿色** 矩形。
- 左上 HUD：短 clip id、当前/总时长、帧号、姿态序号（导出时同样烧进画面）。
- 点画面显示底栏；播放中 3 秒无操作自动隐藏底栏；暂停/结束/图片保持显示。

### 6.2 底栏控件（左→右，图标 `#F5F5F5`）

| 控件 | 文案键 | 行为 |
|------|--------|------|
| Play / Pause | `Play` / `Pause` | 在逻辑入出点内播放；播完从入点再起 |
| 帧定位 | `Copy frame locator` | 复制 JSON；提示 `Frame locator JSON copied` |
| Speed | `Speed` | 0.5 / 0.75 / 1 / 1.25 / 1.5 / 2 |
| Like | `Like` | 该视频帧阶段投票，浅紫选中 |
| Unlike | `Unlike` | 互斥投票，西瓜红 |
| Bad skeleton | `Bad skeleton` | 切换该帧 `skeleton_ok`，灰 |
| Download | `Download` | 导出带叠加的 JPG 或 MP4 |
| Share | `Share` | 菜单打开 YouTube / TikTok / X / Facebook / 微博 / B 站公开上传页（先导出再打开网址） |

投票写入 `frame_feedback.json`。图片片段：隐藏 Play、Speed、时间轴。

### 6.3 胶片时间轴（播放页）

与准备页同一控件，但 **`set_trim_enabled(False)`**：

- 刻度尺 + 缩略图条（约 56px 高、格宽约 88px）。
- 逻辑入出点外变暗；入出点仍画 **深紫竖条**（仅展示，**不能再拖改裁切**）。
- **浅紫菱形** = 分析关键帧（`t_ms`），点击跳转。
- **白竖线** = 播放头；点击/拖胶片寻帧；缩放与平移可用。
- 寻帧限制在分析时保存的 `play_start_ms`–`play_end_ms`。

准备页菱形是人框关键帧；播放页菱形是姿态分析帧。

---

## 7. 报告：五个章节

数据：`assess_clip(analysis)` → `stage_report.json`（schema `2.1.0`）。无文件时只显示：`No stage report yet. Analyze a clip offline first.`

章节标题键：`Summary` / `Checkpoints` / `Next steps` / `Skill tree` / `Filming and scoring`。卡片底 `#1A2433`，标题灰、无编号。分数环颜色由 0→100 从 `#5E35B1` 过渡到 `#CE93D8`。奖杯按阶段：绿/蓝/紫/金。雪道等级用菱形图标（双黑为两枚黑菱，无色块底）。

证据时间可点，播放器 **暂停并跳到该毫秒**。

### 第 1 章 Summary

顺序：

1. 整宽卡：奖杯 + `stage_name`；可选 `stage_focus`。
2. 整宽卡：地形菱形 + `Suggested trail rating: {trail} · {Passed this level… 或 Not passed — train the lowest-scoring checkpoint.}`；可选地形说明。
3. 两列环：`Heuristic score (0-100, not FIS)`。
4. 两列环：`Confidence`（置信度×100）。
5. 若有姿态分：说明 `Four posture scores are coach heuristics…`，再四环 `Stability` `Coordination` `Control` `Balance`（两列）。
6. 各检查点环（失败优先、分低在前；≥5 个时三列否则两列）。
7. 整宽：`Stability over time (time × frame score)` 折线；点击可跳帧。

### 第 2 章 Checkpoints

每检查点一卡：环 + 通过用 `good` / 否则 `bad` + 可选证据时间链接。

### 第 3 章 Next steps

- **已通过：** `Passed this level. Choose a next level on the skill tree.` + 每个下一阶段计划卡（奖杯、Drills、Training venue）。
- **未通过：** 未通过说明；`Weakest checkpoint` + 差评；`Problem frame` 链接；最弱检查点练习；其余 FAIL 的练习卡。

### 第 4 章 Skill tree

一条竖向路径：节点用圆点表示，中心有白色虚线串起来；当前 `#E1BEE7` 加粗实心、已完成 `#CE93D8` 加粗实心、未到 `#757575` 空心。若已通过且有下一关：`Next stage: …`。

### 第 5 章 Filming and scoring

免责声明；若为刻滑启发式再加 `Carve points are heuristics, not FIS carving scores.`；拍摄步骤项目符号列表。

---

## 8. 本地文件

`library/{clip_id}/`：`clip.mp4` 或 `clip.jpg`、`thumb.jpg`、`meta.json`、`analysis.json`、`stage_report.json`、`frame_feedback.json`。运动员档案在用户目录 `athletes.json`。

分析使用 MediaPipe Pose → BlazePose 33 → `libcore_map` 得到 COCO-17；评分特征来自 **Blaze 33**，不是 COCO-17。

移植到 Android / iOS 时，先对照 [移动端开发遗漏清单](clients/mobile-parity-checklist.md)（Windows 为产品源，清单收录移植中实际踩过的坑）。
