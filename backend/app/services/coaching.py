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

from pydantic import BaseModel, Field

from app.config import Settings

logger = logging.getLogger(__name__)


class Improvement(BaseModel):
    issue: str = Field(description="Short name of the swing fault or area to improve")
    why_it_matters: str = Field(description="One or two sentences on the effect on ball flight/consistency")
    drill: str = Field(description="A specific, actionable practice drill for this issue")


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
    "to 3D motion capture — factor that into your confidence."
)


def build_coaching_prompt(metrics: dict, phases: list[dict], handedness: str) -> str:
    """Assemble the user prompt from the analysis payload (pure, testable)."""
    summary = [
        {k: entry[k] for k in ("label", "value", "unit", "ideal_range", "assessment")}
        for entry in metrics.get("summary", [])
        if entry.get("value") is not None
    ]
    payload = {
        "handedness": handedness,
        "phases": [
            {"name": p["name"], "duration_s": round(p["end_time"] - p["start_time"], 2)}
            for p in phases
        ],
        "metrics": summary,
        "kinematic_sequence": metrics.get("kinematic_sequence"),
    }
    return (
        "Here are the biomechanical metrics extracted from a student's swing "
        "video:\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Provide your coaching report: an overall assessment (2-3 sentences), "
        "the top 2-3 specific things this golfer is doing well, the top 2-3 "
        "areas for improvement each with an actionable drill, and any injury "
        "risk flags based on the mechanics observed."
    )


def generate_coaching(metrics: dict, phases: list[dict], handedness: str,
                      settings: Settings) -> dict | None:
    """Call Claude for coaching feedback. Returns None when unavailable."""
    if not settings.anthropic_api_key:
        logger.info("ANTHROPIC_API_KEY not configured; skipping coaching feedback")
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.parse(
            model=settings.coaching_model,
            max_tokens=settings.coaching_max_tokens,
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
        return {"model": settings.coaching_model, **report.model_dump()}
    except Exception:  # noqa: BLE001 — coaching must never fail the analysis job
        logger.exception("coaching feedback generation failed")
        return None
