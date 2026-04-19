import math
import sys
import time
from typing import Dict, Optional

from PyQt5.QtCore import Qt, QTimer, QRect, QUrl
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

from ..config import ASSETS_DIR, TARGET_IMAGE
from ..engine.engine import GameEngine
from ..engine.state import GamePhase, GameState
from ..gaze_providers.base import GazeProvider
from .base import GameRenderer

_FPS = 60
_TICK_MS = 1000 // _FPS

# ── Palette ───────────────────────────────────────────────────────────────────
_C_BG       = QColor(19,  31,  36)
_C_GREEN    = QColor(88,  204,  2)
_C_GREEN_D  = QColor(58,  140,  2)
_C_YELLOW   = QColor(255, 200,  0)
_C_YELLOW_D = QColor(200, 152,  0)
_C_RED      = QColor(255,  75,  75)
_C_BLUE     = QColor(28,  176, 246)
_C_PURPLE   = QColor(206, 130, 255)
_C_PURPLE_D = QColor(140,  80, 200)
_C_WHITE    = QColor(255, 255, 255)
_C_MUTED    = QColor(100, 130, 145)
_C_PANEL    = QColor(24,  40,  50)

_COUNTDOWN_COLORS = {3: _C_RED, 2: _C_YELLOW, 1: _C_GREEN}


def _font(size: int, bold: bool = True) -> QFont:
    f = QFont()
    f.setFamilies(["Nunito", "Arial Rounded MT Bold", "SF Pro Rounded", "Arial"])
    f.setPointSize(size)
    f.setBold(bold)
    return f


class _GameWidget(QWidget):
    def __init__(self, engine: GameEngine, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._last_tick = time.perf_counter()
        self._anim_t: float = 0.0
        self._last_score: int = 0
        self._score_pop_t: float = -99.0   # time of last score change (for pop anim)
        self._last_countdown_num: int = -1

        self._countdown_player = QMediaPlayer(self)
        self._countdown_player.setMedia(
            QMediaContent(QUrl.fromLocalFile(str(ASSETS_DIR / "countdown.mp3")))
        )

        pix = QPixmap(str(TARGET_IMAGE))
        self._target_pixmap: Optional[QPixmap] = pix if not pix.isNull() else None
        self._bonus_cache: Dict[str, QPixmap] = {}

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(_TICK_MS)

        self.setMouseTracking(False)
        self.setCursor(Qt.BlankCursor)

    # ── Timer ─────────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_tick
        self._last_tick = now
        self._anim_t += dt
        self._engine.update(dt)
        state = self._engine.state

        if state.phase == GamePhase.COUNTDOWN:
            if self._last_countdown_num != 1:
                self._last_countdown_num = 1
                self._countdown_player.stop()
                self._countdown_player.play()
        else:
            self._last_countdown_num = -1

        if state.score != self._last_score:
            self._score_pop_t = self._anim_t
            self._last_score = state.score
        self.update()

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        state = self._engine.state
        if event.key() == Qt.Key_Escape:
            QApplication.quit()
            return
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

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        state = self._engine.state
        t = self._anim_t
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        self._draw_background(p, w, h)

        if state.phase == GamePhase.PLAYING:
            self._draw_hud(p, state, w, t)
            if state.bonus_active:
                self._draw_bonus_panel(p, state, w, h, t)
            self._draw_target(p, state, t)
            self._draw_gaze(p, state, t)
        elif state.phase == GamePhase.COUNTDOWN:
            self._draw_target(p, state, t)
            self._draw_gaze(p, state, t)
            self._draw_countdown(p, state, w, h, t)
        elif state.phase == GamePhase.WAITING:
            self._draw_gaze(p, state, t)
            self._draw_waiting(p, w, h)
        elif state.phase == GamePhase.GAME_OVER:
            self._draw_target(p, state, t)
            self._draw_game_over(p, state, w, h)

        p.end()

    # ── Background ────────────────────────────────────────────────────────────

    def _draw_background(self, p: QPainter, w: int, h: int) -> None:
        p.fillRect(0, 0, w, h, _C_BG)
        # Subtle dot grid
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 14)))
        spacing = 38
        for gx in range(0, w + spacing, spacing):
            for gy in range(0, h + spacing, spacing):
                p.drawEllipse(gx - 1, gy - 1, 3, 3)

    # ── Target ────────────────────────────────────────────────────────────────

    def _draw_target(self, p: QPainter, state: GameState, t: float) -> None:
        tx, ty = int(state.target.x), int(state.target.y)
        r = int(state.target.radius)

        if state.tracking:
            # Two staggered expanding pulse rings
            for i in range(2):
                phase = (t * 1.4 + i * 0.5) % 1.0
                ring_r = r + 6 + int(phase * 45)
                alpha = int(220 * (1.0 - phase))
                p.setPen(QPen(QColor(88, 204, 2, alpha), 3))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(tx - ring_r, ty - ring_r, ring_r * 2, ring_r * 2)

        if self._target_pixmap:
            bounce = 1.0 + (0.05 * math.sin(t * 3.5) if state.tracking else 0.0)
            p.save()
            p.translate(tx, ty)
            p.scale(bounce, bounce)
            size = r * 2
            scaled = self._target_pixmap.scaled(
                size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            p.drawPixmap(-scaled.width() // 2, -scaled.height() // 2, scaled)
            p.restore()
        else:
            # Duolingo-style drop shadow + circle
            shadow_col = _C_GREEN_D if state.tracking else _C_YELLOW_D
            fill_col   = _C_GREEN   if state.tracking else _C_YELLOW
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(shadow_col))
            p.drawEllipse(tx - r, ty - r + 5, r * 2, r * 2)
            p.setBrush(QBrush(fill_col))
            p.drawEllipse(tx - r, ty - r, r * 2, r * 2)

        if state.tracking:
            p.setPen(QPen(_C_GREEN, 4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(tx - r - 5, ty - r - 5, (r + 5) * 2, (r + 5) * 2)

    # ── Gaze cursor ───────────────────────────────────────────────────────────

    def _draw_gaze(self, p: QPainter, state: GameState, t: float) -> None:
        gx, gy = state.gaze_x, state.gaze_y
        gr = state.gaze_radius
        color = _C_GREEN if state.tracking else _C_BLUE

        pen = QPen(QColor(color.red(), color.green(), color.blue(), 190), 2)
        pen.setStyle(Qt.DashLine)
        pen.setDashOffset(t * 35 % 16)
        p.setPen(pen)
        p.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 28)))
        p.drawEllipse(gx - gr, gy - gr, gr * 2, gr * 2)

    # ── HUD ───────────────────────────────────────────────────────────────────

    def _draw_hud(self, p: QPainter, state: GameState, w: int, t: float) -> None:
        # Score badge (pill shape with drop shadow)
        score_str = f"★  {state.score}"
        p.setFont(_font(20))
        fm = p.fontMetrics()
        text_w = fm.horizontalAdvance(score_str)
        bw, bh = text_w + 44, 46
        bx, by = 22, 22

        # Pop animation: brief scale-up when score changes
        pop_age = t - self._score_pop_t
        if pop_age < 0.35:
            pop_scale = 1.0 + 0.28 * math.sin(pop_age / 0.35 * math.pi)
            p.save()
            p.translate(bx + bw / 2, by + bh / 2)
            p.scale(pop_scale, pop_scale)
            p.translate(-(bx + bw / 2), -(by + bh / 2))

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_GREEN_D))
        p.drawRoundedRect(bx, by + 4, bw, bh, bh // 2, bh // 2)
        p.setBrush(QBrush(_C_GREEN))
        p.drawRoundedRect(bx, by, bw, bh, bh // 2, bh // 2)
        p.setPen(_C_WHITE)
        p.setFont(_font(20))
        p.drawText(QRect(bx, by, bw, bh), Qt.AlignCenter, score_str)

        if pop_age < 0.35:
            p.restore()

        # Bottom hint
        p.setFont(_font(11, bold=False))
        p.setPen(_C_MUTED)
        if state.bonus_active and state.phase == GamePhase.PLAYING:
            hint = "Type the answer   ↵ submit   Esc quit"
        else:
            hint = "C  calibrate        Esc  quit"
        p.drawText(QRect(0, self.height() - 34, w, 28), Qt.AlignCenter, hint)

    # ── Bonus panel ───────────────────────────────────────────────────────────

    def _draw_bonus_panel(self, p: QPainter, state: GameState, w: int, h: int, t: float) -> None:
        pw, ph = 264, 348
        px = w - pw - 24
        py = 24

        # Drop shadow
        p.setBrush(QBrush(QColor(0, 0, 0, 90)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(px + 5, py + 5, pw, ph, 18, 18)

        # Panel body
        p.setBrush(QBrush(_C_PANEL))
        p.setPen(QPen(_C_PURPLE, 3))
        p.drawRoundedRect(px, py, pw, ph, 18, 18)

        # Header band (top-rounded only — draw full then mask)
        header_h = 48
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_PURPLE))
        p.drawRoundedRect(px, py, pw, header_h, 18, 18)          # rounded top
        p.drawRect(px, py + header_h // 2, pw, header_h // 2)    # fill bottom half square

        p.setPen(_C_WHITE)
        p.setFont(_font(14))
        p.drawText(QRect(px, py, pw, header_h), Qt.AlignCenter, "What is this?")

        # Bonus image
        img_sz = 148
        img_x = px + (pw - img_sz) // 2
        img_y = py + header_h + 14
        pix = self._get_bonus_pixmap(state.bonus_image_path)
        if pix and not pix.isNull():
            scaled = pix.scaled(img_sz, img_sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(
                img_x + (img_sz - scaled.width()) // 2,
                img_y + (img_sz - scaled.height()) // 2,
                scaled,
            )
        else:
            p.setPen(_C_MUTED)
            p.setFont(_font(52))
            p.drawText(QRect(img_x, img_y, img_sz, img_sz), Qt.AlignCenter, "?")

        # Input field
        fi_x = px + 16
        fi_w = pw - 32
        fi_y = img_y + img_sz + 14
        fi_h = 50

        p.setBrush(QBrush(QColor(38, 58, 74)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(fi_x, fi_y, fi_w, fi_h, 12, 12)

        # Thick bottom border (Duolingo signature)
        p.setPen(QPen(_C_PURPLE_D, 4))
        p.drawLine(fi_x + 12, fi_y + fi_h - 2, fi_x + fi_w - 12, fi_y + fi_h - 2)

        # Blinking cursor
        cursor = "▌" if int(t * 2) % 2 == 0 else " "
        p.setPen(_C_WHITE)
        p.setFont(_font(17))
        p.drawText(QRect(fi_x, fi_y, fi_w, fi_h), Qt.AlignCenter,
                   state.bonus_input + cursor)

        # Hint
        p.setFont(_font(11, bold=False))
        p.setPen(_C_MUTED)
        p.drawText(QRect(px, fi_y + fi_h + 10, pw, 22), Qt.AlignCenter, "↵  Enter to submit")

    # ── Waiting ───────────────────────────────────────────────────────────────

    def _draw_waiting(self, p: QPainter, w: int, h: int) -> None:
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 160))
        cy = h // 2

        p.setFont(_font(52))
        p.setPen(_C_WHITE)
        p.drawText(QRect(0, cy - 100, w, 70), Qt.AlignCenter, "Ready?")

        p.setFont(_font(19, bold=False))
        p.setPen(_C_MUTED)
        p.drawText(QRect(0, cy - 18, w, 36), Qt.AlignCenter,
                   "Look at the screen center, then press  C  to calibrate and start")

        # Big glowing C button hint
        bw, bh = 64, 64
        bx, by = (w - bw) // 2, cy + 32
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_GREEN_D))
        p.drawRoundedRect(bx, by + 5, bw, bh, 14, 14)
        p.setBrush(QBrush(_C_GREEN))
        p.drawRoundedRect(bx, by, bw, bh, 14, 14)
        p.setPen(_C_WHITE)
        p.setFont(_font(28))
        p.drawText(QRect(bx, by, bw, bh), Qt.AlignCenter, "C")

    # ── Countdown ─────────────────────────────────────────────────────────────

    def _draw_countdown(self, p: QPainter, state: GameState, w: int, h: int, t: float) -> None:
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 195))

        num = math.ceil(state.countdown) if state.countdown > 0 else 0
        age = 1.0 - (state.countdown % 1.0) if state.countdown > 0 else 1.0
        scale = 1.0 + 0.65 * max(0.0, 1.0 - age / 0.22)

        color = _COUNTDOWN_COLORS.get(num, _C_GREEN)

        p.save()
        p.translate(w / 2, h / 2 - 30)
        p.scale(scale, scale)
        p.setPen(color)
        p.setFont(_font(130))
        label = str(num) if num > 0 else "GO!"
        p.drawText(QRect(-350, -110, 700, 220), Qt.AlignCenter, label)
        p.restore()

        # Subtitle
        p.setPen(_C_MUTED)
        p.setFont(_font(17, bold=False))
        p.drawText(QRect(0, h // 2 + 60, w, 36), Qt.AlignCenter,
                   "Keep your gaze on the target!")

    # ── Game over ─────────────────────────────────────────────────────────────

    def _draw_game_over(self, p: QPainter, state: GameState, w: int, h: int) -> None:
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 210))
        cy = h // 2

        # Trophy
        p.setFont(_font(76))
        p.setPen(_C_YELLOW)
        p.drawText(QRect(0, cy - 190, w, 100), Qt.AlignCenter, "🏆")

        # Title
        p.setFont(_font(54))
        p.setPen(_C_WHITE)
        p.drawText(QRect(0, cy - 90, w, 72), Qt.AlignCenter, "GAME OVER")

        # Score
        p.setFont(_font(34))
        p.setPen(_C_YELLOW)
        p.drawText(QRect(0, cy + 4, w, 50), Qt.AlignCenter, f"★  {state.score} pts")

        # Play again button
        bw, bh = 290, 58
        bx, by = (w - bw) // 2, cy + 80

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_GREEN_D))
        p.drawRoundedRect(bx, by + 5, bw, bh, bh // 2, bh // 2)
        p.setBrush(QBrush(_C_GREEN))
        p.drawRoundedRect(bx, by, bw, bh, bh // 2, bh // 2)

        p.setPen(_C_WHITE)
        p.setFont(_font(21))
        p.drawText(QRect(bx, by, bw, bh), Qt.AlignCenter, "R  PLAY AGAIN")

        p.setFont(_font(13, bold=False))
        p.setPen(_C_MUTED)
        p.drawText(QRect(0, by + bh + 18, w, 28), Qt.AlignCenter, "Esc to quit")

    # ── Helpers ───────────────────────────────────────────────────────────────

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
