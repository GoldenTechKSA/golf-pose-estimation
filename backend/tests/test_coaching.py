"""Coaching report assembly. All pure — no API key, no network.

The point of `build_report` is that the model is not trusted past its own
choices: it names a metric and picks drill ids, and everything a golfer will
read as a fact comes from data we computed.
"""
import pytest
from pydantic import ValidationError

from app.services.coaching import (
    CoachingReport,
    Improvement,
    MetricKey,
    Strength,
    build_report,
)
from app.services.drill_library import DRILLS, drills_for, resolve, valid_ids_for


def _report(improvements: list[Improvement]) -> CoachingReport:
    return CoachingReport(
        overall_assessment="Solid base to build on.",
        strengths=[Strength(title="Posture", detail="Spine tilt is in a good window.")],
        improvements=improvements,
        injury_risk_notes=[],
        limitations_note="2D video has limits.",
    )


@pytest.fixture
def metrics() -> dict:
    return {
        "summary": [
            {
                "key": "early_extension", "label": "Early extension", "value": 14.0,
                "unit": "°", "ideal_range": [-6.0, 8.0], "lower_is_better": True,
                "assessment": "watch", "delta": 6.0, "delta_normalized": 0.43,
                "description": "...",
            },
            {
                "key": "tempo_ratio", "label": "Tempo", "value": 1.8, "unit": ":1",
                "ideal_range": [2.2, 3.8], "lower_is_better": False,
                "assessment": "watch", "delta": -0.4, "delta_normalized": 0.25,
                "description": "...",
            },
            {
                "key": "head_stability", "label": "Head movement", "value": None,
                "unit": "shoulder widths", "ideal_range": [0.0, 0.6],
                "lower_is_better": True, "assessment": None,
                "delta": None, "delta_normalized": None, "description": "...",
            },
        ]
    }


class TestDrillLibraryIntegrity:
    def test_ids_are_globally_unique(self):
        ids = [d["id"] for drills in DRILLS.values() for d in drills]
        assert len(ids) == len(set(ids))

    def test_every_drill_is_complete(self):
        for key, drills in DRILLS.items():
            assert drills, f"{key} has an empty drill list"
            for d in drills:
                assert d["name"].strip()
                assert d["fixes"].strip()
                assert d["how_to"].strip()

    def test_resolve_round_trips(self):
        for drills in DRILLS.values():
            for d in drills:
                assert resolve(d["id"]) == d

    def test_resolve_rejects_an_invented_id(self):
        assert resolve("hoganesque_lag_accelerator") is None

    def test_every_drill_key_is_a_real_metric_key(self):
        """A drill filed under a key the schema forbids can never be selected."""
        allowed = set(MetricKey.__args__)
        assert set(DRILLS) <= allowed, set(DRILLS) - allowed


class TestBuildReport:
    def test_hydrates_drills_and_attaches_the_numbers(self, metrics):
        drill = drills_for("early_extension")[0]["id"]
        out = build_report(
            _report([Improvement(metric_key="early_extension", issue="Standing up",
                                 why_it_matters="Costs strike quality.",
                                 drill_ids=[drill])]),
            metrics,
        )
        [imp] = out["improvements"]
        assert imp["drills"][0]["name"] == resolve(drill)["name"]
        ctx = imp["metric_context"]
        assert ctx["value"] == 14.0
        assert ctx["ideal_range"] == [-6.0, 8.0]
        assert ctx["delta"] == 6.0
        assert ctx["lower_is_better"] is True

    def test_invented_drill_ids_are_filtered_out(self, metrics):
        real = drills_for("early_extension")[0]["id"]
        out = build_report(
            _report([Improvement(metric_key="early_extension", issue="Standing up",
                                 why_it_matters="...",
                                 drill_ids=[real, "hoganesque_lag_accelerator"])]),
            metrics,
        )
        ids = [d["id"] for d in out["improvements"][0]["drills"]]
        assert ids == [real]

    def test_all_ids_invented_falls_back_to_the_catalog(self, metrics):
        out = build_report(
            _report([Improvement(metric_key="tempo_ratio", issue="Rushed",
                                 why_it_matters="...", drill_ids=["totally_made_up"])]),
            metrics,
        )
        [imp] = out["improvements"]
        assert imp["drills"][0]["id"] in valid_ids_for("tempo_ratio")

    def test_drills_from_another_metric_are_rejected(self, metrics):
        foreign = drills_for("tempo_ratio")[0]["id"]
        out = build_report(
            _report([Improvement(metric_key="early_extension", issue="Standing up",
                                 why_it_matters="...", drill_ids=[foreign])]),
            metrics,
        )
        ids = [d["id"] for d in out["improvements"][0]["drills"]]
        assert foreign not in ids
        assert ids[0] in valid_ids_for("early_extension")

    def test_schema_rejects_an_invented_metric_key(self):
        """Structured output cannot return a metric that does not exist."""
        with pytest.raises(ValidationError):
            Improvement(metric_key="swing_vibes", issue="Vibes",
                        why_it_matters="...", drill_ids=[])

    def test_metric_measured_on_another_swing_but_not_this_one_is_dropped(self, metrics):
        """The key is real, so the schema allows it — but this swing has no
        `lead_arm_at_top` entry, and build_report must not invent context."""
        out = build_report(
            _report([Improvement(metric_key="lead_arm_at_top", issue="Bent arm",
                                 why_it_matters="...", drill_ids=[])]),
            metrics,
        )
        assert out["improvements"] == []

    def test_unmeasured_metric_drops_the_improvement(self, metrics):
        """head_stability has value None — masked by the camera-angle guard."""
        out = build_report(
            _report([Improvement(metric_key="head_stability", issue="Head moves",
                                 why_it_matters="...", drill_ids=[])]),
            metrics,
        )
        assert out["improvements"] == []

    def test_duplicate_ids_are_collapsed(self, metrics):
        drill = drills_for("early_extension")[0]["id"]
        out = build_report(
            _report([Improvement(metric_key="early_extension", issue="x",
                                 why_it_matters="y", drill_ids=[drill, drill])]),
            metrics,
        )
        assert len(out["improvements"][0]["drills"]) == 1

    def test_model_prose_survives_untouched(self, metrics):
        out = build_report(
            _report([Improvement(metric_key="tempo_ratio", issue="Rushed transition",
                                 why_it_matters="Timing suffers.",
                                 drill_ids=[drills_for("tempo_ratio")[0]["id"]])]),
            metrics,
        )
        assert out["overall_assessment"] == "Solid base to build on."
        assert out["improvements"][0]["issue"] == "Rushed transition"
        assert out["strengths"][0]["title"] == "Posture"
