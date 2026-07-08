"""Application configuration.

All settings can be overridden with environment variables (case-insensitive)
or a `.env` file in the backend directory, e.g. `DATABASE_URL=postgresql://...`.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Service ---
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # --- Persistence ---
    database_url: str = "sqlite:///./data/swinglens.db"
    storage_dir: Path = Path("./data/storage")

    # --- Task queue ---
    redis_url: str = "redis://localhost:6379/0"
    # "celery": enqueue to the worker (production / docker-compose).
    # "inline": run processing in a background thread of the API process
    #           (single-process dev and integration tests — no Redis needed,
    #           progress falls back to database polling).
    processing_mode: Literal["celery", "inline"] = "celery"

    # --- Uploads ---
    max_upload_mb: int = 200
    allowed_video_extensions: frozenset[str] = frozenset({".mp4", ".mov", ".avi"})

    # --- Pose estimation ---
    # The pose model is swappable: any Ultralytics *-pose checkpoint name works
    # here, and the fallbacks are tried in order if the primary fails to load
    # (e.g. yolo26 weights not yet published for the installed ultralytics).
    pose_model: str = "yolo26m-pose.pt"
    pose_model_fallbacks: list[str] = ["yolo11m-pose.pt", "yolov8m-pose.pt"]
    pose_device: str = ""  # "" lets ultralytics pick (cuda/mps/cpu)
    pose_conf_threshold: float = 0.25
    # Long side of frames fed to the model; larger inputs are downscaled for
    # inference speed (annotation is still rendered at the processing size).
    max_processing_dim: int = 1280

    # --- Golfer ---
    # 2D metrics need to know the lead side; right-handed golfers lead with
    # the left arm. Can be overridden per upload.
    default_handedness: Literal["right", "left"] = "right"

    # --- AI coaching ---
    anthropic_api_key: str = ""
    coaching_model: str = "claude-sonnet-5"
    coaching_max_tokens: int = 2000


@lru_cache
def get_settings() -> Settings:
    return Settings()
