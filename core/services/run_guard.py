"""Én fælles vagt: kører der et run i denne session lige nu?

Hvorfor ÉN vagt og ikke seks (13/10-2026)
-----------------------------------------
Der er seks uafhængige steder der starter baggrunds-runs — `wakeup_dispatcher`,
`scheduled_tasks`, `recurring_tasks`, `routine_trigger_adapters` (heartbeat),
`dreaming_session` og `inbox_idle_waker` — og hver især med sin EGEN vagt,
eller ingen. Det er ikke en detalje: `wakeup_dispatcher._active_turn_blocks`
læser `run_event_log`, som er **in-memory per proces**.

Daemonerne kører i jarvis-runtime (8011, `JARVIS_ENABLE_RUNTIME_SERVICES=1`);
desk'ens chat serveres af jarvis-api (8080, `=0`). En vagt i runtime-processen
kan derfor ikke se Bjørns tur, som kører i api-processen. Målt 13/10-2026:
`autonomous-af9f…` og `visible-4f70…` stod begge `running` i SAMME session
`chat-6f46…` med 31 sekunders mellemrum — den ene født mens den anden kørte.
Det var den dublet Bjørn så som «flere instanser af dig i samme session».

Kilden her er `in_flight_runs`, som ER delt: fil + flock, ejer =
`<pid>:<starttid>`. Både den synlige tur og de autonome runs skriver til den
allerede, så vagten kræver ingen ny bogføring — kun en læser, som ikke fandtes.

Grænsen: kun BAGGRUNDS-kilder rammes
------------------------------------
``BESKYTTEDE_ORIGINS`` er en positivliste. Et wakeup, en planlagt opgave eller
et heartbeat må vente på at sessionen bliver ledig; en Discord-besked Bjørn
selv sendte, eller et barn-agent-svar han venter på, må ikke. Kilden tages RÅ
(før `normalize_origin`), fordi `normalize_origin` kollapser ukendte navne til
"autonomous" — og "inbox" ville dermed blive uskelneligt fra et vilkårligt
autonomt run.

Self-safe: enhver fejl → ingen blokering. Et wakeup må ikke forsvinde, fordi
registret ikke kunne læses.
"""
from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

#: Baggrunds-kilder hvor vagten gælder. RÅ navne — se docstringen.
#:
#: BEVIDST UDE: continuation (`visible_runs_memory` sender ingen origin),
#: Discord/Telegram-svar, agent-resultat-levering (`agent_message_receipt`) og
#: `jarvisx_processes`. De er svar på noget Bjørn selv gjorde, og at blokere
#: dem ville tabe et svar han venter på. De har deres egne vagter, eller
#: ingen — det er en ÅBEN sag, ikke en påstand om at de er dækket.
BESKYTTEDE_ORIGINS: Final[frozenset[str]] = frozenset({
    "wakeup", "self-wakeup", "inbox", "scheduled", "recurring",
    "heartbeat", "heartbeat_runtime", "dream", "council",
})


def levende_run_i_session(session_id: str) -> str:
    """Run-id på et LEVENDE run i sessionen — cross-proces. "" hvis ingen.

    To kilder, i den rækkefølge de er præcise:

    1. ``run_event_log.active_run_for_session`` — samme proces, øjeblikkelig,
       og den eneste der kender et run der endnu ikke har nået journalen.
    2. ``in_flight_runs.levende_koersler`` — den DELTE journal. Det er den der
       fanger api-processens tur set fra runtime-processen, og det er hele
       grunden til at denne funktion findes.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return ""
    try:
        from core.services import run_event_log as rel

        rid = rel.active_run_for_session(sid)
        if rid:
            return str(rid)
    except Exception as exc:  # noqa: BLE001 — self-safe: gæt aldrig på et run
        logger.debug("run_guard: kunne ikke laese run-loggen for %s: %s", sid[:28], exc)
    try:
        from core.services import in_flight_runs as ifr

        poster = ifr.levende_koersler(session_id=sid)
        if poster:
            return str(poster[0].get("run_id") or "")
    except Exception as exc:  # noqa: BLE001 — self-safe, se ovenfor
        logger.debug("run_guard: kunne ikke laese registret for %s: %s", sid[:28], exc)
    return ""


def blokeringsgrund(origin: str, session_id: str) -> str:
    """Årsag hvis et nyt BAGGRUNDS-run ikke må starte her. "" = fri bane.

    Kaldes som pre-flight i run-starterne, FØR et run fødes. Er svaret ikke
    tomt, må runnet ikke starte: forpligtelsen bliver liggende i indbakken og
    tages i den kørende turs kontekst, eller når sessionen er ledig.
    """
    try:
        o = str(origin or "").strip().lower()
        if o not in BESKYTTEDE_ORIGINS:
            return ""
        rid = levende_run_i_session(session_id)
        if not rid:
            return ""
        return f"levende_run_i_session:{rid[:24]}"
    except Exception as exc:  # noqa: BLE001 — self-safe: hellere køre end tabe
        logger.debug("run_guard: vagten kunne ikke afgoeres: %s", exc)
        return ""
