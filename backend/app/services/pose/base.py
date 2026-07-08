"""Model-agnostic pose estimation interface.

The rest of the pipeline (video processing, phase detection, metrics)
depends only on this interface. Concrete backends — YOLO today, anything
else tomorrow — live beside it and are chosen by the factory from config,
so swapping models never touches pipeline code.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class PoseFrame:
    """Pose result for a single video frame.

    keypoints: (17, 3) [x_px, y_px, confidence] in COCO order for the
    primary (tracked) person, or None if nobody was detected.
    """

    keypoints: np.ndarray | None

    @property
    def detected(self) -> bool:
        return self.keypoints is not None


class PoseEstimator(ABC):
    """A pose backend that processes video frames one at a time.

    Implementations must track the *same* person across calls within one
    video (golf videos occasionally catch bystanders or playing partners),
    and call `reset()` between videos.
    """

    #: Human-readable name of the loaded model, for result metadata.
    model_name: str = "unknown"

    @abstractmethod
    def estimate(self, frame_bgr: np.ndarray) -> PoseFrame:
        """Run pose estimation on one BGR frame (OpenCV convention)."""

    def reset(self) -> None:
        """Clear any cross-frame tracking state before a new video."""
