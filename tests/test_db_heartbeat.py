"""Persistence-laget for heartbeat-ticks — formålet skal med hele vejen.

Rod (Bjørn 17/11-2026): `heartbeat_runtime_ticks` bar kun `action_type`, så
«hvad laver heartbeat?» ikke kunne besvares ud af data. Feltet `purpose`
tilføjes nu ved skrivning, backfilles i migrationen, og læses ud igen.

Disse tests bevogter persistence-laget alene. Klassificeringen selv (hvilken
handlingstype hører til hvilket formål, og vagten mod nye grene) ligger i
`tests/test_heartbeat_purpose.py`.
"""
from __future__ import annotations

from core.services.heartbeat_purpose import INNER_LIFE, SESSION, SURVIVAL, WORK


def _skriv_tick(tick_id: str, action_type: str) -> dict:
    from core.runtime.db_heartbeat import record_heartbeat_runtime_tick

    return record_heartbeat_runtime_tick(
        tick_id=tick_id,
        trigger="scheduled",
        tick_status="completed",
        decision_type="execute",
        decision_summary="test",
        decision_reason="test",
        blocked_reason="",
        provider="test",
        model="test",
        lane="test",
        model_source="test",
        resolution_status="",
        fallback_used=False,
        execution_status="success",
        parse_status="ok",
        budget_status="bounded-internal-only",
        ping_eligible=False,
        ping_result="",
        action_status="executed",
        action_summary="test",
        action_type=action_type,
        action_artifact="{}",
        raw_response="",
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.0,
        started_at="2026-11-17T12:00:00+00:00",
        finished_at="2026-11-17T12:00:01+00:00",
    )


def test_ticks_bærer_formaalet_ved_skrivning(isolated_runtime):
    """Formålet udledes i persistence-laget, så intet kaldested kan glemme det."""
    assert _skriv_tick("tick-arbejde", "act_on_initiative")["purpose"] == WORK
    assert _skriv_tick("tick-overlevelse", "cleanup_stale_signals")["purpose"] == SURVIVAL


def test_formaalet_kommer_med_ud_igen(isolated_runtime):
    """Skrevet men usynligt er samme fejl som ikke skrevet."""
    from core.runtime.db_heartbeat import (
        get_heartbeat_runtime_tick,
        recent_heartbeat_runtime_ticks,
    )

    _skriv_tick("tick-session", "webchat-heartbeat-proposal")

    enkelt = get_heartbeat_runtime_tick("tick-session")
    assert enkelt is not None
    assert enkelt["purpose"] == SESSION

    nyeste = recent_heartbeat_runtime_ticks(limit=5)
    assert any(r["purpose"] == SESSION for r in nyeste)


def test_backfill_sætter_formaal_paa_gamle_rækker(isolated_runtime):
    """Rækker skrevet før kolonnen fandtes må ikke stå tomme."""
    from core.runtime.db_core import connect
    from core.runtime.db_heartbeat import _backfill_tick_purposes

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO heartbeat_runtime_ticks (
                tick_id, trigger, tick_status, decision_type, decision_summary,
                decision_reason, blocked_reason, provider, model, lane,
                model_source, resolution_status, fallback_used, execution_status,
                parse_status, budget_status, ping_eligible, ping_result,
                action_status, action_summary, action_type, action_artifact,
                purpose, raw_response, input_tokens, output_tokens, cost_usd,
                started_at, finished_at
            ) VALUES (
                'gammel-tick', 'scheduled', 'completed', 'execute', '',
                '', '', '', '', '', '', '', 0, '', '', '', 0, '',
                '', '', 'run_sleep_batch', '', '', '', 0, 0, 0.0, '', ''
            )
            """
        )
        conn.commit()
        ramte = _backfill_tick_purposes(conn)
        conn.commit()
        row = conn.execute(
            "SELECT purpose FROM heartbeat_runtime_ticks WHERE tick_id = 'gammel-tick'"
        ).fetchone()

    assert ramte >= 1
    assert row["purpose"] == INNER_LIFE


def test_backfill_er_idempotent(isolated_runtime):
    """Anden kørsel må ikke ændre noget — ellers ville hver opstart skrive."""
    from core.runtime.db_core import connect
    from core.runtime.db_heartbeat import _backfill_tick_purposes

    _skriv_tick("tick-x", "act_on_initiative")
    with connect() as conn:
        assert _backfill_tick_purposes(conn) == 0, "en ny tick har allerede et formål"
        assert _backfill_tick_purposes(conn) == 0
        conn.commit()
