import sys
from pathlib import Path

# When frozen by PyInstaller, files are extracted to sys._MEIPASS
_BASE = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent.parent
ASSETS_DIR = _BASE / "assets"

# ── Target (the moving object to follow) ────────────────────────────────────
TARGET_IMAGE = ASSETS_DIR / "target.png"   # fallback to circle if file missing
TARGET_RADIUS = 50                          # pixels — controls image size & hit area

# ── Bonus quiz ───────────────────────────────────────────────────────────────
BONUS_APPEAR_AFTER = 10.0   # seconds of play before first bonus image appears
BONUS_POINTS = 30            # points awarded per correct answer

