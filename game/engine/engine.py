import math

from ..gaze_providers.base import GazeProvider
from .state import GamePhase, GameState, Target

# Lissajous frequencies (rad/s). Irrational ratio keeps path from repeating quickly.
_OMEGA_X = 0.25
_OMEGA_Y = 0.18

# Fraction of half-screen used as amplitude (keeps target away from edges).
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
        self._state = self._initial_state()

    def _initial_state(self) -> GameState:
        return GameState(
            target=Target(x=self._cx, y=self._cy),
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
        self._state = self._initial_state()

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
        state.target.x = self._cx + self._ax * math.sin(_OMEGA_X * self._t)
        state.target.y = self._cy + self._ay * math.sin(_OMEGA_Y * self._t)

        dist = math.hypot(gx - state.target.x, gy - state.target.y)
        state.tracking = dist <= state.target.radius + state.gaze_radius
        if state.tracking:
            state.score += 1
        else:
            state.phase = GamePhase.GAME_OVER

    def calibrate(self) -> None:
        self._gaze.calibrate()
