import math
from pathlib import Path
from typing import List, Tuple

from ..config import ASSETS_DIR, BONUS_APPEAR_AFTER, BONUS_POINTS, TARGET_RADIUS
from ..gaze_providers.base import GazeProvider
from .state import GamePhase, GameState, Target

_OMEGA_X = 0.25
_OMEGA_Y = 0.18
_AMPLITUDE_FRACTION = 0.78
_COUNTDOWN_START = 3.0


class GameEngine:
    def __init__(self, screen_width: int, screen_height: int, gaze_provider: GazeProvider) -> None:
        self._gaze = gaze_provider
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._cx = screen_width / 2
        self._cy = screen_height / 2
        self._ax = self._cx * _AMPLITUDE_FRACTION
        self._ay = self._cy * _AMPLITUDE_FRACTION

        bonus_dir = ASSETS_DIR / "bonus"
        self._bonus_items: List[Tuple[str, str]] = [
            (str(f), f.stem)
            for f in sorted(bonus_dir.iterdir())
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        ]

        self._t = 0.0
        self._elapsed = 0.0
        self._tracking_acc = 0.0
        self._bonus_score = 0
        self._bonus_index = 0
        self._state = self._initial_state()

    def _initial_state(self) -> GameState:
        return GameState(
            target=Target(x=self._cx, y=self._cy, radius=TARGET_RADIUS),
            phase=GamePhase.COUNTDOWN,
            countdown=_COUNTDOWN_START,
            screen_width=self._screen_width,
            screen_height=self._screen_height,
        )

    @property
    def state(self) -> GameState:
        return self._state

    def reset(self) -> None:
        self._t = 0.0
        self._elapsed = 0.0
        self._tracking_acc = 0.0
        self._bonus_score = 0
        self._bonus_index = 0
        self._state = self._initial_state()

    # ── Bonus input handling (called by renderer on keypresses) ──────────────

    def handle_char(self, c: str) -> None:
        if self._state.bonus_active and self._state.phase == GamePhase.PLAYING:
            self._state.bonus_input += c

    def handle_backspace(self) -> None:
        if self._state.bonus_active and self._state.phase == GamePhase.PLAYING:
            self._state.bonus_input = self._state.bonus_input[:-1]

    def handle_submit(self) -> None:
        state = self._state
        if not state.bonus_active or state.phase != GamePhase.PLAYING:
            return
        if not self._bonus_items:
            return
        _, answer = self._bonus_items[self._bonus_index]
        if state.bonus_input.strip().lower() == answer.lower():
            self._bonus_score += BONUS_POINTS
            state.score = int(self._tracking_acc) + self._bonus_score
            self._next_bonus()
        state.bonus_input = ""

    def _next_bonus(self) -> None:
        self._bonus_index = (self._bonus_index + 1) % len(self._bonus_items)
        path, _ = self._bonus_items[self._bonus_index]
        self._state.bonus_image_path = path

    # ── Main update loop ─────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        state = self._state

        if state.phase == GamePhase.GAME_OVER:
            return

        gx, gy = self._gaze.get_gaze_position()
        state.gaze_x, state.gaze_y = gx, gy

        if state.phase == GamePhase.COUNTDOWN:
            state.countdown -= dt
            if state.countdown <= 0:
                state.phase = GamePhase.PLAYING
                self._t = 0.0
            return

        # PLAYING
        self._t += dt
        self._elapsed += dt

        state.target.x = self._cx + self._ax * math.sin(_OMEGA_X * self._t)
        state.target.y = self._cy + self._ay * math.sin(_OMEGA_Y * self._t)

        dist = math.hypot(gx - state.target.x, gy - state.target.y)
        state.tracking = dist <= state.target.radius + state.gaze_radius
        if state.tracking:
            self._tracking_acc += dt
            state.score = int(self._tracking_acc) + self._bonus_score
        else:
            state.phase = GamePhase.GAME_OVER
            return

        # Activate bonus after threshold
        if (not state.bonus_active
                and self._elapsed >= BONUS_APPEAR_AFTER
                and self._bonus_items):
            state.bonus_active = True
            path, _ = self._bonus_items[self._bonus_index]
            state.bonus_image_path = path

    def calibrate(self) -> None:
        self._gaze.calibrate()
