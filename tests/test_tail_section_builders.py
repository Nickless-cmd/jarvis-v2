"""Boy Scout: hale-sektionsbyggerne er udskilt fra prompt_contract - re-eksporten og adfaerden bevares."""
from __future__ import annotations

import pytest

NAMES = ("_central_notices_section", "_pending_promises_section", "_connected_connectors_section",
         "_open_questions_section", "_time_pin_section")


@pytest.mark.parametrize("name", NAMES)
def test_prompt_contract_re_exports_the_very_same_function(name):
    from core.services import prompt_contract as pc
    from core.services.prompt_sections import tail_section_builders as new
    assert getattr(pc, name) is getattr(new, name)


def test_pending_promises_needs_a_session_and_shows_at_most_the_last_three(monkeypatch):
    from core.services.prompt_sections import tail_section_builders as T
    assert T._pending_promises_section(None) is None and T._pending_promises_section("  ") is None
    monkeypatch.setattr("core.services.promise_ledger.pending_promises",
                        lambda sid: [{"text": f"loefte {i}"} for i in range(5)])
    out = T._pending_promises_section("s1")
    assert out.startswith("⚠️ ÅBNE LØFTER") and "loefte 4" in out and "loefte 2" in out and "loefte 1" not in out
    monkeypatch.setattr("core.services.promise_ledger.pending_promises", lambda sid: [])
    assert T._pending_promises_section("s1") is None


def test_open_questions_compacts_and_is_silent_when_empty(monkeypatch):
    from core.services import curiosity_daemon
    from core.services.prompt_sections import tail_section_builders as T
    monkeypatch.setattr(curiosity_daemon, "_open_questions", [])
    assert T._open_questions_section() is None
    monkeypatch.setattr(curiosity_daemon, "_open_questions", ["a?", "b?"])
    assert T._open_questions_section() == "Open questions you're carrying (use search_memory for more):\n- a?\n- b?"
    monkeypatch.setattr(curiosity_daemon, "_open_questions", ["a?", "b?", "c?"])
    assert T._open_questions_section().startswith("Open questions: 3 unresolved (first: \"a?\")")


def _eier(monkeypatch, svar: bool = True):
    """Gaten er fail-CLOSED: testene skal bevise ejerskab eksplicit, ligesom prod gør."""
    monkeypatch.setattr("core.identity.owner_resolver.is_owner_app_session", lambda sid: svar)


def test_central_notices_viser_roed_foerst_med_alder_og_severity(monkeypatch):
    """Accept-test (krav 5): en uløst severity=error SKAL give en ikke-tom sektion med
    rød markering. Fejlede på koden før 11/11-2026, hvor sektionen hed «medium» og
    hverken bar alder eller grad."""
    from core.services.prompt_sections import tail_section_builders as T
    _eier(monkeypatch)
    T._clear_central_notices_cache()
    rows = [{"id": 2, "ts": "2026-11-11T19:08:49+00:00", "severity": "error", "kind": "network_degraded",
             "cluster": "network", "nerve": "health", "message": "API-latens 1790.4ms >= 800ms"},
            {"id": 1, "ts": "2026-11-09T13:52:18+00:00", "severity": "severe", "kind": "undefined_error",
             "cluster": "anomaly", "nerve": "log:Error", "message": "Too many open files"}]
    monkeypatch.setattr("core.runtime.db_central_incidents.list_central_incidents", lambda **kw: rows)
    out = T._central_notices_section("s1")
    assert out is not None and "🔴" in out                       # rød markering
    assert "RØD" in out and "1 severe" in out and "1 error" in out  # antal pr. grad
    assert out.index("log:Error") < out.index("network/health")    # højeste grad først
    assert "gammel" in out                                          # alder er med
    assert "severe" in out                                          # severe er IKKE længere skjult


def test_central_notices_er_tom_naar_intet_roedt_eller_gult_findes(monkeypatch):
    """Krav 2: tom sektion når der intet er → 0 tokens, ingen «alt ok»-støj."""
    from core.services.prompt_sections import tail_section_builders as T
    _eier(monkeypatch)
    T._clear_central_notices_cache()
    monkeypatch.setattr("core.runtime.db_central_incidents.list_central_incidents", lambda **kw: [])
    assert T._central_notices_section("s1") is None


def test_central_notices_info_taelles_men_listes_ikke_naar_der_er_roedt(monkeypatch):
    """FÆLDE (målt): 27 af 29 uløste rækker er info-støj. Listes de, drukner det røde."""
    from core.services.prompt_sections import tail_section_builders as T
    _eier(monkeypatch)
    T._clear_central_notices_cache()
    rows = [{"id": 99, "ts": "2026-11-11T19:08:49+00:00", "severity": "error", "kind": "x",
             "cluster": "network", "nerve": "health", "message": "rød"}]
    rows += [{"id": i, "ts": "2026-11-11T19:00:00+00:00", "severity": "info", "kind": "gate_enforce",
              "cluster": "proactivity", "nerve": "verification", "message": f"stoej {i}"} for i in range(27)]
    monkeypatch.setattr("core.runtime.db_central_incidents.list_central_incidents", lambda **kw: rows)
    out = T._central_notices_section("s1")
    assert "network/health" in out
    assert "+27 gule" in out and "stoej" not in out      # talt, ikke listet


def test_central_notices_er_ejer_only(monkeypatch):
    """Krav 4: en medlems-session må IKKE se Centralens interne tilstand."""
    from core.services.prompt_sections import tail_section_builders as T
    _eier(monkeypatch, False)
    T._clear_central_notices_cache()
    rows = [{"id": 1, "ts": "2026-11-11T19:08:49+00:00", "severity": "severe", "kind": "x",
             "cluster": "anomaly", "nerve": "log:Error", "message": "hemmelig"}]
    monkeypatch.setattr("core.runtime.db_central_incidents.list_central_incidents", lambda **kw: rows)
    assert T._central_notices_section("medlem-session") is None
    assert T._central_notices_section(None) is None


def test_central_notices_snapshot_stops_within_turn_prompt_flapping(monkeypatch):
    from core.services.prompt_sections import tail_section_builders as T
    _eier(monkeypatch)
    now = [100.0]
    rows = [{"id": 1, "ts": "2026-11-11T19:08:49+00:00", "severity": "error", "kind": "x",
             "cluster": "system", "nerve": "provider", "message": "nede"}]
    monkeypatch.setattr(T.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.list_central_incidents",
        lambda **kw: list(rows),
    )
    T._clear_central_notices_cache()
    first = T._central_notices_section("s1")
    rows.clear()
    assert T._central_notices_section("s1") == first
    now[0] += T._CENTRAL_NOTICES_CACHE_TTL_S + 0.1
    assert T._central_notices_section("s1") is None


def test_connected_connectors_lists_only_connected_and_enabled_oauth_apps(monkeypatch):
    from core.services.prompt_sections import tail_section_builders as T
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "u1")
    monkeypatch.setattr("core.services.connectors.list_for_user", lambda uid: [
        {"id": "github", "name": "GitHub", "kind": "oauth", "connected": True, "enabled": True},
        {"id": "gmail", "name": "Gmail", "kind": "oauth", "connected": True, "enabled": False},
        {"id": "local", "name": "Lokal", "kind": "local", "connected": True, "enabled": True}])
    out = T._connected_connectors_section()
    assert "GitHub: forbundet" in out and "github_list_issues" in out and "Gmail" not in out and "Lokal" not in out
    monkeypatch.setattr("core.services.connectors.list_for_user", lambda uid: [])
    assert T._connected_connectors_section() is None


def test_tavse_fald_logger_og_udelader_sektionen(monkeypatch, caplog):
    """De tre sektioner må ikke forsvinde TAVST (målt 9/10-2026).

    Kaster promise_ledger, connectors eller curiosity_daemon, udelades sektionen —
    prompten skal kunne bygges. Men fejlen skal stå i loggen: uden den mister
    Jarvis et værn (sine løfter, sine apps, sine spørgsmål) uden at nogen kan se
    at det skete. Det var præcis hvad instrumentet fangede i de tre fund.
    """
    import logging

    from core.services.prompt_sections import tail_section_builders as T

    def _boom(*a, **k):
        raise RuntimeError("nede")

    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "u1")
    monkeypatch.setattr("core.services.promise_ledger.pending_promises", _boom)
    monkeypatch.setattr("core.services.connectors.list_for_user", _boom)
    monkeypatch.setattr("core.services.curiosity_daemon._open_questions", 42)  # list(42) → TypeError

    with caplog.at_level(logging.WARNING):
        assert T._pending_promises_section("s1") is None
        assert T._connected_connectors_section() is None
        assert T._open_questions_section() is None

    assert "_pending_promises_section" in caplog.text
    assert "_connected_connectors_section" in caplog.text
    assert "_open_questions_section" in caplog.text
