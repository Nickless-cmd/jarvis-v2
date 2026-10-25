"""Rutinens tidsplan og værktøjsadgang — de to huller der gjorde den halv.

Målt 25/10-2026: Michelles ugentlige rutine var korrekt oprettet, synlig i
hendes app og manuelt kørbar — men (a) ``trigger_kind='schedule'`` havde ingen
eksekvering bag sig, og (b) runnet svarede «jeg har ikke adgang til et
madopskrift-værktøj» fordi hverken driver eller executor blev givet et skema.

Disse tests værner de to svar uden at kræve en levende database.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


# ── Tidsberegningen ─────────────────────────────────────────────────────────

def test_ugentlig_forekomst_ligger_paa_den_rigtige_ugedag():
    from core.services.routine_scheduler import _seneste_forekomst

    # Søndag 25/10-2026; seneste mandag kl. 07:00 er den 19/10.
    now = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
    forekomst = _seneste_forekomst(
        {"time": "07:00", "weekday": "monday"}, anchor=now, now=now,
    )
    assert forekomst == datetime(2026, 10, 19, 7, 0, tzinfo=UTC)


def test_daglig_forekomst_er_i_dag():
    from core.services.routine_scheduler import _seneste_forekomst

    now = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
    assert _seneste_forekomst(
        {"time": "07:00"}, anchor=now, now=now,
    ) == datetime(2026, 10, 25, 7, 0, tzinfo=UTC)


def test_interval_giver_ét_punkt_selv_efter_lang_nedetid():
    """En maskine der har været nede i tre dage må ikke fyre 72 gange."""
    from core.services.routine_scheduler import _seneste_forekomst

    now = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
    anchor = now - timedelta(days=3)
    forekomst = _seneste_forekomst(
        {"interval_minutes": 60}, anchor=anchor, now=now,
    )
    assert forekomst is not None
    assert forekomst == anchor + timedelta(hours=72)


def test_ukendt_format_fyrer_ikke():
    """Hellere intet run end et run på et gæt."""
    from core.services.routine_scheduler import _seneste_forekomst

    now = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
    assert _seneste_forekomst({}, anchor=now, now=now) is None
    assert _seneste_forekomst(
        {"time": "07:00", "weekday": "blursday"}, anchor=now, now=now,
    ) is None
    assert _seneste_forekomst(
        {"time": "ikke-et-tidspunkt"}, anchor=now, now=now,
    ) is None


def test_en_rutine_med_legacy_link_tidsstyres_af_sin_kilde(monkeypatch):
    """198 migrerede rutiner har en oprindelig kilde der allerede fyrer dem.

    Uden dette værn ville samme forekomst få to runs.
    """
    from core.services import routine_scheduler

    kaldt: list[str] = []
    monkeypatch.setattr(
        routine_scheduler.db_routines, "list_schedulable_routines",
        lambda: [{"routine_id": "r1", "owner_user_id": "u1",
                  "trigger_kind": "interval",
                  "created_at": "2026-10-01T00:00:00+00:00"}],
    )
    monkeypatch.setattr(
        routine_scheduler.db_routines, "routine_has_legacy_link", lambda _r: True,
    )
    monkeypatch.setattr(
        routine_scheduler.db_routines, "get_routine",
        lambda *a, **k: kaldt.append("get_routine") or {},
    )
    assert routine_scheduler.fire_due(now=datetime(2026, 10, 25, 18, 0, tzinfo=UTC)) == []
    assert kaldt == []


def test_fire_due_springer_en_forekomst_uden_for_vinduet_over(monkeypatch):
    """En ugentlig forekomst fra sidste måned skal ikke indhentes nu."""
    from core.services import routine_scheduler

    monkeypatch.setattr(
        routine_scheduler.db_routines, "list_schedulable_routines",
        lambda: [{"routine_id": "r1", "owner_user_id": "u1",
                  "trigger_kind": "schedule",
                  "created_at": "2026-09-01T00:00:00+00:00"}],
    )
    monkeypatch.setattr(
        routine_scheduler.db_routines, "routine_has_legacy_link", lambda _r: False,
    )
    monkeypatch.setattr(
        routine_scheduler.db_routines, "get_routine",
        lambda *a, **k: {"trigger_config": {"time": "07:00", "weekday": "monday"}},
    )
    # Søndag → seneste mandag er 5 dage væk, uden for 24-timers vinduet.
    assert routine_scheduler.fire_due(now=datetime(2026, 10, 25, 18, 0, tzinfo=UTC)) == []


# ── Værktøjsadgangen ────────────────────────────────────────────────────────

def test_en_rutine_har_madopskrift_i_sit_vaerktoejssaet():
    from core.tools.autonomous_tool_policy import allowed_tools_for_origin

    tilladte = allowed_tools_for_origin("routine")
    for navn in ("madopskrift", "web_search", "notify_user"):
        assert navn in tilladte, f"{navn} mangler — rutinen kan ikke udføre sin opgave"


def test_vaerktoejsskemaet_indeholder_kun_det_rutinen_maа(monkeypatch):
    from core.services import routine_runner

    payload = routine_runner._rutine_tools_payload(
        type("Ctx", (), {"capability_scope": "chat"})()
    )
    navne = {str((d.get("function") or {}).get("name") or "") for d in payload}
    assert "madopskrift" in navne
    # Et værktøj uden for rutinens sæt må ikke snige sig med.
    assert "restart_self" not in navne


def test_systemrutiner_forbliver_vaerktoejs_fri():
    from core.services import routine_runner

    assert routine_runner._rutine_tools_payload(
        type("Ctx", (), {"capability_scope": "system"})()
    ) == []


def test_driveren_sender_skemaet_videre_og_laeser_tool_calls(monkeypatch):
    """Roden til «jeg har ikke adgang»: driveren spurgte aldrig med værktøjer."""
    from core.services import agentic_execution as ae

    set_kald: dict[str, object] = {}

    def _fake(**kwargs):
        set_kald.update(kwargs)
        return {
            "output": "", "usage": {}, "provider": "p", "model": "m",
            "tool_calls": [
                {"id": "c1", "function": {"name": "madopskrift",
                                          "arguments": '{"antal": 3}'}},
            ],
        }

    monkeypatch.setattr(
        "core.services.non_visible_lane_execution.execute_with_role_or_fallback",
        _fake,
    )
    turn = ae._ProviderDriver().complete(ae.AgenticRequest(
        prompt="foreslå opskrifter", provider="p", model="m", round_number=1,
        prior_results=(), tools=({"type": "function",
                                  "function": {"name": "madopskrift"}},),
    ))
    assert set_kald["requires_tools"] is True
    assert set_kald["tools"]
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].name == "madopskrift"
    assert turn.tool_calls[0].arguments == {"antal": 3}


def test_uden_skema_er_driveren_uaendret(monkeypatch):
    from core.services import agentic_execution as ae

    set_kald: dict[str, object] = {}

    def _fake(**kwargs):
        set_kald.update(kwargs)
        return {"output": "svar", "usage": {}, "provider": "p", "model": "m"}

    monkeypatch.setattr(
        "core.services.non_visible_lane_execution.execute_with_role_or_fallback",
        _fake,
    )
    turn = ae._ProviderDriver().complete(ae.AgenticRequest(
        prompt="hej", provider="p", model="m", round_number=1, prior_results=(),
    ))
    assert set_kald["requires_tools"] is False
    assert set_kald["tools"] is None
    assert turn.tool_calls == ()
    assert turn.text == "svar"
