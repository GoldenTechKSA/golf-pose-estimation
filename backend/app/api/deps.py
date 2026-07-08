"""FastAPI dependencies backed by app.state (set up in main.create_app)."""
from fastapi import Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.services.storage import LocalStorage


def get_db(request: Request):
    session: Session
    with request.app.state.session_factory() as session:
        yield session


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_storage_dep(request: Request) -> LocalStorage:
    return request.app.state.storage
