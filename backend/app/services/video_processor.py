"""OpenCV/FFmpeg video pipeline: probe, normalize, extract keypoints, render.

Uploads arrive as .mp4/.mov/.avi from phones and cameras with arbitrary
codecs, rotations, and resolutions. Everything is normalized once up front
(H.264 mp4, capped resolution, sane pixel format) so the rest of the
pipeline — and the browser <video> tag — deals with exactly one format.

OpenCV's own mp4 writer produces MPEG-4 Part 2 streams that browsers won't
play, so annotated renders are written to a temp file and re-encoded with
FFmpeg (H.264 + faststart) as a final step.
"""
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from app.core.keypoints import SKELETON_EDGES, KeypointSeries, NUM_KEYPOINTS
from app.services.pose.base import PoseEstimator

logger = logging.getLogger(__name__)

ProgressFn = Callable[[float, str], None]  # (fraction 0..1, message)

# BGR colors per body region for the base skeleton.
REGION_COLORS = {
    "head": (0, 215, 255),
    "torso": (80, 220, 60),
    "arms": (255, 170, 0),
    "legs": (220, 90, 240),
}
JOINT_COLOR = (255, 255, 255)
DRAW_CONF_THRESHOLD = 0.3


@dataclass
class VideoInfo:
    fps: float
    width: int
    height: int
    n_frames: int

    @property
    def duration(self) -> float:
        return self.n_frames / self.fps if self.fps else 0.0


def probe(path: Path) -> VideoInfo:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"could not open video: {path}")
    try:
        return VideoInfo(
            fps=float(cap.get(cv2.CAP_PROP_FPS)) or 30.0,
            width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            n_frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        )
    finally:
        cap.release()


def _require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg is required for video transcoding but was not found on PATH "
            "(it is installed in the Docker image; for bare-metal dev install ffmpeg)"
        )
    return ffmpeg


def _run_ffmpeg(args: list[str]) -> None:
    cmd = [_require_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[:2000]}")


def normalize_video(src: Path, dst: Path, max_dim: int = 1280) -> None:
    """Transcode any supported upload to browser-safe H.264 mp4.

    - scales so the long side is at most `max_dim` (keypoints and renders
      then operate at this resolution — plenty for pose work, much faster)
    - forces even dimensions and yuv420p (H.264/browser requirements)
    - applies container rotation metadata (phone videos) by re-encoding
    - moves the moov atom up front so playback starts before full download
    """
    scale = (
        f"scale=w={max_dim}:h={max_dim}:force_original_aspect_ratio=decrease:"
        "force_divisible_by=2"
    )
    _run_ffmpeg([
        "-i", str(src),
        "-vf", scale,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(dst),
    ])


def reencode_for_browser(src: Path, dst: Path) -> None:
    """Re-encode an OpenCV-written mp4 into browser-playable H.264."""
    _run_ffmpeg([
        "-i", str(src),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(dst),
    ])


def iter_frames(path: Path):
    """Yield (index, frame_bgr) for every frame of a video."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"could not open video: {path}")
    try:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield idx, frame
            idx += 1
    finally:
        cap.release()


def extract_keypoints(path: Path, estimator: PoseEstimator,
                      on_progress: ProgressFn | None = None) -> KeypointSeries:
    """Run pose estimation over every frame of a normalized video."""
    info = probe(path)
    estimator.reset()
    frames: list[np.ndarray] = []
    for idx, frame in iter_frames(path):
        pose = estimator.estimate(frame)
        frames.append(
            pose.keypoints if pose.detected else np.zeros((NUM_KEYPOINTS, 3))
        )
        if on_progress and (idx % 5 == 0 or idx == info.n_frames - 1):
            on_progress((idx + 1) / max(info.n_frames, idx + 1),
                        f"extracting keypoints — frame {idx + 1}/{info.n_frames}")

    if not frames:
        raise ValueError("video contained no readable frames")

    detected = sum(1 for f in frames if f[:, 2].any())
    if detected < len(frames) * 0.2:
        raise ValueError(
            f"golfer detected in only {detected}/{len(frames)} frames — "
            "make sure the full body is visible in the video"
        )

    return KeypointSeries(
        data=np.stack(frames), fps=info.fps, width=info.width, height=info.height,
        meta={"model": estimator.model_name, "detected_frames": detected},
    )


def draw_skeleton(frame: np.ndarray, kpts: np.ndarray,
                  region_colors: dict[str, tuple[int, int, int]] | None = None) -> None:
    """Draw the COCO-17 skeleton onto a frame in place."""
    colors = region_colors or REGION_COLORS
    h = frame.shape[0]
    line_w = max(2, h // 300)
    radius = max(3, h // 240)
    for region, edges in SKELETON_EDGES.items():
        color = colors.get(region, (255, 255, 255))
        for a, b in edges:
            if kpts[a, 2] >= DRAW_CONF_THRESHOLD and kpts[b, 2] >= DRAW_CONF_THRESHOLD:
                pa = (int(kpts[a, 0]), int(kpts[a, 1]))
                pb = (int(kpts[b, 0]), int(kpts[b, 1]))
                cv2.line(frame, pa, pb, color, line_w, cv2.LINE_AA)
    for j in range(NUM_KEYPOINTS):
        if kpts[j, 2] >= DRAW_CONF_THRESHOLD:
            center = (int(kpts[j, 0]), int(kpts[j, 1]))
            cv2.circle(frame, center, radius, JOINT_COLOR, -1, cv2.LINE_AA)


def _draw_banner(frame: np.ndarray, text: str, accent_bgr: tuple[int, int, int]) -> None:
    """Phase label banner across the top of the frame."""
    h, w = frame.shape[:2]
    scale = max(0.6, h / 900)
    thickness = max(1, int(scale * 2))
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
    pad = int(th * 0.8)
    x0 = (w - tw) // 2 - pad
    y1 = th + 2 * pad
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, 0), (x0 + tw + 2 * pad, y1), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.putText(frame, text, ((w - tw) // 2, th + pad), cv2.FONT_HERSHEY_DUPLEX,
                scale, (255, 255, 255), thickness, cv2.LINE_AA)
    cv2.rectangle(frame, (x0, y1), (x0 + tw + 2 * pad, y1 + max(3, h // 200)), accent_bgr, -1)


def _draw_timeline(frame: np.ndarray, frame_idx: int, n_frames: int,
                   segments: list[tuple[int, int, tuple[int, int, int]]]) -> None:
    """Phase-colored timeline bar with playhead along the bottom edge."""
    h, w = frame.shape[:2]
    bar_h = max(6, h // 90)
    y0 = h - bar_h
    for start, end, color in segments:
        x0 = int(start / n_frames * w)
        x1 = int((end + 1) / n_frames * w)
        cv2.rectangle(frame, (x0, y0), (x1, h), color, -1)
    x = int(frame_idx / n_frames * w)
    cv2.rectangle(frame, (x - 2, y0 - max(3, bar_h // 2)), (x + 2, h), (255, 255, 255), -1)


def render_annotated(source: Path, dst: Path, series: KeypointSeries,
                     frame_labels: list[str] | None = None,
                     label_colors: dict[str, tuple[int, int, int]] | None = None,
                     on_progress: ProgressFn | None = None) -> None:
    """Render the annotated video: skeleton overlay, phase banner, timeline.

    frame_labels: optional per-frame phase name (len == n_frames). When
    provided, each frame gets a banner and the bottom timeline is colored
    by phase using `label_colors` (BGR).
    """
    info = probe(source)
    n = min(info.n_frames, series.n_frames) or info.n_frames

    segments: list[tuple[int, int, tuple[int, int, int]]] = []
    if frame_labels and label_colors:
        start = 0
        for i in range(1, len(frame_labels) + 1):
            if i == len(frame_labels) or frame_labels[i] != frame_labels[start]:
                color = label_colors.get(frame_labels[start], (128, 128, 128))
                segments.append((start, i - 1, color))
                start = i

    with tempfile.TemporaryDirectory() as tmp:
        raw_path = Path(tmp) / "raw.mp4"
        writer = cv2.VideoWriter(
            str(raw_path), cv2.VideoWriter_fourcc(*"mp4v"), info.fps,
            (info.width, info.height),
        )
        try:
            for idx, frame in iter_frames(source):
                if idx < series.n_frames:
                    draw_skeleton(frame, series.data[idx])
                if frame_labels and idx < len(frame_labels):
                    label = frame_labels[idx]
                    accent = (label_colors or {}).get(label, (200, 200, 200))
                    _draw_banner(frame, label.upper(), accent)
                    _draw_timeline(frame, idx, n, segments)
                writer.write(frame)
                if on_progress and idx % 10 == 0:
                    on_progress((idx + 1) / max(info.n_frames, idx + 1),
                                f"rendering annotated video — frame {idx + 1}/{info.n_frames}")
        finally:
            writer.release()
        reencode_for_browser(raw_path, dst)


def save_thumbnail(source: Path, dst: Path, at_fraction: float = 0.1) -> None:
    """Save a poster JPEG from early in the video (address position)."""
    info = probe(source)
    target = int(info.n_frames * at_fraction)
    cap = cv2.VideoCapture(str(source))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        ok, frame = cap.read()
        if not ok:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        if ok:
            cv2.imwrite(str(dst), frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
    finally:
        cap.release()
