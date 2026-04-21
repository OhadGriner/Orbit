import math
import random

from ..config import BONUS_APPEAR_AFTER, BONUS_POINTS, TARGET_RADIUS
from ..gaze_providers.base import GazeProvider
from .state import GamePhase, GameState, Target

_OMEGA_X = 0.25
_OMEGA_Y = 0.18
_AMPLITUDE_FRACTION = 0.78
_COUNTDOWN_START = 3.0
_LOOKAWAY_FIRE_S = 3.0  # seconds of continuous drift before termination

_BUZZ_PHRASES = [
    "Let's take this offline",
    "Circle back on that",
    "Move the needle",
    "It is what it is",
    "Per my last email",
    "Synergy",
    "Low-hanging fruit",
    "Boil the ocean",
    "Hard stop at 3",
    "Let's put a pin in it",
    "Bandwidth",
    "Quick wins",
    "Touch base",
    "Going forward",
    "Reach out",
    "At the end of the day",
    "Deep dive",
    "Think outside the box",
    "Game changer",
    "Leverage our core competencies",
]


class GameEngine:
    def __init__(self, screen_width: int, screen_height: int, gaze_provider: GazeProvider) -> None:
        self._gaze = gaze_provider
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._cx = screen_width / 2
        self._cy = screen_height / 2
        self._ax = self._cx * _AMPLITUDE_FRACTION
        self._ay = self._cy * _AMPLITUDE_FRACTION

        self._t = 0.0
        self._elapsed = 0.0
        self._tracking_acc = 0.0
        self._bonus_score = 0
        self._bonus_index = 0
        self._drift_s = 0.0
        self._state = self._initial_state()

    def _initial_state(self) -> GameState:
        return GameState(
            target=Target(x=self._cx, y=self._cy, radius=TARGET_RADIUS),
            phase=GamePhase.WELCOME,
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
        self._drift_s = 0.0
        self._state = self._initial_state()

    # ── Bonus input (called by renderer on keypresses) ────────────────────

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
        if state.bonus_input.strip().lower() == state.bonus_phrase.lower():
            self._bonus_score += BONUS_POINTS
            state.score = int(self._tracking_acc) + self._bonus_score
            self._next_phrase()
        state.bonus_input = ""

    def _next_phrase(self) -> None:
        self._bonus_index = (self._bonus_index + 1) % len(_BUZZ_PHRASES)
        self._state.bonus_phrase = _BUZZ_PHRASES[self._bonus_index]

    # ── Main update loop ──────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        state = self._state

        if state.phase in (GamePhase.WELCOME, GamePhase.GAME_OVER):
            gx, gy = self._gaze.get_gaze_position()
            state.gaze_x, state.gaze_y = gx, gy
            return

        if state.phase == GamePhase.WAITING:
            gx, gy = self._gaze.get_gaze_position()
            state.gaze_x, state.gaze_y = gx, gy
            return

        gx, gy = self._gaze.get_gaze_position()
        state.gaze_x, state.gaze_y = gx, gy

        if state.phase == GamePhase.COUNTDOWN:
            state.countdown -= dt
            if state.countdown <= 0:
                state.phase = GamePhase.PLAYING
            return

        # PLAYING
        self._t += dt
        self._elapsed += dt

        state.target.x = self._cx + self._ax * math.sin(_OMEGA_X * self._t)
        state.target.y = self._cy + self._ay * math.sin(_OMEGA_Y * self._t)

        dist = math.hypot(gx - state.target.x, gy - state.target.y)
        state.tracking = dist <= state.target.radius + state.gaze_radius

        if state.tracking:
            self._drift_s = max(0.0, self._drift_s - dt * 2)
            self._tracking_acc += dt
            state.score = int(self._tracking_acc) + self._bonus_score
        else:
            self._drift_s += dt
            if self._drift_s >= _LOOKAWAY_FIRE_S:
                state.phase = GamePhase.GAME_OVER
                state.drift_pct = 1.0
                return

        state.drift_pct = min(1.0, self._drift_s / _LOOKAWAY_FIRE_S)

        if (not state.bonus_active
                and self._elapsed >= BONUS_APPEAR_AFTER
                and _BUZZ_PHRASES):
            state.bonus_active = True
            self._bonus_index = random.randrange(len(_BUZZ_PHRASES))
            state.bonus_phrase = _BUZZ_PHRASES[self._bonus_index]

    def click_start(self) -> None:
        if self._state.phase == GamePhase.WELCOME:
            self._state.phase = GamePhase.WAITING

    def calibrate(self) -> None:
        self._gaze.calibrate()
        if self._state.phase == GamePhase.WAITING:
            self._t = 0.0  # target begins at screen centre (sin(0) = 0)
            self._state.target.x = self._cx
            self._state.target.y = self._cy
            self._state.phase = GamePhase.COUNTDOWN
            self._state.countdown = _COUNTDOWN_START
