# PyInstaller spec for the desktop client (Windows + macOS).
#
# core/, schemas/, models/, locales/ all resolve paths as
# Path(__file__).resolve().parents[N] relative to the repo root (see
# core/mediapipe_engine.py's DEFAULT_TASK, core/i18n.py's LOCALES_DIR). PyInstaller
# preserves each frozen module's package-relative __file__ under sys._MEIPASS, so
# bundling these directories at the archive root reproduces that same layout and
# every existing path lookup keeps working unmodified.
#
# Run from the repo root:
#   pyinstaller scripts/packaging/visualpose.spec --noconfirm
import sys
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).resolve().parents[1]

datas = [
    (str(ROOT / "models" / "pose_landmarker_full.task"), "models"),
    (str(ROOT / "locales"), "locales"),
    (str(ROOT / "clients" / "windows" / "assets"), "assets"),
    (str(ROOT / "clients" / "windows" / "ui" / "icons"), "clients/windows/ui/icons"),
    (str(ROOT / "content"), "content"),
]

hiddenimports = [
    "mediapipe",
    "cv2",
    "PySide6.QtSvg",
]

a = Analysis(
    [str(ROOT / "clients" / "windows" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "torchvision", "ultralytics"],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

is_macos = sys.platform == "darwin"
icon = str(ROOT / "clients" / "windows" / "assets" / ("icon.icns" if is_macos else "icon.ico"))

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VisualPose",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="VisualPose",
)

if is_macos:
    app = BUNDLE(
        coll,
        name="VisualPose.app",
        icon=icon,
        bundle_identifier="local.visual.corepose",
        info_plist={
            "NSCameraUsageDescription": "Visual Pose uses the camera to record ski clips for pose analysis.",
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
        },
    )
