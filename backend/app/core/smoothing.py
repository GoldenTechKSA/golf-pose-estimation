"""Signal cleanup for keypoint time series.

Raw per-frame detections jitter and occasionally drop joints (occlusion by
the club, motion blur at impact). Phase detection and metric computation
both assume clean signals, so the pipeline runs every series through:

1. gap filling — joints below a confidence threshold are treated as missing
   and linearly interpolated from the nearest confident frames, and
2. moving-average smoothing — a short centered window that removes jitter
   without shifting events in time (an EMA would lag the impact frame).

All functions are pure and operate on plain numpy arrays so they can be
unit-tested without any ML or video dependencies.
"""
import numpy as np

from app.core.keypoints import NUM_KEYPOINTS, KeypointSeries


def interpolate_gaps(data: np.ndarray, conf_threshold: float = 0.3) -> np.ndarray:
    """Fill low-confidence keypoints by linear interpolation along time.

    data: (n_frames, 17, 3). Returns a copy; positions of frames whose
    confidence is below `conf_threshold` are interpolated per joint and
    coordinate. Leading/trailing gaps are held at the nearest confident
    value. Joints with no confident frame at all are left untouched.
    Confidence values themselves are preserved so downstream code can still
    tell which frames were observed vs. inferred.
    """
    out = data.copy()
    n = data.shape[0]
    if n == 0:
        return out
    t = np.arange(n)
    for j in range(NUM_KEYPOINTS):
        valid = data[:, j, 2] >= conf_threshold
        if not valid.any() or valid.all():
            continue
        for c in (0, 1):
            out[:, j, c] = np.interp(t, t[valid], data[valid, j, c])
    return out


def moving_average(signal: np.ndarray, window: int) -> np.ndarray:
    """Centered moving average along axis 0, edge-padded to keep length.

    Works on 1D signals or stacked (n, ...) arrays.
    """
    window = max(1, int(window))
    if window == 1 or signal.shape[0] == 0:
        return signal.astype(np.float64, copy=True)
    pad_front = window // 2
    pad_back = window - 1 - pad_front
    pad_width = [(pad_front, pad_back)] + [(0, 0)] * (signal.ndim - 1)
    padded = np.pad(signal.astype(np.float64), pad_width, mode="edge")
    kernel = np.ones(window) / window
    return np.apply_along_axis(lambda s: np.convolve(s, kernel, mode="valid"), 0, padded)


def smooth_series(series: KeypointSeries, conf_threshold: float = 0.3,
                  window: int | None = None) -> KeypointSeries:
    """Gap-fill and smooth a KeypointSeries, returning a new instance.

    The default window is ~1/6 of a second of frames — short enough that a
    ~1s downswing keeps its shape, long enough to suppress single-frame
    detector jitter.
    """
    if window is None:
        window = max(3, int(round(series.fps / 6.0)) | 1)  # odd, >= 3
    filled = interpolate_gaps(series.data, conf_threshold)
    smoothed = filled.copy()
    smoothed[:, :, :2] = moving_average(filled[:, :, :2], window)
    return KeypointSeries(
        data=smoothed,
        fps=series.fps,
        width=series.width,
        height=series.height,
        meta={**series.meta, "smoothing_window": window},
    )


def velocity(signal: np.ndarray, fps: float) -> np.ndarray:
    """First derivative of a signal in units/second, same length as input."""
    if signal.shape[0] < 2:
        return np.zeros_like(signal, dtype=np.float64)
    return np.gradient(signal.astype(np.float64), axis=0) * fps
