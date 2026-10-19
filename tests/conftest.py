import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.config import settings
from core.database import init_db, DEFAULT_PROMPT_NAME


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Each test gets its own empty SQLite database (never the real prompts.db)."""
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "test_prompts.db"))
    init_db()
    return settings.DATABASE_PATH


@pytest.fixture
def client(temp_db):
    """Minimal app with only the prompts router (main.py would load PaddleOCR)."""
    from api.endpoints import prompts
    app = FastAPI()
    app.include_router(prompts.router, prefix="/api")
    return TestClient(app)


@pytest.fixture
def default_prompt_name():
    return DEFAULT_PROMPT_NAME


@pytest.fixture
def no_api_key(monkeypatch):
    """Guarantees no real Gemini call can happen during a test."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
