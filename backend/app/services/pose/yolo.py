"""Ultralytics YOLO pose backend.

Works with any Ultralytics `*-pose` checkpoint (yolo26m-pose, yolo11m-pose,
yolov8m-pose, ...) since they share the COCO-17 keypoint output format.
`ultralytics` (and torch underneath) is imported lazily so that the API
process, unit tests, and any environment without the ML stack can import
this module freely — the heavy import only happens in the worker when a
video is actually processed.
"""
import logging

import numpy as np

from app.core.keypoints import NUM_KEYPOINTS
from app.services.pose.base import PoseEstimator, PoseFrame

logger = logging.getLogger(__name__)


class YoloPoseEstimator(PoseEstimator):
    def __init__(self, model_name: str, device: str = "", conf_threshold: float = 0.25,
                 imgsz: int = 640):
        from ultralytics import YOLO  # lazy: pulls in torch

        self.model = YOLO(model_name)
        self.model_name = model_name
        self.device = device
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz
        self._last_center: np.ndarray | None = None

    def reset(self) -> None:
        self._last_center = None

    def estimate(self, frame_bgr: np.ndarray) -> PoseFrame:
        results = self.model(
            frame_bgr,
            verbose=False,
            conf=self.conf_threshold,
            imgsz=self.imgsz,
            **({"device": self.device} if self.device else {}),
        )
        result = results[0]
        if result.keypoints is None or len(result.keypoints) == 0:
            return PoseFrame(keypoints=None)

        kpts = result.keypoints.data.cpu().numpy()  # (n_people, 17, 3)
        if kpts.shape[0] == 0 or kpts.shape[1] != NUM_KEYPOINTS:
            return PoseFrame(keypoints=None)

        boxes = (
            result.boxes.xyxy.cpu().numpy()
            if result.boxes is not None and len(result.boxes) == kpts.shape[0]
            else None
        )
        idx = self._select_person(kpts, boxes)
        person = kpts[idx].astype(np.float64)
        self._last_center = self._person_center(person)
        return PoseFrame(keypoints=person)

    def _select_person(self, kpts: np.ndarray, boxes: np.ndarray | None) -> int:
        """Pick the golfer among detected people.

        First frame: the most prominent person (largest box, weighted by
        keypoint confidence). Later frames: the person closest to where the
        golfer was last seen, so a bystander walking through frame doesn't
        steal the track.
        """
        if kpts.shape[0] == 1:
            return 0

        if self._last_center is not None:
            centers = np.stack([self._person_center(p) for p in kpts])
            dists = np.linalg.norm(centers - self._last_center, axis=1)
            return int(np.argmin(dists))

        mean_conf = kpts[:, :, 2].mean(axis=1)
        if boxes is not None:
            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            return int(np.argmax(areas * mean_conf))
        return int(np.argmax(mean_conf))

    @staticmethod
    def _person_center(person_kpts: np.ndarray) -> np.ndarray:
        """Confidence-weighted centroid of one person's keypoints."""
        conf = person_kpts[:, 2]
        if conf.sum() <= 0:
            return person_kpts[:, :2].mean(axis=0)
        return (person_kpts[:, :2] * conf[:, None]).sum(axis=0) / conf.sum()
