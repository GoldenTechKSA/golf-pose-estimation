"""Celery application for background video processing.

Redis is both broker and result backend. Worker startup:

    celery -A app.tasks.celery_app worker --loglevel=info --concurrency=1

Concurrency defaults to 1 in docker-compose because a single pose-model
inference already saturates the CPU/GPU; scale with more worker containers
rather than more threads fighting over one model.
"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "swinglens",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.process_swing"],
)

celery_app.conf.update(
    task_acks_late=True,               # re-deliver if a worker dies mid-video
    worker_prefetch_multiplier=1,      # one long video job at a time
    task_track_started=True,
    result_expires=3600,
)
