"""Verify /mc/tool-router-state endpoint returns expected shape.

Tests the route directly (not via full app lifespan) to keep the test
fast and independent of all the other services.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.tool_router import router as tool_router_router


@pytest.fixture(autouse=True)
def _init_db():
    from core.runtime.db import init_db
    init_db()


def test_tool_router_state_returns_200_and_shape():
    app = FastAPI()
    app.include_router(tool_router_router)
    with TestClient(app) as c:
        r = c.get("/mc/tool-router-state")
        assert r.status_code == 200
        body = r.json()
        assert "enabled" in body
        assert "totals" in body
        assert "config" in body
        assert "recent_decisions" in body
        assert "confidence_histogram" in body
        assert "top_missed_tools_7d" in body


def test_tool_router_state_config_fields():
    app = FastAPI()
    app.include_router(tool_router_router)
    with TestClient(app) as c:
        r = c.get("/mc/tool-router-state")
        cfg = r.json().get("config", {})
        assert "threshold" in cfg
        assert "always_core_size" in cfg
        assert "k_embeddings" in cfg
        assert "embedding_model" in cfg
