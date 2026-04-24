import math
import os
import random
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QTimer, QRect, QUrl
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen, QBrush, QRadialGradient
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

from ..config import ASSETS_DIR, LEVEL_NAMES, LEVEL_START_SCORES
from ..engine.engine import GameEngine
from ..engine.state import GamePhase, GameState
from ..gaze_providers.base import GazeProvider
from .base import GameRenderer

_FPS = 60
_TICK_MS = 1000 // _FPS

# ── Corporate palette ──────────────────────────────────────────────────────
_C_BRAND    = QColor(10, 122, 99)
_C_BRAND_D  = QColor(7,  90,  73)
_C_BRAND_T  = QColor(230, 243, 239)
_C_SEL      = QColor(45,  75, 217)
_C_SEL_A    = QColor(45,  75, 217, 26)
_C_INK      = QColor(31,  32,  36)
_C_INK2     = QColor(74,  77,  85)
_C_INK3     = QColor(138, 141, 149)
_C_LINE     = QColor(228, 228, 222)
_C_LINE2    = QColor(212, 212, 204)
_C_CANVAS   = QColor(250, 250, 248)
_C_SURFACE  = QColor(255, 255, 255)
_C_ROW_ALT  = QColor(247, 247, 243)
_C_HDR_BG   = QColor(244, 244, 238)
_C_HDR_BG2  = QColor(238, 238, 232)
_C_DANGER   = QColor(196,  52,  43)
_C_OK_TEXT  = QColor(44, 107, 68)
_C_OK_BG    = QColor(228, 240, 232)
_C_RISK_TEXT= QColor(138,  90, 16)
_C_RISK_BG  = QColor(247, 236, 212)
_C_OFF_TEXT = QColor(138,  32, 25)
_C_OFF_BG   = QColor(247, 219, 216)

# ── Spreadsheet layout ────────────────────────────────────────────────────
_CHROME_H  = 108   # titlebar(44) + toolbar(36) + formula(28)
_TABS_H    = 34
_COL_HDR_H = 22
_ROW_H     = 22
_ROW_HDR_W = 38

_COL_NAMES   = list('ABCDEFGHIJKLMNOPQRST')
_COL_WIDTHS  = [80, 180, 100, 55, 75, 95, 50, 55, 55, 65, 75, 75, 75, 50, 65, 60, 65, 110, 90, 50]
_COL_HEADERS = ['ID','Initiative','Owner','Q','Synergy Δ','Status','P','Effort',
                'Impact','Conf','Budget','Actual','Var','NPS','% Done','Risk',
                'Dep.','Blockers','Updated','Sig']

_INITIATIVES = [
    'North Star Alignment','Voice-of-Customer Synthesis','KPI Cascade v2',
    'Vertical Integration','Stakeholder Heatmap','OKR Rollup',
    'Synergy Capture Framework','RACI Refresh','Burn-down Re-baseline',
    'Capability Maturity Audit','Roadmap Atomisation','Backlog Grooming',
    'Channel Partner Sync','Enablement Workstream','Post-Mortem Pre-Mortem',
    'Bandwidth Reconciliation','Q4 Pre-Read','Portfolio Pruning',
    'Cost Center Hygiene','Momentum Preservation',
]
_OWNERS   = ['Chadley','Brinleigh','Piotr','Rhiannon','Devonte','Agnetha','Marcus','Ingrid','Reggie','Celestine']
_BLOCKERS = ['—','Procurement','Legal','VPN','Nobody answered','Holiday']
_RISKS    = ['Low','Med','High','Elev.']
_EFFORTS  = ['XS','S','M','L','XL']
_PRIS     = ['P0','P1','P2','P3']
_QTRS     = ['Q1','Q2','Q3','Q4']
_SIGNALS  = ['●','◐','◑','○']

_SENDERS = [
    ("Chadley Ashworth",   "CA", QColor(45,  75, 217)),
    ("Brinleigh Okafor",   "BO", QColor(196,  52,  43)),
    ("Piotr Van Halen",    "PV", QColor(124,  91, 209)),
    ("Rhiannon Chen",      "RC", QColor(10,  122,  99)),
    ("Devonte Kovacs",     "DK", QColor(184, 103,  27)),
    ("Agnetha Silveira",   "AS", QColor(110,  59, 158)),
    ("Marcus Brumble",     "MB", QColor(42,  127, 138)),
    ("Ingrid Tattersall",  "IT", QColor(201, 106,  45)),
]

# ── Google Slides palette ─────────────────────────────────────────────────────
_S_BG          = QColor(250, 249, 248)
_S_TOPBAR_BG   = QColor(255, 255, 255)
_S_YELLOW      = QColor(251, 188,   5)
_S_TOPBAR_H    = 64
_S_TOOLBAR_H   = 40
_S_PANEL_W     = 220
_S_STATUS_H    = 28
_S_GREY        = QColor( 95,  99, 104)
_S_GREY_L      = QColor(218, 220, 224)
_S_INK         = QColor( 32,  33,  36)
_S_CANVAS_BG   = QColor(240, 240, 240)
_S_SLIDE_SHADOW = QColor(  0,   0,   0, 50)

# ── Gmail palette & data ──────────────────────────────────────────────────────
_G_BG       = QColor(246, 248, 252)
_G_BLUE     = QColor(26,  115, 232)
_G_RED      = QColor(234,  67,  53)
_G_GREY     = QColor(95,   99, 104)
_G_GREY_L   = QColor(218, 220, 224)
_G_INK      = QColor(32,   33,  36)
_G_ROW_UNREAD = QColor(255, 255, 255)
_G_ROW_READ   = QColor(242, 245, 253)
_G_SIDEBAR_W  = 256
_G_TOPBAR_H   = 64
_G_TAB_H      = 48
_G_ROW_H      = 52

_GMAIL_EMAILS = [
    ("Chadley Ashworth", "Re: Q3 Synergy Deliverables",   "Just circling back — are we aligned on this?",                "4:47 PM",   True),
    ("The Algorithm",    "URGENT: Gaze deviation",        "Your attention metrics have fallen below tolerance...",        "4:43 PM",   True),
    ("Brinleigh Okafor", "OKR Rollup v3 FINAL (2)",       "Per my last email, please find the updated rollup attached",   "3:22 PM",   True),
    ("Piotr Van Halen",  "Quick sync?",                   "Do you have 5 minutes? Hard stop at 3.",                      "2:15 PM",   False),
    ("HR Department",    "Performance Review Q3",         "Your assessment results are ready. Band: Needs Improvement",   "11:30 AM",  True),
    ("Rhiannon Chen",    "North Star Alignment deck",     "Moving the needle on this — thoughts before EOD?",            "10:14 AM",  False),
    ("Devonte Kovacs",   "Bandwidth check",               "Wanted to touch base re: your bandwidth for Q4",              "9:47 AM",   False),
    ("Agnetha Silveira", "Synergy Capture Framework",     "Low-hanging fruit identified. Let's put a pin in it.",        "Yesterday", False),
    ("Google Calendar",  "Reminder: Mandatory offsite",   "All-hands Alignment offsite tomorrow 9:00 AM — non-optional", "Yesterday", False),
    ("Marcus Brumble",   "Re: Re: Re: Deep dive",         "At the end of the day, it is what it is.",                   "Mon",       False),
    ("Ingrid Tattersall","Moving forward",                "Following up on our previous circle-back. Shall we?",         "Mon",       False),
    ("Reggie van Putten","Core competencies leverage",    "Game changer attached. Think outside the box on this one.",   "Sun",       False),
]

_HR_VERDICTS = [
    ("Meets Expectations",
     "Competent but unremarkable. Your manager will acknowledge this in writing, eventually, possibly."),
    ("Needs Improvement",
     "Several deliverables fell outside the expected attention window. An offsite has been scheduled."),
    ("Terminated",
     "Gaze deviation exceeded tolerance. Your access has been revoked. HR will post a 'we wish you well' note at 4:47 pm."),
    ("Peak Performer",
     "Impeccable. HR will be in touch about additional responsibilities at your current compensation level."),
]


def _lcg(s: int) -> Tuple[int, float]:
    s = (s * 9301 + 49297) % 233280
    return s, s / 233280.0


def _font(size: int, bold: bool = True, mono: bool = False) -> QFont:
    f = QFont()
    if mono:
        f.setFamilies(["SF Mono", "Menlo", "Consolas", "Courier New"])
    else:
        f.setFamilies(["-apple-system", "Segoe UI", "Helvetica Neue", "Arial"])
    f.setPointSize(size)
    f.setBold(bold)
    return f


# ── Pre-computed spreadsheet cell data ────────────────────────────────────

class _Cell:
    __slots__ = ('text', 'right', 'fg', 'pill')
    def __init__(self, text='', right=False, fg=None, pill=None):
        self.text  = text
        self.right = right
        self.fg    = fg    # QColor | None
        self.pill  = pill  # None | (text, fg_color, bg_color)


def _build_sheet_rows() -> List[List[_Cell]]:
    rows: List[List[_Cell]] = []

    # Row 0: column headers
    rows.append([_Cell(h, False, _C_INK) for h in _COL_HEADERS])

    statuses = [
        ('On Track',  _C_OK_TEXT,   _C_OK_BG),
        ('At Risk',   _C_RISK_TEXT, _C_RISK_BG),
        ('Off Track', _C_OFF_TEXT,  _C_OFF_BG),
    ]

    for r in range(1, 49):
        s = r * 9301
        s, v = _lcg(s)
        synergy = f'{(v * 40 - 5):.1f}%'
        s, vi = _lcg(s); s, vc = _lcg(s); s, vb = _lcg(s)
        s, va = _lcg(s); s, vv = _lcg(s); s, vn = _lcg(s)
        s, vd = _lcg(s)

        st_label, st_fg, st_bg = statuses[r % 3]
        row = [
            _Cell(f'SYN-{1000+r:04d}',                      False, _C_INK3),
            _Cell(_INITIATIVES[(r-1) % len(_INITIATIVES)],   False, _C_INK),
            _Cell(_OWNERS[r % len(_OWNERS)],                 False, _C_INK),
            _Cell(_QTRS[r % 4],                              False, _C_INK3),
            _Cell(synergy,                                   True,  _C_INK2),
            _Cell('',    False, st_fg, pill=(st_label, st_fg, st_bg)),
            _Cell(_PRIS[r % 4],                              False, _C_INK3),
            _Cell(_EFFORTS[r % 5],                           False, _C_INK3),
            _Cell(f'{vi*10:.1f}',                            True,  _C_INK2),
            _Cell(f'{int(vc*90+10)}%',                       True,  _C_INK2),
            _Cell(f'${int(vb*480+20)}k',                     True,  _C_INK2),
            _Cell(f'${int(va*520+15)}k',                     True,  _C_INK2),
            _Cell(f'{"+$" if vv>0.5 else "-$"}{int(abs(vv*2-1)*90)}k', True, _C_INK2),
            _Cell(str(int(vn*80+10)),                        True,  _C_INK2),
            _Cell(f'{int(vd*100)}%',                         True,  _C_INK2),
            _Cell(_RISKS[r % 4],                             False, _C_INK),
            _Cell(f'SYN-{1000+((r*3+5)%120):04d}',          False, _C_INK3),
            _Cell(_BLOCKERS[r % len(_BLOCKERS)],             False, _C_INK),
            _Cell(f'2025-10-{1+(r+5)%28:02d}',              True,  _C_INK3),
            _Cell(_SIGNALS[r % 4],                           False, _C_INK2),
        ]
        rows.append(row)

    return rows


_SHEET_ROWS = _build_sheet_rows()


class _GameWidget(QWidget):
    def __init__(self, engine: GameEngine, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._last_tick = time.perf_counter()
        self._anim_t: float = 0.0
        self._last_score: int = 0
        self._score_pop_t: float = -99.0
        self._last_bonus_phrase: str = ""
        self._popup_sender_idx: int = 0
        self._start_btn_rect: QRect = QRect()
        self._level_transition: float = 0.0
        self._level_transition_23: float = 0.0
        self._popup_x: int = 0
        self._popup_y: int = 0
        self._inbox: list = list(_GMAIL_EMAILS[:2])
        self._inbox_next_idx: int = 2
        self._next_email_in: float = random.uniform(3, 10)

        from PyQt5.QtGui import QPixmap as _QPixmap
        _pix = _QPixmap(str(ASSETS_DIR / "target.png"))
        self._target_pixmap = _pix if not _pix.isNull() else None
        _gpix = _QPixmap(str(ASSETS_DIR / "gmail_logo.webp"))
        self._gmail_logo_pixmap = _gpix if not _gpix.isNull() else None
        _spix = _QPixmap(str(ASSETS_DIR / "slide.png"))
        self._slide_pixmap = _spix if not _spix.isNull() else None

        self._last_level: int = 0
        self._last_phase = None
        self._dev_mode: bool = False
        self._dev_d_pressed_at: Optional[float] = None
        self._dev_selected_level: int = 1

        self._countdown_player = QMediaPlayer(self)
        self._countdown_player.setMedia(
            QMediaContent(QUrl.fromLocalFile(str(ASSETS_DIR / "countdown.mp3")))
        )
        self._level_stingers: dict = {}
        for lvl in (1, 2, 3):
            pl = QMediaPlayer(self)
            pl.setMedia(QMediaContent(QUrl.fromLocalFile(str(ASSETS_DIR / f"level-{lvl}.mp3"))))
            self._level_stingers[lvl] = pl
        self._popping_player = QMediaPlayer(self)
        self._popping_player.setMedia(
            QMediaContent(QUrl.fromLocalFile(str(ASSETS_DIR / "popping.mp3")))
        )

        _alert_playlist = QMediaPlaylist(self)
        _alert_playlist.addMedia(QMediaContent(QUrl.fromLocalFile(str(ASSETS_DIR / "alert.mp3"))))
        _alert_playlist.setPlaybackMode(QMediaPlaylist.Loop)
        self._alert_player = QMediaPlayer(self)
        self._alert_player.setPlaylist(_alert_playlist)

        self._music_player = QMediaPlayer(self)
        self._music_player.setMedia(
            QMediaContent(QUrl.fromLocalFile(str(ASSETS_DIR / "game-music.mp3")))
        )
        self._music_player.mediaStatusChanged.connect(self._on_music_status)
        self._music_player.play()

        self._youre_fired_player = QMediaPlayer(self)
        self._youre_fired_player.setMedia(
            QMediaContent(QUrl.fromLocalFile(str(ASSETS_DIR / "YoureFired.mp3")))
        )

        self._last_countdown_started = False

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(_TICK_MS)

        self.setMouseTracking(True)
        self.setCursor(Qt.ArrowCursor)

    # ── Mouse ─────────────────────────────────────────────────────────────

    def _on_music_status(self, status: int) -> None:
        if status == QMediaPlayer.EndOfMedia:
            self._music_player.setPosition(0)
            self._music_player.play()

    def mousePressEvent(self, event) -> None:
        if (self._engine.state.phase == GamePhase.WELCOME
                and self._start_btn_rect.contains(event.pos())):
            self._engine.click_start()
            self.setCursor(Qt.BlankCursor)

    # ── Timer ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_tick
        self._last_tick = now
        self._anim_t += dt

        if (self._dev_d_pressed_at is not None and not self._dev_mode
                and self._engine.state.phase == GamePhase.WELCOME):
            if now - self._dev_d_pressed_at >= 3.0:
                self._dev_mode = True
                self._dev_d_pressed_at = None
                self._dev_selected_level = 1

        self._engine.update(dt)
        state = self._engine.state

        # Advance level transitions (1.5 s crossfade each)
        if state.level >= 2 and self._level_transition < 1.0:
            self._level_transition = min(1.0, self._level_transition + dt / 1.5)
        if state.level >= 3 and self._level_transition_23 < 1.0:
            self._level_transition_23 = min(1.0, self._level_transition_23 + dt / 1.5)

        # Drip new inbox messages during Gmail level
        if self._level_transition > 0.0:
            self._next_email_in -= dt
            if self._next_email_in <= 0:
                src = _GMAIL_EMAILS[self._inbox_next_idx % len(_GMAIL_EMAILS)]
                self._inbox.insert(0, (src[0], src[1], src[2], "just now", True))
                self._inbox_next_idx += 1
                self._next_email_in = random.uniform(3, 10)

        if state.phase == GamePhase.COUNTDOWN:
            if not self._last_countdown_started:
                self._last_countdown_started = True
                self._countdown_player.stop()
                self._countdown_player.play()
        else:
            self._last_countdown_started = False

        # Level stingers
        new_level = state.level if state.phase in (GamePhase.COUNTDOWN, GamePhase.PLAYING) else 0
        if new_level == 1 and self._last_level == 0 and state.phase == GamePhase.PLAYING:
            self._level_stingers[1].stop()
            self._level_stingers[1].play()
            self._last_level = 1
        elif new_level == 2 and self._last_level == 1:
            self._level_stingers[2].stop()
            self._level_stingers[2].play()
            self._last_level = 2
        elif new_level == 3 and self._last_level == 2:
            self._level_stingers[3].stop()
            self._level_stingers[3].play()
            self._last_level = 3

        # New deliverable appeared
        if state.bonus_phrase != self._last_bonus_phrase and state.bonus_phrase:
            self._popup_sender_idx = random.randrange(len(_SENDERS))
            self._last_bonus_phrase = state.bonus_phrase
            self._popup_x, self._popup_y = self._pick_popup_pos(state)
            self._popping_player.stop()
            self._popping_player.play()

        # Auto-submit when phrase typed exactly
        if (state.bonus_active and state.phase == GamePhase.PLAYING
                and state.bonus_input.strip().lower() == state.bonus_phrase.lower()):
            self._engine.handle_submit()

        if state.score != self._last_score:
            self._score_pop_t = self._anim_t
            self._last_score = state.score

        # "You're Fired" sting: play once on transition into GAME_OVER
        if state.phase == GamePhase.GAME_OVER and self._last_phase != GamePhase.GAME_OVER:
            self._youre_fired_player.setPosition(0)
            self._youre_fired_player.play()
        self._last_phase = state.phase

        # Background music: pause on game-over screen, resume everywhere else
        music_playing = self._music_player.state() == QMediaPlayer.PlayingState
        if state.phase == GamePhase.GAME_OVER and music_playing:
            self._music_player.pause()
        elif state.phase != GamePhase.GAME_OVER and not music_playing:
            self._music_player.play()

        # Alert sound: loop while gaze is off target, stop when back on or game ends
        alert_playing = self._alert_player.state() == QMediaPlayer.PlayingState
        should_alert = (state.phase == GamePhase.PLAYING and not state.tracking)
        if should_alert and not alert_playing:
            self._alert_player.play()
        elif not should_alert and alert_playing:
            self._alert_player.stop()

        self.update()

    # ── Keyboard ──────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        state = self._engine.state

        # Dev mode: hold D for 3 s on welcome screen
        if state.phase == GamePhase.WELCOME and event.key() == Qt.Key_D:
            if not event.isAutoRepeat() and self._dev_d_pressed_at is None and not self._dev_mode:
                self._dev_d_pressed_at = time.perf_counter()
            return

        # Dev mode overlay controls
        if self._dev_mode:
            if event.key() == Qt.Key_Escape:
                self._dev_mode = False
                self._dev_d_pressed_at = None
            elif event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3):
                self._dev_selected_level = int(event.text())
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                self._dev_mode = False
                self._engine.set_start_level(self._dev_selected_level)
                self._engine.click_start()
                if self._dev_selected_level >= 2:
                    self._level_transition = 1.0
                if self._dev_selected_level >= 3:
                    self._level_transition_23 = 1.0
                self._last_level = self._dev_selected_level - 1
                self.setCursor(Qt.BlankCursor)
            return

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
            self._youre_fired_player.stop()
            self._last_phase = None
            self._engine.reset()
            self._last_tick = time.perf_counter()
            self._last_bonus_phrase = ""
            self._last_level = 0
            self._level_transition = 0.0
            self._level_transition_23 = 0.0
            self._inbox = list(_GMAIL_EMAILS[:2])
            self._inbox_next_idx = 2
            self._next_email_in = random.uniform(3, 10)
            self.setCursor(Qt.ArrowCursor)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key_D and not event.isAutoRepeat() and not self._dev_mode:
            self._dev_d_pressed_at = None

    # ── Paint ─────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        state = self._engine.state
        t = self._anim_t
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        if state.phase == GamePhase.WELCOME:
            self._draw_welcome(p, w, h)
            if self._dev_mode:
                self._draw_dev_overlay(p, w, h)
            elif self._dev_d_pressed_at is not None:
                held = min(1.0, (time.perf_counter() - self._dev_d_pressed_at) / 3.0)
                self._draw_dev_hold_progress(p, w, h, held)
            p.end()
            return

        self._draw_background(p, w, h)

        if state.phase == GamePhase.WAITING:
            self._draw_waiting(p, w, h)
            self._draw_gaze(p, state, t)
        elif state.phase == GamePhase.PLAYING:
            if state.bonus_active:
                self._draw_popup(p, state, w, h, t)
            self._draw_hud(p, state, w, h, t)
            self._draw_vignette(p, state, w, h, t)
            self._draw_target(p, state, t)
            self._draw_gaze(p, state, t)
        elif state.phase == GamePhase.COUNTDOWN:
            self._draw_countdown(p, state, w, h, t)
            self._draw_target(p, state, t)
            self._draw_gaze(p, state, t)
        elif state.phase == GamePhase.GAME_OVER:
            self._draw_fired(p, state, w, h)

        p.end()

    # ── Background: spreadsheet ───────────────────────────────────────────

    def _draw_background(self, p: QPainter, w: int, h: int) -> None:
        tr12 = self._level_transition
        tr23 = self._level_transition_23
        # Level 1 (spreadsheet): opacity = 1 - tr12
        if tr12 < 1.0:
            p.save()
            p.setOpacity(1.0 - tr12)
            p.fillRect(0, 0, w, h, _C_CANVAS)
            self._draw_sheet_chrome(p, w, h)
            self._draw_sheet_grid(p, w, h)
            self._draw_sheet_tabs(p, w, h)
            p.restore()
        # Level 2 (Gmail): opacity = tr12 * (1 - tr23)
        if tr12 > 0.0 and tr23 < 1.0:
            p.save()
            p.setOpacity(tr12 * (1.0 - tr23))
            self._draw_gmail_bg(p, w, h)
            p.restore()
        # Level 3 (Slides): opacity = tr23
        if tr23 > 0.0:
            p.save()
            p.setOpacity(tr23)
            self._draw_slides_bg(p, w, h)
            p.restore()

    def _draw_sheet_chrome(self, p: QPainter, w: int, h: int) -> None:
        # ── Title bar (y=0..44) ──────────────────────────────────────────
        p.fillRect(0, 0, w, 44, _C_SURFACE)
        p.setPen(QPen(_C_LINE, 1))
        p.drawLine(0, 43, w, 43)

        # Logo box
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_BRAND))
        p.drawRoundedRect(14, 8, 28, 28, 6, 6)
        p.setPen(QColor(255, 255, 255, 200))
        p.setFont(_font(14, bold=True))
        p.drawText(QRect(14, 8, 28, 28), Qt.AlignCenter, "L")

        # Filename
        p.setPen(_C_INK)
        p.setFont(_font(13, bold=False))
        p.drawText(QRect(50, 4, 500, 20), Qt.AlignLeft | Qt.AlignVCenter,
                   "Q3_Synergy_Tracker_FINAL_v2_ACTUAL_FINAL.ledger")
        p.setPen(_C_INK3)
        p.setFont(_font(11, bold=False))
        p.drawText(QRect(50, 24, 500, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   "☆  ·  Shared — Dept. of Productivity")

        # Menubar
        menu_items = ["File","Edit","View","Insert","Format","Data","Tools","Extensions","Help"]
        mx = 50
        p.setFont(_font(11, bold=False))
        for item in menu_items:
            fm = p.fontMetrics()
            iw = fm.horizontalAdvance(item) + 16
            p.setPen(_C_INK2)
            p.drawText(QRect(mx, 26, iw, 16), Qt.AlignCenter, item)
            mx += iw

        # Right side: Share pill + avatar
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_BRAND))
        p.drawRoundedRect(w - 80, 12, 56, 22, 11, 11)
        p.setPen(_C_SURFACE)
        p.setFont(_font(11, bold=True))
        p.drawText(QRect(w - 80, 12, 56, 22), Qt.AlignCenter, "Share")

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(124, 91, 209)))
        p.drawEllipse(w - 112, 10, 26, 26)
        p.setPen(_C_SURFACE)
        p.setFont(_font(10, bold=True))
        p.drawText(QRect(w - 112, 10, 26, 26), Qt.AlignCenter, "KP")

        # Last edited note
        p.setPen(_C_INK3)
        p.setFont(_font(10, bold=False))
        p.drawText(QRect(mx + 8, 28, 300, 14), Qt.AlignLeft | Qt.AlignVCenter,
                   "Last edit was 4 minutes ago by Chadley")

        # ── Toolbar (y=44..80) ───────────────────────────────────────────
        p.fillRect(0, 44, w, 36, _C_HDR_BG)
        p.setPen(QPen(_C_LINE, 1))
        p.drawLine(0, 79, w, 79)

        tb_items = ["▶","▷","🖨","100%","$","%",".0",".00","123","Default","10",
                    "B","I","U","S","A▾","🎨","←","→","↔","📊","💬","Σ"]
        tx = 10
        p.setFont(_font(11, bold=False))
        for item in tb_items:
            fm = p.fontMetrics()
            iw = max(28, fm.horizontalAdvance(item) + 16)
            p.setPen(_C_INK2)
            p.drawText(QRect(tx, 44, iw, 36), Qt.AlignCenter, item)
            if item in ("🖨", "123", "10", "🎨", "↔"):
                p.setPen(QPen(_C_LINE2, 1))
                p.drawLine(tx + iw + 4, 52, tx + iw + 4, 72)
            tx += iw
            if tx > w - 40:
                break

        # ── Formula bar (y=80..108) ──────────────────────────────────────
        p.fillRect(0, 80, w, 28, _C_SURFACE)
        p.setPen(QPen(_C_LINE, 1))
        p.drawLine(0, 107, w, 107)
        p.drawLine(80, 80, 80, 108)
        p.drawLine(112, 80, 112, 108)

        p.setPen(_C_INK2)
        p.setFont(_font(11, bold=False, mono=True))
        p.drawText(QRect(4, 80, 76, 28), Qt.AlignCenter, "B12")
        p.setPen(_C_INK3)
        p.setFont(_font(11, bold=False))
        p.drawText(QRect(82, 80, 28, 28), Qt.AlignCenter, "fx")

        p.setPen(_C_INK)
        p.setFont(_font(10, bold=False, mono=True))
        formula = ('=IFERROR(VLOOKUP("synergy",$A$2:$H$847,6,FALSE)*ROUND(RAND()*1.7,2),'
                   '"REFRESH Q4")&" — owner: "&INDIRECT("Headcount!C"&MATCH(A12,Headcount!A:A,0))')
        p.drawText(QRect(116, 80, w - 120, 28), Qt.AlignLeft | Qt.AlignVCenter, formula)

    def _draw_sheet_grid(self, p: QPainter, w: int, h: int) -> None:
        grid_top = _CHROME_H
        grid_bot = h - _TABS_H
        grid_h   = grid_bot - grid_top

        p.save()
        p.setClipRect(0, grid_top, w, grid_h)

        # Row header column background
        p.fillRect(0, grid_top, _ROW_HDR_W, grid_h, _C_HDR_BG)

        # Column header row background
        p.fillRect(0, grid_top, w, _COL_HDR_H, _C_HDR_BG)

        # Build column x positions
        col_xs = []
        cx = _ROW_HDR_W
        for cw in _COL_WIDTHS:
            col_xs.append(cx)
            cx += cw

        # Data rows
        y = grid_top + _COL_HDR_H
        small = _font(10, bold=False)
        small_bold = _font(10, bold=True)
        for row_idx, row_cells in enumerate(_SHEET_ROWS):
            if y >= grid_bot:
                break
            is_header = (row_idx == 0)
            if is_header:
                p.fillRect(_ROW_HDR_W, y, w - _ROW_HDR_W, _ROW_H, _C_HDR_BG)
            elif row_idx % 2 == 0:
                p.fillRect(_ROW_HDR_W, y, w - _ROW_HDR_W, _ROW_H, _C_ROW_ALT)
            else:
                p.fillRect(_ROW_HDR_W, y, w - _ROW_HDR_W, _ROW_H, _C_SURFACE)

            # Row number
            p.setFont(small)
            p.setPen(_C_INK3)
            p.drawText(QRect(0, y, _ROW_HDR_W, _ROW_H), Qt.AlignCenter,
                       "  " if is_header else str(row_idx))

            # Cells
            for ci, cell in enumerate(row_cells):
                if ci >= len(col_xs):
                    break
                cx2 = col_xs[ci]
                cw2 = _COL_WIDTHS[ci] if ci < len(_COL_WIDTHS) else 60
                if cx2 > w:
                    break

                if cell.pill:
                    label, pfg, pbg = cell.pill
                    pill_w = min(cw2 - 8, 66)
                    pill_x = cx2 + 4
                    pill_h = 14
                    pill_y = y + (_ROW_H - pill_h) // 2
                    p.setPen(Qt.NoPen)
                    p.setBrush(QBrush(pbg))
                    p.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, 7, 7)
                    p.setFont(_font(8, bold=False))
                    p.setPen(pfg)
                    p.drawText(QRect(pill_x, pill_y, pill_w, pill_h), Qt.AlignCenter, label)
                else:
                    p.setFont(small_bold if is_header else small)
                    p.setPen(cell.fg or _C_INK2)
                    align = (Qt.AlignRight | Qt.AlignVCenter) if cell.right else (Qt.AlignLeft | Qt.AlignVCenter)
                    p.drawText(QRect(cx2 + 4, y, cw2 - 8, _ROW_H), align, cell.text)

            y += _ROW_H

        # Horizontal grid lines
        y = grid_top
        p.setPen(QPen(_C_LINE, 1))
        while y <= grid_bot:
            p.drawLine(0, y, w, y)
            y += _ROW_H

        # Vertical grid lines (column separators + row header border)
        p.setPen(QPen(_C_LINE, 1))
        cx2 = _ROW_HDR_W
        for cw2 in _COL_WIDTHS:
            p.drawLine(cx2, grid_top, cx2, grid_bot)
            cx2 += cw2
            if cx2 > w:
                break
        # Row header right border slightly darker
        p.setPen(QPen(_C_LINE2, 1))
        p.drawLine(_ROW_HDR_W, grid_top, _ROW_HDR_W, grid_bot)

        # Column header labels (on top, re-draw to cover row stripes)
        p.fillRect(0, grid_top, w, _COL_HDR_H, _C_HDR_BG)
        p.fillRect(0, grid_top, _ROW_HDR_W, _COL_HDR_H, _C_HDR_BG2)
        p.setFont(small)
        for ci, (cname, cx2, cw2) in enumerate(zip(_COL_NAMES, col_xs, _COL_WIDTHS)):
            if cx2 > w:
                break
            p.setPen(_C_INK2)
            p.drawText(QRect(cx2, grid_top, cw2, _COL_HDR_H), Qt.AlignCenter, cname)
        p.setPen(QPen(_C_LINE, 1))
        p.drawLine(0, grid_top + _COL_HDR_H, w, grid_top + _COL_HDR_H)
        p.setPen(QPen(_C_LINE2, 1))
        p.drawLine(0, grid_bot, w, grid_bot)

        p.restore()

    def _draw_sheet_tabs(self, p: QPainter, w: int, h: int) -> None:
        tab_y = h - _TABS_H
        p.fillRect(0, tab_y, w, _TABS_H, _C_HDR_BG)
        p.setPen(QPen(_C_LINE, 1))
        p.drawLine(0, tab_y, w, tab_y)

        tabs = ["Q3 Synergies", "KPI Dashboard", "Headcount", "Deliverables", "Archive (DO NOT DELETE)"]
        tx = 6
        for i, tab in enumerate(tabs):
            p.setFont(_font(11, bold=(i == 0)))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(tab) + 28
            tab_rect = QRect(tx, tab_y, tw, _TABS_H)
            if i == 0:
                p.fillRect(tx, tab_y + 1, tw, _TABS_H - 1, _C_SURFACE)
                p.setPen(QPen(_C_BRAND, 2))
                p.drawLine(tx, tab_y + 2, tx + tw, tab_y + 2)
                p.setPen(_C_BRAND_D)
            else:
                p.setPen(_C_INK3)
            p.drawText(tab_rect, Qt.AlignCenter, tab)
            p.setPen(QPen(_C_LINE, 1))
            p.drawLine(tx + tw, tab_y + 4, tx + tw, tab_y + _TABS_H - 4)
            tx += tw

        # Row count info (right side)
        p.setPen(_C_INK3)
        p.setFont(_font(10, bold=False))
        p.drawText(QRect(w - 200, tab_y, 190, _TABS_H), Qt.AlignRight | Qt.AlignVCenter,
                   "847 rows  ·  autosaved 4m ago")

    # ── Background: Google Slides ────────────────────────────────────────

    def _draw_slides_bg(self, p: QPainter, w: int, h: int) -> None:
        p.fillRect(0, 0, w, h, _S_BG)
        self._draw_slides_topbar(p, w)
        self._draw_slides_toolbar(p, w)
        self._draw_slides_main(p, w, h)
        self._draw_slides_statusbar(p, w, h)

    def _draw_slides_topbar(self, p: QPainter, w: int) -> None:
        p.fillRect(0, 0, w, _S_TOPBAR_H, _S_TOPBAR_BG)
        p.setPen(QPen(_S_GREY_L, 1))
        p.drawLine(0, _S_TOPBAR_H - 1, w, _S_TOPBAR_H - 1)

        # Slides logo: yellow rectangle + "Slides"
        lx, ly = 16, (_S_TOPBAR_H - 36) // 2
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_S_YELLOW))
        p.drawRoundedRect(lx, ly, 28, 36, 3, 3)
        # white lines to simulate slide stripes
        p.setPen(QPen(QColor(255, 255, 255, 180), 2))
        for i in range(3):
            yy = ly + 8 + i * 8
            p.drawLine(lx + 5, yy, lx + 23, yy)
        # "Slides" text
        p.setPen(_S_GREY)
        p.setFont(_font(16, bold=False))
        p.drawText(QRect(lx + 34, 0, 80, _S_TOPBAR_H), Qt.AlignLeft | Qt.AlignVCenter, "Slides")

        # File name
        p.setPen(_S_INK)
        p.setFont(_font(13, bold=False))
        p.drawText(QRect(lx + 120, 4, 460, 20), Qt.AlignLeft | Qt.AlignVCenter,
                   "Q3_Leadership_Alignment_Deck_FINAL_v4.pptx")
        p.setPen(_S_GREY)
        p.setFont(_font(10, bold=False))
        menu_items = ["File", "Edit", "View", "Insert", "Format", "Slide", "Arrange", "Tools", "Help"]
        mx = lx + 120
        for item in menu_items:
            p.setFont(_font(11, bold=False))
            fm = p.fontMetrics()
            iw = fm.horizontalAdvance(item) + 16
            p.setPen(_S_GREY)
            p.drawText(QRect(mx, 24, iw, 18), Qt.AlignCenter, item)
            mx += iw

        # Right: Share + avatar
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_G_BLUE))
        p.drawRoundedRect(w - 90, 14, 64, 26, 13, 13)
        p.setPen(QColor(255, 255, 255))
        p.setFont(_font(11, bold=True))
        p.drawText(QRect(w - 90, 14, 64, 26), Qt.AlignCenter, "Share")

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(124, 91, 209)))
        p.drawEllipse(w - 136, 12, 30, 30)
        p.setPen(QColor(255, 255, 255))
        p.setFont(_font(10, bold=True))
        p.drawText(QRect(w - 136, 12, 30, 30), Qt.AlignCenter, "KP")

    def _draw_slides_toolbar(self, p: QPainter, w: int) -> None:
        ty = _S_TOPBAR_H
        p.fillRect(0, ty, w, _S_TOOLBAR_H, _S_TOPBAR_BG)
        p.setPen(QPen(_S_GREY_L, 1))
        p.drawLine(0, ty + _S_TOOLBAR_H - 1, w, ty + _S_TOOLBAR_H - 1)

        tools = ["↩", "↪", "🖨", "100%", "|", "T", "▭", "⬡", "↗", "🖼", "♫", "▶", "|",
                 "B", "I", "U", "A▾", "≡", "≡", "≡", "|", "⬚"]
        tx = 14
        p.setFont(_font(11, bold=False))
        for item in tools:
            if item == "|":
                p.setPen(QPen(_S_GREY_L, 1))
                p.drawLine(tx + 4, ty + 8, tx + 4, ty + _S_TOOLBAR_H - 8)
                tx += 12
                continue
            fm = p.fontMetrics()
            iw = max(28, fm.horizontalAdvance(item) + 14)
            p.setPen(_S_GREY)
            p.drawText(QRect(tx, ty, iw, _S_TOOLBAR_H), Qt.AlignCenter, item)
            tx += iw
            if tx > w - 60:
                break

        # Presenter view label (right)
        p.setPen(_S_GREY)
        p.setFont(_font(11, bold=False))
        p.drawText(QRect(w - 160, ty, 150, _S_TOOLBAR_H), Qt.AlignRight | Qt.AlignVCenter,
                   "Slideshow ▾")

    def _draw_slides_main(self, p: QPainter, w: int, h: int) -> None:
        content_top = _S_TOPBAR_H + _S_TOOLBAR_H
        content_h = h - content_top - _S_STATUS_H

        # ── Left thumbnail panel ──────────────────────────────────────────
        p.fillRect(0, content_top, _S_PANEL_W, content_h, QColor(248, 247, 247))
        p.setPen(QPen(_S_GREY_L, 1))
        p.drawLine(_S_PANEL_W, content_top, _S_PANEL_W, content_top + content_h)

        thumb_labels = [
            "Alignment Summit", "The Problem Space", "Our Solution",
            "Road to Synergy", "KPIs & Metrics", "Risk Matrix", "Next Steps",
        ]
        tw, th = _S_PANEL_W - 24, 80
        tx2 = 12
        ty2 = content_top + 12
        for i, label in enumerate(thumb_labels):
            is_active = (i == 2)
            # selection border
            if is_active:
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor(66, 133, 244, 50)))
                p.drawRoundedRect(tx2 - 4, ty2 - 4, tw + 8, th + 8, 4, 4)
                p.setPen(QPen(_G_BLUE, 2))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(tx2 - 4, ty2 - 4, tw + 8, th + 8, 4, 4)
            # thumbnail
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawRect(tx2, ty2, tw, th)
            if is_active and self._slide_pixmap:
                from PyQt5.QtCore import Qt as _Qt
                scaled = self._slide_pixmap.scaled(tw, th, _Qt.KeepAspectRatioByExpanding,
                                                   _Qt.SmoothTransformation)
                p.setClipRect(tx2, ty2, tw, th)
                p.drawPixmap(tx2, ty2, scaled)
                p.setClipRect(0, 0, self.width(), self.height())
            else:
                p.setPen(_S_GREY_L)
                p.setFont(_font(8, bold=False))
                p.drawText(QRect(tx2, ty2, tw, th), Qt.AlignCenter, label)
            # slide number
            p.setPen(_S_GREY)
            p.setFont(_font(9, bold=False))
            p.drawText(QRect(0, ty2, tx2 - 2, th), Qt.AlignRight | Qt.AlignVCenter, str(i + 1))
            ty2 += th + 8
            if ty2 + th > content_top + content_h:
                break

        # ── Main slide canvas ─────────────────────────────────────────────
        canvas_x = _S_PANEL_W
        canvas_w = w - canvas_x
        canvas_cx = canvas_x + canvas_w // 2

        # 16:9 slide sizing — fit within available space with padding
        pad = 48
        avail_w = canvas_w - pad * 2
        avail_h = content_h - pad * 2
        slide_w = avail_w
        slide_h = int(slide_w * 9 / 16)
        if slide_h > avail_h:
            slide_h = avail_h
            slide_w = int(slide_h * 16 / 9)
        slide_x = canvas_cx - slide_w // 2
        slide_y = content_top + (content_h - slide_h) // 2

        # Canvas background
        p.fillRect(canvas_x, content_top, canvas_w, content_h, _S_CANVAS_BG)

        # Drop shadow
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_S_SLIDE_SHADOW))
        p.drawRect(slide_x + 6, slide_y + 6, slide_w, slide_h)

        # Slide white background
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawRect(slide_x, slide_y, slide_w, slide_h)

        # Slide content (slide.png)
        if self._slide_pixmap:
            from PyQt5.QtCore import Qt as _Qt
            scaled = self._slide_pixmap.scaled(slide_w, slide_h, _Qt.IgnoreAspectRatio,
                                               _Qt.SmoothTransformation)
            p.setClipRect(slide_x, slide_y, slide_w, slide_h)
            p.drawPixmap(slide_x, slide_y, scaled)
            p.setClipRect(0, 0, self.width(), self.height())
        else:
            # Fallback placeholder slide
            p.setPen(_S_INK)
            p.setFont(_font(24, bold=True))
            p.drawText(QRect(slide_x, slide_y, slide_w, slide_h // 2),
                       Qt.AlignCenter, "Q3 Leadership Alignment")
            p.setFont(_font(14, bold=False))
            p.setPen(_S_GREY)
            p.drawText(QRect(slide_x, slide_y + slide_h // 2, slide_w, slide_h // 2),
                       Qt.AlignCenter, "Dept. of Productivity  ·  Confidential")

        # Slide border
        p.setPen(QPen(_S_GREY_L, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(slide_x, slide_y, slide_w, slide_h)

    def _draw_slides_statusbar(self, p: QPainter, w: int, h: int) -> None:
        sy = h - _S_STATUS_H
        p.fillRect(0, sy, w, _S_STATUS_H, _S_TOPBAR_BG)
        p.setPen(QPen(_S_GREY_L, 1))
        p.drawLine(0, sy, w, sy)
        p.setPen(_S_GREY)
        p.setFont(_font(10, bold=False))
        p.drawText(QRect(16, sy, 300, _S_STATUS_H), Qt.AlignLeft | Qt.AlignVCenter,
                   "Slide 3 of 7  ·  Speaker notes hidden")
        p.drawText(QRect(w - 260, sy, 244, _S_STATUS_H), Qt.AlignRight | Qt.AlignVCenter,
                   "⊞ Present  ·  100%  ·  ⚙")

    # ── Background: Gmail ────────────────────────────────────────────────

    def _draw_gmail_bg(self, p: QPainter, w: int, h: int) -> None:
        p.fillRect(0, 0, w, h, _G_BG)
        self._draw_gmail_topbar(p, w)
        self._draw_gmail_sidebar(p, h)
        self._draw_gmail_emails(p, w, h)

    def _draw_gmail_topbar(self, p: QPainter, w: int) -> None:
        p.fillRect(0, 0, w, _G_TOPBAR_H, QColor(255, 255, 255))
        p.setPen(QPen(_G_GREY_L, 1))
        p.drawLine(0, _G_TOPBAR_H - 1, w, _G_TOPBAR_H - 1)

        # Hamburger lines
        p.setPen(QPen(_G_GREY, 2))
        for i in range(3):
            p.drawLine(18, 22 + i * 8, 38, 22 + i * 8)

        # Gmail logo image
        logo_size = 40
        logo_y = (_G_TOPBAR_H - logo_size) // 2
        if self._gmail_logo_pixmap:
            from PyQt5.QtCore import Qt as _Qt
            scaled = self._gmail_logo_pixmap.scaled(
                logo_size, logo_size, _Qt.KeepAspectRatio, _Qt.SmoothTransformation)
            p.drawPixmap(50, logo_y, scaled)
        else:
            p.setFont(_font(20, bold=False))
            p.setPen(_G_RED)
            p.drawText(QRect(52, 0, 22, _G_TOPBAR_H), Qt.AlignLeft | Qt.AlignVCenter, "G")
            p.setPen(_G_GREY)
            p.drawText(QRect(74, 0, 56, _G_TOPBAR_H), Qt.AlignLeft | Qt.AlignVCenter, "mail")

        # Search bar (centered)
        sb_w = min(640, w - 480)
        sb_x = (w - sb_w) // 2
        sb_y = 12
        sb_h = 40
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(232, 240, 254)))
        p.drawRoundedRect(sb_x, sb_y, sb_w, sb_h, 20, 20)
        p.setPen(QPen(_G_GREY, 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(sb_x + 14, sb_y + 11, 17, 17)
        p.drawLine(sb_x + 29, sb_y + 27, sb_x + 36, sb_y + 34)
        p.setPen(_G_GREY)
        p.setFont(_font(13, bold=False))
        p.drawText(QRect(sb_x + 46, sb_y, sb_w - 60, sb_h),
                   Qt.AlignLeft | Qt.AlignVCenter, "Search mail")

        # Right side: icons + avatar
        rx = w - 168
        p.setPen(_G_GREY)
        p.setFont(_font(18, bold=False))
        for icon in ["?", "⚙", "⊞"]:
            p.drawText(QRect(rx, 0, 40, _G_TOPBAR_H), Qt.AlignCenter, icon)
            rx += 44
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_G_BLUE))
        p.drawEllipse(rx + 4, 16, 30, 30)
        p.setPen(QColor(255, 255, 255))
        p.setFont(_font(11, bold=True))
        p.drawText(QRect(rx + 4, 16, 30, 30), Qt.AlignCenter, "KP")

    def _draw_gmail_sidebar(self, p: QPainter, h: int) -> None:
        p.fillRect(0, _G_TOPBAR_H, _G_SIDEBAR_W, h - _G_TOPBAR_H, QColor(255, 255, 255))

        # Compose button
        bx, by, bw2, bh2 = 16, _G_TOPBAR_H + 16, 144, 46
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(194, 231, 255)))
        p.drawRoundedRect(bx, by, bw2, bh2, 16, 16)
        p.setPen(QColor(0, 74, 119))
        p.setFont(_font(13, bold=False))
        p.drawText(QRect(bx + 14, by, bw2 - 14, bh2), Qt.AlignLeft | Qt.AlignVCenter, "✏  Compose")

        nav = [("Inbox", "3", True), ("Starred", "", False), ("Snoozed", "", False),
               ("Sent", "", False), ("Drafts", "1", False), ("More ▾", "", False)]
        ny = by + bh2 + 16
        for label, badge, selected in nav:
            if selected:
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor(210, 227, 252)))
                p.drawRoundedRect(8, ny, _G_SIDEBAR_W - 16, 36, 18, 18)
            p.setPen(_G_INK if selected else _G_GREY)
            p.setFont(_font(13, bold=selected))
            p.drawText(QRect(24, ny, 130, 36), Qt.AlignLeft | Qt.AlignVCenter, label)
            if badge:
                p.setPen(_G_INK)
                p.setFont(_font(12, bold=True))
                p.drawText(QRect(0, ny, _G_SIDEBAR_W - 20, 36),
                           Qt.AlignRight | Qt.AlignVCenter, badge)
            ny += 36

    def _draw_gmail_emails(self, p: QPainter, w: int, h: int) -> None:
        ex = _G_SIDEBAR_W

        # Tab bar
        tab_y = _G_TOPBAR_H
        p.fillRect(ex, tab_y, w - ex, _G_TAB_H, QColor(255, 255, 255))
        p.setPen(QPen(_G_GREY_L, 1))
        p.drawLine(ex, tab_y + _G_TAB_H - 1, w, tab_y + _G_TAB_H - 1)

        tx = ex + 16
        for tab_name, active in [("Primary", True), ("Social", False), ("Promotions", False)]:
            tab_w = 110
            if active:
                p.setPen(QPen(_G_BLUE, 3))
                p.drawLine(tx, tab_y + _G_TAB_H - 3, tx + tab_w, tab_y + _G_TAB_H - 3)
                p.setPen(_G_BLUE)
            else:
                p.setPen(_G_GREY)
            p.setFont(_font(12, bold=active))
            p.drawText(QRect(tx, tab_y, tab_w, _G_TAB_H), Qt.AlignCenter, tab_name)
            tx += tab_w + 8

        # Email rows
        row_y = tab_y + _G_TAB_H
        sender_col_w = 168
        for sender, subject, snippet, date, unread in self._inbox:
            if row_y + _G_ROW_H > h:
                break
            p.fillRect(ex, row_y, w - ex, _G_ROW_H,
                       _G_ROW_UNREAD if unread else _G_ROW_READ)
            p.setPen(QPen(_G_GREY_L, 1))
            p.drawLine(ex, row_y + _G_ROW_H - 1, w, row_y + _G_ROW_H - 1)

            # Checkbox
            p.setPen(QPen(_G_GREY_L, 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(ex + 14, row_y + (_G_ROW_H - 18) // 2, 18, 18)

            # Star
            p.setPen(_G_GREY_L)
            p.setFont(_font(15, bold=False))
            p.drawText(QRect(ex + 44, row_y, 22, _G_ROW_H), Qt.AlignCenter, "☆")

            # Sender
            p.setPen(_G_INK)
            p.setFont(_font(12, bold=unread))
            s = sender if len(sender) <= 16 else sender[:15] + "…"
            p.drawText(QRect(ex + 76, row_y, sender_col_w, _G_ROW_H),
                       Qt.AlignLeft | Qt.AlignVCenter, s)

            # Subject + snippet on two lines
            subj_x = ex + 76 + sender_col_w + 8
            subj_w = w - subj_x - 88
            mid_y = row_y + _G_ROW_H // 2
            p.setFont(_font(12, bold=unread))
            p.setPen(_G_INK)
            p.drawText(QRect(subj_x, row_y + 6, subj_w, mid_y - row_y - 4),
                       Qt.AlignLeft | Qt.AlignBottom, subject)
            p.setFont(_font(11, bold=False))
            p.setPen(_G_GREY)
            p.drawText(QRect(subj_x, mid_y, subj_w, _G_ROW_H // 2 - 4),
                       Qt.AlignLeft | Qt.AlignTop, snippet)

            # Date
            p.setFont(_font(11, bold=False))
            p.setPen(_G_GREY)
            p.drawText(QRect(w - 86, row_y, 78, _G_ROW_H),
                       Qt.AlignRight | Qt.AlignVCenter, date)

            # Unread dot
            if unread:
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(_G_BLUE))
                p.drawEllipse(w - 18, row_y + _G_ROW_H // 2 - 5, 10, 10)

            row_y += _G_ROW_H

    # ── Target: moving cell selection ─────────────────────────────────────

    def _draw_target(self, p: QPainter, state: GameState, t: float) -> None:
        tx, ty = int(state.target.x), int(state.target.y)
        tr = self._level_transition

        # ── Level 1: spreadsheet cell-selection rectangle ─────────────────
        if tr < 1.0:
            p.save()
            p.setOpacity(1.0 - tr)
            tw, th = 120, 36
            if state.tracking:
                phase = (t * 1.4) % 1.0
                glow_r = int(6 + phase * 20)
                alpha = int(180 * (1.0 - phase))
                p.setPen(QPen(QColor(_C_SEL.red(), _C_SEL.green(), _C_SEL.blue(), alpha), 4))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(tx - tw // 2 - glow_r, ty - th // 2 - glow_r,
                                  tw + glow_r * 2, th + glow_r * 2, 4, 4)
            sel_color = _C_BRAND if state.tracking else _C_SEL
            p.setPen(QPen(sel_color, 2))
            p.setBrush(QBrush(QColor(sel_color.red(), sel_color.green(), sel_color.blue(), 30)))
            p.drawRect(tx - tw // 2, ty - th // 2, tw, th)
            hs = 8
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(sel_color))
            for hx2, hy2 in [(tx-tw//2, ty-th//2), (tx+tw//2-hs, ty-th//2),
                             (tx-tw//2, ty+th//2-hs), (tx+tw//2-hs, ty+th//2-hs)]:
                p.drawRect(hx2, hy2, hs, hs)
            p.restore()

        # ── Level 2: Google G logo PNG ────────────────────────────────────
        if tr > 0.0 and self._target_pixmap:
            p.save()
            p.setOpacity(tr)
            r = int(state.target.radius)
            if state.tracking:
                for i in range(2):
                    phase = (t * 1.4 + i * 0.5) % 1.0
                    ring_r = r + 6 + int(phase * 45)
                    alpha = int(220 * (1.0 - phase))
                    p.setPen(QPen(QColor(88, 204, 2, alpha), 3))
                    p.setBrush(Qt.NoBrush)
                    p.drawEllipse(tx - ring_r, ty - ring_r, ring_r * 2, ring_r * 2)
            bounce = 1.0 + (0.05 * math.sin(t * 3.5) if state.tracking else 0.0)
            p.translate(tx, ty)
            p.scale(bounce, bounce)
            size = r * 2
            from PyQt5.QtCore import Qt as _Qt
            scaled = self._target_pixmap.scaled(size, size, _Qt.KeepAspectRatio, _Qt.SmoothTransformation)
            p.drawPixmap(-scaled.width() // 2, -scaled.height() // 2, scaled)
            p.restore()

    # ── Gaze cursor: spreadsheet cell cursor ──────────────────────────────

    def _draw_gaze(self, p: QPainter, state: GameState, t: float) -> None:
        gx, gy = state.gaze_x, state.gaze_y
        tr = self._level_transition
        dash_offset = (t * 35) % 16

        # ── Level 1: spreadsheet cell cursor ─────────────────────────────
        if tr < 1.0:
            p.save()
            p.setOpacity(1.0 - tr)
            cw, ch = 72, 22
            pen = QPen(_C_SEL, 2)
            pen.setStyle(Qt.DashLine)
            pen.setDashOffset(dash_offset)
            p.setPen(pen)
            p.setBrush(QBrush(_C_SEL_A))
            p.drawRect(gx - cw // 2, gy - ch // 2, cw, ch)
            fhs = 7
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(_C_SEL))
            p.drawRect(gx + cw // 2 - fhs, gy + ch // 2 - fhs, fhs, fhs)
            p.restore()

        # ── Level 2: dashed circle ────────────────────────────────────────
        if tr > 0.0:
            p.save()
            p.setOpacity(tr)
            gr = state.gaze_radius
            color = _C_BRAND if state.tracking else _C_SEL
            pen = QPen(QColor(color.red(), color.green(), color.blue(), 190), 2)
            pen.setStyle(Qt.DashLine)
            pen.setDashOffset(dash_offset)
            p.setPen(pen)
            p.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 28)))
            p.drawEllipse(gx - gr, gy - gr, gr * 2, gr * 2)
            p.restore()

    # ── HUD ───────────────────────────────────────────────────────────────

    def _draw_hud(self, p: QPainter, state: GameState, w: int, h: int, t: float) -> None:
        # Score pill (top-right)
        score_str = str(state.score)
        p.setFont(_font(12, bold=True))
        fm = p.fontMetrics()
        score_w = fm.horizontalAdvance(score_str)

        label = "Deliverables completed"
        p.setFont(_font(11, bold=False))
        lw = p.fontMetrics().horizontalAdvance(label)

        pill_w = lw + score_w + 60
        pill_h = 28
        pill_x = w - pill_w - 14
        pill_y = 10

        pop_age = t - self._score_pop_t
        if pop_age < 0.35:
            pop_s = 1.0 + 0.2 * math.sin(pop_age / 0.35 * math.pi)
            p.save()
            p.translate(pill_x + pill_w / 2, pill_y + pill_h / 2)
            p.scale(pop_s, pop_s)
            p.translate(-(pill_x + pill_w / 2), -(pill_y + pill_h / 2))

        p.setPen(QPen(_C_LINE, 1))
        p.setBrush(QBrush(QColor(255, 255, 255, 220)))
        p.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, pill_h // 2, pill_h // 2)

        p.setPen(_C_INK2)
        p.setFont(_font(11, bold=False))
        p.drawText(QRect(pill_x + 14, pill_y, lw + 10, pill_h), Qt.AlignLeft | Qt.AlignVCenter, label)

        p.setPen(QPen(_C_LINE2, 1))
        sep_x = pill_x + 14 + lw + 10
        p.drawLine(sep_x, pill_y + 6, sep_x, pill_y + pill_h - 6)

        p.setPen(_C_BRAND_D)
        p.setFont(_font(12, bold=True))
        p.drawText(QRect(sep_x + 8, pill_y, score_w + 14, pill_h), Qt.AlignLeft | Qt.AlignVCenter, score_str)

        # "live" chip
        chip_x = pill_x + pill_w + 8
        chip_w = 38
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_BRAND))
        p.drawRoundedRect(chip_x, pill_y + 4, chip_w, pill_h - 8, (pill_h - 8) // 2, (pill_h - 8) // 2)
        p.setPen(_C_SURFACE)
        p.setFont(_font(9, bold=True))
        p.drawText(QRect(chip_x, pill_y + 4, chip_w, pill_h - 8), Qt.AlignCenter, "live")

        if pop_age < 0.35:
            p.restore()

        # Bottom hint
        if state.bonus_active:
            hint = "Type the phrase exactly · ↵ submit · Esc quit"
        else:
            hint = "C  calibrate        Esc  quit"
        p.setFont(_font(10, bold=False))
        p.setPen(_C_INK3)
        p.drawText(QRect(0, h - _TABS_H - 26, w, 22), Qt.AlignCenter, hint)

    # ── Bonus deliverable popup ────────────────────────────────────────────

    def _pick_popup_pos(self, state: GameState) -> tuple:
        pw, ph = 320, 195
        w, h = self.width(), self.height()
        x_min, x_max = 20, max(20, w - pw - 20)
        y_min, y_max = 120, max(120, h - ph - 20)
        tx, ty = state.target.x, state.target.y
        for _ in range(40):
            x = random.randint(x_min, x_max)
            y = random.randint(y_min, y_max)
            # Keep away from target centre
            if math.hypot(x + pw // 2 - tx, y + ph // 2 - ty) < 260:
                continue
            # Keep away from previous popup position
            if math.hypot(x - self._popup_x, y - self._popup_y) < 220:
                continue
            return x, y
        return x_min, y_min

    def _draw_popup(self, p: QPainter, state: GameState, w: int, h: int, t: float) -> None:
        pw, ph = 320, 195
        px, py = self._popup_x, self._popup_y

        name, initials, av_color = _SENDERS[self._popup_sender_idx]

        # Drop shadow
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 60)))
        p.drawRoundedRect(px + 4, py + 4, pw, ph, 10, 10)

        # Card body
        p.setBrush(QBrush(_C_SURFACE))
        p.setPen(QPen(_C_LINE, 1))
        p.drawRoundedRect(px, py, pw, ph, 10, 10)

        # Header
        hdr_h = 36
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_HDR_BG))
        p.drawRoundedRect(px, py, pw, hdr_h, 10, 10)
        p.drawRect(px, py + hdr_h // 2, pw, hdr_h // 2)  # square bottom half

        p.setPen(QPen(_C_LINE, 1))
        p.drawLine(px, py + hdr_h, px + pw, py + hdr_h)

        # Header dot
        p.setPen(Qt.NoPen)
        grad_col = QColor(45, 75, 217)
        p.setBrush(QBrush(grad_col))
        p.drawRoundedRect(px + 10, py + 10, 14, 14, 3, 3)

        p.setPen(_C_INK)
        p.setFont(_font(11, bold=True))
        p.drawText(QRect(px + 30, py, 120, hdr_h), Qt.AlignLeft | Qt.AlignVCenter, "TeamPulse")
        p.setPen(_C_INK3)
        p.setFont(_font(10, bold=False))
        p.drawText(QRect(px + 100, py, pw - 120, hdr_h), Qt.AlignLeft | Qt.AlignVCenter, " · Direct message")

        # Close X
        p.setPen(_C_INK3)
        p.setFont(_font(14, bold=False))
        p.drawText(QRect(px + pw - 30, py, 26, hdr_h), Qt.AlignCenter, "×")

        # Body
        body_y = py + hdr_h + 10
        # Avatar
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(av_color))
        p.drawEllipse(px + 12, body_y, 32, 32)
        p.setPen(_C_SURFACE)
        p.setFont(_font(11, bold=True))
        p.drawText(QRect(px + 12, body_y, 32, 32), Qt.AlignCenter, initials)

        # Sender name + time
        p.setPen(_C_INK)
        p.setFont(_font(12, bold=True))
        p.drawText(QRect(px + 52, body_y, pw - 70, 18), Qt.AlignLeft | Qt.AlignVCenter, name)
        p.setPen(_C_INK3)
        p.setFont(_font(10, bold=False))
        p.drawText(QRect(px + 52, body_y + 18, pw - 70, 14), Qt.AlignLeft | Qt.AlignVCenter,
                   "now · typing to you specifically")

        # Message phrase
        p.setPen(_C_INK)
        p.setFont(_font(13, bold=False))
        p.drawText(QRect(px + 52, body_y + 34, pw - 66, 22), Qt.AlignLeft | Qt.AlignVCenter,
                   f'"{state.bonus_phrase}"')

        # Input field
        fi_y = body_y + 62
        fi_h = 36
        fi_x = px + 10
        fi_w = pw - 20

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(245, 245, 242)))
        p.drawRoundedRect(fi_x, fi_y, fi_w, fi_h, 8, 8)
        p.setPen(QPen(_C_LINE2, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(fi_x, fi_y, fi_w, fi_h, 8, 8)

        cursor_str = "▌" if int(t * 2) % 2 == 0 else " "
        typed = state.bonus_input + cursor_str
        # Color typed text green if it matches so far
        is_match = state.bonus_phrase.lower().startswith(state.bonus_input.lower())
        p.setPen(_C_BRAND if is_match and state.bonus_input else _C_INK)
        p.setFont(_font(12, bold=False))
        p.drawText(QRect(fi_x + 10, fi_y, fi_w - 20, fi_h), Qt.AlignLeft | Qt.AlignVCenter, typed)

        # Footer
        foot_y = fi_y + fi_h + 4
        foot_h = ph - (foot_y - py)
        p.setPen(QPen(_C_LINE, 1))
        p.drawLine(px, foot_y, px + pw, foot_y)
        half = pw // 2
        p.setPen(_C_SEL)
        p.setFont(_font(11, bold=True))
        p.drawText(QRect(px, foot_y, half, foot_h), Qt.AlignCenter, "↵ Reply")
        p.setPen(QPen(_C_LINE, 1))
        p.drawLine(px + half, foot_y + 4, px + half, py + ph - 4)
        p.setPen(_C_INK3)
        p.setFont(_font(11, bold=False))
        p.drawText(QRect(px + half, foot_y, half, foot_h), Qt.AlignCenter, "✓ Mark as read")

    # ── Danger vignette ───────────────────────────────────────────────────

    def _draw_vignette(self, p: QPainter, state: GameState, w: int, h: int, t: float) -> None:
        if state.drift_pct <= 0.01:
            return
        pulse = 0.5 + 0.5 * math.sin(t * math.pi * 2.5) if state.drift_pct > 0.5 else 1.0
        alpha = int(state.drift_pct * pulse * 200)
        color = QColor(_C_DANGER.red(), _C_DANGER.green(), _C_DANGER.blue(), alpha)
        pen = QPen(color, max(1, int(state.drift_pct * 80)))
        pen.setStyle(Qt.SolidLine)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        inset = int(state.drift_pct * 80)
        p.drawRect(inset, inset, w - inset * 2, h - inset * 2)

        # Inner glow at edges
        edge = max(1, int(state.drift_pct * 60))
        grad_alpha = int(state.drift_pct * pulse * 140)
        for i in range(3):
            a = max(0, grad_alpha - i * 40)
            p.setPen(QPen(QColor(_C_DANGER.red(), _C_DANGER.green(), _C_DANGER.blue(), a),
                          max(1, edge - i * 10)))
            off = inset + i * 12
            p.drawRect(off, off, w - off * 2, h - off * 2)

    # ── Welcome screen (Orbit-style) ──────────────────────────────────────

    def _draw_welcome(self, p: QPainter, w: int, h: int) -> None:
        _GBL = QColor( 66, 133, 244)
        _GRD = QColor(234,  67,  53)
        _GYL = QColor(251, 188,   5)
        _GGR = QColor( 52, 168,  83)
        _GRY = QColor( 95,  99, 104)

        # ── Background ───────────────────────────────────────────────────
        p.fillRect(0, 0, w, h, QColor(229, 234, 244))

        # ── Top navigation bar ────────────────────────────────────────────
        bar_h = 4
        nav_h = 52
        # 4-color accent stripe across full width
        seg_w = w // 4
        for i, col in enumerate([_GBL, _GRD, _GYL, _GGR]):
            bx = i * seg_w
            bw2 = seg_w if i < 3 else w - seg_w * 3
            p.fillRect(bx, 0, bw2, bar_h, col)
        # White navbar
        p.fillRect(0, bar_h, w, nav_h, QColor(255, 255, 255))
        p.setPen(QPen(QColor(218, 220, 224), 1))
        p.drawLine(0, bar_h + nav_h - 1, w, bar_h + nav_h - 1)

        nav_y = bar_h   # top of navbar area
        # Left: grid icon + tiny logo + "Orbit" + separator + "Vision Assessment"
        nx = 16
        p.setPen(_GRY)
        p.setFont(_font(18, bold=False))
        p.drawText(QRect(nx, nav_y, 36, nav_h), Qt.AlignCenter, "⊞")
        nx += 42
        if self._target_pixmap:
            tiny = self._target_pixmap.scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(nx, nav_y + (nav_h - 26) // 2, tiny)
            nx += 30
        p.setPen(QColor(30, 30, 30))
        p.setFont(_font(14, bold=True))
        p.drawText(QRect(nx, nav_y, 60, nav_h), Qt.AlignLeft | Qt.AlignVCenter, "Orbit")
        nx += p.fontMetrics().horizontalAdvance("Orbit") + 10
        p.setPen(QPen(QColor(200, 200, 200), 1))
        p.drawLine(nx, nav_y + 12, nx, nav_y + nav_h - 12)
        nx += 12
        p.setPen(_GRY)
        p.setFont(_font(13, bold=False))
        p.drawText(QRect(nx, nav_y, 180, nav_h), Qt.AlignLeft | Qt.AlignVCenter, "Vision Assessment")

        # Center: search bar
        sb_w = min(440, w - 600)
        sb_x = (w - sb_w) // 2
        sb_y = nav_y + (nav_h - 34) // 2
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(241, 243, 244)))
        p.drawRoundedRect(sb_x, sb_y, sb_w, 34, 17, 17)
        p.setPen(_GRY)
        p.setFont(_font(13, bold=False))
        fm_sb = p.fontMetrics()
        p.drawText(QRect(sb_x + 14, sb_y, 22, 34), Qt.AlignCenter, "🔍")
        p.drawText(QRect(sb_x + 38, sb_y, sb_w - 50, 34),
                   Qt.AlignLeft | Qt.AlignVCenter, "Search")

        # Right: LABS badge · bell · (0) · avatar
        rx = w - 14
        av_d = 32
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_GBL))
        p.drawEllipse(rx - av_d, nav_y + (nav_h - av_d) // 2, av_d, av_d)
        p.setPen(QColor(255, 255, 255))
        p.setFont(_font(12, bold=True))
        p.drawText(QRect(rx - av_d, nav_y + (nav_h - av_d) // 2, av_d, av_d),
                   Qt.AlignCenter, "J")
        rx -= av_d + 10
        p.setPen(_GRY)
        p.setFont(_font(11, bold=False))
        p.drawText(QRect(rx - 28, nav_y, 28, nav_h), Qt.AlignCenter, "(0)")
        rx -= 32
        p.setFont(_font(16, bold=False))
        p.drawText(QRect(rx - 28, nav_y, 28, nav_h), Qt.AlignCenter, "🔔")
        rx -= 36
        labs_w = 46
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(103, 58, 183)))
        p.drawRoundedRect(rx - labs_w, nav_y + (nav_h - 22) // 2, labs_w, 22, 4, 4)
        p.setPen(QColor(255, 255, 255))
        p.setFont(_font(9, bold=True))
        p.drawText(QRect(rx - labs_w, nav_y + (nav_h - 22) // 2, labs_w, 22),
                   Qt.AlignCenter, "LABS")

        # ── Card ─────────────────────────────────────────────────────────
        nav_total = bar_h + nav_h
        card_w  = min(700, max(500, w // 2 + 60))
        card_h  = 640
        card_x  = (w - card_w) // 2
        card_y  = nav_total + max(16, (h - nav_total - card_h) // 2)
        card_cx = card_x + card_w // 2

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 45)))
        p.drawRoundedRect(card_x + 6, card_y + 8, card_w, card_h, 20, 20)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawRoundedRect(card_x, card_y, card_w, card_h, 20, 20)

        # 4-color top bar clipped to card
        p.save()
        clip = QPainterPath()
        clip.addRoundedRect(card_x, card_y, card_w, card_h, 20, 20)
        p.setClipPath(clip)
        cseg = card_w // 4
        for i, col in enumerate([_GBL, _GRD, _GYL, _GGR]):
            bx = card_x + i * cseg
            bw2 = cseg if i < 3 else card_w - cseg * 3
            p.fillRect(bx, card_y, bw2, 6, col)
        p.restore()

        # ── Content ───────────────────────────────────────────────────────
        cy = card_y + 6 + 32

        # Logo icon
        icon_sz  = 80
        frame_sz = icon_sz + 20
        frame_x  = card_cx - frame_sz // 2
        p.setPen(QPen(QColor(218, 218, 218), 1))
        p.setBrush(QBrush(QColor(246, 246, 246)))
        p.drawRoundedRect(frame_x, cy, frame_sz, frame_sz, 18, 18)
        if self._target_pixmap:
            scaled = self._target_pixmap.scaled(
                icon_sz, icon_sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(frame_x + (frame_sz - scaled.width()) // 2,
                         cy     + (frame_sz - scaled.height()) // 2, scaled)
        cy += frame_sz + 16

        # "Orbit"
        p.setPen(QColor(20, 20, 20))
        p.setFont(_font(42, bold=True))
        p.drawText(QRect(card_x, cy, card_w, 54), Qt.AlignCenter, "Orbit")
        cy += 54 + 10

        # "PERIPHERAL VISION ASSESSMENT  PROTOCOL A  —  by  Google"
        tag1  = "PERIPHERAL VISION ASSESSMENT"
        tag2  = "  PROTOCOL A"
        by_s  = "  —  by  "
        p.setFont(_font(10, bold=False))
        fm_s   = p.fontMetrics()
        t1_w   = fm_s.horizontalAdvance(tag1)
        t2_w   = fm_s.horizontalAdvance(tag2)
        by_w   = fm_s.horizontalAdvance(by_s)
        p.setFont(_font(11, bold=True))
        fm_g   = p.fontMetrics()
        g_ws   = [fm_g.horizontalAdvance(c) for c in "Google"]
        total_w = t1_w + t2_w + by_w + sum(g_ws)
        rx = card_cx - total_w // 2
        base = cy + 16
        p.setFont(_font(10, bold=False))
        p.setPen(QColor(130, 130, 130))
        p.drawText(rx, base, tag1);  rx += t1_w
        p.setPen(QColor(100, 100, 100))
        p.drawText(rx, base, tag2);  rx += t2_w
        p.setPen(QColor(130, 130, 130))
        p.drawText(rx, base, by_s);  rx += by_w
        p.setFont(_font(11, bold=True))
        for ch, col, cw in zip("Google", [_GBL, _GRD, _GYL, _GBL, _GGR, _GRD], g_ws):
            p.setPen(col)
            p.drawText(rx, base, ch)
            rx += cw
        cy += 24

        # "v3.2.1-q3.rc.4  ·  ~3 min  ·  non-optional"
        p.setPen(QColor(160, 160, 160))
        p.setFont(_font(10, bold=False))
        p.drawText(QRect(card_x, cy, card_w, 20), Qt.AlignCenter,
                   "v3.2.1-q3.rc.4  ·  ~3 min  ·  non-optional")
        cy += 20 + 26

        # ── Steps ─────────────────────────────────────────────────────────
        step_colors = [_GBL, _GRD, _GGR]
        steps = [
            ("Look at the center of the screen",
             "then press C to calibrate and start the game."),
            ("Follow the target",
             "with your gaze and head movement throughout the session."),
            ("Try to respond to your corporate colleagues",
             "by completing their deliverables as they appear."),
        ]
        pad_l  = 44
        circ_d = 28
        text_x = card_x + pad_l + circ_d + 14
        text_w = card_w - pad_l - circ_d - 14 - 36
        line_h = 20

        for i, (bold_lbl, desc) in enumerate(steps):
            sy = cy
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(step_colors[i]))
            p.drawEllipse(card_x + pad_l, sy, circ_d, circ_d)
            p.setPen(QColor(255, 255, 255))
            p.setFont(_font(10, bold=True))
            p.drawText(QRect(card_x + pad_l, sy, circ_d, circ_d), Qt.AlignCenter, str(i + 1))

            p.setFont(_font(12, bold=True))
            p.setPen(QColor(25, 25, 25))
            lbl_w  = p.fontMetrics().horizontalAdvance(bold_lbl + " ")
            base_y = sy + circ_d // 2 + 5
            p.drawText(text_x, base_y, bold_lbl + " ")

            p.setFont(_font(12, bold=False))
            p.setPen(QColor(70, 70, 70))
            fm_d = p.fontMetrics()
            avail = text_w - lbl_w
            words = desc.split()
            line1: list = []
            for word in words:
                test = " ".join(line1 + [word])
                if fm_d.horizontalAdvance(test) <= avail:
                    line1.append(word)
                else:
                    break
            rest_words = words[len(line1):]
            p.drawText(text_x + lbl_w, base_y, " ".join(line1))
            if rest_words:
                p.drawText(text_x, base_y + line_h, " ".join(rest_words))
                cy += max(circ_d, line_h * 2 + 8) + 14
            else:
                cy += max(circ_d, line_h + 4) + 14

        cy += 8

        # ── "Begin Assessment →" button ───────────────────────────────────
        btn_w = card_w - 80
        btn_h = 54
        btn_x = card_cx - btn_w // 2
        self._start_btn_rect = QRect(btn_x, cy, btn_w, btn_h)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_GBL))
        p.drawRoundedRect(btn_x, cy, btn_w, btn_h, btn_h // 2, btn_h // 2)
        p.setPen(QColor(255, 255, 255))
        p.setFont(_font(14, bold=True))
        p.drawText(QRect(btn_x, cy, btn_w, btn_h), Qt.AlignCenter, "Begin Assessment  →")
        cy += btn_h + 14

        # Footer
        p.setPen(QColor(175, 175, 175))
        p.setFont(_font(9, bold=False))
        p.drawText(QRect(card_x, cy, card_w, 20), Qt.AlignCenter,
                   "A cognitive performance assessment by Orbit Labs™")


    # ── Developer mode overlay ────────────────────────────────────────────

    def _draw_dev_hold_progress(self, p: QPainter, w: int, h: int, progress: float) -> None:
        bar_w, bar_h = 120, 4
        bx = (w - bar_w) // 2
        by = h - 30
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(60, 60, 60, 180)))
        p.drawRoundedRect(bx, by, bar_w, bar_h, 2, 2)
        p.setBrush(QBrush(QColor(255, 160, 0)))
        p.drawRoundedRect(bx, by, int(bar_w * progress), bar_h, 2, 2)

    def _draw_dev_overlay(self, p: QPainter, w: int, h: int) -> None:
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 160))

        panel_w, panel_h = 420, 330
        px = (w - panel_w) // 2
        py = (h - panel_h) // 2

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(28, 28, 30)))
        p.drawRoundedRect(px, py, panel_w, panel_h, 16, 16)

        p.setPen(QColor(255, 160, 0))
        p.setFont(_font(11, bold=True))
        p.drawText(QRect(px, py + 22, panel_w, 24), Qt.AlignCenter, "⚙  DEVELOPER MODE")

        p.setPen(QColor(150, 150, 155))
        p.setFont(_font(11, bold=False))
        p.drawText(QRect(px, py + 50, panel_w, 20), Qt.AlignCenter, "Select starting level")

        level_labels = [f"Level {lvl}  —  {LEVEL_NAMES[lvl]}" for lvl in sorted(LEVEL_NAMES)]
        level_hints  = [f"Score starts at {LEVEL_START_SCORES[lvl]}" for lvl in sorted(LEVEL_START_SCORES)]
        btn_w, btn_h = panel_w - 60, 52
        btn_x = px + 30
        by = py + 82

        for i, (label, hint) in enumerate(zip(level_labels, level_hints)):
            level = i + 1
            selected = level == self._dev_selected_level
            if selected:
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor(45, 75, 217)))
                p.drawRoundedRect(btn_x, by, btn_w, btn_h, 10, 10)
                name_col = QColor(255, 255, 255)
                hint_col = QColor(180, 200, 255)
            else:
                p.setPen(QPen(QColor(70, 70, 75), 1))
                p.setBrush(QBrush(QColor(44, 44, 46)))
                p.drawRoundedRect(btn_x, by, btn_w, btn_h, 10, 10)
                name_col = QColor(190, 190, 195)
                hint_col = QColor(110, 110, 115)

            p.setPen(name_col)
            p.setFont(_font(12, bold=True))
            p.drawText(QRect(btn_x + 16, by, btn_w - 16, btn_h // 2 + 6),
                       Qt.AlignLeft | Qt.AlignVCenter, f"{level}   {label}")
            p.setPen(hint_col)
            p.setFont(_font(10, bold=False))
            p.drawText(QRect(btn_x + 16, by + btn_h // 2, btn_w - 16, btn_h // 2),
                       Qt.AlignLeft | Qt.AlignVCenter, hint)
            by += btn_h + 10

        p.setPen(QColor(100, 100, 105))
        p.setFont(_font(10, bold=False))
        p.drawText(QRect(px, by + 10, panel_w, 20), Qt.AlignCenter,
                   "1 / 2 / 3  to select   ·   Enter  to start   ·   Esc  to cancel")

    # ── Waiting/calibrate screen ──────────────────────────────────────────

    def _draw_waiting(self, p: QPainter, w: int, h: int) -> None:
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 120))

        msg = "Look at the center of the screen, then press  C  to calibrate"
        p.setFont(_font(24, bold=True))
        fm = p.fontMetrics()
        msg_w = fm.horizontalAdvance(msg)
        msg_h = 36
        pill_pad_x, pill_pad_y = 28, 14
        pill_w = msg_w + pill_pad_x * 2
        pill_h = msg_h + pill_pad_y * 2
        pill_x = (w - pill_w) // 2
        pill_y = h // 2 - 80

        # Dark pill backdrop
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 180)))
        p.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, pill_h // 2, pill_h // 2)

        p.setPen(QColor(255, 255, 255))
        p.drawText(QRect(pill_x, pill_y, pill_w, pill_h), Qt.AlignCenter, msg)
        bw2, bh2 = 64, 64
        bx2 = (w - bw2) // 2
        by2 = h // 2 + 20
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_BRAND_D))
        p.drawRoundedRect(bx2, by2 + 4, bw2, bh2, 14, 14)
        p.setBrush(QBrush(_C_BRAND))
        p.drawRoundedRect(bx2, by2, bw2, bh2, 14, 14)
        p.setPen(_C_SURFACE)
        p.setFont(_font(28, bold=True))
        p.drawText(QRect(bx2, by2, bw2, bh2), Qt.AlignCenter, "C")

    # ── Countdown ─────────────────────────────────────────────────────────

    def _draw_countdown(self, p: QPainter, state: GameState, w: int, h: int, t: float) -> None:
        p.fillRect(0, 0, w, h, QColor(31, 32, 36, 210))

        num = math.ceil(state.countdown) if state.countdown > 0 else 0
        age = 1.0 - (state.countdown % 1.0) if state.countdown > 0 else 1.0
        scale = 1.0 + 0.65 * max(0.0, 1.0 - age / 0.22)

        colors = {3: QColor(196, 52, 43), 2: QColor(208, 138, 31), 1: _C_BRAND, 0: _C_SURFACE}
        color = colors.get(num, _C_SURFACE)

        p.save()
        p.translate(w / 2, h / 2 - 30)
        p.scale(scale, scale)
        p.setPen(color)
        p.setFont(_font(120, bold=True))
        label = str(num) if num > 0 else "GO!"
        p.drawText(QRect(-350, -110, 700, 220), Qt.AlignCenter, label)
        p.restore()

        p.setPen(_C_INK3)
        p.setFont(_font(14, bold=False))
        p.drawText(QRect(0, h // 2 + 60, w, 30), Qt.AlignCenter,
                   "Keep your gaze on the moving selection")

    # ── Game over: YOU'RE FIRED ────────────────────────────────────────────

    def _draw_fired(self, p: QPainter, state: GameState, w: int, h: int) -> None:
        # Dark red background gradient
        grad = QRadialGradient(w / 2, h / 2, max(w, h) * 0.7)
        grad.setColorAt(0.0, QColor(196, 52, 43))
        grad.setColorAt(1.0, QColor(80, 12, 8))
        p.fillRect(0, 0, w, h, QBrush(grad))

        cy = h // 2

        # "YOU'RE FIRED" — Impact-style
        p.setFont(_font(96, bold=True))
        p.setPen(QColor(0, 0, 0, 120))
        p.drawText(QRect(6, cy - 164, w, 160), Qt.AlignCenter, "YOU'RE FIRED")
        p.setPen(_C_SURFACE)
        p.drawText(QRect(0, cy - 168, w, 160), Qt.AlignCenter, "YOU'RE FIRED")

        # Subtitle
        p.setFont(_font(15, bold=False, mono=True))
        p.setPen(QColor(255, 255, 255, 200))
        p.drawText(QRect(0, cy + 8, w, 28), Qt.AlignCenter,
                   "effective immediately  ·  please vacate the pod")

        # Divider
        p.setPen(QPen(QColor(255, 255, 255, 50), 1))
        p.drawLine(w // 2 - 180, cy + 50, w // 2 + 180, cy + 50)

        # Stats
        p.setFont(_font(26, bold=True))
        p.setPen(_C_SURFACE)
        p.drawText(QRect(0, cy + 58, w, 40), Qt.AlignCenter, f"{state.score}")
        p.setFont(_font(11, bold=False))
        p.setPen(QColor(255, 255, 255, 160))
        p.drawText(QRect(0, cy + 100, w, 20), Qt.AlignCenter, "deliverables completed before termination")

        # Verdict from HR
        if state.score >= 60:
            verdict_idx = 3  # Peak Performer
        elif state.score >= 20:
            verdict_idx = 0  # Meets Expectations
        elif state.score >= 5:
            verdict_idx = 1  # Needs Improvement
        else:
            verdict_idx = 2  # Terminated
        band, verdict = _HR_VERDICTS[verdict_idx]

        vcard_w, vcard_h = 480, 64
        vcard_x = (w - vcard_w) // 2
        vcard_y = cy + 128
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 80)))
        p.drawRoundedRect(vcard_x, vcard_y, vcard_w, vcard_h, 6, 6)
        p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(vcard_x, vcard_y, vcard_w, vcard_h, 6, 6)
        p.setPen(QColor(255, 255, 255, 100))
        p.setFont(_font(9, bold=True))
        p.drawText(QRect(vcard_x + 14, vcard_y + 8, vcard_w - 28, 14), Qt.AlignLeft, "VERDICT FROM HR")
        p.setPen(_C_SURFACE)
        p.setFont(_font(11, bold=False))
        p.drawText(QRect(vcard_x + 14, vcard_y + 24, vcard_w - 28, 32),
                   Qt.AlignLeft | Qt.TextWordWrap, verdict)

        # Restart button
        bw2, bh2 = 280, 44
        bx2 = (w - bw2) // 2
        by2 = vcard_y + vcard_h + 24
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 40)))
        p.drawRoundedRect(bx2, by2, bw2, bh2, 8, 8)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(_C_SURFACE))
        p.drawRoundedRect(bx2, by2, bw2, bh2, 8, 8)
        p.setPen(_C_DANGER)
        p.setFont(_font(14, bold=True))
        p.drawText(QRect(bx2, by2, bw2, bh2), Qt.AlignCenter, "R — Run Another Sprint")

        p.setPen(QColor(255, 255, 255, 100))
        p.setFont(_font(10, bold=False))
        p.drawText(QRect(0, by2 + bh2 + 12, w, 20), Qt.AlignCenter,
                   "signed, The Algorithm  ·  Esc to quit")


def _load_bundled_fonts() -> None:
    for ttf in (ASSETS_DIR / "fonts").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(ttf))


class PyQtRenderer(GameRenderer):
    def start(self, gaze_provider: GazeProvider) -> None:
        # When frozen by PyInstaller, Qt doesn't know where its plugins landed.
        # Point it at the extracted _MEIPASS tree before QApplication starts.
        if getattr(sys, "frozen", False):
            meipass = Path(sys._MEIPASS)
            for candidate in [
                meipass / "PyQt5" / "Qt5" / "plugins",
                meipass / "PyQt5" / "Qt" / "plugins",
                meipass / "PyQt5",
                meipass,
            ]:
                if candidate.exists():
                    os.environ["QT_PLUGIN_PATH"] = str(candidate)
                    break

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        _load_bundled_fonts()
        screen = app.primaryScreen().geometry()
        w, h = screen.width(), screen.height()

        gaze_provider.start()
        engine = GameEngine(w, h, gaze_provider)

        win = QMainWindow()
        widget = _GameWidget(engine, win)
        win.setCentralWidget(widget)
        win.setWindowTitle("Dept. of Productivity — Peripheral Vision Assessment")
        win.showFullScreen()
        widget.setFocus()

        exit_code = app.exec_()
        gaze_provider.stop()
        sys.exit(exit_code)
