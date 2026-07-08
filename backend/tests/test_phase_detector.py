import numpy as np
import pytest

from app.core.keypoints import NUM_KEYPOINTS, KeypointSeries
from app.services.phase_detector import PHASE_ORDER, detect_phases

from tests.synthetic import make_static_series, make_swing_series


@pytest.fixture(scope="module")
def swing():
    series, truth = make_swing_series()
    return detect_phases(series), truth


class TestPhaseDetection:
    def test_detects_all_seven_phases_in_order(self, swing):
        phases, _ = swing
        names = [s["name"] for s in phases.segments]
        assert names == PHASE_ORDER

    def test_segments_tile_the_video_exactly(self, swing):
        phases, truth = swing
        assert phases.segments[0]["start_frame"] == 0
        assert phases.segments[-1]["end_frame"] == truth["n_frames"] - 1
        for prev, cur in zip(phases.segments, phases.segments[1:]):
            assert cur["start_frame"] == prev["end_frame"] + 1

    def test_frame_labels_match_segments(self, swing):
        phases, truth = swing
        assert len(phases.frame_labels) == truth["n_frames"]
        for seg in phases.segments:
            assert phases.frame_labels[seg["start_frame"]] == seg["name"]
            assert phases.frame_labels[seg["end_frame"]] == seg["name"]

    def test_top_event_near_truth(self, swing):
        phases, truth = swing
        lo, hi = truth["top_range"]
        assert lo - 3 <= phases.events["top"] <= hi + 3

    def test_impact_event_near_truth(self, swing):
        phases, truth = swing
        assert abs(phases.events["impact"] - truth["impact"]) <= 4

    def test_takeaway_after_address_starts(self, swing):
        phases, truth = swing
        # takeaway is where the wrists have measurably left address height —
        # after the still period, well before the top
        assert truth["address_end"] - 2 <= phases.events["takeaway"] < truth["top_range"][0]

    def test_finish_detected_after_follow_through(self, swing):
        phases, truth = swing
        assert phases.events["finish"] >= truth["impact"]
        finish_seg = phases.segments[-1]
        assert finish_seg["name"] == "finish"
        assert finish_seg["start_frame"] >= truth["impact"] + 1

    def test_times_derive_from_frames(self, swing):
        phases, _ = swing
        seg = phases.segments[1]
        assert seg["start_time"] == pytest.approx(seg["start_frame"] / 50.0, abs=1e-3)


class TestRejection:
    def test_static_video_is_not_a_swing(self):
        with pytest.raises(ValueError, match="no golf swing"):
            detect_phases(make_static_series())

    def test_too_short_video_rejected(self):
        data = np.zeros((5, NUM_KEYPOINTS, 3))
        series = KeypointSeries(data=data, fps=30, width=640, height=480)
        with pytest.raises(ValueError, match="too few frames"):
            detect_phases(series)
