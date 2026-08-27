# 移动端开发遗漏清单（iOS 必查）

Windows PySide6 客户端（[`clients/windows`](../../clients/windows)）是**产品源**。完整界面与跳转见 [windows-product.md](../windows-product.md)。Android 从演示 Demo 接到同一产品时，下面每一条都实际漏过或做错过。做 iOS 时按勾选表走，不要靠「看起来差不多」。

原则：

- 行为、文案、色值、间距、图标路径以桌面为准，平台只换控件（`UIDocumentPicker` / `UIActivityViewController` / `AVPlayer`），不换产品语义。
- 原生 UI，不用 WebView。
- 先对照桌面点一遍四页，再写代码。

---

## 0. 开工前

- [ ] 读完 [windows-product.md](../windows-product.md) 全文（四页、跳转、底栏、五章报告）。
- [ ] 文案只走 `locales/strings.json`：**key = 英文显示原文**，没有 `en` 字段，至少有 `zh`。界面禁止硬编码中英文句子。
- [ ] 滑雪术语改完后走教练英文 → 翻译审核（见 `.cursor/rules/copy-coach-translator.mdc`）。
- [ ] 同一份 `models/pose_landmarker_full.task`（checksum 与 Windows/Android 一致）。
- [ ] 姿态走 `native/core_map` C ABI（BlazePose 33 → COCO-17 JSON）。**评分特征用 Blaze 33，不是 COCO-17。**
- [ ] MediaPipe 归一化坐标必须先变成像素：`x_px = x * width`，`y_px = y * height`，再交给 `core_map_from_blaze33`。
- [ ] 骨骼可见度阈值 **≥ 0.3** 才画骨；橙色骨骼、红色关节点、**绿色**检测框。
- [ ] 色值：表面 `#121212`，Camera/Import/Report `#5E35B1`，再分析 `#8E24AA`，删除 `#E94B6A`，纸色/底栏图标 `#F5F5F5`，卡片 `#1A2433`。不要另起一套「iOS 风格」调色板。
- [ ] 间距 token：页边 `PAGE_INSET` 12；章与章、播放区↔报告 `SPACE_CHAPTER` 36；同章卡片 `SPACE_PANEL` 24；段与段、文案↔图 `SPACE_TEXT` 16。禁止用 `\n` 把两段塞进同一个 label。
- [ ] 图标必须**复制桌面 SVG path**（`clients/windows/ui/icons/`），不要用 SF Symbol / Material 里「看起来像」的替代。Android 曾把赞做成铅笔、踩做成图钉、分享做成第二个下载。

---

## 1. 导航与状态机（漏了就整页对不上）

| 曾漏 | 正确行为 | iOS 怎么查 |
|------|----------|------------|
| 做成「打开即分析」 | Camera/Import 只入库 **Pending**，必须进准备页画框 + 档案后才分析 | 导入后列表应是 Pending，点卡片进 Prepare，不是直接 Player |
| 列表也有返回 | 列表**没有**返回；拍摄/准备/播放左上浮动返回（44×44，距边 12，半透明深底白箭头）一律回列表 | 首页无 Back；其它三页有，且避开刘海 Safe Area |
| Done 与 Report 分叉 | 点 **Done 卡片** 和点 **Report** 进**同一**播放+报告页 | 两个入口同一 `Player` |
| Report 永远隐藏 | 仅 `status=done` **且**有 `stage_report.json` 才显示 Report | 分析完成后按钮出现；无报告文件则隐藏 |
| Processing 仍能进播放 | 点 Processing 只弹窗：`This clip is still processing. Play it when it is done.` | 点卡片不得 push Player |
| Reanalyze 只删一半 | 清 `analysis.json`、`stage_report.json`、人框与逻辑出入点，状态回 Pending，再打开准备页 | 再分析后必须重新画框 |
| 按钮点到卡片 | 卡片操作与行点击互斥 | Report/Reanalyze/Delete 不得同时打开 Player |
| 导入超长片直接失败 | 视频 **>120s** 先 Trim（窗口 ≤2 分钟），规范化入库；原片不进库 | 长视频弹裁剪，库里只有规范后的媒体 |

状态芯片：Pending `#9E9E9E`；Processing / Done `#CE93D8`。Processing 行要转圈。失败时芯片带 `(failed, retry)`，点击仍按枚举状态走。

---

## 2. 坐标与画面（骨骼对不齐画面）

这是最容易「看起来能播、骨架漂在旁边」的一类。

- [ ] **信箱（aspect fit / contain）**：完整帧，不裁切铺满。准备画布、播放舞台、导出叠图用同一套 contain 变换。Android 曾用 fill/cover，骨架与人错位。
- [ ] Overlay 层与视频层 **同一尺寸、同一 letterbox**。不要按解码 buffer 画、按 view 显示（或反过来）。
- [ ] 点画面画人框：触摸坐标要 **unmapContain** 回源像素，再存 `seeds[]`。
- [ ] 播放暂停/拖胶片：显示的那一帧必须是 **最接近的实际帧**（iOS：`AVAssetImageGenerator` tolerance 尽量小；Android 踩过 ticker 在 `currentPosition==0` 时反复 seek、以及暂停时骨架对不上静帧）。
- [ ] 开播顺序：**先 seek 到逻辑入点，seek 完成后再 play**。不要 play 后再 seek，也不要在 position 仍为 0 时被 HUD 定时器再次 seek。
- [ ] 逻辑区间 `play_start_ms`–`play_end_ms`：只播这段；出点后停在出点，再播从入点起。寻帧不得超出该区间。原文件不裁。
- [ ] 图片片段：隐藏 Play、Speed、胶片条；画面 + 单帧 overlay。

---

## 3. 准备页

- [ ] 布局自上而下：信箱画面 → `m:ss / m:ss` → 胶片条 → 运动员两列表单 → Start analysis → 只读区间说明。
- [ ] **不要**在画面上方放长说明（Android 去掉后画面才够大）。
- [ ] 胶片：**可拖**蓝/紫入出点；**绿菱形** = 已存人框关键帧（点菱形跳到该帧）。与播放页菱形不是同一数据。
- [ ] 同一帧再画覆盖；不同时刻可多框。
- [ ] 表单：Saved profile / New；Name、Birthday（`MM/dd/yyyy`）、Height cm、Gender（Unspecified/Female/Male/Other）、Weight kg、Ski length。缺框 → `No box`；缺档案 → `Athlete info required`。
- [ ] Start analysis 成功后回列表，状态 Processing，全屏遮罩 `Analyzing pose…`。导入遮罩 `Uploading and loading…`。

---

## 4. 播放页底栏（图标错了等于功能错了）

底栏浮在视频上，**不要**做成永久占高、把画面挤小。点画面显示；播放中约 3 秒无操作隐藏；暂停/结束/图片保持显示。

左 → 右（与桌面一致）：

| 控件 | 图标来源 | 行为 | 曾漏 |
|------|----------|------|------|
| Play / Pause | `play.svg` / `pause.svg` | 逻辑区间内播 | — |
| 帧定位 | 短 clip id 文本（桌面另有 `tag.svg`） | 复制 locator JSON，Toast `Frame locator JSON copied` | 无障碍标签要翻译 |
| Speed | 文本 `1x` | 0.5 / 0.75 / 1 / 1.25 / 1.5 / 2 | — |
| Like | `thumb_up.svg` | 该**视频帧**阶段投票，浅紫选中 | 曾绘成铅笔 |
| Unlike | `thumb_down.svg` | 互斥，西瓜红 | 曾绘成图钉 |
| Bad skeleton | `reanalyze.svg`（刷新圈） | 切换该帧 `skeleton_ok` | 不要换成「警告」图标 |
| Download | `download.svg` | **另存**带叠加的文件 | 曾误走系统分享 |
| Share | `share.svg`（方框+向外箭头） | 平台菜单 + 把文件交给用户 | 曾与 Download 长得一样；曾同时弹浏览器把分享页盖掉 |

投票写入 `frame_feedback.json`。Like/Unlike 的 `zh` 仍可能是英文 key——iOS 不要照抄，先补翻译再上。

### 下载（必测）

- [ ] Download **不是** Share。桌面：保存对话框；视频导出叠图 MP4，图片 JPG。Android 目前只能存叠图 JPEG（能力缺口，iOS 能 mux 就对齐桌面 MP4）。
- [ ] 叠图含当前帧、橙色骨骼、红点、绿框（与屏幕一致）。
- [ ] 失败 Toast/告警用 `Export failed`，成功有明确反馈。
- [ ] 实测：能在「文件」/相册里打开刚存的文件，不是只弹了面板。

### 分享（必测）

- [ ] **禁止**微信 / TikTok / YouTube SDK。菜单项打开公开上传 URL（与桌面 `SHARE_TARGETS` 相同：YouTube、TikTok、X、Facebook、微博、B 站）。
- [ ] 先导出叠图（桌面还会把路径放进剪贴板）。iOS：`UIActivityViewController` 分享图片/视频。
- [ ] **不要**同一时刻抢焦点：系统分享页 + 立刻 `openURL` 会互相覆盖（Android 已踩）。二选一为主路径，另一条放 Extra 文本或等分享页关掉再开 URL。
- [ ] 分享 URI 必须可被目标 App 读（Android 要用 FileProvider + `clipData` + `FLAG_GRANT_READ_URI_PERMISSION`；iOS 用临时文件 / `NSItemProvider`，别传沙盒内别人打不开的路径）。
- [ ] 实测：菜单出现 → 选一项 → 能发出图片或打开对应上传页；失败有 `Export failed`。

---

## 5. 胶片时间轴（准备 vs 播放）

同一视觉控件，**模式不同**：

| | 准备 | 播放 |
|--|------|------|
| 裁切入出点 | 可拖 | **只展示**深紫竖条，不能改 |
| 菱形 | 绿 = 人框 | 浅紫 = 分析关键帧 `t_ms` |
| 白竖线 | 播放头 | 播放头 |
| 区间外 | 变暗 | 变暗 |
| 与视频间距 | `SPACE_PANEL` 24 | **0**（条贴在舞台下） |

点击/拖胶片寻帧；缩放与平移可做。播放页寻帧仍限制在分析时保存的入出点。

---

## 6. 报告五章

无 `stage_report.json`：只显示 `No stage report yet. Analyze a clip offline first.`

章节标题：`Summary` / `Checkpoints` / `Next steps` / `Skill tree` / `Filming and scoring`。灰字 **32px**，无「1. 2. 3.」前缀，标题下 16px 再接内容。

- [ ] 页面**不是**整页滚动：上半固定（视频+底栏+胶片），下半从 Summary 起滚。章间距 36。
- [ ] 卡片圆角、`#1A2433`。图/环/折线在卡内**整宽**；并列的环可以 2–3 列，但**同排卡片等高**，矮的底部留空，不要把环拉变形。
- [ ] 分数环：0 或缺失用**不透明灰** `#9E9E9E`，不要走紫渐变（0 分曾被画成深紫，看起来像「有分」）。正分：`#5E35B1` → `#CE93D8`。
- [ ] 奖杯按阶段绿/蓝/紫/金。雪道等级用**菱形图标、无色块底**；黑道/双黑填充 `#000000`，需要时 **1px 白描边**（深底上看不见纯黑）。不要发明第二套描边色 token。
- [ ] 证据时间是可点链接（`#4FC3F7`）：播放器**暂停并跳到该毫秒**。
- [ ] 检查点：失败优先、分低在前；文案通过用 `good` 否则 `bad`。
- [ ] **技能树**：竖向列表，圆点 + 名称，**白色虚线竖着把节点串起来**。当前 `#E1BEE7` 实心加粗，已完成 `#CE93D8` 实心加粗，未到 `#757575` 空心。不要做成无连接的纯文字，也不要只做横向 `A → B → C`（那是旧桌面，已改）。
- [ ] 免责声明与「非 FIS 分数」文案必须在；启发式刻滑再加 `Carve points are heuristics, not FIS carving scores.`

分析结束必须写 `stage_report.json`（schema 与桌面一致）。Android 曾分析完却从不写报告，导致 Report 按钮永远没有。

---

## 7. 本地数据（字段漏了就无法再分析）

`library/{clip_id}/`：

- `clip.mp4` 或 `clip.jpg`、`thumb.jpg`、`meta.json`
- 完成后：`analysis.json`、`stage_report.json`
- 投票：`frame_feedback.json`
- 运动员：应用目录 `athletes.json`（不是写进 clip）

`meta.json` 至少包含：`clip_id`、`created_at`、`display_name`（`MM/dd/yyyy-HH:mm`）、`duration_ms`、宽高 fps、`kind`、`status`、`seeds` / `seed_box`、`play_start_ms` / `play_end_ms`、`athleteKey`。

- [ ] 列表名用本地时区时间戳，不要用文件名。
- [ ] 时长 `m:ss`，图片 `--`。
- [ ] Reanalyze 后这些分析产物必须真正删掉。

---

## 8. 平台工程（装不上 / 跑不起来）

Android 已踩、iOS 对应项：

| Android | iOS 对应 |
|---------|----------|
| native `.so` **16 KB 页对齐**，S26 否则装了闪退 | 用同一份 `core_map.c`；注意 bitcode/链接，真机 arm64 |
| 不要打 `armeabi-v7a` | 不要只做模拟器 x86_64 就当完成；真机跑一遍 |
| 模型打进 assets，缺模型构建应失败 | `.task` 进 bundle，启动时能 load |
| Camera 运行时权限 + 文案键 | `Info.plist` 相机/相册说明走 i18n 键，不要硬编码一句英文 |
| 模拟器虚拟场景不是人，必须 **Import 真实雪道片** 测骨架 | 模拟器摄像头同样不能当验收；用相册导入滑雪片 |
| 文件管理器旁路安装不可靠，要用 adb | 用 Xcode / `ios-deploy`，不要只靠「隔空投送 ipa」当唯一路径 |
| FileProvider `cache/share` + `files/library` | App Group / tmp 导出目录要在分享前复制到可访问位置 |

GPU 推理失败要能回落到 CPU（模拟器尤其如此）。

---

## 9. 验收时必须亲手点的路径

不要只看截图。至少：

1. 导入一段滑雪视频 → Pending → 准备画框 + 入出点 + 档案 → 分析 → Done。
2. 点卡片与点 Report 都进播放页；Processing 被拦截。
3. 播放：信箱、骨架贴人、入点起播、拖胶片暂停帧与骨架一致。
4. 底栏：赞/踩/骨骼差可切换；**Download 能存开**；**Share 菜单 + 能发出图或打开上传页**。
5. 报告五章都在；0 分环是灰的；技能树有竖向白虚线；点证据时间会跳帧。
6. Reanalyze 后必须重新准备。
7. 切语言：四页文案与报告都变（包括底栏无障碍标签）。
8. 图片 clip 与视频 clip 各测一条。

对照物：同一 clip 在 Windows 上的播放页和报告。iOS 应能并排指着说「一样」，而不是「差不多」。

---

## 10. 已知平台差异（不要假装没有）

| 项 | Windows | Android 现状 | iOS 目标 |
|----|---------|--------------|----------|
| 视频 Download | 叠图 MP4 | 仅 JPEG 静帧 | 能 mux 则 MP4，否则在 UI 上与 Android 一样诚实 |
| Share | 剪贴板路径 + 打开上传 URL | 系统分享图 + Extra 里放 URL（避免与浏览器抢焦点） | 优先 `UIActivityViewController`；若再开 URL，错开呈现 |
| 准备页提示条 | 桌面有一句操作说明 | 已去掉以增大画面 | 跟 Android：不要挡画面 |

这些差异要写进该端 README，不要 silently 少功能却用同一句「Download」。

---

## 参考

- 产品：[windows-product.md](../windows-product.md)
- 桌面实现笔记：[windows-client.md](windows-client.md)
- 骨骼映射：[../research/blazepose-coco17.md](../research/blazepose-coco17.md)
- 桌面图标：`clients/windows/ui/icons/`
- 文案：`locales/strings.json`
- Android 对照实现：`clients/android/`（Kotlin，无 WebView）
