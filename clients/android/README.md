# Android Visual Pose client

Kotlin + CameraX + MediaPipe Tasks Vision. Same workflow as the Windows client: **list → camera/import → prepare (person box + in/out) → analyze → player overlay**. Pose landmarks go through `libcore_map.so` (same C as Windows/iOS) and draw a COCO-17 skeleton.

The debug APK ships **arm64-v8a** (S26) and **x86_64** (Windows emulator). Native libs are 16 KB page-aligned. Do not ship `armeabi-v7a`.

## Workflow (matches desktop)

1. **List** — Camera and Import (deep purple, white icon + label), Language on the right. Clip cards: thumb, `MM/dd/yyyy-HH:mm`, duration `m:ss`, status Pending / Processing / Done, Report (when a stage report exists), Reanalyze, Delete.
2. Camera or Import copies media into the local library as **Pending**. Nothing is analyzed yet.
3. Tap a pending card → **Prepare**: seek, draw a person box, Mark in / Mark out, enter athlete name, **Start analysis**.
4. List shows **Processing** with a spinner; opaque overlay **Analyzing pose…**
5. Analysis writes BlazePose 33 joints plus `stage_report.json` (schema **3.0.0**). Tap **Done** or **Report** → **Player**: letterboxed video, COCO-17 overlay, green bbox, filmstrip (in/out display-only), chrome, and a twelve-chapter stage report (empty chapters hidden) that scrolls under the video.
6. **Reanalyze** clears analysis and the report, then opens Prepare again.

Clips live under the app files dir: `library/{clip_id}/clip.mp4`, `thumb.jpg`, `meta.json`, `analysis.json`, `stage_report.json`.

Download saves a stamped still (skeleton + green box) through the system save dialog. This build does not mux an overlay MP4. Share stamps the still, opens the Android share sheet, then the same public upload URLs as desktop (YouTube, TikTok, X, Facebook, Weibo, Bilibili).

Display copy comes from `locales/strings.json` (English key → `zh` and other langs).

Shared content with desktop (copied into APK assets at build): `content/ski/curriculum.v3.json`, `content/ski/knowledge/*.json`, `locales/strings.json`, `models/pose_landmarker_full.task`. Feature gap matrix: [`docs/clients/desktop-android-parity-v3.md`](../../docs/clients/desktop-android-parity-v3.md).

## Prerequisites (Windows PC)

- JDK 17 (`JAVA_HOME`, or Microsoft/Temurin 17 in Program Files / `%LOCALAPPDATA%\jdk-17`)
- Android SDK with **API 35**, **NDK 28.1+**, and **platform-tools** (`adb`)
- `models/pose_landmarker_full.task` (the build script downloads it if missing)

Set `ANDROID_HOME`, or install Android Studio so the SDK is at `%LOCALAPPDATA%\Android\Sdk`. The first build writes `clients/android/local.properties` (not committed).

## Debug on the emulator first

Windows x64 cannot run the S26 ARM64 slice in a typical emulator, so debug builds also include `x86_64`. Create an API 35 Google APIs AVD, boot it, install, and launch:

```powershell
cd d:\AI\visual
powershell -File scripts/run_android_emulator.ps1
```

That script installs the `emulator` package and `system-images;android-35;google_apis;x86_64` if missing, creates AVD `VisualPoseApi35` (Pixel 7), starts it with the **virtual scene** camera (a 3D room — PC webcam is often blocked on Windows), waits for boot, then builds/installs and starts **Visual Pose**. Grant the emulator camera permission if the system dialog still appears.

Logs:

```powershell
adb logcat -s CorePose:I *:E
```

The virtual scene is a room, not a person. Use **Import** on the list, pick a ski clip, then tap the pending card, draw a box around the skier, and start analysis.

To put a clip on the emulator:

```powershell
adb push path\to\ski.mp4 /sdcard/Download/ski.mp4
```

Then Import → Files → Downloads.

Windows Hypervisor Platform / WHPX must be enabled or the emulator will fail to boot.

## Build and install on S26

1. Phone: **Settings → About phone → Software information** → tap **Build number** seven times.
2. Phone: **Settings → Developer options → USB debugging** on.
3. Phone: **Settings → Security and privacy → Auto Blocker** off (Samsung).
4. Connect the USB cable (or use wireless debugging). On the phone, accept the RSA prompt.
5. PC: `adb devices` must show `device`, not `unauthorized` or `offline`.

```powershell
cd d:\AI\visual
python scripts/download_pose_landmarker.py
powershell -File scripts/build_android_apk.ps1
```

The script runs `gradlew assembleDebug`, checks that every bundled `.so` has PT_LOAD alignment ≥ 16384, prints the APK path, and `adb install -r` if a device or emulator is connected.

APK path: `clients/android/app/build/outputs/apk/debug/app-debug.apk`

Manual install if the script skipped adb:

```powershell
adb install -r clients\android\app\build\outputs\apk\debug\app-debug.apk
```

## File-manager fallback (not the supported path)

If `adb` is unavailable: copy the APK over USB storage, enable **Install unknown apps** for My Files / Files, and accept Play Protect **Install anyway**. One UI may still block a file-manager sideload even with Auto Blocker off. **Use `adb install`.**

## Android Studio

Open the `clients/android` folder. Gradle copies `models/pose_landmarker_full.task`, `locales/strings.json`, `curriculum.v3.json`, and `knowledge/*.json` into assets. Build/run on a device with a camera.

The C sources are compiled via `app/src/main/cpp/CMakeLists.txt` pointing at `native/core_map/core_map.c`.
