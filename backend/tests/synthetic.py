"""Synthetic golf swing generator for testing phase detection and metrics.

Builds a KeypointSeries that mimics the kinematics of a real right-handed
swing viewed face-on, with known ground-truth event frames:

    address (still) -> backswing (wrists rise, shoulders turn) -> top (pause)
    -> downswing (fast drop) -> impact -> follow-through (rise) -> finish (still)

The geometry is crude but respects the invariants the detector and metric
code rely on: the downswing is the fastest wrist motion, the follow-through
finishes high, shoulders turn more than hips, and the body goes still at
the end.
"""
import numpy as np

from app.core.keypoints import KP, NUM_KEYPOINTS, KeypointSeries

FPS = 50.0
WIDTH, HEIGHT = 1280, 720

# Ground-truth phase boundaries (frame indices).
ADDRESS_END = 49        # still until here
TOP_START, TOP_END = 130, 139
IMPACT = 159
FOLLOW_END = 219        # rising until here
N_FRAMES = 280

WRIST_ADDRESS_Y = 560.0
WRIST_TOP_Y = 180.0
WRIST_IMPACT_Y = 580.0
WRIST_FINISH_Y = 220.0


def _smoothstep(t: np.ndarray) -> np.ndarray:
    """Ease-in-out ramp on [0, 1] — velocity is zero at both ends."""
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(t, 0.0, 1.0))


def _wrist_y() -> np.ndarray:
    y = np.full(N_FRAMES, WRIST_ADDRESS_Y)
    # backswing: rise from address height to top height
    up = np.arange(ADDRESS_END + 1, TOP_START)
    y[up] = WRIST_ADDRESS_Y + (WRIST_TOP_Y - WRIST_ADDRESS_Y) * _smoothstep(
        (up - ADDRESS_END) / (TOP_START - ADDRESS_END))
    # top: hold
    y[TOP_START:TOP_END + 1] = WRIST_TOP_Y
    # downswing: fast drop to impact
    down = np.arange(TOP_END + 1, IMPACT + 1)
    y[down] = WRIST_TOP_Y + (WRIST_IMPACT_Y - WRIST_TOP_Y) * _smoothstep(
        (down - TOP_END) / (IMPACT - TOP_END))
    # follow-through: rise to finish height
    follow = np.arange(IMPACT + 1, FOLLOW_END + 1)
    y[follow] = WRIST_IMPACT_Y + (WRIST_FINISH_Y - WRIST_IMPACT_Y) * _smoothstep(
        (follow - IMPACT) / (FOLLOW_END - IMPACT))
    # finish: hold
    y[FOLLOW_END + 1:] = WRIST_FINISH_Y
    return y


def _turn_profile(max_deg_offset_px: float) -> np.ndarray:
    """Vertical offset (px) applied antisymmetrically to a left/right joint
    pair to fake a projected rotation: 0 at address, max at top, back to ~0
    by impact, partial at finish."""
    profile = np.zeros(N_FRAMES)
    up = np.arange(ADDRESS_END + 1, TOP_START)
    profile[up] = max_deg_offset_px * _smoothstep((up - ADDRESS_END) / (TOP_START - ADDRESS_END))
    profile[TOP_START:TOP_END + 1] = max_deg_offset_px
    down = np.arange(TOP_END + 1, IMPACT + 1)
    profile[down] = max_deg_offset_px * (1 - _smoothstep((down - TOP_END) / (IMPACT - TOP_END)))
    return profile


def make_swing_series() -> tuple[KeypointSeries, dict]:
    data = np.zeros((N_FRAMES, NUM_KEYPOINTS, 3))
    data[:, :, 2] = 1.0

    def place(joint: KP, x: float, y) -> None:
        data[:, joint, 0] = x
        data[:, joint, 1] = y

    # Head (static — good head stability)
    place(KP.NOSE, 640, 200)
    place(KP.LEFT_EYE, 630, 195)
    place(KP.RIGHT_EYE, 650, 195)
    place(KP.LEFT_EAR, 620, 200)
    place(KP.RIGHT_EAR, 660, 200)

    # Torso with projected turn: shoulders tilt more than hips.
    shoulder_offset = _turn_profile(30.0)   # ~37 deg over 40px half-width
    hip_offset = _turn_profile(10.0)        # ~18 deg over 30px half-width
    place(KP.LEFT_SHOULDER, 600, 280 + shoulder_offset)
    place(KP.RIGHT_SHOULDER, 680, 280 - shoulder_offset)
    place(KP.LEFT_HIP, 610, 420 + hip_offset)
    place(KP.RIGHT_HIP, 670, 420 - hip_offset)

    # Legs (slight athletic flex, static)
    place(KP.LEFT_KNEE, 600, 550)
    place(KP.RIGHT_KNEE, 680, 550)
    place(KP.LEFT_ANKLE, 590, 670)
    place(KP.RIGHT_ANKLE, 690, 670)

    # Arms: wrists carry the swing; elbows track between shoulder and wrist.
    wy = _wrist_y()
    place(KP.LEFT_WRIST, 630, wy)
    place(KP.RIGHT_WRIST, 650, wy)
    data[:, KP.LEFT_ELBOW, 0] = 615
    data[:, KP.LEFT_ELBOW, 1] = (data[:, KP.LEFT_SHOULDER, 1] + wy) / 2
    data[:, KP.RIGHT_ELBOW, 0] = 665
    data[:, KP.RIGHT_ELBOW, 1] = (data[:, KP.RIGHT_SHOULDER, 1] + wy) / 2

    series = KeypointSeries(data=data, fps=FPS, width=WIDTH, height=HEIGHT)
    truth = {
        "address_end": ADDRESS_END,
        "top_range": (TOP_START, TOP_END),
        "impact": IMPACT,
        "finish_from": FOLLOW_END,
        "n_frames": N_FRAMES,
    }
    return series, truth


def make_static_series(n_frames: int = 100) -> KeypointSeries:
    """A person standing still — must NOT be detected as a swing."""
    series, _ = make_swing_series()
    data = np.repeat(series.data[:1], n_frames, axis=0).copy()
    return KeypointSeries(data=data, fps=FPS, width=WIDTH, height=HEIGHT)
