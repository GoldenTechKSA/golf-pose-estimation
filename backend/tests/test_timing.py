import time

import pytest

from app.core.timing import format_timings, record


class TestRecord:
    def test_records_elapsed_seconds_under_key(self):
        timings: dict[str, float] = {}
        with record(timings, "work_s"):
            time.sleep(0.02)
        assert timings["work_s"] >= 0.02

    def test_records_even_when_the_block_raises(self):
        """A stage that blows up is exactly the one whose duration you want."""
        timings: dict[str, float] = {}
        with pytest.raises(RuntimeError):
            with record(timings, "boom_s"):
                raise RuntimeError("stage failed")
        assert "boom_s" in timings

    def test_keys_accumulate_across_stages(self):
        timings: dict[str, float] = {}
        with record(timings, "a_s"):
            pass
        with record(timings, "b_s"):
            pass
        assert sorted(timings) == ["a_s", "b_s"]


class TestFormatTimings:
    def test_renders_key_value_pairs_in_call_order(self):
        line = format_timings(swing="abc", total_s=1.5, n_frames=120)
        assert line == "swing=abc total_s=1.5 n_frames=120"

    def test_empty_is_empty(self):
        assert format_timings() == ""
