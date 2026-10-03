import time

from apps.api.jarvis_api.routes import chat


def test_active_runs_adds_research_snapshot(monkeypatch):
    class Settings:
        server_authoritative_runs = True

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: Settings())
    monkeypatch.setattr("core.services.run_event_log.aabne_run_ids", lambda **kw: ["visible-1"])
    monkeypatch.setattr("core.services.run_event_log.session_for_run", lambda rid: "session-1")
    monkeypatch.setattr(
        "core.services.research_store.active_for_session",
        lambda sid: {"id": "research-1", "status": "researching", "tier": "orchestrated"},
    )
    result = chat.chat_active_runs()
    assert result["sessions"][0] == {
        "session_id": "session-1", "run_id": "visible-1", "status": "working",
        "research_run_id": "research-1", "research_status": "researching",
        "research_tier": "orchestrated",
    }


# ── Blinket (3/10-2026) ─────────────────────────────────────────────────────
# Bjørn: «ofte efter du har sendt en besked, så stopper liveness indikator og så
# starter den op igen og køre x sekunder og så stopper igen?»
#
# Roden: endpointet læste `live_run_ids()`, der er FRISKHEDS-baseret — et run
# falder ud når der ikke er kommet en frame i 45 s. Under et langt blokerende
# værktøjskald kommer der ingen frames, så runnet forsvandt og kom tilbage.
# `aabne_run_ids` er TILSTANDS-baseret: et run er i gang til det er FÆRDIGT.


def test_stille_men_aabent_run_holder_indikatoren_taendt(monkeypatch):
    """Et run midt i en lang tool-runde (ingen frames i 5 min) skal BLIVE i
    /active-runs — ellers slukker klienten indikatoren og tænder den igen."""
    import core.services.run_event_log as rel

    class Settings:
        server_authoritative_runs = True

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: Settings())
    monkeypatch.setattr("core.services.run_event_log.session_for_run", lambda rid: "session-1")
    monkeypatch.setattr("core.services.research_store.active_for_session", lambda sid: None)

    rel.create("visible-stille", "session-1")
    nu = time.monotonic()
    # Kørt længere end create-grace (60 s) OG ping-loopet sultet (ingen frame i
    # 300 s) — præcis den tilstand der gav blinket.
    rel._RUNS["visible-stille"]["created_at"] = nu - 400.0
    rel._RUNS["visible-stille"]["last_append_at"] = nu - 300.0
    try:
        # Den gamle regel tabte den — det ER defekten.
        assert "visible-stille" not in rel.live_run_ids()
        # Den nye holder fast, og endpointet rapporterer sessionen.
        assert "visible-stille" in rel.aabne_run_ids()
        assert "session-1" in chat.chat_active_runs()["session_ids"]
    finally:
        rel._RUNS.pop("visible-stille", None)


def test_gammelt_aabent_run_droppes_af_alders_loftet(monkeypatch):
    """Zombie-værnet: et run der ALDRIG blev markeret færdigt må ikke holde
    indikatoren tændt i det uendelige. Loftet er endpointets eget (10 min)."""
    import core.services.run_event_log as rel

    class Settings:
        server_authoritative_runs = True

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: Settings())
    monkeypatch.setattr("core.services.run_event_log.session_for_run", lambda rid: "session-zombie")
    monkeypatch.setattr("core.services.research_store.active_for_session", lambda sid: None)

    rel.create("visible-zombie", "session-zombie")
    rel._RUNS["visible-zombie"]["created_at"] = time.monotonic() - (
        chat._AKTIVE_RUNS_ALDER_LOFT_S + 60.0
    )
    try:
        assert "session-zombie" not in chat.chat_active_runs()["session_ids"]
    finally:
        rel._RUNS.pop("visible-zombie", None)
