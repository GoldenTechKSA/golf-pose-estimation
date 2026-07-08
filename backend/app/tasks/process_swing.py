"""Celery task wrapper around the processing pipeline."""
from app.services.pipeline import run_swing_processing
from app.tasks.celery_app import celery_app


@celery_app.task(name="swinglens.process_swing")
def process_swing(swing_id: str) -> str:
    """Process one uploaded swing video end to end.

    Failures are recorded on the swing row by the pipeline itself (status
    FAILED + error message), so the task doesn't retry: a video that fails
    deterministically (corrupt file, no person visible) would just fail
    again.
    """
    run_swing_processing(swing_id)
    return swing_id
