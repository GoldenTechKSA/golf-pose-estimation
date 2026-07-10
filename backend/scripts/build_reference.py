"""Build a reference swing from a video file. Maintainer tool, run offline.

    python -m scripts.build_reference \
        --input /path/to/swing.mp4 \
        --id ref-a \
        --display-name "Reference A (tour-caliber, down the line)" \
        --handedness right \
        --source "self-filmed, consented" \
        --license "owned"

Runs the same pipeline stages a user upload does — normalize, pose, smooth,
phases, metrics — and freezes the result under {storage_dir}/references/{id}/.
Nothing here touches the Swing table or Celery: a reference has no lifecycle.

Deliberately source-agnostic. It takes a path and records whatever provenance
you give it; where the video came from, and whether you may ship it, is a
decision this script does not make and cannot make for you.
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from app.config import get_settings
from app.core.smoothing import smooth_series
from app.services import video_processor as vp
from app.services.metric_calculator import compute_metrics
from app.services.phase_detector import detect_phases
from app.services.pose import create_pose_estimator
from app.services.reference_library import ReferenceLibrary

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("build_reference")


def build(args: argparse.Namespace) -> int:
    settings = get_settings()
    library = ReferenceLibrary(settings)
    ref_dir = library.reference_dir(args.id)
    ref_dir.mkdir(parents=True, exist_ok=True)

    source = ref_dir / "source.mp4"
    logger.info("normalizing %s", args.input)
    vp.normalize_video(Path(args.input), source, settings.max_processing_dim)
    info = vp.probe(source)
    vp.save_thumbnail(source, ref_dir / "thumbnail.jpg")

    logger.info("extracting keypoints (%d frames)", info.n_frames)
    raw = vp.extract_keypoints(source, create_pose_estimator(settings))

    # Persist the SMOOTHED series: it is the one phases and metrics were computed
    # from, so an overlay drawn from it will agree with the numbers beside it.
    smoothed = smooth_series(raw, conf_threshold=settings.pose_conf_threshold)
    phases = detect_phases(smoothed)
    metrics = compute_metrics(smoothed, phases, args.handedness)

    payload = smoothed.to_json_payload()
    payload["meta"] = {**payload.get("meta", {}), "smoothed": True}
    (ref_dir / "keypoints.json").write_text(json.dumps(payload))
    (ref_dir / "phases.json").write_text(json.dumps(
        {"segments": phases.segments, "events": phases.events}))
    (ref_dir / "metrics.json").write_text(json.dumps(metrics))

    camera = metrics["camera"]
    profile = {
        "id": args.id,
        "display_name": args.display_name,
        "handedness": args.handedness,
        # Detected, not asserted: the manifest records what the footage shows.
        "camera_view": camera["view"],
        "frontality": camera["frontality"],
        "source": args.source,
        "license": args.license,
        "has_video": True,
        "n_frames": info.n_frames,
        "fps": info.fps,
        # Inference resolution shifts these metrics by more than the golfer
        # differences a comparison is trying to show (640 -> 512 moved
        # shoulder_turn_at_top 8.5 deg and flipped early_extension's verdict).
        # Record what produced these numbers so a mismatch can be surfaced.
        "pose_model": settings.pose_model,
        "pose_imgsz": settings.pose_imgsz,
    }
    (ref_dir / "profile.json").write_text(json.dumps(profile, indent=2))

    index_path = library.root / "index.json"
    existing = [r for r in library.list() if r["id"] != args.id]
    summary = {k: profile[k] for k in
               ("id", "display_name", "handedness", "camera_view", "source",
                "license", "has_video", "pose_model", "pose_imgsz")}
    index_path.write_text(json.dumps({"references": existing + [summary]}, indent=2))

    logger.info("built reference %s: view=%s frontality=%s",
                args.id, camera["view"], camera["frontality"])
    if camera["view"] != "down_the_line":
        logger.warning("this reference is %s, not down_the_line — it will only be "
                       "comparable against swings filmed the same way",
                       camera["view"])

    _warn_if_not_exemplary(metrics)
    return 0


def _warn_if_not_exemplary(metrics: dict) -> None:
    """A reference is something a golfer is asked to move toward.

    If the reference's own metrics sit outside their ideal bands, comparing
    against it is arithmetic without meaning: the diff will be large, correct,
    and useless. Usually this means the pose track is poor, not that the golfer
    is bad. Either way it should not silently become the thing users aim at.
    """
    offenders = [
        e for e in metrics["summary"]
        if e.get("reliable", True) and e["assessment"] == "watch"
    ]
    if not offenders:
        return
    logger.warning("this reference is outside the ideal band on %d metric(s):",
                   len(offenders))
    for e in offenders:
        logger.warning("    %-28s %-8s ideal %s", e["label"], e["value"], e["ideal_range"])
    logger.warning("It will still build. But golfers will be compared against these "
                   "numbers, so check the annotated video before shipping it.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, help="path to the source video")
    p.add_argument("--id", required=True, help="opaque reference id, e.g. ref-a")
    p.add_argument("--display-name", required=True)
    p.add_argument("--handedness", default="right", choices=("right", "left"))
    p.add_argument("--source", required=True,
                   help="provenance, recorded verbatim in the manifest")
    p.add_argument("--license", required=True,
                   help="what you are allowed to do with this footage")
    return build(p.parse_args())


if __name__ == "__main__":
    sys.exit(main())
