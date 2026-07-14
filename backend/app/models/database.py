"""SQLAlchemy models and session management.

Works against SQLite for single-process dev/tests and PostgreSQL in
docker-compose — the JSON column type maps to native JSON on both.
"""
import enum
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import Settings


class SwingStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage(str, enum.Enum):
    """Coarse steps surfaced to the user while a swing processes."""

    QUEUED = "queued"
    PREPARING = "preparing"                    # probe + transcode
    EXTRACTING_KEYPOINTS = "extracting_keypoints"
    ANALYZING = "analyzing"                    # phases + metrics
    RENDERING = "rendering"                    # annotated video
    COACHING = "coaching"                      # Claude feedback
    DONE = "done"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Swing(Base):
    __tablename__ = "swings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                    default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    original_filename: Mapped[str] = mapped_column(String(255))
    handedness: Mapped[str] = mapped_column(String(8), default="right")

    status: Mapped[SwingStatus] = mapped_column(
        Enum(SwingStatus, values_callable=lambda e: [m.value for m in e]),
        default=SwingStatus.QUEUED,
    )
    stage: Mapped[str] = mapped_column(String(32), default=ProcessingStage.QUEUED.value)
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0..100
    error: Mapped[str | None] = mapped_column(Text, default=None)

    # Video metadata, filled in once the source video is probed.
    fps: Mapped[float | None] = mapped_column(Float, default=None)
    width: Mapped[int | None] = mapped_column(Integer, default=None)
    height: Mapped[int | None] = mapped_column(Integer, default=None)
    n_frames: Mapped[int | None] = mapped_column(Integer, default=None)
    duration: Mapped[float | None] = mapped_column(Float, default=None)

    pose_model: Mapped[str | None] = mapped_column(String(64), default=None)
    # Inference resolution this swing was actually processed at. Recorded so a
    # later change to the global pose_imgsz setting cannot retroactively distort
    # a comparison against a reference built at the swing's original resolution.
    pose_imgsz: Mapped[int | None] = mapped_column(Integer, default=None)

    analysis: Mapped["SwingAnalysis | None"] = relationship(
        back_populates="swing", uselist=False, cascade="all, delete-orphan"
    )


class SwingAnalysis(Base):
    __tablename__ = "swing_analyses"

    swing_id: Mapped[str] = mapped_column(
        ForeignKey("swings.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    phases: Mapped[list | None] = mapped_column(JSON, default=None)
    metrics: Mapped[dict | None] = mapped_column(JSON, default=None)
    coaching: Mapped[dict | None] = mapped_column(JSON, default=None)

    swing: Mapped[Swing] = relationship(back_populates="analysis")


def create_session_factory(settings: Settings) -> sessionmaker:
    """Engine + session factory; also ensures the schema exists.

    For a portfolio-scale app, create_all at startup stands in for
    migrations; Alembic can be layered on when the schema stabilizes.
    """
    url = settings.database_url
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        if not db_path.is_absolute():
            db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
