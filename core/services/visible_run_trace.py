"""Sporet gennem én synlig kørsel — og runde-grænserne i den.

## Hvorfor den er udskilt (14/9-2026)

Boy Scout-reglen i CLAUDE.md: rører man en fil over 2.000 linjer, udskiller man
først den nærmeste naturlige sammenhængende enhed. `visible_runs.py` var på
**7.583 linjer** — husets største — og var vokset fra de 7.290 listen nævnte
8/9. Anledningen er at runde-etiketten skal hænge på
`_publish_agentic_round_start`, og det er netop den funktion der bor her.

Enheden er ikke tilfældigt valgt: de seks funktioner herunder deler ÉN tilstand
(`_LAST_VISIBLE_EXECUTION_TRACE`) og ét ansvar — at føre bog over hvad en
kørsel gjorde, og hvornår en runde begyndte.

## Bagudkompatibilitet

`visible_runs` gen-eksporterer alt herfra, så eksisterende imports ikke
brækker. Målt før flytningen: `get_last_visible_execution_trace` har tre
eksterne kaldere, `_update_visible_execution_trace` seks og
`_publish_agentic_round_start` fire — heraf tests der griber direkte i
`visible_runs`-navnerummet.

En test i `test_process_lifecycle` læser løkkens KILDETEKST og kræver at
nedluknings-vagten står før `_publish_agentic_round_start`. Den holder: kaldet
bliver hvor det er, kun definitionen flytter.

## Én ting der gik galt undervejs, værd at huske

Første forsøg skar blokken ud på LINJENUMRE og tog filens sidste
gen-eksport-blok med — den der peger på `visible_runs_cognitive` og de øvrige
tidligere udskillelser. 22 tests gik røde på
`has no attribute '_track_runtime_candidates'`. En udskillelse skal følge
funktions-grænser, ikke et udsnit man ikke har læst til ende.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.eventbus.bus import event_bus

if TYPE_CHECKING:
    from core.services.visible_runs import VisibleRun

#: Sidste kørsels spor. Bor her sammen med de funktioner der rører den — en
#: tilstand uden sine funktioner er en global, ikke en enhed.
_LAST_VISIBLE_EXECUTION_TRACE: dict[str, object] | None = None


def get_last_visible_execution_trace() -> dict[str, object] | None:
    return dict(_LAST_VISIBLE_EXECUTION_TRACE) if _LAST_VISIBLE_EXECUTION_TRACE else None


def _start_visible_execution_trace(run: VisibleRun) -> dict[str, object]:
    trace = {
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "selected_capability_id": None,
        "parsed_target_path": None,
        "parsed_command_text": None,
        "normalized_command_text": None,
        "path_normalization_applied": False,
        "normalization_source": "none",
        "argument_source": "none",
        "argument_binding_mode": "id-only",
        "invoke_status": "not-invoked",
        "blocked_reason": None,
        "provider_first_pass_status": "started",
        "provider_second_pass_status": "not-started",
        "provider_error_summary": None,
        "provider_call_count": 0,
        "capability_markup_count": 0,
        "multiple_capability_tags": False,
        "first_pass_input_tokens": 0,
        "first_pass_output_tokens": 0,
        "second_pass_input_tokens": 0,
        "second_pass_output_tokens": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "final_status": "running",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _set_last_visible_execution_trace(trace)
    return trace


def _update_visible_execution_trace(run: VisibleRun, updates: dict[str, object]) -> None:
    trace = get_last_visible_execution_trace() or {}
    merged = {
        **trace,
        **updates,
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _set_last_visible_execution_trace(merged)


def _set_last_visible_execution_trace(trace: dict[str, object]) -> None:
    global _LAST_VISIBLE_EXECUTION_TRACE
    _LAST_VISIBLE_EXECUTION_TRACE = dict(trace)
    event_bus.publish(
        "runtime.visible_run_execution_trace",
        dict(trace),
    )


def _visible_trace_payload(run: VisibleRun) -> dict[str, object]:
    trace = get_last_visible_execution_trace() or {}
    return {
        "type": "trace",
        "run_id": run.run_id,
        **trace,
    }


def _publish_agentic_round_start(*, run_id: str, round_num: int) -> int:
    """Publish runtime.agentic_round_start event and return its event_id.

    Used by the causal graph layer (commit 894a214) to anchor all events
    inside an agentic round to a stable round-start parent. Inferens-
    daemonen kan derefter trække chains via shared run_id eller via
    EventContext-auto-pickup når events publiceres inden i round'en.
    """
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    event_bus.publish(
        "runtime.agentic_round_start",
        {"run_id": run_id, "round": round_num},
    )
    # SPOERG EFTER SIN EGEN EVENT (fase 10). Foer stod her «nyeste af sin
    # slags», og begge units koerer samme app — saa en samtidig runde i den
    # ANDEN proces kunne blive kaedens foraelder. MAALT: 240 af 5.457
    # runde-start-events (4,4 %) har en soeskende inden for ét sekund, saa det
    # er ikke teoretisk. Telemetri maa registrere arbejde, ikke forveksle det.
    with connect() as conn:
        row = None
        try:
            row = conn.execute(
                "SELECT id FROM events WHERE kind = ? "
                "AND json_valid(payload_json) "
                "AND json_extract(payload_json, '$.run_id') = ? "
                "AND json_extract(payload_json, '$.round') = ? "
                "ORDER BY id DESC LIMIT 1",
                ("runtime.agentic_round_start", run_id, round_num),
            ).fetchone()
        except Exception:
            # `json_extract` KASTER paa ugyldig JSON — den giver ikke NULL. Uden
            # `json_valid` foran ville én oedelagt raekke vaelte hele opslaget,
            # og faldbacken nedenfor (som kun saa efter `None`) ville aldrig
            # koere. Min egen test fandt det.
            row = None
        if row is None:
            # Aeldre rakker uden brugbar payload, eller en sqlite uden JSON1:
            # fald tilbage til den gamle adfaerd frem for at tabe kaeden helt.
            row = conn.execute(
                "SELECT id FROM events WHERE kind = ? ORDER BY id DESC LIMIT 1",
                ("runtime.agentic_round_start",),
            ).fetchone()
    return int(row["id"]) if row else 0
