import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path}/test.db",
        storage_dir=tmp_path / "storage",
        processing_mode="inline",
        # Point at a closed port so progress reporting exercises its
        # no-redis fallback quickly instead of finding a real server.
        redis_url="redis://127.0.0.1:6399/0",
        anthropic_api_key="",
    )


@pytest.fixture
def test_app(settings):
    return create_app(settings)


@pytest.fixture
def enqueued(monkeypatch) -> list[str]:
    """Capture dispatched swing ids instead of actually processing videos."""
    calls: list[str] = []
    monkeypatch.setattr(
        "app.api.routes.swings.enqueue_processing",
        lambda settings, swing_id: calls.append(swing_id),
    )
    return calls


@pytest.fixture
def client(test_app, enqueued):
    with TestClient(test_app) as c:
        yield c


def upload_fake_swing(client, filename: str = "swing.mp4") -> str:
    """Upload a dummy video file and return the new swing id."""
    response = client.post(
        "/api/v1/swings/upload",
        files={"file": (filename, b"\x00" * 1024, "video/mp4")},
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]
