"""Swing phase segmentation from keypoint time series.

Segments a swing into the 7 canonical phases used in golf biomechanics:
address, backswing, top, downswing, impact, follow-through, finish.

The approach is heuristic and *global*: unlike a streaming state machine, we
look at the whole wrist-height signal at once, which makes the key events
easy to anchor robustly:

1. The downswing contains the fastest wrist motion in the entire swing —
   biomechanically guaranteed — so the global peak of downward wrist
   velocity is a reliable anchor even in noisy footage.
2. TOP is the highest wrist position *before* that anchor (the follow-
   through often finishes higher than the top, so a global argmax would be
   wrong).
3. IMPACT is the lowest wrist position in the fraction of a second *after*
   the anchor.
4. TAKEAWAY is the last frame before top where the wrists were still near
   their address height; FINISH begins when overall body motion settles
   after impact.

All functions are pure numpy over a KeypointSeries — no ML, no video.
"""
from dataclasses import dataclass, field

import numpy as np

from app.core.keypoints import KP, KeypointSeries
from app.core.smoothing import velocity

PHASE_ORDER = [
    "address", "backswing", "top", "downswing", "impact", "follow_through", "finish",
]

# BGR colors used to paint the skeleton/timeline per phase in rendered video.
PHASE_COLORS_BGR: dict[str, tuple[int, int, int]] = {
    "address": (180, 180, 180),
    "backswing": (240, 160, 60),
    "top": (250, 220, 80),
    "downswing": (80, 130, 255),
    "impact": (60, 60, 235),
    "follow_through": (200, 120, 220),
    "finish": (130, 210, 130),
}

# Tunables (fractions of swing amplitude / seconds).
_TAKEAWAY_RISE_FRAC = 0.08     # wrists above address by >8% of amplitude = swinging
_TOP_BAND_FRAC = 0.04          # frames within 4% of peak height count as "top"
_IMPACT_SEARCH_S = 0.6         # impact must occur within this window after max speed
_IMPACT_HALF_WIDTH_S = 0.03    # impact phase spans +/- this around the impact frame
_FINISH_MOTION_FRAC = 0.12     # body motion below 12% of its peak = settled
_FINISH_HOLD_S = 0.2           # ...sustained for this long
_MIN_AMPLITUDE_TORSOS = 0.6    # swing must move wrists at least this many torso-lengths


@dataclass
class SwingPhases:
    """Result of phase detection over one video."""

    segments: list[dict]          # {name, start_frame, end_frame, start_time, end_time}
    frame_labels: list[str]       # phase name per frame, len == n_frames
    events: dict[str, int]        # takeaway / top / impact / finish key frames
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> list[dict]:
        return self.segments


def _torso_length(series: KeypointSeries) -> float:
    """Median hip-center to shoulder-center distance, as a pixel scale unit."""
    shoulders = series.midpoint(KP.LEFT_SHOULDER, KP.RIGHT_SHOULDER)
    hips = series.midpoint(KP.LEFT_HIP, KP.RIGHT_HIP)
    dist = np.linalg.norm(shoulders - hips, axis=1)
    dist = dist[dist > 1e-6]
    return float(np.median(dist)) if dist.size else 0.0


def _body_motion(series: KeypointSeries) -> np.ndarray:
    """(n_frames,) mean speed of all joints in px/s — a "how still" signal."""
    vel = velocity(series.data[:, :, :2], series.fps)
    return np.linalg.norm(vel, axis=2).mean(axis=1)


def detect_phases(series: KeypointSeries) -> SwingPhases:
    """Segment a single golf swing into the 7 canonical phases.

    Raises ValueError when the video clearly doesn't contain a swing (too
    short, or wrist travel is small relative to body size).
    """
    n = series.n_frames
    fps = series.fps
    if n < 10:
        raise ValueError("video has too few frames to contain a golf swing")

    h = series.wrist_height()          # up-positive
    v = velocity(h, fps)               # positive = wrists rising
    warnings: list[str] = []

    # A swing must move the wrists substantially relative to body size;
    # check before anchoring so a static video gets a clear rejection.
    torso = _torso_length(series)
    if torso <= 0 or float(h.max() - h.min()) < _MIN_AMPLITUDE_TORSOS * torso:
        raise ValueError(
            "no golf swing detected — wrist movement is too small relative to "
            "body size (make sure the video shows a full swing)"
        )

    # 1. Anchor: fastest downward wrist motion — always inside the downswing.
    t_fast = int(np.argmin(v))
    if t_fast == 0 or t_fast == n - 1:
        raise ValueError("could not locate a downswing in this video")

    # 2. Top of the backswing: highest point before the anchor.
    top = int(np.argmax(h[: t_fast + 1]))

    # 3. Impact: lowest point shortly after the anchor.
    impact_window_end = min(n, t_fast + int(round(_IMPACT_SEARCH_S * fps)) + 1)
    impact = t_fast + int(np.argmin(h[t_fast:impact_window_end]))

    # Sanity: the rise into the top must itself be substantial (a video
    # where the wrists only travel *downward* isn't a swing either).
    baseline = float(np.min(h[: top + 1]))
    amplitude = float(h[top]) - baseline
    if amplitude < _MIN_AMPLITUDE_TORSOS * torso:
        raise ValueError(
            "no golf swing detected — could not find a backswing (make sure "
            "the video shows a full swing)"
        )

    # 4. Takeaway: last frame before top where wrists were still near address.
    rise = h[: top + 1] - baseline
    near_address = np.flatnonzero(rise <= _TAKEAWAY_RISE_FRAC * amplitude)
    takeaway = int(near_address[-1]) if near_address.size else 0

    # 5. Top phase: contiguous band of frames around the peak.
    in_band = h >= h[top] - _TOP_BAND_FRAC * amplitude
    top_start = top
    while top_start > takeaway + 1 and in_band[top_start - 1]:
        top_start -= 1
    top_end = top
    while top_end < t_fast - 1 and in_band[top_end + 1]:
        top_end += 1

    # 6. Finish: first sustained "stillness" after impact.
    motion = _body_motion(series)
    peak_motion = float(motion.max()) or 1.0
    hold = max(1, int(round(_FINISH_HOLD_S * fps)))
    settle_threshold = _FINISH_MOTION_FRAC * peak_motion
    finish_start = n - 1
    search_from = min(n - 1, impact + int(round(0.2 * fps)))
    for t in range(search_from, n - hold + 1):
        if np.all(motion[t : t + hold] < settle_threshold):
            finish_start = t
            break
    else:
        warnings.append("golfer never fully settled after the swing; finish "
                        "phase estimated at the last frames")
        finish_start = max(impact + 1, n - max(2, n // 20))

    # 7. Impact phase: a short symmetric window around the impact frame.
    half = max(1, int(round(_IMPACT_HALF_WIDTH_S * fps)))
    impact_start, impact_end = impact - half, impact + half

    # Assemble boundaries in canonical order and force monotonicity — a
    # noisy signal can propose slightly out-of-order boundaries; clamping
    # keeps segments valid and deterministic.
    boundaries = np.array([
        0,                # address start
        takeaway + 1,     # backswing start
        top_start,        # top start
        top_end + 1,      # downswing start
        impact_start,     # impact start
        impact_end + 1,   # follow-through start
        finish_start,     # finish start
        n,                # end sentinel
    ])
    boundaries = np.maximum.accumulate(np.clip(boundaries, 0, n))

    segments: list[dict] = []
    frame_labels = ["address"] * n
    for name, start, end_excl in zip(PHASE_ORDER, boundaries[:-1], boundaries[1:]):
        if end_excl <= start:
            continue  # phase not present (e.g. video starts mid-takeaway)
        end = int(end_excl) - 1
        segments.append({
            "name": name,
            "start_frame": int(start),
            "end_frame": end,
            "start_time": round(float(start) / fps, 3),
            "end_time": round(float(end + 1) / fps, 3),
        })
        for t in range(int(start), int(end_excl)):
            frame_labels[t] = name

    return SwingPhases(
        segments=segments,
        frame_labels=frame_labels,
        events={
            "takeaway": takeaway,
            "top": top,
            "impact": impact,
            "finish": int(finish_start),
        },
        warnings=warnings,
    )
