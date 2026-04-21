from dataclasses import dataclass
from enum import Enum, auto


class GamePhase(Enum):
    WELCOME = auto()
    WAITING = auto()
    COUNTDOWN = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Target:
    x: float
    y: float
    radius: float = 40.0


@dataclass
class GameState:
    target: Target
    phase: GamePhase = GamePhase.COUNTDOWN
    countdown: float = 3.0
    gaze_x: int = 0
    gaze_y: int = 0
    gaze_radius: int = 150
    score: int = 0
    tracking: bool = False
    screen_width: int = 1920
    screen_height: int = 1080
    drift_pct: float = 0.0   # 0.0–1.0 danger level; drives vignette intensity
    level: int = 1           # 1 = spreadsheet, 2 = Gmail
    # Bonus deliverable
    bonus_active: bool = False
    bonus_phrase: str = ""   # corporate buzzword phrase to type back
    bonus_input: str = ""
