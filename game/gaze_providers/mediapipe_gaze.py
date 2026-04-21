import math
import threading
from collections import deque
from typing import Tuple

import cv2
import mediapipe as mp
import numpy as np
import pyautogui

from .base import GazeProvider

_FILTER_LENGTH = 16
_YAW_DEGREES = 35
_PITCH_DEGREES = 18
_LANDMARKS = {"left": 234, "right": 454, "top": 10, "bottom": 152, "front": 1}


class MediaPipeGazeProvider(GazeProvider):
    """Head-pose gaze provider using MediaPipe FaceMesh. Ports MonitorTracking.py into a class."""

    def __init__(self, camera_index: int = 0) -> None:
        self._camera_index = camera_index
        self._screen_w, self._screen_h = pyautogui.size()

        self._lock = threading.Lock()
        self._gaze_x = self._screen_w // 2
        self._gaze_y = self._screen_h // 2
        self._raw_yaw: float = 180.0
        self._raw_pitch: float = 180.0
        self._calibration_yaw: float = 0.0
        self._calibration_pitch: float = 0.0

        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def get_gaze_position(self) -> Tuple[int, int]:
        with self._lock:
            return self._gaze_x, self._gaze_y

    def calibrate(self) -> None:
        with self._lock:
            self._calibration_yaw = 180.0 - self._raw_yaw
            self._calibration_pitch = 180.0 - self._raw_pitch

    def _landmark_to_np(self, landmark, w: int, h: int) -> np.ndarray:
        return np.array([landmark.x * w, landmark.y * h, landmark.z * w])

    def _run(self) -> None:
        face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        cap = cv2.VideoCapture(self._camera_index)
        ray_origins: deque = deque(maxlen=_FILTER_LENGTH)
        ray_directions: deque = deque(maxlen=_FILTER_LENGTH)
        reference_forward = np.array([0.0, 0.0, -1.0])

        try:
            while self._running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                h, w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb)

                if not results.multi_face_landmarks:
                    continue

                lm = results.multi_face_landmarks[0].landmark
                kp = {name: self._landmark_to_np(lm[idx], w, h) for name, idx in _LANDMARKS.items()}

                right_axis = kp["right"] - kp["left"]
                right_axis /= np.linalg.norm(right_axis)
                up_axis = kp["top"] - kp["bottom"]
                up_axis /= np.linalg.norm(up_axis)
                forward_axis = -np.cross(right_axis, up_axis)
                forward_axis /= np.linalg.norm(forward_axis)

                center = sum(kp.values()) / len(kp)
                ray_origins.append(center)
                ray_directions.append(forward_axis)

                avg_dir = np.mean(ray_directions, axis=0)
                avg_dir /= np.linalg.norm(avg_dir)

                xz = np.array([avg_dir[0], 0.0, avg_dir[2]])
                xz_norm = np.linalg.norm(xz)
                if xz_norm < 1e-6:
                    continue
                xz /= xz_norm
                yaw_rad = math.acos(np.clip(np.dot(reference_forward, xz), -1.0, 1.0))
                if avg_dir[0] < 0:
                    yaw_rad = -yaw_rad

                yz = np.array([0.0, avg_dir[1], avg_dir[2]])
                yz_norm = np.linalg.norm(yz)
                if yz_norm < 1e-6:
                    continue
                yz /= yz_norm
                pitch_rad = math.acos(np.clip(np.dot(reference_forward, yz), -1.0, 1.0))
                if avg_dir[1] > 0:
                    pitch_rad = -pitch_rad

                yaw_deg = math.degrees(yaw_rad)
                pitch_deg = math.degrees(pitch_rad)

                # Normalize to 0–360 with center gaze at 180°
                yaw_deg = abs(yaw_deg) if yaw_deg < 0 else (360.0 - yaw_deg if yaw_deg < 180 else yaw_deg)
                pitch_deg = 360.0 + pitch_deg if pitch_deg < 0 else pitch_deg

                with self._lock:
                    raw_yaw, raw_pitch = yaw_deg, pitch_deg
                    self._raw_yaw = raw_yaw
                    self._raw_pitch = raw_pitch
                    cal_yaw = yaw_deg + self._calibration_yaw
                    cal_pitch = pitch_deg + self._calibration_pitch

                sx = int(((cal_yaw - (180 - _YAW_DEGREES)) / (2 * _YAW_DEGREES)) * self._screen_w)
                sy = int(((180 + _PITCH_DEGREES - cal_pitch) / (2 * _PITCH_DEGREES)) * self._screen_h)
                sx = max(0, min(sx, self._screen_w))
                sy = max(0, min(sy, self._screen_h))

                with self._lock:
                    self._gaze_x = sx
                    self._gaze_y = sy
        finally:
            cap.release()
            face_mesh.close()
