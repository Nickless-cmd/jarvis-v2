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


def test_central_notices_keeps_one_per_nerve_max_three_and_skips_security_and_severe(monkeypatch):
    from core.services.prompt_sections import tail_section_builders as T
    rows = [{"severity": "error", "kind": "x", "cluster": f"c{i // 2}", "nerve": f"n{i // 2}", "message": f"m{i}"}
            for i in range(8)]
    rows += [{"severity": "severe", "kind": "x", "cluster": "s", "nerve": "s", "message": "severe"},
             {"severity": "error", "kind": "fail_open", "cluster": "f", "nerve": "f", "message": "sikkerhed"}]
    monkeypatch.setattr("core.runtime.db_central_incidents.list_central_incidents", lambda **kw: rows)
    out = T._central_notices_section()
    assert out.count("•") == 3 and out.count("c0/n0") == 1 and "c2/n2" in out     # én pr. nerve
    assert "severe" not in out and "sikkerhed" not in out
    monkeypatch.setattr("core.runtime.db_central_incidents.list_central_incidents", lambda **kw: [])
    assert T._central_notices_section() is None


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
