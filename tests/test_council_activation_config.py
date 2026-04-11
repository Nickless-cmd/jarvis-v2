from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import pytest
from fastapi.testclient import TestClient


def test_get_activation_config_returns_valid_shape():
    """Endpoint returns dict with sensitivity and auto_convene fields."""
    from apps.api.jarvis_api.app import app
    client = TestClient(app)
    resp = client.get("/mc/council-activation-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "sensitivity" in data
    assert "auto_convene" in data
    assert data["sensitivity"] in {"conservative", "balanced", "minimal"}
    assert isinstance(data["auto_convene"], bool)


def test_save_activation_config_returns_saved_flag():
    """POST endpoint persists and returns saved=True."""
    from apps.api.jarvis_api.app import app
    client = TestClient(app)
    resp = client.post(
        "/mc/council-activation-config",
        json={"sensitivity": "minimal", "auto_convene": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sensitivity"] == "minimal"
    assert data["auto_convene"] is False
    assert data["saved"] is True


def test_invalid_sensitivity_falls_back_to_balanced():
    """Unknown sensitivity value is coerced to 'balanced'."""
    from apps.api.jarvis_api.app import app
    client = TestClient(app)
    resp = client.post(
        "/mc/council-activation-config",
        json={"sensitivity": "extreme", "auto_convene": True},
    )
    assert resp.status_code == 200
    assert resp.json()["sensitivity"] == "balanced"
