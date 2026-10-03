import time

from apps.api.jarvis_api.routes import chat


def setup_function():
    # 3/10-2026: filen ryddede ikke run-loggen mellem tests. `session_for_run`
    # mockkes til at svare det SAMME for ethvert run, så et run der lå tilbage
    # fra en tidligere test fik zombie-testen til at se sin session i listen.
    # Filen alene var grøn; sammen med søsterfilen fejlede den.
    import core.services.run_event_log as rel

    rel._RUNS.clear()
    rel._ALIASER.clear()
    rel._ALIASER_OMVENDT.clear()


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


# ── Alias-mismatchet (3/10-2026) ────────────────────────────────────────────
# Målt med en poller mod det kørende endpoint: vinduet efter et svar var ~1 s på
# serveren, men klientens 6 s-latch gjorde det til 5-7 s synligt — og op til 20+
# når efterbehandlingen tog længere. Kilden var ikke vinduets længde, men at
# klienten ikke KUNNE genkende sit eget run.


def test_active_runs_svarer_med_klientens_eget_run_id(monkeypatch):
    """Klientens guard er `run_id !== activeRunId`.

    `activeRunId` kommer fra system_event(kind=run) = runnets EGET id. Svarede
    endpointet med LOG-id'et, var de to aldrig ens — guarden var altid falsk, og
    indikatoren tændte på klientens egen efterbehandling efter hvert svar.
    """
    import core.services.run_event_log as rel

    class Settings:
        server_authoritative_runs = True

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: Settings())
    monkeypatch.setattr("core.services.research_store.active_for_session", lambda sid: None)

    log_id, _ = rel.claim_or_create("session-klient-id")
    rel.alias("visible-klientens-eget", log_id)
    try:
        data = chat.chat_active_runs()
        item = next(s for s in data["sessions"] if s["session_id"] == "session-klient-id")
        assert item["run_id"] == "visible-klientens-eget"
        assert item["run_id"] != log_id
    finally:
        rel._RUNS.pop(log_id, None)
        rel._ALIASER.pop("visible-klientens-eget", None)
        rel._ALIASER_OMVENDT.pop(log_id, None)
