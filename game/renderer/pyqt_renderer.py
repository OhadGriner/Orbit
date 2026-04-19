import math
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

from ..config import TARGET_IMAGE
from ..engine.engine import GameEngine
from ..engine.state import GamePhase, GameState
from ..gaze_providers.base import GazeProvider
from .base import GameRenderer

_FPS = 60
_TICK_MS = 1000 // _FPS

_COLOR_BG = QColor(12, 12, 18)
_COLOR_TARGET_HIT_RING = QColor(80, 220, 100)
_COLOR_GAZE_FILL = QColor(100, 190, 255, 120)
_COLOR_GAZE_BORDER = QColor(100, 190, 255, 220)
_COLOR_TEXT = QColor(240, 240, 240)
_COLOR_OVERLAY = QColor(0, 0, 0, 160)
_COLOR_PANEL_BG = QColor(20, 20, 35, 210)
_COLOR_PANEL_BORDER = QColor(90, 90, 130)

_BONUS_PANEL_W = 250
_BONUS_PANEL_H = 310
_BONUS_IMG_SIZE = 160
_BONUS_PANEL_MARGIN = 20


class _GameWidget(QWidget):
    def __init__(self, engine: GameEngine, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._last_tick = time.perf_counter()

        # Load target image once; fall back to None → draws circle
        pix = QPixmap(str(TARGET_IMAGE))
        self._target_pixmap: Optional[QPixmap] = pix if not pix.isNull() else None

        # Bonus image cache: path → QPixmap
        self._bonus_cache: Dict[str, QPixmap] = {}

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(_TICK_MS)

        self.setMouseTracking(False)
        self.setCursor(Qt.BlankCursor)

    # ── Timer tick ───────────────────────────────────────────────────────────

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_tick
        self._last_tick = now
        self._engine.update(dt)
        self.update()

    # ── Keyboard input ───────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        state = self._engine.state

        if event.key() == Qt.Key_Escape:
            QApplication.quit()
            return

        # Bonus typing mode takes priority over all other bindings
        if state.phase == GamePhase.PLAYING and state.bonus_active:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self._engine.handle_submit()
            elif event.key() == Qt.Key_Backspace:
                self._engine.handle_backspace()
            elif event.text() and event.text().isprintable():
                self._engine.handle_char(event.text())
            return

        if event.key() == Qt.Key_C:
            self._engine.calibrate()
        elif event.key() == Qt.Key_R and state.phase == GamePhase.GAME_OVER:
            self._engine.reset()
            self._last_tick = time.perf_counter()

    # ── Paint ────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        state: GameState = self._engine.state
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        p.fillRect(self.rect(), _COLOR_BG)

        self._draw_target(p, state)
        self._draw_gaze(p, state)
        self._draw_hud(p, state)

        if state.bonus_active and state.phase == GamePhase.PLAYING:
            self._draw_bonus_panel(p, state)

        if state.phase == GamePhase.COUNTDOWN:
            self._draw_countdown(p, state)
        elif state.phase == GamePhase.GAME_OVER:
            self._draw_game_over(p, state)

        p.end()

    def _draw_target(self, p: QPainter, state: GameState) -> None:
        tx, ty = int(state.target.x), int(state.target.y)
        r = int(state.target.radius)

        if self._target_pixmap:
            size = r * 2
            scaled = self._target_pixmap.scaled(
                size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            p.drawPixmap(tx - scaled.width() // 2, ty - scaled.height() // 2, scaled)
        else:
            # Fallback circle
            color = QColor(80, 220, 100) if state.tracking else QColor(230, 120, 40)
            p.setBrush(QBrush(color))
            p.setPen(Qt.NoPen)
            p.drawEllipse(tx - r, ty - r, r * 2, r * 2)

        # Green ring when gaze is on target
        if state.tracking:
            p.setPen(QPen(_COLOR_TARGET_HIT_RING, 4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(tx - r - 4, ty - r - 4, r * 2 + 8, r * 2 + 8)

    def _draw_gaze(self, p: QPainter, state: GameState) -> None:
        gx, gy = state.gaze_x, state.gaze_y
        gr = state.gaze_radius
        p.setPen(QPen(_COLOR_GAZE_BORDER, 2))
        p.setBrush(QBrush(_COLOR_GAZE_FILL))
        p.drawEllipse(gx - gr, gy - gr, gr * 2, gr * 2)

    def _draw_hud(self, p: QPainter, state: GameState) -> None:
        p.setPen(_COLOR_TEXT)
        p.setFont(QFont("Arial", 22, QFont.Bold))
        p.drawText(20, 40, f"Score: {state.score}")

        p.setFont(QFont("Arial", 11))
        p.setPen(QColor(140, 140, 140))
        if state.bonus_active and state.phase == GamePhase.PLAYING:
            p.drawText(20, self.height() - 16, "Type the answer   Enter = submit   Esc = quit")
        else:
            p.drawText(20, self.height() - 16, "C = calibrate   Esc = quit")

    def _draw_bonus_panel(self, p: QPainter, state: GameState) -> None:
        pw, ph = _BONUS_PANEL_W, _BONUS_PANEL_H
        px = self.width() - pw - _BONUS_PANEL_MARGIN
        py = _BONUS_PANEL_MARGIN

        # Panel background
        p.setBrush(QBrush(_COLOR_PANEL_BG))
        p.setPen(QPen(_COLOR_PANEL_BORDER, 1))
        p.drawRoundedRect(px, py, pw, ph, 10, 10)

        # "What is this?" label
        p.setPen(_COLOR_TEXT)
        p.setFont(QFont("Arial", 13, QFont.Bold))
        p.drawText(QRect(px, py + 10, pw, 28), Qt.AlignCenter, "What is this?")

        # Bonus image
        pix = self._get_bonus_pixmap(state.bonus_image_path)
        img_y = py + 44
        if pix and not pix.isNull():
            scaled = pix.scaled(
                _BONUS_IMG_SIZE, _BONUS_IMG_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            img_x = px + (pw - scaled.width()) // 2
            p.drawPixmap(img_x, img_y + (_BONUS_IMG_SIZE - scaled.height()) // 2, scaled)

        # Text input line
        input_y = img_y + _BONUS_IMG_SIZE + 12
        p.setPen(QColor(160, 160, 200))
        p.setFont(QFont("Courier", 15))
        display = "> " + state.bonus_input + "▌"
        p.drawText(QRect(px, input_y, pw, 28), Qt.AlignCenter, display)

        # Submit hint
        p.setFont(QFont("Arial", 10))
        p.setPen(QColor(100, 100, 130))
        p.drawText(QRect(px, input_y + 32, pw, 20), Qt.AlignCenter, "Enter to submit")

    def _draw_countdown(self, p: QPainter, state: GameState) -> None:
        p.fillRect(self.rect(), _COLOR_OVERLAY)
        p.setPen(_COLOR_TEXT)
        p.setFont(QFont("Arial", 120, QFont.Bold))
        label = str(math.ceil(state.countdown)) if state.countdown > 0 else "GO!"
        p.drawText(self.rect(), Qt.AlignCenter, label)

    def _draw_game_over(self, p: QPainter, state: GameState) -> None:
        p.fillRect(self.rect(), _COLOR_OVERLAY)
        p.setPen(_COLOR_TEXT)
        p.setFont(QFont("Arial", 52, QFont.Bold))
        p.drawText(
            self.rect(), Qt.AlignCenter,
            f"GAME OVER\n{state.score} pts\n\nR = restart   Esc = quit"
        )

    def _get_bonus_pixmap(self, path: str) -> Optional[QPixmap]:
        if not path:
            return None
        if path not in self._bonus_cache:
            self._bonus_cache[path] = QPixmap(path)
        return self._bonus_cache[path]


class PyQtRenderer(GameRenderer):
    def start(self, gaze_provider: GazeProvider) -> None:
        app = QApplication(sys.argv)
        screen = app.primaryScreen().geometry()
        w, h = screen.width(), screen.height()

        gaze_provider.start()
        engine = GameEngine(w, h, gaze_provider)

        win = QMainWindow()
        widget = _GameWidget(engine, win)
        win.setCentralWidget(widget)
        win.setWindowTitle("Gaze Tracker Game")
        win.showFullScreen()
        widget.setFocus()

        exit_code = app.exec_()
        gaze_provider.stop()
        sys.exit(exit_code)
