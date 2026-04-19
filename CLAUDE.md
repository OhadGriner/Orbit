# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Ignored directories

Do not read or reference files under `deprecated/`. Those are old, unused implementations.

## Environment setup

This project uses `uv` for dependency management (Python >=3.9).

```bash
uv sync           # install dependencies into .venv
source .venv/bin/activate
```

## Running

```bash
python MonitorTracking.py
```

Requires a connected webcam and a display. The script opens two OpenCV windows and moves the mouse based on head pose.

## Runtime controls

| Key | Action |
|-----|--------|
| `q` | Quit |
| `c` | Calibrate — sets current head pose as "center" (zeroes yaw/pitch offsets) |
| `F7` | Toggle mouse control on/off |

## Architecture

`MonitorTracking.py` is the entire application — a single-file, single-process program:

1. **MediaPipe Face Mesh** detects 468 3D facial landmarks from the webcam feed.
2. **Head pose estimation** — five key landmarks (`left`=234, `right`=454, `top`=10, `bottom`=152, `front`=1) define a right/up/forward orthonormal basis. A wireframe bounding cube is projected onto the frame for visualization.
3. **Smoothing** — the last `filter_length` (default 8) ray origins and directions are averaged via `deque` buffers to reduce jitter.
4. **Angle → screen mapping** — yaw and pitch are extracted from the smoothed forward axis and linearly mapped to screen coordinates. `yawDegrees=20` and `pitchDegrees=10` define the angular range that spans the full screen width/height. Calibration offsets shift this mapping so the current pose becomes center.
5. **Mouse mover thread** — a daemon thread calls `pyautogui.moveTo` at ~100 Hz, reading from `mouse_target` under a lock, decoupled from the main camera loop.

The coordinate convention after normalization: yaw 180° = straight ahead, <180° = left, >180° = right; pitch 180° = straight ahead, <180° = down, >180° = up.
