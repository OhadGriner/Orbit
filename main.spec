# PyInstaller spec for Eye Tracking Game (macOS)
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

mp_datas, mp_binaries, mp_hiddenimports = collect_all("mediapipe")
cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all("cv2")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=mp_binaries + cv2_binaries,
    datas=[
        ("assets", "assets"),
        *mp_datas,
        *cv2_datas,
    ],
    hiddenimports=[
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.QtMultimedia",
        "PyQt5.QtMultimediaWidgets",
        "PyQt5.sip",
        "pyautogui",
        "keyboard",
        "scipy",
        "scipy.special._ufuncs_cxx",
        *collect_submodules("PyQt5"),
        *mp_hiddenimports,
        *cv2_hiddenimports,
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EyeTrackingGame",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="EyeTrackingGame",
)

app = BUNDLE(
    coll,
    name="EyeTrackingGame.app",
    bundle_identifier="com.eyetracking.game",
    info_plist={
        "NSCameraUsageDescription": "This app uses the camera to track eye gaze.",
        "NSMicrophoneUsageDescription": "Not used.",
        "LSUIElement": False,
    },
)
