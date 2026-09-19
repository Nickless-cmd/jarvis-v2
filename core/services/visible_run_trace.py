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

import logging
import threading
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

from core.eventbus.bus import event_bus

if TYPE_CHECKING:
    from core.services.visible_runs import VisibleRun

logger = logging.getLogger(__name__)

#: Færdige etiketter der venter på at blive sendt, pr. kørsel.
#:
#: En generator kan kun `yield` fra sit eget flow, og etiketten regnes i en
#: tråd. Derfor lægges den her, og løkken tømmer køen ved næste rundes start.
#: Det er samme grund som får Claude Code til at levere sin NÆSTE tur — vi har
#: bare flere runder pr. tur, så ventetiden bliver kortere.
_VENTENDE: dict[str, list[dict[str, Any]]] = {}
_VENTENDE_LAAS = threading.Lock()

#: Loft pr. kørsel. En kørsel der døde midt i tømmer aldrig sin kø, og en kø
#: uden loft vokser til den fylder noget. Huset har haft 2,81 mio. kanter på
#: præcis den måde.
MAKS_VENTENDE: int = 8

#: Traade der stadig regner en etiket, pr. kørsel. Bogføres for at kunne vente
#: KORT paa dem naar turen lukker — uden dem ville den sidste tool-rundes
#: etiket gaa tabt, og det er ofte den mest interessante runde.
_TRAADE: dict[str, list[threading.Thread]] = {}

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


def _etiket(vaerktoejer: list[dict[str, Any]], hensigt: str) -> str:
    """Indirektion så tråden kan byttes ud i en test uden at røre modellen."""
    from core.services.tool_round_label import etiket
    return etiket(vaerktoejer, hensigt)


def _tanke_resume(tanke: str, hensigt: str) -> str:
    """Indirektion så tråden kan testes uden at røre modellen."""
    from core.services.tanke_resume import tanke_resume
    return tanke_resume(tanke, hensigt)


def udsend_runde_etiket(
    *, run_id: str, round_num: int,
    vaerktoejer: list[dict[str, Any]], hensigt: str = "",
    tanke: str = "",
) -> threading.Thread | None:
    """Skriv én kort etiket for runden og udsend den. Blokerer ALDRIG.

    ## Hvad den er

    «Rettede fejl i login» — hvad runden UDRETTEDE. Klienternes mekaniske linje
    («Kørte en kommando og redigerede 2 filer +12 −4») siger hvad der SKETE. De
    to står sammen, etiketten først.

    ## Hvorfor en tråd, og hvorfor det er betingelsen

    Claude Code bærer sin som `pendingToolUseSummary: Promise<…>` og leverer den
    NÆSTE tur — derfor koster den ingen ventetid. Vi kan levere i SAMME runde,
    fordi streamen allerede bærer top-level runde-events og begge klienter
    grupperer værktøjer pr. runde. Men kun hvis kaldet ikke får runden til at
    vente: ellers havde vi byttet en langsommere tur for en pænere linje.

    Tråden er daemon. Ellers kunne en langsom etiket holde processen i live ved
    nedlukning, og det er præcis den slags der har kostet en dag i dette hus.

    ## Hvad der ikke sker

    Ingen værktøjer → ingen tråd. En runde uden værktøjer har intet at
    opsummere, og en tråd pr. tekst-runde ville være ren spild.

    Tom etiket → intet event. En tom overskrift ville få klienten til at rydde
    plads til ingenting.

    En fejl vælter ingenting. En etiket er en overskrift; en tur må aldrig
    vælte fordi overskriften ikke kunne skrives.
    """
    if not vaerktoejer:
        return None

    def _arbejd() -> None:
        try:
            from core.services.tool_round_label import tool_use_ids
            tekst = _etiket(vaerktoejer, hensigt)
            # Tænke-resuméet (visningstilstanden «Tænkning», 19/9-2026): kun
            # når kalderen gav tænkningen med — dvs. når klienten bad om det.
            resume = _tanke_resume(tanke, hensigt) if (tanke or "").strip() else ""
            if not (tekst or "").strip() and not resume:
                return
            nyttelast = {
                "run_id": run_id,
                "round": round_num,
                "etiket": tekst,
                "tool_use_ids": tool_use_ids(vaerktoejer),
            }
            if resume:
                nyttelast["tanke_resume"] = resume
            event_bus.publish("runtime.tool_round_label", nyttelast)
            with _VENTENDE_LAAS:
                koe = _VENTENDE.setdefault(run_id, [])
                koe.append(nyttelast)
                if len(koe) > MAKS_VENTENDE:
                    del koe[:-MAKS_VENTENDE]
        except Exception:
            logger.debug("runde-etiket fejlede for %s runde %s", run_id, round_num,
                         exc_info=True)

    t = threading.Thread(target=_arbejd, name=f"runde-etiket-{run_id}", daemon=True)
    with _VENTENDE_LAAS:
        traade = _TRAADE.setdefault(run_id, [])
        traade[:] = [x for x in traade if x.is_alive()]
        traade.append(t)
    t.start()
    return t


def haent_ventende(run_id: str) -> list[dict[str, Any]]:
    """Tøm køen af færdige etiketter for en kørsel.

    Tømmes den ikke, ville samme etiket blive sendt igen ved hver runde-start.
    En ukendt kørsel giver en tom liste — ikke en fejl; den normale tilstand er
    at der intet er.
    """
    with _VENTENDE_LAAS:
        return _VENTENDE.pop(run_id, [])


def hoest_etiketter(run_id: str, tur: Any = None, frist_s: float | None = None) -> list[dict[str, Any]]:
    """Hent faerdige runde-etiketter — og laeg dem i turen, saa de GEMMES.

    Foer blev etiketterne kun streamet. Den sidste rundes etiket kom endda
    foerst EFTER at svaret var gemt, saa den forsvandt ved hver genindlaesning
    — og den er ofte den mest interessante. Hoesten sker nu ét sted og goer
    begge dele: returnerer etiketterne til streamen og giver dem til turens
    akkumulator som `tool_use_summary`-blokke (Claude Desktops egen form).
    """
    ud = haent_ventende_med_frist(run_id, frist_s) if frist_s else haent_ventende(run_id)
    if tur is not None:
        for e in ud:
            try:
                tur.add_round_label(e)
            except Exception:
                pass
    return ud


def ryd_ventende(run_id: str) -> None:
    """Smid en kørsels kø OG dens tråd-bogholderi væk.

    Begge dele, ellers vokser `_TRAADE` for hver eneste kørsel.
    """
    with _VENTENDE_LAAS:
        _VENTENDE.pop(run_id, None)
        _TRAADE.pop(run_id, None)


def haent_ventende_med_frist(run_id: str, frist_s: float) -> list[dict[str, Any]]:
    """Tøm køen — men vent KORT på en etiket der stadig regnes.

    ## Hvorfor den findes

    Køen fyldtes ved rundens SLUTNING og tømtes kun ved NÆSTE rundes start. Den
    sidste tool-rundes etiket blev derfor aldrig hentet — der var ingen næste
    runde — og det er ofte den mest interessante runde. Det er «events i en kø
    ingen tømmer», den fejl huset har haft før.

    Ved turens afslutning er der ikke mere at lave, så en kort venten på en
    etiket der er et halvt sekund fra at være færdig, er bedre end at tabe den.

    ## Fristen er et LOFT, ikke en ventetid

    Er der intet i gang, ventes der slet ikke — den almindelige tilstand må
    ikke koste tid. Hænger en etiket, løber fristen ud og turen lukker; en
    overskrift må aldrig kunne forsinke et svar i det uendelige.
    """
    with _VENTENDE_LAAS:
        traade = [x for x in _TRAADE.get(run_id, []) if x.is_alive()]
    if traade:
        import time
        udloeb = time.monotonic() + max(0.0, float(frist_s))
        for x in traade:
            rest = udloeb - time.monotonic()
            if rest <= 0:
                break
            x.join(timeout=rest)
    return haent_ventende(run_id)
