"""Comparing two swings. Pure — no storage, no database.

A 2D angle is a property of the swing *and* the camera. Most of these tests are
about refusing to compare things that only look comparable.
"""
from app.services.comparison import (
    compute_comparison,
    rotation_note,
    views_compatible,
)


def _metrics(view: str, values: dict[str, float | None], *, reliable_rotation=False) -> dict:
    spec = {
        "tempo_ratio": ("Tempo", ":1", [2.2, 3.8], False),
        "spine_angle_at_address": ("Spine tilt at address", "°", [15.0, 45.0], False),
        "early_extension": ("Early extension", "°", [-6.0, 8.0], True),
        "shoulder_turn_at_top": ("Shoulder turn at top", "°", [60.0, 120.0], False),
    }
    summary = []
    for key, (label, unit, ideal, lower) in spec.items():
        if key not in values:
            continue
        rotation = key == "shoulder_turn_at_top"
        reliable = reliable_rotation if rotation else True
        summary.append({
            "key": key, "label": label, "value": values[key], "unit": unit,
            "ideal_range": ideal, "lower_is_better": lower,
            "assessment": "good", "delta": 0.0, "delta_normalized": 0.0,
            "reliable": reliable,
            "unreliable_reason": None if reliable else "camera axis",
            "description": "",
        })
    return {"camera": {"view": view, "frontality": 0.1, "rotation_measurable": False},
            "summary": summary}


class TestViewCompatibility:
    def test_same_view_is_compatible(self):
        assert views_compatible("down_the_line", "down_the_line")

    def test_different_views_are_not(self):
        assert not views_compatible("face_on", "down_the_line")

    def test_unknown_is_never_compatible(self):
        assert not views_compatible("unknown", "unknown")
        assert not views_compatible("face_on", "unknown")


class TestCompareSameView:
    def test_compares_metrics_and_signs_the_difference(self):
        user = _metrics("down_the_line", {"spine_angle_at_address": 31.4})
        ref = _metrics("down_the_line", {"spine_angle_at_address": 38.0})
        out = compute_comparison(user, ref)
        [m] = out["metrics"]
        assert m["user_value"] == 31.4
        assert m["reference_value"] == 38.0
        assert m["difference"] == -6.6  # the user sits below the reference

    def test_gap_is_normalized_by_the_ideal_band(self):
        """A 6-degree gap matters more against a 14-wide band than a 30-wide one."""
        user = _metrics("down_the_line", {"spine_angle_at_address": 20.0, "early_extension": 0.0})
        ref = _metrics("down_the_line", {"spine_angle_at_address": 26.0, "early_extension": 6.0})
        out = compute_comparison(user, ref)
        by_key = {m["key"]: m for m in out["metrics"]}
        assert by_key["early_extension"]["gap_normalized"] > \
            by_key["spine_angle_at_address"]["gap_normalized"]

    def test_biggest_gap_is_ranked_first(self):
        user = _metrics("down_the_line", {"spine_angle_at_address": 20.0, "early_extension": 0.0})
        ref = _metrics("down_the_line", {"spine_angle_at_address": 26.0, "early_extension": 6.0})
        out = compute_comparison(user, ref)
        assert out["metrics"][0]["key"] == "early_extension"

    def test_rotation_is_skipped_when_neither_can_measure_it(self):
        user = _metrics("down_the_line", {"shoulder_turn_at_top": 12.1})
        ref = _metrics("down_the_line", {"shoulder_turn_at_top": 95.0})
        out = compute_comparison(user, ref)
        assert out["metrics"] == []
        assert out["skipped"][0]["key"] == "shoulder_turn_at_top"

    def test_rotation_is_compared_when_both_are_face_on(self):
        user = _metrics("face_on", {"shoulder_turn_at_top": 80.0}, reliable_rotation=True)
        ref = _metrics("face_on", {"shoulder_turn_at_top": 95.0}, reliable_rotation=True)
        out = compute_comparison(user, ref)
        assert out["metrics"][0]["difference"] == -15.0


class TestCompareAcrossViews:
    def test_projected_angles_are_refused(self):
        """Spine tilt means different things from the two views; it does not convert."""
        user = _metrics("down_the_line", {"spine_angle_at_address": 31.4})
        ref = _metrics("face_on", {"spine_angle_at_address": 22.0})
        out = compute_comparison(user, ref)
        assert out["camera"]["compatible"] is False
        assert out["metrics"] == []
        assert "different views" in out["skipped"][0]["reason"]

    def test_tempo_still_compares_because_it_never_touches_the_projection(self):
        user = _metrics("down_the_line", {"tempo_ratio": 1.8, "spine_angle_at_address": 31.4})
        ref = _metrics("face_on", {"tempo_ratio": 3.0, "spine_angle_at_address": 22.0})
        out = compute_comparison(user, ref)
        assert [m["key"] for m in out["metrics"]] == ["tempo_ratio"]
        assert out["metrics"][0]["view_independent"] is True
        assert out["metrics"][0]["difference"] == -1.2

    def test_the_reason_names_both_views(self):
        user = _metrics("down_the_line", {"tempo_ratio": 1.8})
        ref = _metrics("face_on", {"tempo_ratio": 3.0})
        reason = compute_comparison(user, ref)["camera"]["reason"]
        assert "down the line" in reason and "face on" in reason


class TestMissingData:
    def test_metric_absent_from_the_reference_is_skipped(self):
        user = _metrics("down_the_line", {"tempo_ratio": 1.8, "early_extension": 5.5})
        ref = _metrics("down_the_line", {"tempo_ratio": 3.0})
        out = compute_comparison(user, ref)
        assert [s["key"] for s in out["skipped"]] == ["early_extension"]

    def test_unmeasured_value_is_skipped(self):
        user = _metrics("down_the_line", {"tempo_ratio": None})
        ref = _metrics("down_the_line", {"tempo_ratio": 3.0})
        out = compute_comparison(user, ref)
        assert out["metrics"] == []
        assert "not measured" in out["skipped"][0]["reason"]


class TestRotationNote:
    def test_silent_when_face_on(self):
        assert rotation_note("face_on") is None

    def test_explains_itself_otherwise(self):
        assert "cannot be measured" in rotation_note("down_the_line")
