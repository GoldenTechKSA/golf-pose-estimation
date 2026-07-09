"""Compare a user's swing against a reference swing.

Pure functions over two metrics payloads. No I/O, no database.

The governing rule is that a 2D metric is a property of a swing *and* a camera.
Spine tilt from face-on measures how far the golfer leans toward the ball; from
down the line it measures forward bend from vertical. Both are called
"spine_angle" and neither converts into the other. So two swings can only be
compared metric-for-metric when they were filmed from the same view.

The exceptions are metrics that never touch the projection. Tempo is a ratio of
frame counts: it means the same thing from anywhere.
"""
from app.services.metric_calculator import ROTATION_METRIC_KEYS

# Metrics derived from timing rather than geometry. They survive any camera.
VIEW_INDEPENDENT_KEYS = frozenset({"tempo_ratio"})


def _entries(metrics: dict) -> dict[str, dict]:
    return {e["key"]: e for e in metrics.get("summary", [])}


def views_compatible(user_view: str, reference_view: str) -> bool:
    """Same known view, or we cannot honestly line the numbers up."""
    if user_view == "unknown" or reference_view == "unknown":
        return False
    return user_view == reference_view


def _skip(key: str, label: str, reason: str) -> dict:
    return {"key": key, "label": label, "reason": reason}


def compute_comparison(user_metrics: dict, reference_metrics: dict) -> dict:
    """Diff every metric the two swings can honestly be compared on.

    A metric is comparable when: both swings measured it, both consider it
    reliable for their camera view, and either the views match or the metric is
    view-independent.
    """
    user_view = (user_metrics.get("camera") or {}).get("view", "unknown")
    ref_view = (reference_metrics.get("camera") or {}).get("view", "unknown")
    compatible = views_compatible(user_view, ref_view)

    user_by_key = _entries(user_metrics)
    ref_by_key = _entries(reference_metrics)

    compared: list[dict] = []
    skipped: list[dict] = []

    for key, user in user_by_key.items():
        ref = ref_by_key.get(key)
        label = user["label"]

        if ref is None:
            skipped.append(_skip(key, label, "the reference swing has no such metric"))
            continue
        if user["value"] is None or ref["value"] is None:
            skipped.append(_skip(key, label, "not measured in one of the swings"))
            continue
        if not user.get("reliable", True) or not ref.get("reliable", True):
            reason = user.get("unreliable_reason") or ref.get("unreliable_reason") \
                or "not measurable from this camera angle"
            skipped.append(_skip(key, label, reason))
            continue
        if not compatible and key not in VIEW_INDEPENDENT_KEYS:
            skipped.append(_skip(
                key, label,
                f"the swings were filmed from different views ({user_view} vs "
                f"{ref_view}), so this angle is not comparable"))
            continue

        difference = round(user["value"] - ref["value"], 1)
        compared.append({
            "key": key,
            "label": label,
            "unit": user["unit"],
            "user_value": user["value"],
            "reference_value": ref["value"],
            "difference": difference,
            "ideal_range": user["ideal_range"],
            "user_assessment": user["assessment"],
            "lower_is_better": user["lower_is_better"],
            # Rank by how far the golfer sits from the reference, in the ideal
            # band's own units, so a big gap on a tight metric outranks a big
            # gap on a loose one. No band, no ranking.
            "gap_normalized": _gap_normalized(difference, user["ideal_range"]),
            "view_independent": key in VIEW_INDEPENDENT_KEYS,
        })

    compared.sort(key=lambda m: -(m["gap_normalized"] or 0.0))

    return {
        "camera": {
            "user_view": user_view,
            "reference_view": ref_view,
            "compatible": compatible,
            "reason": None if compatible else _incompatible_reason(user_view, ref_view),
        },
        "metrics": compared,
        "skipped": skipped,
    }


def _gap_normalized(difference: float, ideal_range: list | None) -> float | None:
    if not ideal_range:
        return None
    width = ideal_range[1] - ideal_range[0]
    if width <= 0:
        return None
    return round(abs(difference) / width, 2)


def _incompatible_reason(user_view: str, ref_view: str) -> str:
    if "unknown" in (user_view, ref_view):
        return ("The camera angle of one of these swings could not be determined, "
                "so their projected angles cannot be lined up.")
    return (f"Your swing was filmed {user_view.replace('_', ' ')} and the reference "
            f"{ref_view.replace('_', ' ')}. A 2D angle is a property of the swing and "
            "the camera together, so only timing can be compared across views.")


def rotation_note(user_view: str) -> str | None:
    """Rotation is absent from any non-face-on comparison; say why once."""
    if user_view == "face_on":
        return None
    return ("Shoulder turn, hip turn and X-Factor are not compared: they cannot be "
            "measured from this view in either swing.")


__all__ = [
    "ROTATION_METRIC_KEYS",
    "VIEW_INDEPENDENT_KEYS",
    "compute_comparison",
    "rotation_note",
    "views_compatible",
]
