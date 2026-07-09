"""Align a reference skeleton onto a user's swing, in time and in space.

Two problems, solved separately.

**Time.** Two swings differ in tempo and length, so frame 40 of one is not frame
40 of the other. `detect_phases` already gives both swings the same four
landmarks — takeaway, top, impact, finish — so we warp piecewise-linearly
between them. The map is monotonic by construction and lines up the moments a
coach cares about. Dynamic time warping would also work, but it is opaque, needs
a signal to warp on, and can produce non-monotonic maps that look wrong on video.

**Space.** Two golfers differ in size, distance from the camera, and framing. The
transform is scale + translate only. Rotation is deliberately excluded: golfers
should be compared upright, and rotating the reference to fit would hide exactly
the posture differences the overlay exists to show.
"""
import numpy as np

from app.core.keypoints import KP, KeypointSeries

# Left/right COCO indices, swapped when the two golfers differ in handedness.
_MIRROR_PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]

_ANCHOR_EVENTS = ("takeaway", "top", "impact", "finish")


def anchors(events: dict[str, int], n_frames: int) -> list[int]:
    """Frame indices to warp between: the ends, pinned, plus the four events.

    Clamped and made strictly increasing — a swing where two events land on the
    same frame would otherwise divide by zero.
    """
    raw = [0, *(events[k] for k in _ANCHOR_EVENTS), n_frames - 1]
    out: list[int] = []
    for value in raw:
        value = max(0, min(int(value), n_frames - 1))
        if out and value <= out[-1]:
            value = out[-1] + 1
        out.append(value)
    # If clamping pushed past the end, walk the tail back down.
    for i in range(len(out) - 1, 0, -1):
        if out[i] > n_frames - 1:
            out[i] = n_frames - 1
        if out[i] <= out[i - 1]:
            out[i - 1] = out[i] - 1
    return out


def frame_map(user_events: dict[str, int], user_frames: int,
              ref_events: dict[str, int], ref_frames: int) -> list[int]:
    """For every user frame, the reference frame that is at the same point."""
    a_user = anchors(user_events, user_frames)
    a_ref = anchors(ref_events, ref_frames)

    mapped: list[int] = []
    for f in range(user_frames):
        # Find the segment [a_user[i], a_user[i+1]] holding this frame.
        i = 0
        while i < len(a_user) - 2 and f > a_user[i + 1]:
            i += 1
        lo, hi = a_user[i], a_user[i + 1]
        t = 0.0 if hi == lo else (f - lo) / (hi - lo)
        r_lo, r_hi = a_ref[i], a_ref[i + 1]
        mapped.append(int(round(r_lo + t * (r_hi - r_lo))))
    return [max(0, min(m, ref_frames - 1)) for m in mapped]


def hip_centers(series: KeypointSeries) -> np.ndarray:
    return series.midpoint(KP.LEFT_HIP, KP.RIGHT_HIP)


def torso_scale(series: KeypointSeries) -> float:
    """Median hip-centre to shoulder-centre distance.

    Shoulder *width* foreshortens badly from behind; torso height does not, so
    it is the one body length that survives every camera view.
    """
    shoulders = series.midpoint(KP.LEFT_SHOULDER, KP.RIGHT_SHOULDER)
    lengths = np.linalg.norm(shoulders - hip_centers(series), axis=-1)
    usable = lengths[lengths > 1e-6]
    return float(np.median(usable)) if usable.size else 1.0


def mirror_keypoints(data: np.ndarray, width: int) -> np.ndarray:
    """Flip a series horizontally and swap left/right joints."""
    out = data.copy()
    out[..., 0] = width - out[..., 0]
    for a, b in _MIRROR_PAIRS:
        out[:, [a, b]] = out[:, [b, a]]
    return out


def build_overlay(user: KeypointSeries, user_events: dict[str, int],
                  reference: KeypointSeries, ref_events: dict[str, int],
                  mirror: bool) -> dict:
    """Everything a client needs to draw the reference over the user's video.

    The transform is returned rather than applied so the client can switch
    between anchoring modes without another round trip:

        address-anchored:  p' = c_user[anchor] + s * (p - c_ref[mapped anchor])
        body-locked:       p' = c_user[f]      + s * (p - c_ref[mapped f])

    Address-anchored keeps each golfer's own translation through the swing, so
    sway and early extension stay visible. That is the default, and it is what a
    coach is looking for. Body-locked cancels translation to isolate limb shape.
    """
    ref_data = reference.data
    if mirror:
        ref_data = mirror_keypoints(ref_data, reference.width)
        reference = KeypointSeries(ref_data, reference.fps, reference.width,
                                   reference.height)

    mapping = frame_map(user_events, user.n_frames, ref_events, reference.n_frames)
    scale = torso_scale(user) / max(torso_scale(reference), 1e-6)
    anchor = int(user_events["takeaway"])  # end of address: both golfers are still

    return {
        "frame_map": mapping,
        "anchor_frame": anchor,
        "scale": round(scale, 4),
        "mirrored": mirror,
        "user": {
            "fps": user.fps,
            "n_frames": user.n_frames,
            "width": user.width,
            "height": user.height,
            "hip_centers": np.round(hip_centers(user), 1).tolist(),
        },
        "reference": {
            "n_frames": reference.n_frames,
            "width": reference.width,
            "height": reference.height,
            "hip_centers": np.round(hip_centers(reference), 1).tolist(),
            "keypoints": np.round(ref_data, 1).tolist(),
        },
    }
