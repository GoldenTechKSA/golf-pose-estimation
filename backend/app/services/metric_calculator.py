"""Biomechanical metrics from 2D keypoint time series.

Every angle here is a *projected* 2D angle from monocular video — an honest
proxy for the true 3D anatomical angle, not a replacement for motion
capture. The UI and coaching prompt both carry this caveat (see NOTES).

Two kinds of output:
- per-frame series (shoulder/hip line angles, X-Factor, spine tilt, lead
  arm extension, knee flex, normalized wrist height) for charting, and
- summary metrics evaluated at the phase events (top, impact, ...) with
  reference ranges so the UI can show good/needs-work indicators. Ranges
  are heuristics informed by golf biomechanics literature (e.g. pros show
  roughly 3:1 tempo and ~40-60 degrees of hip/shoulder separation at the
  top), loosened to account for 2D projection error.
"""
import numpy as np

from app.core.keypoints import KP, KeypointSeries
from app.core.smoothing import moving_average, velocity
from app.services.phase_detector import SwingPhases

NOTES = [
    "All angles are 2D projections from monocular video, not true 3D "
    "anatomical angles. Rotation values in particular are proxies and "
    "depend on camera angle.",
    "Reference ranges are heuristic guidance, not medical or professional "
    "fitting advice.",
]


# ---------------------------------------------------------------------------
# Geometry helpers (pure, unit-tested)
# ---------------------------------------------------------------------------

def line_angle_deg(p_a: np.ndarray, p_b: np.ndarray) -> np.ndarray:
    """Signed angle in degrees of the line a->b versus the image horizontal.

    Works framewise on (n, 2) arrays. y is flipped so positive angle means
    point b is *above* point a. Returns NaN where the points coincide.

    The `1e-9` degeneracy guard only catches exactly-coincident points. It says
    nothing about *conditioning*: at 5px of separation the angle is already
    noise. Prefer `line_angle_masked` for body lines, which knows the body's
    scale and can tell a short line from a well-formed one.
    """
    d = np.asarray(p_b, dtype=np.float64) - np.asarray(p_a, dtype=np.float64)
    degenerate = np.linalg.norm(d, axis=-1) < 1e-9
    angle = np.degrees(np.arctan2(-d[..., 1], d[..., 0]))
    return np.where(degenerate, np.nan, angle)


# A projected line shorter than this fraction of torso length is pointing too
# near the camera axis for its angle to mean anything: at that separation a
# pixel of pose noise swings the angle tens of degrees. Measured on the sample
# swing, the shoulder line collapses to 0.075 of torso length at impact while
# sitting near 0.5 through the rest of the swing.
MIN_LINE_RATIO = 0.15


def line_angle_masked(p_a: np.ndarray, p_b: np.ndarray,
                      scale: np.ndarray) -> np.ndarray:
    """`line_angle_deg`, but NaN wherever the line is too foreshortened to trust.

    `scale` is a per-frame body length (torso). Without this guard a line seen
    end-on produces a noise-driven angle, and its derivative produces a spike
    large enough to dominate the kinematic sequence.
    """
    angle = line_angle_deg(p_a, p_b)
    length = np.linalg.norm(np.asarray(p_b) - np.asarray(p_a), axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(scale > 1e-6, length / scale, 0.0)
    return np.where(ratio < MIN_LINE_RATIO, np.nan, angle)


def joint_angle_deg(p_a: np.ndarray, p_b: np.ndarray, p_c: np.ndarray) -> np.ndarray:
    """Interior angle at vertex b for points a-b-c, in degrees [0, 180].

    Framewise on (n, 2) arrays; NaN where either limb has zero length.
    180 = fully straight (e.g. extended elbow).
    """
    v1 = np.asarray(p_a, dtype=np.float64) - np.asarray(p_b, dtype=np.float64)
    v2 = np.asarray(p_c, dtype=np.float64) - np.asarray(p_b, dtype=np.float64)
    n1 = np.linalg.norm(v1, axis=-1)
    n2 = np.linalg.norm(v2, axis=-1)
    degenerate = (n1 < 1e-9) | (n2 < 1e-9)
    safe = np.where(degenerate, 1.0, n1 * n2)
    cos = np.clip((v1 * v2).sum(axis=-1) / safe, -1.0, 1.0)
    return np.where(degenerate, np.nan, np.degrees(np.arccos(cos)))


def vertical_tilt_deg(p_bottom: np.ndarray, p_top: np.ndarray) -> np.ndarray:
    """Angle of the bottom->top line away from vertical, in degrees.

    0 = perfectly upright. Used for spine tilt (hip center -> shoulder
    center).
    """
    d = np.asarray(p_top, dtype=np.float64) - np.asarray(p_bottom, dtype=np.float64)
    degenerate = np.linalg.norm(d, axis=-1) < 1e-9
    # arctan2(horizontal, upward) -> 0 when perfectly vertical
    angle = np.degrees(np.arctan2(np.abs(d[..., 0]), -d[..., 1]))
    return np.where(degenerate, np.nan, angle)


def _round_series(values: np.ndarray, ndigits: int = 1) -> list:
    """Round a float series and convert NaN to None for JSON storage."""
    out = []
    for value in np.asarray(values, dtype=np.float64):
        out.append(None if np.isnan(value) else round(float(value), ndigits))
    return out


# ---------------------------------------------------------------------------
# Per-frame series
# ---------------------------------------------------------------------------

def compute_series(series: KeypointSeries, handedness: str = "right") -> dict[str, np.ndarray]:
    """All per-frame metric signals, keyed by name (raw numpy, may hold NaN).

    A right-handed golfer leads with the left arm/leg.
    """
    lead = "LEFT" if handedness == "right" else "RIGHT"
    trail = "RIGHT" if handedness == "right" else "LEFT"

    def kp(name: str) -> np.ndarray:
        return series.xy(KP[name])

    mid_shoulder = series.midpoint(KP.LEFT_SHOULDER, KP.RIGHT_SHOULDER)
    mid_hip = series.midpoint(KP.LEFT_HIP, KP.RIGHT_HIP)
    torso = np.linalg.norm(mid_shoulder - mid_hip, axis=-1)

    # Shoulder and hip lines are only meaningful while they still project to a
    # usable length. Down the line they never do; face-on they collapse near the
    # top of the backswing. Masking is honest — a NaN reads as "not measurable
    # from this camera", where a number reads as a fact.
    shoulders = line_angle_masked(
        kp(f"{trail}_SHOULDER"), kp(f"{lead}_SHOULDER"), torso)
    hips = line_angle_masked(kp(f"{trail}_HIP"), kp(f"{lead}_HIP"), torso)

    return {
        "shoulder_angle": shoulders,
        "hip_angle": hips,
        "x_factor": shoulders - hips,
        "spine_angle": vertical_tilt_deg(mid_hip, mid_shoulder),
        "lead_arm": joint_angle_deg(
            kp(f"{lead}_SHOULDER"), kp(f"{lead}_ELBOW"), kp(f"{lead}_WRIST")),
        "lead_knee_flex": joint_angle_deg(
            kp(f"{lead}_HIP"), kp(f"{lead}_KNEE"), kp(f"{lead}_ANKLE")),
        "trail_knee_flex": joint_angle_deg(
            kp(f"{trail}_HIP"), kp(f"{trail}_KNEE"), kp(f"{trail}_ANKLE")),
        "wrist_height": series.wrist_height() / max(series.height, 1),
    }


# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------

def _entry(key: str, label: str, value: float | None, unit: str,
           ideal: tuple[float, float] | None, description: str,
           lower_is_better: bool = False) -> dict:
    assessment = None
    if value is not None and ideal is not None:
        lo, hi = ideal
        if lo <= value <= hi:
            assessment = "good"
        else:
            assessment = "watch"
    return {
        "key": key,
        "label": label,
        "value": None if value is None else round(float(value), 1),
        "unit": unit,
        "ideal_range": list(ideal) if ideal else None,
        "lower_is_better": lower_is_better,
        "assessment": assessment,
        "description": description,
    }


def _safe(series: np.ndarray, idx: int) -> float | None:
    value = float(series[idx])
    return None if np.isnan(value) else value


def _kinematic_sequence(series: KeypointSeries, signals: dict[str, np.ndarray],
                        events: dict[str, int], handedness: str) -> dict:
    """Order in which body segments reach peak rotational speed in the
    downswing. An efficient swing sequences proximal-to-distal:
    hips -> torso -> arms."""
    lead = "LEFT" if handedness == "right" else "RIGHT"
    mid_shoulder = series.midpoint(KP.LEFT_SHOULDER, KP.RIGHT_SHOULDER)
    mid_hip = series.midpoint(KP.LEFT_HIP, KP.RIGHT_HIP)
    torso = np.linalg.norm(mid_shoulder - mid_hip, axis=-1)
    arm_line = line_angle_masked(
        series.xy(KP[f"{lead}_SHOULDER"]), series.xy(KP[f"{lead}_WRIST"]), torso)

    top, impact = events["top"], events["impact"]
    if impact - top < 3:
        return {"available": False, "reason": "downswing too short to sequence"}

    window = slice(top, impact + 1)
    inputs = (("hips", signals["hip_angle"]),
              ("torso", signals["shoulder_angle"]),
              ("arms", arm_line))

    # A masked frame anywhere in the downswing means at least one segment's
    # rotation was unmeasurable there. Zero-filling it would manufacture a
    # velocity spike and hand the ordering to an artifact, so decline instead.
    if any(np.isnan(signal[window]).any() for _, signal in inputs):
        return {"available": False,
                "reason": "segment rotation not measurable from this camera angle"}

    peaks: dict[str, int] = {}
    for name, signal in inputs:
        speed = np.abs(velocity(signal, series.fps))[window]
        smooth = moving_average(speed, 3)
        peaks[name] = top + int(np.argmax(smooth))

    order = sorted(peaks, key=peaks.get)
    return {
        "available": True,
        "order": order,
        "peak_frames": peaks,
        "proximal_to_distal": order == ["hips", "torso", "arms"],
    }


def compute_metrics(series: KeypointSeries, phases: SwingPhases,
                    handedness: str = "right") -> dict:
    """Full metrics payload stored with the swing and served to the UI."""
    signals = compute_series(series, handedness)
    ev = phases.events
    takeaway, top, impact, finish = ev["takeaway"], ev["top"], ev["impact"], ev["finish"]
    fps = series.fps

    address_ref = max(0, takeaway)  # angles at setup, used as rotation baseline

    def turn_at_top(signal: np.ndarray) -> float | None:
        at_top, at_address = _safe(signal, top), _safe(signal, address_ref)
        if at_top is None or at_address is None:
            return None
        return abs(at_top - at_address)

    shoulder_turn = turn_at_top(signals["shoulder_angle"])
    hip_turn = turn_at_top(signals["hip_angle"])

    xf = np.abs(signals["x_factor"])
    x_factor_top = _safe(xf, top)
    # X-Factor stretch: extra hip/shoulder separation gained in transition
    # (hips fire toward the target while shoulders are still turning back).
    stretch_end = min(impact, top + max(2, int(round(0.15 * fps)))) + 1
    transition = xf[top:stretch_end]
    x_factor_stretch = None
    if x_factor_top is not None and transition.size and not np.all(np.isnan(transition)):
        x_factor_stretch = max(0.0, float(np.nanmax(transition)) - x_factor_top)

    spine_address = _safe(signals["spine_angle"], address_ref)
    spine_impact = _safe(signals["spine_angle"], impact)
    early_extension = None
    if spine_address is not None and spine_impact is not None:
        # positive = stood up (lost forward tilt) into impact
        early_extension = spine_address - spine_impact

    tempo = None
    if impact > top > takeaway:
        tempo = (top - takeaway) / (impact - top)

    # Head stability: nose drift up to impact, in units of shoulder width.
    nose = series.xy(KP.NOSE)
    shoulder_width = np.linalg.norm(
        series.xy(KP.LEFT_SHOULDER) - series.xy(KP.RIGHT_SHOULDER), axis=1)
    width_scale = float(np.median(shoulder_width[shoulder_width > 1e-6])) \
        if np.any(shoulder_width > 1e-6) else None
    head_stability = None
    if width_scale:
        anchor = nose[address_ref]
        drift = np.linalg.norm(nose[address_ref:impact + 1] - anchor, axis=1)
        head_stability = float(np.max(drift)) / width_scale

    summary = [
        _entry("tempo_ratio", "Tempo (backswing : downswing)", tempo, ":1",
               (2.2, 3.8),
               "Pros average roughly 3:1 — an unhurried backswing with an "
               "aggressive downswing."),
        _entry("shoulder_turn_at_top", "Shoulder turn at top", shoulder_turn, "°",
               (60.0, 120.0),
               "Projected rotation of the shoulder line at the top of the "
               "backswing, relative to address."),
        _entry("hip_turn_at_top", "Hip turn at top", hip_turn, "°",
               (25.0, 65.0),
               "Projected rotation of the hip line at the top. Hips should "
               "turn noticeably less than shoulders."),
        _entry("x_factor_at_top", "X-Factor at top", x_factor_top, "°",
               (25.0, 65.0),
               "Separation between shoulder and hip lines at the top — a key "
               "power indicator."),
        _entry("x_factor_stretch", "X-Factor stretch", x_factor_stretch, "°",
               None,
               "Extra separation gained early in the downswing as the hips "
               "lead. More stretch generally means more stored power."),
        _entry("lead_arm_at_top", "Lead arm extension at top",
               _safe(signals["lead_arm"], top), "°", (150.0, 180.0),
               "Angle at the lead elbow at the top; straighter creates a "
               "wider, more repeatable arc."),
        _entry("lead_arm_at_impact", "Lead arm extension at impact",
               _safe(signals["lead_arm"], impact), "°", (155.0, 180.0),
               "Lead arm should be extended through the strike."),
        _entry("spine_angle_at_address", "Spine tilt at address", spine_address, "°",
               (15.0, 45.0),
               "Forward tilt of the torso from vertical at setup."),
        _entry("early_extension", "Early extension", early_extension, "°",
               (-6.0, 8.0),
               "Loss of spine tilt between address and impact. Large positive "
               "values mean standing up through the ball — a common amateur "
               "fault.", lower_is_better=True),
        _entry("head_stability", "Head movement", head_stability, "shoulder widths",
               (0.0, 0.6),
               "How far the head drifts between address and impact. Less "
               "movement makes consistent contact easier.",
               lower_is_better=True),
        _entry("lead_knee_flex_at_address", "Lead knee flex at address",
               _safe(signals["lead_knee_flex"], address_ref), "°", (140.0, 170.0),
               "Athletic knee flex at setup (180 = fully straight)."),
    ]

    return {
        "summary": summary,
        "series": {name: _round_series(values) for name, values in signals.items()
                   if name != "wrist_height"} | {
                   "wrist_height": _round_series(signals["wrist_height"], 3)},
        "kinematic_sequence": _kinematic_sequence(series, signals, ev, handedness),
        "events": {k: int(v) for k, v in ev.items()},
        "fps": fps,
        "handedness": handedness,
        "notes": NOTES,
    }
