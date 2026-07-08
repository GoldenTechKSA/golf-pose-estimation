import numpy as np
import pytest

from app.core.keypoints import KP, NUM_KEYPOINTS, KeypointSeries
from app.core.smoothing import interpolate_gaps, moving_average, smooth_series, velocity


def make_series(n_frames: int = 30, fps: float = 30.0) -> KeypointSeries:
    data = np.zeros((n_frames, NUM_KEYPOINTS, 3))
    data[:, :, 2] = 1.0  # fully confident
    return KeypointSeries(data=data, fps=fps, width=1280, height=720)


class TestInterpolateGaps:
    def test_fills_gap_linearly(self):
        data = np.zeros((5, NUM_KEYPOINTS, 3))
        data[:, :, 2] = 1.0
        # left wrist x ramps 0,10,20,30,40 but frame 2 is a dropout
        data[:, KP.LEFT_WRIST, 0] = [0, 10, 999, 30, 40]
        data[2, KP.LEFT_WRIST, 2] = 0.0

        out = interpolate_gaps(data, conf_threshold=0.3)

        assert out[2, KP.LEFT_WRIST, 0] == pytest.approx(20.0)
        # confidence preserved so callers still know frame 2 was inferred
        assert out[2, KP.LEFT_WRIST, 2] == 0.0
        # confident frames untouched
        assert out[1, KP.LEFT_WRIST, 0] == 10.0

    def test_holds_edges(self):
        data = np.zeros((4, NUM_KEYPOINTS, 3))
        data[:, :, 2] = 1.0
        data[:, KP.NOSE, 1] = [999, 50, 60, 888]
        data[0, KP.NOSE, 2] = 0.0
        data[3, KP.NOSE, 2] = 0.0

        out = interpolate_gaps(data)

        assert out[0, KP.NOSE, 1] == 50.0
        assert out[3, KP.NOSE, 1] == 60.0

    def test_never_detected_joint_left_alone(self):
        data = np.zeros((4, NUM_KEYPOINTS, 3))
        data[:, :, 2] = 1.0
        data[:, KP.LEFT_EAR, 2] = 0.0
        out = interpolate_gaps(data)
        assert (out[:, KP.LEFT_EAR, :2] == 0).all()


class TestMovingAverage:
    def test_preserves_constant_signal(self):
        sig = np.full(20, 7.0)
        out = moving_average(sig, 5)
        assert out == pytest.approx(sig)

    def test_preserves_length_and_smooths_spike(self):
        sig = np.zeros(11)
        sig[5] = 10.0
        out = moving_average(sig, 5)
        assert out.shape == sig.shape
        assert out[5] == pytest.approx(2.0)  # spike spread over the window
        assert out.max() < sig.max()

    def test_window_one_is_identity(self):
        sig = np.arange(6, dtype=float)
        assert moving_average(sig, 1) == pytest.approx(sig)

    def test_works_on_stacked_arrays(self):
        sig = np.random.default_rng(0).normal(size=(50, NUM_KEYPOINTS, 2))
        out = moving_average(sig, 5)
        assert out.shape == sig.shape
        assert out.std() < sig.std()


class TestSmoothSeries:
    def test_reduces_jitter_without_shifting_mean(self):
        rng = np.random.default_rng(42)
        series = make_series(60)
        clean_x = np.linspace(100, 500, 60)
        series.data[:, KP.RIGHT_WRIST, 0] = clean_x + rng.normal(0, 8, 60)

        smoothed = smooth_series(series)

        noisy_err = np.abs(series.data[:, KP.RIGHT_WRIST, 0] - clean_x).mean()
        smooth_err = np.abs(smoothed.data[:, KP.RIGHT_WRIST, 0] - clean_x).mean()
        assert smooth_err < noisy_err
        assert smoothed.meta["smoothing_window"] % 2 == 1

    def test_returns_new_instance(self):
        series = make_series()
        smoothed = smooth_series(series)
        assert smoothed is not series
        assert smoothed.n_frames == series.n_frames


class TestVelocity:
    def test_linear_ramp_has_constant_velocity(self):
        sig = np.linspace(0, 90, 91)  # 1 unit per frame
        v = velocity(sig, fps=30.0)
        assert v == pytest.approx(np.full(91, 30.0))

    def test_short_signal(self):
        assert velocity(np.array([1.0]), fps=30.0) == pytest.approx([0.0])


class TestKeypointSeries:
    def test_shape_validation(self):
        with pytest.raises(ValueError):
            KeypointSeries(data=np.zeros((10, 5, 3)), fps=30, width=100, height=100)

    def test_wrist_height_flips_image_coordinates(self):
        series = make_series()
        series.data[:, KP.LEFT_WRIST, 1] = 700.0   # near bottom of 720p frame
        series.data[:, KP.RIGHT_WRIST, 1] = 700.0
        low = series.wrist_height()[0]
        series.data[:, KP.LEFT_WRIST, 1] = 100.0   # raised overhead
        series.data[:, KP.RIGHT_WRIST, 1] = 100.0
        high = series.wrist_height()[0]
        assert high > low

    def test_json_roundtrip(self):
        series = make_series(5)
        series.data[:, :, 0] = 123.456
        payload = series.to_json_payload()
        restored = KeypointSeries.from_json_payload(payload)
        assert restored.n_frames == 5
        assert restored.fps == series.fps
        assert restored.data[0, 0, 0] == pytest.approx(123.46)
