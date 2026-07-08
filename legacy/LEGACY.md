# Legacy: CSE 455 Class Project

This directory preserves the original computer vision class project that SwingLens grew out of:
a CLI tool using MediaPipe Pose (with an experimental RTMPose training pipeline) that annotates
a golf swing video with skeleton keypoints, a 5-phase state-machine detector, and rule-based
per-phase feedback.

Nothing in here is imported by the SwingLens application. It is kept for provenance — the
platform's phase detection and biomechanics were redesigned from scratch in `backend/`
(7 canonical phases, global signal analysis instead of a single-pass state machine, and pure,
unit-tested metric functions).

See the original [README](README.md) and [DOCUMENTATION](DOCUMENTATION.md) for how it worked.
