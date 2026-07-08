#!/usr/bin/env python3
"""
Swing Phase Detector for Golf Swing Analysis
Detects 5 phases: Address, Backswing, Top, Downswing, Follow-through
Uses wrist position relative to body and movement direction.
"""
import numpy as np
from collections import deque
from typing import Tuple


class SwingPhaseDetector:
    """
    Detects golf swing phases based on wrist position and movement.

    Phases:
    - Address: Initial setup, wrists low and stable
    - Backswing: Wrists moving up (away from ground)
    - Top: Wrists at highest point
    - Downswing: Wrists moving down toward ball
    - Follow-through: After impact, wrists rise again
    """

    def __init__(self, window_size: int = 10):
        """
        Initialize the phase detector.

        Args:
            window_size: Number of frames to track for smoothing
        """
        self.window_size = window_size
        self.wrist_history = deque(maxlen=window_size)
        self.current_phase = "Address"
        self.phase_start_frame = 0

        # Track swing state
        self.min_y = float('inf')  # Highest point (lowest y value)
        self.max_y = float('-inf')  # Lowest point (highest y value)
        self.passed_top = False
        self.passed_impact = False

        # Calibration (first few frames establish baseline)
        self.calibrated = False
        self.address_y = None  # Y position at address
        self.frame_height = None

    def update(self, left_wrist: Tuple[float, float],
               right_wrist: Tuple[float, float],
               frame_number: int,
               frame_height: int = None) -> str:
        """
        Update phase detection with new wrist positions.

        Args:
            left_wrist: (x, y) position of left wrist in pixels
            right_wrist: (x, y) position of right wrist in pixels
            frame_number: Current frame number
            frame_height: Height of video frame for normalization

        Returns:
            Current phase name as string
        """
        if frame_height:
            self.frame_height = frame_height

        # Use average of both wrists
        wrist_y = (left_wrist[1] + right_wrist[1]) / 2
        wrist_x = (left_wrist[0] + right_wrist[0]) / 2

        self.wrist_history.append(wrist_y)

        # Calibrate on first frames
        if not self.calibrated and frame_number < 5:
            self.address_y = wrist_y
            return "Address"
        elif frame_number == 5:
            self.calibrated = True
            self.address_y = np.mean(list(self.wrist_history))

        # Update min/max tracking
        if wrist_y < self.min_y:
            self.min_y = wrist_y
        if wrist_y > self.max_y:
            self.max_y = wrist_y

        # Calculate movement direction (smoothed)
        if len(self.wrist_history) >= 3:
            recent_avg = np.mean(list(self.wrist_history)[-3:])
            older_avg = np.mean(list(self.wrist_history)[:-3]) if len(self.wrist_history) > 3 else self.wrist_history[0]
            movement = recent_avg - older_avg  # Positive = moving down, Negative = moving up
        else:
            movement = 0

        # Determine phase based on position and movement
        new_phase = self._detect_phase(wrist_y, movement, frame_number)

        if new_phase != self.current_phase:
            self.current_phase = new_phase
            self.phase_start_frame = frame_number

        return self.current_phase

    def _detect_phase(self, wrist_y: float, movement: float, frame_number: int) -> str:
        """
        Determine swing phase based on wrist position and movement direction.

        Args:
            wrist_y: Current wrist Y position
            movement: Movement direction (positive = down, negative = up)
            frame_number: Current frame number

        Returns:
            Phase name
        """
        if self.address_y is None:
            return "Address"

        # Calculate how far wrist is from address position
        # Negative = above address (backswing/top), Positive = below address
        displacement = wrist_y - self.address_y

        # Thresholds (in pixels, relative to frame)
        threshold = 30  # Minimum movement to consider phase change

        # STATE MACHINE LOGIC

        # Address: Near starting position, minimal movement
        if self.current_phase == "Address":
            # Transition to Backswing when wrists start moving up significantly
            if movement < -5 and displacement < -threshold:
                return "Backswing"
            return "Address"

        # Backswing: Moving upward (negative y direction)
        if self.current_phase == "Backswing":
            # Transition to Top when movement slows/reverses at high point
            if movement > 2 and wrist_y <= self.min_y + threshold:
                self.passed_top = True
                return "Top"
            # Still going up
            if movement < 0:
                return "Backswing"
            return "Backswing"

        # Top: Highest point, transitioning to downswing
        if self.current_phase == "Top":
            # Transition to Downswing when moving down
            if movement > 3:
                return "Downswing"
            return "Top"

        # Downswing: Moving down toward impact
        if self.current_phase == "Downswing":
            # Transition to Follow-through when wrists start rising again
            # This happens after impact - wrists go from moving down to moving up
            if movement < -3:
                self.passed_impact = True
                return "Follow-through"
            return "Downswing"

        # Follow-through: After impact
        if self.current_phase == "Follow-through":
            return "Follow-through"

        return self.current_phase

    def get_phase_duration(self, frame_number: int, fps: float = 30.0) -> float:
        """
        Get duration of current phase in seconds.
        """
        frames_in_phase = frame_number - self.phase_start_frame
        return frames_in_phase / fps

    def reset(self):
        """Reset detector for new video or new swing."""
        self.wrist_history.clear()
        self.current_phase = "Address"
        self.phase_start_frame = 0
        self.min_y = float('inf')
        self.max_y = float('-inf')
        self.passed_top = False
        self.passed_impact = False
        self.calibrated = False
        self.address_y = None
