"""Autonome sessioner — rotér pr. oprindelse+dag + historik-projektion.

Invarianter: en autonom run funneler ikke længere ind i én udødelig silo; hver
(oprindelse, dag) får sin egen deterministiske session; historik-surfacen grupperer
pr. oprindelse med tællere (egress-sikkert).
"""
from __future__ import annotations

from unittest import mock

import core.services.autonomous_sessions as autos


def test_normalize_origin_falls_back_to_autonomous():
    assert autos.normalize_origin("dream") == "dream"
    assert autos.normalize_origin("DREAM") == "dream"
    assert autos.normalize_origin("ukendt-ting") == "autonomous"
    assert autos.normalize_origin(None) == "autonomous"


def test_resolve_session_deterministic_per_origin_and_day():
    """Samme oprindelse+dag → samme deterministiske id; forskellig oprindelse → forskelligt."""
    captured = []
    with mock.patch("core.services.chat_sessions.get_or_create_named_session",
                    side_effect=lambda sid, title: captured.append((sid, title)) or sid):
        with mock.patch.object(autos, "_today", return_value="20260706"):
            a = autos.resolve_autonomous_session("dream")
            b = autos.resolve_autonomous_session("dream")
            c = autos.resolve_autonomous_session("work")
    assert a == "auto-dream-20260706"
    assert a == b                      # idempotent — samme dag+oprindelse
    assert c == "auto-work-20260706"   # anden oprindelse → anden session
    assert a != c
    # titel er menneskelæsbar + dansk label
    assert captured[0][1] == "Autonom · Drømme · 2026-07-06"


def test_origin_extraction_from_session_id():
    assert autos._origin_of_session("auto-dream-20260706") == "dream"
    assert autos._origin_of_session("auto-work-20260706") == "work"
    assert autos._origin_of_session("chat-abc123") == "autonomous"  # ikke-auto → fallback


def test_unknown_origin_routes_to_autonomous_bucket():
    with mock.patch("core.services.chat_sessions.get_or_create_named_session",
                    side_effect=lambda sid, title: sid):
        with mock.patch.object(autos, "_today", return_value="20260706"):
            sid = autos.resolve_autonomous_session("vrøvl")
    assert sid == "auto-autonomous-20260706"


def test_history_surface_groups_by_origin(monkeypatch):
    """build_autonomous_history_surface grupperer roterende sessioner pr. oprindelse
    med besked- og fejl-tællere; intet råt beskedindhold."""
    class _Row(dict):
        def __getitem__(self, k):
            return super().__getitem__(k)

    fake_rows = [
        _Row(session_id="auto-dream-20260706", title="Autonom · Drømme · 2026-07-06",
             updated_at="2026-07-06T10:00:00+00:00", msgs=12, ctx_err=2),
        _Row(session_id="auto-dream-20260705", title="Autonom · Drømme · 2026-07-05",
             updated_at="2026-07-05T10:00:00+00:00", msgs=8, ctx_err=0),
        _Row(session_id="auto-work-20260706", title="Autonom · Arbejde · 2026-07-06",
             updated_at="2026-07-06T09:00:00+00:00", msgs=30, ctx_err=1),
    ]

    class _Conn:
        def execute(self, *a, **k):
            class _Cur:
                def fetchall(_self):
                    return fake_rows
            return _Cur()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr("core.runtime.db_core.connect", lambda: _Conn())
    surf = autos.build_autonomous_history_surface(days=3650)  # vidt vindue → ingen dato-filtrering
    assert surf["total_sessions"] == 3
    assert surf["total_messages"] == 50
    assert surf["total_context_errors"] == 3
    assert surf["origins"]["dream"]["sessions"] == 2
    assert surf["origins"]["dream"]["messages"] == 20
    assert surf["origins"]["dream"]["context_errors"] == 2
    assert surf["origins"]["work"]["messages"] == 30
    assert surf["origins"]["dream"]["label"] == "Drømme"
