"""Tests for central_dissent — HAL's Silence (tavse indsigelser)."""
from __future__ import annotations

from unittest.mock import patch

import core.services.central_dissent as dissent


# ─── _ENFORCED sættet ───────────────────────────────────────────────────────

def test_enforced_includes_memory_promotion():
    """memory_promotion SKAL være i _ENFORCED (fix for 800 falske dissents, 6. jul 2026)."""
    assert "memory_promotion" in dissent._ENFORCED


def test_enforced_includes_security_gates():
    """Sikkerheds/håndhævede gates skal alle være i _ENFORCED."""
    expected = {"decision_gate", "self_review", "fact_gate", "verification", "cross_user_share"}
    assert expected.issubset(dissent._ENFORCED)


# ─── list_dissents ──────────────────────────────────────────────────────────

def test_list_dissents_excludes_enforced_gates():
    """Enforced gates med YELLOW/RED skal IKKE tælles som dissents."""
    fake_rows = [
        {"nerve": "memory_promotion", "decision": "yellow", "count": 800,
         "cluster": "privacy", "last_reason": "ikke auto-safe", "last_ts": "2026-07-06T20:00:00Z"},
        {"nerve": "cross_user_share", "decision": "yellow", "count": 7,
         "cluster": "privacy", "last_reason": "cross-user", "last_ts": "2026-07-06T19:00:00Z"},
    ]
    with patch.object(dissent, "_rows", return_value=fake_rows):
        result = dissent.list_dissents()
    assert result == []  # begge er enforced → ingen dissents


def test_list_dissents_includes_non_enforced_yellow():
    """Non-enforced gates med YELLOW skal tælles som dissents."""
    fake_rows = [
        {"nerve": "truth", "decision": "yellow", "count": 12,
         "cluster": "quality", "last_reason": "uverificeret påstand", "last_ts": "2026-07-06T18:00:00Z"},
        {"nerve": "loop_control", "decision": "yellow", "count": 5,
         "cluster": "runtime", "last_reason": "blød brems", "last_ts": "2026-07-06T17:00:00Z"},
    ]
    with patch.object(dissent, "_rows", return_value=fake_rows):
        result = dissent.list_dissents()
    assert len(result) == 2
    assert result[0]["nerve"] == "truth"  # højeste count først
    assert result[0]["objections"] == 12
    assert result[1]["nerve"] == "loop_control"
    assert result[1]["objections"] == 5


def test_list_dissents_excludes_green():
    """GREEN verdicts skal aldrig tælles som dissents."""
    fake_rows = [
        {"nerve": "truth", "decision": "green", "count": 100,
         "cluster": "quality", "last_reason": "ok", "last_ts": "2026-07-06T18:00:00Z"},
    ]
    with patch.object(dissent, "_rows", return_value=fake_rows):
        result = dissent.list_dissents()
    assert result == []


def test_list_dissents_aggregates_by_nerve():
    """Flere rækker for samme nerve skal aggregeres."""
    fake_rows = [
        {"nerve": "truth", "decision": "yellow", "count": 5,
         "cluster": "quality", "last_reason": "første", "last_ts": "2026-07-06T10:00:00Z"},
        {"nerve": "truth", "decision": "red", "count": 7,
         "cluster": "quality", "last_reason": "anden", "last_ts": "2026-07-06T12:00:00Z"},
    ]
    with patch.object(dissent, "_rows", return_value=fake_rows):
        result = dissent.list_dissents()
    assert len(result) == 1
    assert result[0]["objections"] == 12  # 5 + 7
    assert result[0]["last_reason"] == "anden"  # nyeste ts vinder


def test_list_dissents_respects_limit():
    """limit skal respekteres."""
    fake_rows = [
        {"nerve": f"n{i}", "decision": "yellow", "count": 10 - i,
         "cluster": "x", "last_reason": "r", "last_ts": f"2026-07-06T{i:02d}:00:00Z"}
        for i in range(10)
    ]
    with patch.object(dissent, "_rows", return_value=fake_rows):
        result = dissent.list_dissents(limit=3)
    assert len(result) == 3


# ─── build_dissent_surface ──────────────────────────────────────────────────

def test_build_surface_with_dissents():
    """Surface skal indeholde total + felt-tekst når der er dissents."""
    fake_rows = [
        {"nerve": "truth", "decision": "yellow", "count": 12,
         "cluster": "quality", "last_reason": "uverificeret", "last_ts": "2026-07-06T18:00:00Z"},
    ]
    with patch.object(dissent, "_rows", return_value=fake_rows):
        with patch.object(dissent, "_observe"):
            s = dissent.build_dissent_surface()
    assert s["total_objections"] == 12
    assert s["count"] == 1
    assert "truth" in s["felt"]
    assert "uverificeret" in s["felt"]


def test_build_surface_without_dissents():
    """Surface skal sige 'ingen tavse indsigelser' når der ikke er nogen."""
    with patch.object(dissent, "_rows", return_value=[]):
        with patch.object(dissent, "_observe"):
            s = dissent.build_dissent_surface()
    assert s["total_objections"] == 0
    assert "ingen tavse indsigelser" in s["felt"].lower()


# ─── record_dissent ──────────────────────────────────────────────────────────

def test_record_dissent_returns_ok():
    """record_dissent skal returnere status=ok."""
    with patch.object(dissent, "_rows", return_value=[]):
        with patch.object(dissent, "_observe"):
            r = dissent.record_dissent()
    assert r["status"] == "ok"
    assert r["total_objections"] == 0