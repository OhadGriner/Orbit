import math
import random

from ..config import BONUS_APPEAR_AFTER, BONUS_POINTS, LEVEL_START_SCORES, TARGET_RADIUS, WIN_SCORE
from ..gaze_providers.base import GazeProvider
from .state import GamePhase, GameState, Target

_COUNTDOWN_START = 3.0
_LOOKAWAY_FIRE_S = 3.0  # seconds of continuous drift before termination

# ── Speed profiles (pixels / second) ─────────────────────────────────────────
# Level 1: DVD-style linear bounce, slow and predictable
L1_SPEED_START = 80.0    # px/s at the start of level 1
L1_SPEED_END   = 180.0   # px/s at full ramp
L1_RAMP_S      = 10.0    # seconds until full speed is reached

# Level 2: same DVD bounce, starts faster
L2_SPEED_START = 180.0
L2_SPEED_END   = 380.0
L2_RAMP_S      = 20.0

# Level 3: fluid stochastic movement (random steering + speed jitter)
L3_SPEED_START  = 280.0
L3_SPEED_END    = 400.0
L3_RAMP_S       = 15.0
L3_STEER_RATE   = 1.8    # RMS angular noise (rad/s) — higher = more random turns
L3_SPEED_JITTER = 0.30   # fractional speed variation (+/- this fraction of base speed)

_BUZZ_L1 = [
    "Synergy",
    "Bandwidth",
    "Deliverables",
    "Pivot",
    "Alignment",
]

_BUZZ_L2 = [
    "Reach out",
    "Touch base",
    "Quick wins",
    "Deep dive",
    "Hard stop",
    "Going forward",
    "Move the needle",
    "It is what it is",
]

_BUZZ_L3 = [
    "Low-hanging fruit",
    "Boil the ocean",
    "Per my last email",
    "Let's park that",
    "Circle back on that",
    "Hard stop at 3",
    "Let's put a pin in it",
    "Take this offline",
    "On my radar",
    "Drink the Kool-Aid",
    "Peel back the onion",
    "Let's not boil the ocean",
    "We need to be more agile",
    "Let's take this offline",
    "Lots of moving parts here",
    "We need to align on this",
    "Let's get all our ducks in a row",
]


class GameEngine:
    def __init__(self, screen_width: int, screen_height: int, gaze_provider: GazeProvider) -> None:
        self._gaze = gaze_provider
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._cx = screen_width / 2
        self._cy = screen_height / 2
        self._ax = self._cx - TARGET_RADIUS
        self._ay = self._cy - TARGET_RADIUS

        self._t = 0.0
        self._elapsed = 0.0
        self._tracking_acc = 0.0
        self._bonus_score = 0
        self._bonus_index = 0
        self._drift_s = 0.0
        self._vel_x: float = 0.0
        self._vel_y: float = 0.0
        self._angle: float = 0.0       # L3 current heading (radians)
        self._angle_vel: float = 0.0   # L3 angular velocity
        self._level_elapsed: float = 0.0
        self._prev_level: int = 1
        self._print_bucket: int = -1
        self._start_level: int = 1
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

    def set_start_level(self, level: int) -> None:
        self._start_level = max(1, min(3, level))

    def reset(self) -> None:
        self._t = 0.0
        self._elapsed = 0.0
        self._tracking_acc = 0.0
        self._bonus_score = 0
        self._bonus_index = 0
        self._drift_s = 0.0
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._angle = 0.0
        self._angle_vel = 0.0
        self._level_elapsed = 0.0
        self._prev_level = 1
        self._print_bucket = -1
        self._start_level = 1
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

    def _phrases(self) -> list:
        return {1: _BUZZ_L1, 2: _BUZZ_L2, 3: _BUZZ_L3}.get(self._state.level, _BUZZ_L1)

    def _next_phrase(self) -> None:
        pool = self._phrases()
        self._bonus_index = (self._bonus_index + 1) % len(pool)
        self._state.bonus_phrase = pool[self._bonus_index]

    # ── Main update loop ──────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        state = self._state

        if state.phase in (GamePhase.WELCOME, GamePhase.GAME_OVER, GamePhase.WIN):
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

        # Reset level ramp clock on level change
        if state.level != self._prev_level:
            self._level_elapsed = 0.0
            if state.level == 3:
                # Inherit current direction as the L3 heading
                self._angle = math.atan2(self._vel_y, self._vel_x)
                self._angle_vel = 0.0
            self._prev_level = state.level
        self._level_elapsed += dt

        if state.level <= 2:
            self._update_dvd(dt, state)
        else:
            self._update_l3(dt, state)

        dist = math.hypot(gx - state.target.x, gy - state.target.y)
        state.tracking = dist <= state.target.radius + state.gaze_radius

        if state.tracking:
            self._drift_s = max(0.0, self._drift_s - dt * 2)
            self._tracking_acc += dt
            state.score = int(self._tracking_acc) + self._bonus_score
            if state.level == 1 and state.score >= LEVEL_START_SCORES[2]:
                state.level = 2
            elif state.level == 2 and state.score >= LEVEL_START_SCORES[3]:
                state.level = 3
            elif state.level == 3 and state.score >= WIN_SCORE:
                state.phase = GamePhase.WIN
                return
        else:
            self._drift_s += dt
            if self._drift_s >= _LOOKAWAY_FIRE_S:
                state.phase = GamePhase.GAME_OVER
                state.drift_pct = 1.0
                return

        state.drift_pct = min(1.0, self._drift_s / _LOOKAWAY_FIRE_S)

        if not state.bonus_active and self._elapsed >= BONUS_APPEAR_AFTER:
            pool = self._phrases()
            state.bonus_active = True
            self._bonus_index = random.randrange(len(pool))
            state.bonus_phrase = pool[self._bonus_index]

    # ── Movement helpers ──────────────────────────────────────────────────

    def _dvd_speed(self, state: GameState) -> float:
        if state.level == 1:
            start, end, ramp = L1_SPEED_START, L1_SPEED_END, L1_RAMP_S
        else:
            start, end, ramp = L2_SPEED_START, L2_SPEED_END, L2_RAMP_S
        t = min(1.0, self._level_elapsed / ramp)
        return start + (end - start) * t

    def _update_dvd(self, dt: float, state: GameState) -> None:
        speed = self._dvd_speed(state)

        # Rescale velocity to current ramp speed
        cur = math.hypot(self._vel_x, self._vel_y)
        if cur > 1e-6:
            self._vel_x = (self._vel_x / cur) * speed
            self._vel_y = (self._vel_y / cur) * speed

        nx = state.target.x + self._vel_x * dt
        ny = state.target.y + self._vel_y * dt

        x_min, x_max = self._cx - self._ax, self._cx + self._ax
        y_min, y_max = self._cy - self._ay, self._cy + self._ay
        if nx <= x_min:
            self._vel_x = abs(self._vel_x)
            nx = x_min
        elif nx >= x_max:
            self._vel_x = -abs(self._vel_x)
            nx = x_max
        if ny <= y_min:
            self._vel_y = abs(self._vel_y)
            ny = y_min
        elif ny >= y_max:
            self._vel_y = -abs(self._vel_y)
            ny = y_max

        state.target.x = nx
        state.target.y = ny
        self._log_speed(speed, state.level)

    def _update_l3(self, dt: float, state: GameState) -> None:
        t = min(1.0, self._level_elapsed / L3_RAMP_S)
        base_speed = L3_SPEED_START + (L3_SPEED_END - L3_SPEED_START) * t
        speed = base_speed * (1.0 + L3_SPEED_JITTER * math.sin(self._t * 1.7))

        # Random angular drift — Gaussian noise scaled by sqrt(dt) for frame-rate independence
        self._angle_vel += random.gauss(0.0, L3_STEER_RATE) * math.sqrt(dt)
        self._angle_vel = max(-3.0, min(3.0, self._angle_vel))
        self._angle_vel *= max(0.0, 1.0 - 2.5 * dt)  # damping prevents perpetual spin
        self._angle += self._angle_vel * dt

        self._vel_x = math.cos(self._angle) * speed
        self._vel_y = math.sin(self._angle) * speed

        nx = state.target.x + self._vel_x * dt
        ny = state.target.y + self._vel_y * dt

        x_min, x_max = self._cx - self._ax, self._cx + self._ax
        y_min, y_max = self._cy - self._ay, self._cy + self._ay
        if nx <= x_min:
            self._angle = math.pi - self._angle
            self._angle_vel *= -0.5
            nx = x_min + 1
        elif nx >= x_max:
            self._angle = math.pi - self._angle
            self._angle_vel *= -0.5
            nx = x_max - 1
        if ny <= y_min:
            self._angle = -self._angle
            self._angle_vel *= -0.5
            ny = y_min + 1
        elif ny >= y_max:
            self._angle = -self._angle
            self._angle_vel *= -0.5
            ny = y_max - 1

        state.target.x = nx
        state.target.y = ny
        self._log_speed(speed, state.level)

    def _log_speed(self, speed: float, level: int) -> None:
        bucket = int(self._elapsed)
        if bucket != self._print_bucket:
            self._print_bucket = bucket
            print(
                f"[L{level}]  speed={speed:6.1f} px/s"
                f"  level_elapsed={self._level_elapsed:5.1f}s"
                f"  total_elapsed={self._elapsed:6.1f}s"
            )

    def click_start(self) -> None:
        if self._state.phase == GamePhase.WELCOME:
            self._state.phase = GamePhase.WAITING

    def force_win(self) -> None:
        self._state.phase = GamePhase.WIN

    def calibrate(self) -> None:
        self._gaze.calibrate()
        if self._state.phase == GamePhase.WAITING:
            self._t = 0.0
            self._state.target.x = self._cx
            self._state.target.y = self._cy
            self._angle = random.uniform(0.2, 1.2)
            start_speed = {1: L1_SPEED_START, 2: L2_SPEED_START, 3: L3_SPEED_START}.get(self._start_level, L1_SPEED_START)
            self._vel_x = math.cos(self._angle) * start_speed
            self._vel_y = math.sin(self._angle) * start_speed
            self._level_elapsed = 0.0
            self._prev_level = self._start_level
            self._state.level = self._start_level
            self._tracking_acc = {1: 0.0, 2: 100.0, 3: 200.0}.get(self._start_level, 0.0)
            self._bonus_score = 0
            self._state.score = int(self._tracking_acc)
            self._state.phase = GamePhase.COUNTDOWN
            self._state.countdown = _COUNTDOWN_START
