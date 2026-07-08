"""COCO-17 keypoint definitions and the KeypointSeries container.

Every pose backend in SwingLens normalizes its output to this format:
per frame, a (17, 3) float array of [x_px, y_px, confidence] in the COCO
keypoint order. All downstream code (phase detection, metrics, rendering)
depends only on this module, never on a specific model's output types.

Note on image coordinates: y grows *downward*, so "wrists at the top of the
backswing" means the *minimum* y value. Helpers here expose height-like
signals already flipped so callers can reason in intuitive terms.
"""
from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np


class KP(IntEnum):
    """COCO-17 keypoint indices."""

    NOSE = 0
    LEFT_EYE = 1
    RIGHT_EYE = 2
    LEFT_EAR = 3
    RIGHT_EAR = 4
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_HIP = 11
    RIGHT_HIP = 12
    LEFT_KNEE = 13
    RIGHT_KNEE = 14
    LEFT_ANKLE = 15
    RIGHT_ANKLE = 16


# Limb connections for skeleton rendering, grouped by body region so the
# renderer can color them independently.
SKELETON_EDGES: dict[str, list[tuple[KP, KP]]] = {
    "head": [
        (KP.NOSE, KP.LEFT_EYE),
        (KP.NOSE, KP.RIGHT_EYE),
        (KP.LEFT_EYE, KP.LEFT_EAR),
        (KP.RIGHT_EYE, KP.RIGHT_EAR),
    ],
    "torso": [
        (KP.LEFT_SHOULDER, KP.RIGHT_SHOULDER),
        (KP.LEFT_SHOULDER, KP.LEFT_HIP),
        (KP.RIGHT_SHOULDER, KP.RIGHT_HIP),
        (KP.LEFT_HIP, KP.RIGHT_HIP),
    ],
    "arms": [
        (KP.LEFT_SHOULDER, KP.LEFT_ELBOW),
        (KP.LEFT_ELBOW, KP.LEFT_WRIST),
        (KP.RIGHT_SHOULDER, KP.RIGHT_ELBOW),
        (KP.RIGHT_ELBOW, KP.RIGHT_WRIST),
    ],
    "legs": [
        (KP.LEFT_HIP, KP.LEFT_KNEE),
        (KP.LEFT_KNEE, KP.LEFT_ANKLE),
        (KP.RIGHT_HIP, KP.RIGHT_KNEE),
        (KP.RIGHT_KNEE, KP.RIGHT_ANKLE),
    ],
}

NUM_KEYPOINTS = 17


@dataclass
class KeypointSeries:
    """Keypoint tracks for one person across a whole video.

    data: (n_frames, 17, 3) array of [x_px, y_px, confidence]. Frames where
    the person was not detected have confidence 0 for all joints.
    """

    data: np.ndarray
    fps: float
    width: int
    height: int
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.data = np.asarray(self.data, dtype=np.float64)
        if self.data.ndim != 3 or self.data.shape[1:] != (NUM_KEYPOINTS, 3):
            raise ValueError(f"expected (n, {NUM_KEYPOINTS}, 3) array, got {self.data.shape}")

    @property
    def n_frames(self) -> int:
        return int(self.data.shape[0])

    @property
    def duration(self) -> float:
        return self.n_frames / self.fps if self.fps else 0.0

    def xy(self, joint: KP) -> np.ndarray:
        """(n_frames, 2) pixel positions of one joint."""
        return self.data[:, joint, :2]

    def conf(self, joint: KP) -> np.ndarray:
        """(n_frames,) confidence of one joint."""
        return self.data[:, joint, 2]

    def midpoint(self, a: KP, b: KP) -> np.ndarray:
        """(n_frames, 2) midpoint between two joints (e.g. hip center)."""
        return (self.xy(a) + self.xy(b)) / 2.0

    def wrist_height(self) -> np.ndarray:
        """(n_frames,) average wrist height in *upward* pixels.

        Flipped from image coordinates so larger = higher, which keeps the
        phase-detection logic readable ("top of backswing" = argmax).
        """
        avg_y = (self.xy(KP.LEFT_WRIST)[:, 1] + self.xy(KP.RIGHT_WRIST)[:, 1]) / 2.0
        return self.height - avg_y

    def to_json_payload(self) -> dict:
        """Serializable payload stored alongside the processed video."""
        return {
            "format": "coco17",
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "keypoints": np.round(self.data, 2).tolist(),
            **({"meta": self.meta} if self.meta else {}),
        }

    @classmethod
    def from_json_payload(cls, payload: dict) -> "KeypointSeries":
        return cls(
            data=np.asarray(payload["keypoints"], dtype=np.float64),
            fps=float(payload["fps"]),
            width=int(payload["width"]),
            height=int(payload["height"]),
            meta=payload.get("meta", {}),
        )
