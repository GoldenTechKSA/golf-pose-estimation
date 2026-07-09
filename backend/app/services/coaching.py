"""AI coaching feedback via the Claude API.

Takes the computed swing metrics and asks Claude to write coaching feedback
a golfer can act on. Structured output (a Pydantic schema enforced through
`messages.parse`) guarantees the response is valid JSON the frontend can
render section by section — no free-text parsing.

Coaching is a best-effort enhancement: any failure (no API key, network,
rate limit) logs and returns None so the swing analysis itself still
completes.
"""
import json
import logging
from typing import Literal

from pydantic import BaseModel, Field

from app.config import Settings
from app.services.drill_library import drills_for, resolve, valid_ids_for

logger = logging.getLogger(__name__)


# The metric keys are static, so the schema itself can forbid an invented one.
# `build_report` still guards against a key that exists but was not measured on
# this particular swing — that is a runtime fact the schema cannot know.
MetricKey = Literal[
    "tempo_ratio",
    "shoulder_turn_at_top",
    "hip_turn_at_top",
    "x_factor_at_top",
    "x_factor_stretch",
    "lead_arm_at_top",
    "lead_arm_at_impact",
    "spine_angle_at_address",
    "early_extension",
    "head_stability",
    "lead_knee_flex_at_address",
]


class Improvement(BaseModel):
    metric_key: MetricKey = Field(
        description="The `key` of the metric this improvement is about. Must be one "
                    "of the keys given in the metrics payload.")
    issue: str = Field(description="Short name of the swing fault or area to improve")
    why_it_matters: str = Field(description="One or two sentences on the effect on ball flight/consistency")
    drill_ids: list[str] = Field(
        description="1-3 drill ids chosen from the drill catalog for this metric_key. "
                    "Never invent an id.")


class Strength(BaseModel):
    title: str = Field(description="Short name of what the golfer does well")
    detail: str = Field(description="One or two sentences of specific, encouraging detail")


class CoachingReport(BaseModel):
    overall_assessment: str = Field(
        description="2-3 sentence overall read of the swing, encouraging but honest")
    strengths: list[Strength] = Field(description="Top 2-3 things this golfer does well")
    improvements: list[Improvement] = Field(
        description="Top 2-3 areas to improve, each with an actionable drill")
    injury_risk_notes: list[str] = Field(
        description="Any injury-risk flags suggested by the mechanics; empty if none")
    limitations_note: str = Field(
        description="One sentence acknowledging these metrics come from 2D video "
                    "analysis with inherent limitations vs 3D motion capture")


SYSTEM_PROMPT = (
    "You are a golf teaching professional analyzing a student's swing metrics "
    "produced by a 2D pose-estimation system. Be encouraging but honest. Use "
    "plain language, not jargon. Ground every observation in the specific "
    "numbers provided; never invent measurements. The metrics are projected "
    "2D angles from monocular video and have inherent limitations compared "
    "to 3D motion capture — factor that into your confidence.\n\n"
    "Two hard rules. First, for each improvement, set `metric_key` to one of "
    "the metric keys given to you, and pick `drill_ids` only from that metric's "
    "drill catalog — never invent a drill, a drill id, or a drill name. Second, "
    "do not restate the numbers in your prose: the value, ideal range, and delta "
    "are attached automatically. Say what the number means, not what it is.\n\n"
    "Rank improvements by `delta_normalized` (how far outside its ideal range a "
    "metric sits, in range-widths) rather than by the raw delta, so a small miss "
    "on a narrow range outranks a large miss on a wide one.\n\n"
    "You are shown only the metrics this camera angle can actually measure. "
    "`camera_view` tells you what you are looking at. From a down-the-line view "
    "shoulder and hip rotation are absent from the list on purpose — they cannot "
    "be recovered from this footage, so do not speculate about turn, coil, or "
    "X-Factor. Coach what you can see."
)


_PROMPT_FIELDS = (
    "key", "label", "value", "unit", "ideal_range",
    "delta", "delta_normalized", "assessment",
)


def usable_metrics(metrics: dict) -> list[dict]:
    """Entries the model is allowed to reason about: measured, and trustworthy.

    A metric the camera could not see is worse than a missing one — it looks
    like evidence. Ranking by delta_normalized would otherwise put the largest
    projection artifact at the top of the coaching report.
    """
    return [
        entry for entry in metrics.get("summary", [])
        if entry.get("value") is not None and entry.get("reliable", True)
    ]


def build_coaching_prompt(metrics: dict, phases: list[dict], handedness: str) -> str:
    """Assemble the user prompt from the analysis payload (pure, testable)."""
    summary = [
        {k: entry[k] for k in _PROMPT_FIELDS} for entry in usable_metrics(metrics)
    ]
    # Only offer drills for metrics this swing actually measured, so the model
    # cannot pick a drill for a metric it is not allowed to talk about.
    catalog = {
        entry["key"]: [
            {"id": d["id"], "name": d["name"]} for d in drills_for(entry["key"])
        ]
        for entry in summary
        if drills_for(entry["key"])
    }
    camera = metrics.get("camera") or {}
    payload = {
        "handedness": handedness,
        "camera_view": camera.get("view", "unknown"),
        "phases": [
            {"name": p["name"], "duration_s": round(p["end_time"] - p["start_time"], 2)}
            for p in phases
        ],
        "metrics": summary,
        "kinematic_sequence": metrics.get("kinematic_sequence"),
        "drill_catalog": catalog,
    }
    return (
        "Here are the biomechanical metrics extracted from a student's swing "
        "video, and the drills you may prescribe for each:\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Provide your coaching report: an overall assessment (2-3 sentences), "
        "the top 2-3 specific things this golfer is doing well, and the top 2-3 "
        "areas for improvement. For each improvement give the metric_key, the "
        "issue, why it matters, and 1-3 drill_ids from that metric's catalog. "
        "Add any injury risk flags the mechanics suggest."
    )


def build_report(report: CoachingReport, metrics: dict) -> dict:
    """Validate the model's selections and attach the authoritative numbers.

    Pure: no API key, no network. This is where the model stops being trusted —
    it chose a metric and some drill ids, and everything else (values, ranges,
    deltas, drill text) comes from data we computed.
    """
    by_key = {e["key"]: e for e in usable_metrics(metrics)}

    improvements = []
    for item in report.improvements:
        entry = by_key.get(item.metric_key)
        if entry is None:
            logger.warning("coaching named an unknown or unmeasured metric: %s",
                           item.metric_key)
            continue

        allowed = valid_ids_for(item.metric_key)
        chosen = [i for i in dict.fromkeys(item.drill_ids) if i in allowed]
        if len(chosen) != len(item.drill_ids):
            logger.warning("coaching proposed drill ids outside the catalog for %s: %s",
                           item.metric_key, set(item.drill_ids) - allowed)
        if not chosen:
            # Rather than drop a real fault over a bad id, fall back to the
            # catalogued drill for that metric.
            chosen = [d["id"] for d in drills_for(item.metric_key)[:1]]
        if not chosen:
            continue

        improvements.append({
            "metric_key": item.metric_key,
            "issue": item.issue,
            "why_it_matters": item.why_it_matters,
            "metric_context": {
                k: entry[k] for k in
                ("label", "value", "unit", "ideal_range",
                 "delta", "delta_normalized", "assessment", "lower_is_better")
            },
            "drills": [resolve(i) for i in chosen],
        })

    return {
        "overall_assessment": report.overall_assessment,
        "strengths": [s.model_dump() for s in report.strengths],
        "improvements": improvements,
        "injury_risk_notes": report.injury_risk_notes,
        "limitations_note": report.limitations_note,
    }


_client_singleton = None


def _cached_client(api_key: str):
    """Reuse one client per process so repeated jobs share the connection pool."""
    global _client_singleton
    if _client_singleton is None:
        import anthropic

        _client_singleton = anthropic.Anthropic(api_key=api_key)
    return _client_singleton


def generate_coaching(metrics: dict, phases: list[dict], handedness: str,
                      settings: Settings) -> dict | None:
    """Call Claude for coaching feedback. Returns None when unavailable."""
    if not settings.anthropic_api_key:
        logger.info("ANTHROPIC_API_KEY not configured; skipping coaching feedback")
        return None

    try:
        client = _cached_client(settings.anthropic_api_key)
        response = client.messages.parse(
            model=settings.coaching_model,
            max_tokens=settings.coaching_max_tokens,
            # Thinking tokens are drawn from max_tokens. Left on, they can starve
            # the JSON and truncate it into an unparseable response. This call is
            # extraction from numbers already computed, so there is nothing to reason
            # about.
            thinking={"type": "disabled"},
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": build_coaching_prompt(metrics, phases, handedness),
            }],
            output_format=CoachingReport,
        )
        report: CoachingReport | None = response.parsed_output
        if report is None:
            logger.warning("coaching response could not be parsed (stop_reason=%s)",
                           response.stop_reason)
            return None
        return {"model": settings.coaching_model, **build_report(report, metrics)}
    except Exception:  # noqa: BLE001 — coaching must never fail the analysis job
        logger.exception("coaching feedback generation failed")
        return None
