from __future__ import annotations

from datetime import UTC, datetime


def test_recent_invocations_reads_every_page_in_window(monkeypatch):
    import core.runtime.db_cheap_lane_control as db
    from core.services.cheap_lane_diagnostics import recent_invocations

    pages = {
        "": {"items": [{"invocation_id": "new"}], "next_cursor": "older"},
        "older": {"items": [{"invocation_id": "old"}], "next_cursor": None},
    }
    monkeypatch.setattr(db, "list_cheap_lane_invocations", lambda **kw: pages[kw.get("cursor", "")])

    rows = recent_invocations(since=datetime(2026, 9, 26, tzinfo=UTC))
    assert [row["invocation_id"] for row in rows] == ["new", "old"]


def test_invocation_health_is_split_by_account_and_provider():
    from core.services.cheap_lane_diagnostics import invocation_health

    rows = [
        {"provider": "groq", "auth_profile": "default", "status": "completed", "latency_ms": 100},
        {"provider": "groq", "auth_profile": "account2", "status": "failed", "latency_ms": 900},
        {"provider": "groq", "auth_profile": "account2", "status": "completed", "latency_ms": 300},
    ]
    health = invocation_health(rows)

    assert health["requests"] == 3
    assert health["failures"] == 1
    assert health["p95_latency_ms"] == 900
    assert health["by_profile"]["account2"]["failures"] == 1
    assert health["by_provider_profile"]["groq::default"]["p95_latency_ms"] == 100


def test_route_integrity_waits_for_inflight_invocation(isolated_runtime):
    from datetime import timedelta
    from core.runtime.db_core import connect
    from core.runtime.db_cheap_lane_control import _ensure_control_schema
    from core.services.cheap_lane_diagnostics import route_integrity

    now = datetime.now(UTC)
    old = (now - timedelta(minutes=10)).isoformat()
    fresh = now.isoformat()
    with connect() as conn:
        _ensure_control_schema(conn)
        for route_id, created_at in (("old", old), ("fresh", fresh)):
            conn.execute(
                "INSERT INTO cheap_lane_route_decisions "
                "(route_decision_id,correlation_id,created_at) VALUES (?,?,?)",
                (route_id, route_id, created_at),
            )

    mismatches = route_integrity(since=now - timedelta(hours=1))
    assert [row["route_decision_id"] for row in mismatches] == ["old"]


def test_route_interrupted_near_runtime_restart_is_classified_separately(isolated_runtime):
    from datetime import timedelta
    from core.runtime.db_core import connect
    from core.runtime.db_cheap_lane_control import _ensure_control_schema
    from core.services.cheap_lane_diagnostics import route_integrity

    now = datetime.now(UTC)
    routed_at = (now - timedelta(minutes=10)).isoformat()
    started_at = (now - timedelta(minutes=9, seconds=50)).isoformat()
    with connect() as conn:
        _ensure_control_schema(conn)
        conn.execute(
            "INSERT INTO cheap_lane_route_decisions "
            "(route_decision_id,correlation_id,created_at) VALUES (?,?,?)",
            ("interrupted", "corr", routed_at),
        )
        conn.execute(
            "INSERT INTO events(kind,payload_json,created_at) VALUES (?,?,?)",
            ("runtime.started", '{"component":"api"}', started_at),
        )

    rows = route_integrity(since=now - timedelta(hours=1))
    assert [(row["route_decision_id"], row["kind"]) for row in rows] == [
        ("interrupted", "route-interrupted-by-restart"),
    ]


def test_restart_interruption_does_not_raise_route_mismatch_high(monkeypatch):
    import core.services.cheap_lane_diagnostics as diagnostics

    monkeypatch.setattr(diagnostics, "balancer_snapshot", lambda: {
        "eligible_now": 1, "slots": [],
    })
    monkeypatch.setattr(diagnostics, "capacity_snapshot", lambda **_kw: {"windows": []})
    monkeypatch.setattr(diagnostics, "fuld_registrering", lambda: {"udbydere": []})
    monkeypatch.setattr(diagnostics, "recent_invocations", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "central_evidence", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "route_integrity", lambda **_kw: [
        {"kind": "route-interrupted-by-restart", "route_decision_id": "restart"},
        {"kind": "route-without-invocation", "route_decision_id": "real"},
    ])

    findings = diagnostics.diagnose_cheap_lane(
        now=datetime(2026, 9, 27, 12, tzinfo=UTC)
    )["findings"]
    routes = {item["code"]: item for item in findings if item["code"].startswith("route-")}
    assert routes["route-trace-mismatch"]["evidence"]["count"] == 1
    assert routes["route-interrupted"]["severity"] == "medium"
    assert routes["route-interrupted"]["evidence"]["count"] == 1


def test_local_ollama_fallback_is_not_a_pool_route_bypass():
    from core.services.cheap_lane_diagnostics import unrouted_pool_invocations

    rows = [
        {"provider": "ollama", "status": "failed", "route_decision_id": ""},
        {"provider": "groq", "status": "failed", "route_decision_id": ""},
        {"provider": "groq", "status": "completed", "route_decision_id": "route-1"},
    ]
    assert unrouted_pool_invocations(rows) == [rows[1]]


def test_diagnostics_detects_starvation_and_stale_quota(monkeypatch):
    import core.services.cheap_lane_diagnostics as diagnostics

    monkeypatch.setattr(diagnostics, "balancer_snapshot", lambda: {
        "eligible_now": 0,
        "saved_at": "2026-09-18T11:59:00+00:00",
        "slots": [{
            "slot_id": "groq::llama::default", "provider": "groq",
            "auth_profile": "default", "egress": "home", "weight": 0,
            "status": "cooldown", "breaker_level": 0,
            "consecutive_failures": 1,
        }],
    })
    monkeypatch.setattr(diagnostics, "capacity_snapshot", lambda **_kw: {
        "windows": [{
            "provider": "groq", "auth_profile": "default", "period": "month",
            "unit": "tokens", "limit": 1000, "remaining": 500, "used": 500,
            "observed_usage": 500, "freshness": "stale", "source": "configured",
        }],
    })
    monkeypatch.setattr(diagnostics, "fuld_registrering", lambda: {
        "udbydere": [{"provider": "groq", "credentials_ready": True}],
    })
    monkeypatch.setattr(diagnostics, "recent_invocations", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "route_integrity", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "central_evidence", lambda **_kw: [])

    findings = diagnostics.diagnose_cheap_lane(
        now=datetime(2026, 9, 18, 12, tzinfo=UTC)
    )["findings"]
    codes = {finding["code"] for finding in findings}

    assert {"no-eligible-slot", "provider-starvation", "quota-stale"} <= codes
    assert all("severity" in finding and "evidence" in finding for finding in findings)


def test_diagnostics_detects_concentration_credentials_and_exhaustion(monkeypatch):
    import core.services.cheap_lane_diagnostics as diagnostics

    monkeypatch.setattr(diagnostics, "balancer_snapshot", lambda: {
        "eligible_now": 2,
        "saved_at": "2026-09-18T12:00:00+00:00",
        "slots": [
            {"slot_id": "a", "provider": "groq", "auth_profile": "default",
             "egress": "home", "weight": 1, "status": "healthy",
             "breaker_level": 0, "consecutive_failures": 0},
            {"slot_id": "b", "provider": "groq", "auth_profile": "default",
             "egress": "home", "weight": 1, "status": "healthy",
             "breaker_level": 0, "consecutive_failures": 0},
        ],
    })
    monkeypatch.setattr(diagnostics, "capacity_snapshot", lambda **_kw: {
        "windows": [{
            "provider": "groq", "auth_profile": "default", "period": "day",
            "unit": "requests", "limit": 100, "remaining": 4, "used": 96,
            "observed_usage": 96, "freshness": "fresh", "source": "provider",
        }],
    })
    monkeypatch.setattr(diagnostics, "fuld_registrering", lambda: {
        "udbydere": [{"provider": "mistral", "credentials_ready": False}],
    })
    monkeypatch.setattr(diagnostics, "recent_invocations", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "route_integrity", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "central_evidence", lambda **_kw: [])

    codes = {
        item["code"] for item in diagnostics.diagnose_cheap_lane(
            now=datetime(2026, 9, 18, 12, tzinfo=UTC)
        )["findings"]
    }
    assert {"capacity-concentrated", "quota-near-exhaustion", "credentials-missing"} <= codes


def test_account_cooldown_is_one_parked_finding_not_four_breakers(monkeypatch):
    import core.services.cheap_lane_diagnostics as diagnostics

    slots = [
        {"slot_id": f"chatanywhere::m{i}::default", "provider": "chatanywhere",
         "auth_profile": "default", "egress": "home", "weight": 0,
         "status": "cooldown", "breaker_level": 3,
         "consecutive_failures": 10, "cooldown_reason": "provider-blocked",
         "account_block_reason": "provider-blocked",
         "account_block_until": "2026-09-18T18:00:00+00:00"}
        for i in range(4)
    ]
    slots.append({
        "slot_id": "groq::bad-model::default", "provider": "groq",
        "auth_profile": "default", "egress": "home", "weight": 0.1,
        "status": "recovering", "breaker_level": 3,
        "consecutive_failures": 10, "cooldown_reason": "model-not-found",
        "account_block_reason": None,
    })
    slots.append({
        "slot_id": "ovhcloud::bad-model::default", "provider": "ovhcloud",
        "auth_profile": "default", "egress": "home", "weight": 0,
        "status": "cooldown", "breaker_level": 3,
        "consecutive_failures": 10, "cooldown_reason": "model-not-found",
        "account_block_reason": None,
    })
    monkeypatch.setattr(diagnostics, "balancer_snapshot", lambda: {
        "eligible_now": 1, "saved_at": "2026-09-18T12:00:00+00:00", "slots": slots,
    })
    monkeypatch.setattr(diagnostics, "capacity_snapshot", lambda **_kw: {"windows": []})
    monkeypatch.setattr(diagnostics, "fuld_registrering", lambda: {"udbydere": []})
    monkeypatch.setattr(diagnostics, "recent_invocations", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "route_integrity", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "central_evidence", lambda **_kw: [])

    findings = diagnostics.diagnose_cheap_lane(
        now=datetime(2026, 9, 18, 12, tzinfo=UTC)
    )["findings"]
    parked = [item for item in findings if item["code"] == "account-parked"]
    breakers = [item for item in findings if item["code"] == "breaker-repeated"]
    starvation = [item for item in findings if item["code"] == "provider-starvation"]
    assert len(parked) == 1
    assert parked[0]["severity"] == "medium"
    assert parked[0]["evidence"]["affected_slots"] == 4
    assert parked[0]["evidence"]["reason"] == "provider-blocked"
    assert {item["slot_id"]: item["severity"] for item in breakers} == {
        "groq::bad-model::default": "medium",
        "ovhcloud::bad-model::default": "high",
    }
    assert {item["provider"]: item["severity"] for item in starvation} == {
        "chatanywhere": "medium", "ovhcloud": "high",
    }


# ── To bøger over samme udbyders sundhed (codex' fund, 27/9-2026) ───────


def _base_med_invocation(monkeypatch, *, provider, profil, tidspunkt,
                         model="x", status="completed"):
    """En rigtig SQLite med én invocation. Hele pointen er SQL'en."""
    import sqlite3
    from contextlib import contextmanager

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE cheap_provider_invocations "
                 "(provider TEXT, model TEXT, auth_profile TEXT, status TEXT, created_at TEXT)")
    if tidspunkt:
        conn.execute("INSERT INTO cheap_provider_invocations VALUES (?,?,?,?,?)",
                     (provider, model, profil, status, tidspunkt))
    conn.commit()

    @contextmanager
    def _c():
        yield conn

    monkeypatch.setattr("core.runtime.db_core.connect", _c)
    return conn


def _slot(**kw):
    s = {"provider": "ovhcloud", "model": "x", "auth_profile": "default",
         "slot_id": "ovhcloud::x::default", "status": "cooldown",
         "last_success_at": "2026-09-27T06:40:00+00:00",
         "last_failure_at": "2026-09-27T06:40:00+00:00"}
    s.update(kw)
    return s


def test_lanens_succes_EFTER_balancerens_er_en_uenighed(monkeypatch):
    """Codex' konkrete fund: OVHcloud gennemførte et kald 06:58, mens
    balancerens registrerede seneste succes stod på 06:40 og slottet lå i
    cooldown.

    Årsagen er mekanisk: `_register_success` rydder cooldown, men kaldes kun
    når kaldet gik GENNEM balanceren. En selection-succes når aldrig frem, og
    slottet bliver liggende i en cooldown virkeligheden har modbevist.
    """
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", profil="default",
                         tidspunkt="2026-09-27T06:58:00+00:00")
    ud = health_divergence([_slot()], since=datetime(2026, 9, 27, tzinfo=UTC))
    assert len(ud) == 1
    assert ud[0]["balancer_last_success"] == "2026-09-27T06:40:00+00:00"
    assert ud[0]["lane_last_success"] == "2026-09-27T06:58:00+00:00"
    assert ud[0]["bagud_s"] == 1080.0


def test_en_succes_FOER_balancerens_beviser_ingenting(monkeypatch):
    """Den nuance codex selv fangede: OVHclouds succes kl. 06:38 lå FØR
    balancerens fejl kl. 06:40 og beviste derfor ikke stale state. Kun en
    nyere succes er en uenighed."""
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", profil="default",
                         tidspunkt="2026-09-27T06:38:00+00:00")
    assert health_divergence([_slot()], since=datetime(2026, 9, 27, tzinfo=UTC)) == []


def test_cooldown_UDEN_nyere_succes_er_balanceren_der_goer_sit_arbejde(monkeypatch):
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", profil="default",
                         tidspunkt=None)
    assert health_divergence([_slot()], since=datetime(2026, 9, 27, tzinfo=UTC)) == []


def test_et_slot_der_IKKE_er_i_cooldown_maales_ikke(monkeypatch):
    """Uenigheden betyder kun noget når balanceren holder slottet tilbage."""
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", profil="default",
                         tidspunkt="2026-09-27T06:58:00+00:00")
    assert health_divergence([_slot(status="healthy")],
                             since=datetime(2026, 9, 27, tzinfo=UTC)) == []


def test_en_FEJLET_invocation_er_ikke_en_succes(monkeypatch):
    """Kun `status='ok'` tæller. Ellers ville en fejl bagefter se ud som et
    bevis på at cooldown'en var forkert — stik modsat."""
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", profil="default",
                         tidspunkt="2026-09-27T06:58:00+00:00", status="failed")
    assert health_divergence([_slot()], since=datetime(2026, 9, 27, tzinfo=UTC)) == []


def test_profilen_skal_passe_saa_en_anden_konto_ikke_frikender(monkeypatch):
    """`account2`s succes siger intet om `default`s cooldown — det er to
    konti hos samme udbyder."""
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", profil="account2",
                         tidspunkt="2026-09-27T06:58:00+00:00")
    assert health_divergence([_slot()], since=datetime(2026, 9, 27, tzinfo=UTC)) == []


def test_modellen_skal_passe_saa_en_anden_model_ikke_frikender(monkeypatch):
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", model="other-model",
                         profil="default", tidspunkt="2026-09-27T06:58:00+00:00")
    assert health_divergence([_slot()], since=datetime(2026, 9, 27, tzinfo=UTC)) == []


def test_succes_foer_sidste_balancerfejl_frikender_ikke(monkeypatch):
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", profil="default",
                         tidspunkt="2026-09-27T06:58:00+00:00")
    assert health_divergence(
        [_slot(last_failure_at="2026-09-27T07:00:00+00:00")],
        since=datetime(2026, 9, 27, tzinfo=UTC),
    ) == []


def test_status_vaerdien_er_maalt_og_ikke_opfundet():
    """Første udgave filtrerede på `status = 'ok'` — en værdi JEG fandt på.
    Vagten kunne aldrig have fyret.

    Målt i produktionen 27/9-2026, sidste døgn: `completed` 5082, `failed`
    434. Der findes ingen `ok`. Samme fejlklasse som dengang klienten læste
    `old_string` mens værktøjet sendte `old_text`: testen pinnede sit eget
    opdigtede navn og bestod, mens produktionen aldrig ramte koden.
    """
    from core.services.cheap_lane_diagnostics import _STATUS_SUCCES

    assert _STATUS_SUCCES == "completed"


def test_en_FEJLET_invocation_taeller_ikke_med_den_aegte_vaerdi(monkeypatch):
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", profil="default",
                         tidspunkt="2026-09-27T06:58:00+00:00", status="failed")
    assert health_divergence([_slot()], since=datetime(2026, 9, 27, tzinfo=UTC)) == []


def test_tidsstempel_med_Z_suffiks_laeses(monkeypatch):
    """Produktionen skriver `2026-09-27T06:58:48.786792Z`; balanceren skriver
    uden suffiks. Begge skal kunne sammenlignes."""
    from core.services.cheap_lane_diagnostics import health_divergence

    _base_med_invocation(monkeypatch, provider="ovhcloud", profil="default",
                         tidspunkt="2026-09-27T06:58:48.786792Z")
    ud = health_divergence([_slot()], since=datetime(2026, 9, 27, tzinfo=UTC))
    assert len(ud) == 1
