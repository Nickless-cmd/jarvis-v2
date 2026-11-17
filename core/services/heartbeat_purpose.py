"""Hvad var heartbeat-slaget TIL? — én definition, fire formål.

Baggrund (Bjørn 17/11-2026: *«hvad skal heartbeat egentlig lave?»*). Spørgsmålet
kunne ikke besvares ud af data, fordi `heartbeat_runtime_ticks` kun bar en
`action_type` — ikke hvad slaget var *til for*. Målt 17/11 over 7 dage: 57,9 %
arbejde, 38,7 % indre liv, 1,8 % session, 1,5 % overlevelse. Overlevelse og
arbejde havde samme kadence og samme tabel, så arbejdet betalte for
overlevelsens ure.

Dette modul er den ene definition. Klassificeringen er ikke lavet på
`action_type`'ens navn, men på **hvad dens artefakt skriver til** — målt i
`action_artifact` over 60 dage (se
`docs/findings/heartbeat-formaal-klassificering-2026-11-17.md`).

Den vigtige præcisering undervejs: `act_on_initiative` og
`refresh_memory_context` bærer BEGGE et `session_id` i deres artefakt, men
ingen af dem leverer noget til samtalen — de skriver til task/flow og til
hukommelse. Reglen er derfor ikke «kender en session», men **«leverer til en
session»**. Kun `webchat-heartbeat-proposal` gør det (den har `message_id` og
`delivery_channel`).

Klasserne har forskellige krav, og det er hele pointen med feltet:

| Formål | Skal køre af sig selv | Skal vække nogen | Skal lande i en session |
|---|---|---|---|
| overlevelse | ja | nej | nej |
| session | nej — kun når nogen venter | ja | ja |
| indre_liv | ja, egen kadence | nej | nej |
| arbejde | nej — kun ved reel kø | kun ved blokering | ja, hvis den har en ophavssamtale |
"""
from __future__ import annotations

from typing import Final

#: Skriver til systemets egen tilstand. Ingen læser resultatet som arbejde.
SURVIVAL: Final[str] = "overlevelse"

#: Leverer noget TIL en samtale — den eneste klasse med en modtager.
SESSION: Final[str] = "session"

#: Skriver til filer og tilstande jeg selv læser senere. Ingen samtale.
INNER_LIFE: Final[str] = "indre_liv"

#: Forsøger at gøre noget i verden. Skriver til tabeller uden for en samtale.
WORK: Final[str] = "arbejde"

#: Fasens bogføring af det samme slag — ikke et slag i sig selv.
#: `tick_dispatched` skrives ved siden af den indre tick for hvert slag, så
#: tæller man begge, fordobles kadencen (målt 17/11: 218 dispatch + 219 indre
#: over to døgn = ~110 slag, ikke 180).
DISPATCH: Final[str] = "dispatch"

#: Pladsholder skrevet fordi dispatch-grenen krævede en prioritet der ikke
#: fandtes. Målt: 2.876 kald frem til 3/11-2026, alle med samme summary.
#: Det er ikke en handling — det er navnet på en manglende prioritet.
IDLE: Final[str] = "tomgang"

#: Tom `action_type` (ældre rækker) eller en gren ingen har klassificeret.
UNKNOWN: Final[str] = "ukendt"

ALL_PURPOSES: Final[tuple[str, ...]] = (
    SURVIVAL,
    SESSION,
    INNER_LIFE,
    WORK,
    DISPATCH,
    IDLE,
    UNKNOWN,
)

#: De fire formål et slag kan have. `dispatch`, `tomgang` og `ukendt` er
#: mangel på formål, ikke formål — de holdes uden for fordelingen.
REAL_PURPOSES: Final[tuple[str, ...]] = (SURVIVAL, SESSION, INNER_LIFE, WORK)

# Observeret i `action_artifact` over 60 dage. Klassificeret på hvad grenen
# skriver til, ikke på navnet.
_OBSERVED: Final[dict[str, str]] = {
    # ── overlevelse: systemets egen tilstand ──────────────────────────────
    # progress_lifecycles → carried/fading/released/stale
    "progress_lifecycles": SURVIVAL,
    # decay_forgotten_signals → faded_keys/total_tracked
    "decay_forgotten_signals": SURVIVAL,
    # cleanup_stale_signals → archived/tables_scanned
    "cleanup_stale_signals": SURVIVAL,
    "cleanup_web_cache": SURVIVAL,
    "cleanup_daemon_output_log": SURVIVAL,
    # ── session: leverer TIL samtalen ─────────────────────────────────────
    # webchat-heartbeat-proposal → session_id + message_id + delivery_channel
    "webchat-heartbeat-proposal": SESSION,
    # ── indre liv: filer og tilstande jeg selv læser senere ───────────────
    # analyze_cross_signals → liste af mønsternavne
    "analyze_cross_signals": INNER_LIFE,
    # run_sleep_batch → liste (drømme)
    "run_sleep_batch": INNER_LIFE,
    # generate_counterfactual_dreams → cf_id
    "generate_counterfactual_dreams": INNER_LIFE,
    # run_mirror_reflection → insight_id
    "run_mirror_reflection": INNER_LIFE,
    # autonomous_daily_note → path (en fil)
    "autonomous_daily_note": INNER_LIFE,
    # write_growth_journal → chronicle/insight
    "write_growth_journal": INNER_LIFE,
    # write_chronicle_entry → entry_id/period
    "write_chronicle_entry": INNER_LIFE,
    # update_compass → bearing/compass_id
    "update_compass": INNER_LIFE,
    "update_anticipatory_context": INNER_LIFE,
    "produce_emergent_signals": INNER_LIFE,
    # review_recent_conversations → moods/topics (læser samtaler, skriver indsigt)
    "review_recent_conversations": INNER_LIFE,
    "update_boredom_state": INNER_LIFE,
    # ── arbejde: forsøger at gøre noget i verden ──────────────────────────
    # act_on_initiative → initiative/task/flow (+ session_id, men skriver ikke til den)
    "act_on_initiative": WORK,
    # follow_open_loop → eksekverede kommandoer
    "follow_open_loop": WORK,
    # process_contract_writes → tællinger (målt 47/47 tomme, men det ER et forsøg)
    "process_contract_writes": WORK,
    # inspect_repo_context → items
    "inspect_repo_context": WORK,
    # verify_recent_claim → grounding_preview
    "verify_recent_claim": WORK,
    "gather_system_context": WORK,
    # manage_runtime_work → flow/task-id'er
    "manage_runtime_work": WORK,
    # explore_own_codebase → insight_id (undersøger kode, ikke eget sind)
    "explore_own_codebase": WORK,
    # refresh_memory_context → memory_items (+ session_id, men skriver hukommelse)
    "refresh_memory_context": WORK,
    "run_candidate_scan": WORK,
    # ── bogføring og tomgang ──────────────────────────────────────────────
    "tick_dispatched": DISPATCH,
    "productive_idle": IDLE,
}

#: Grene der findes i `heartbeat_runtime.py` men ikke er ramt i 60 dage.
#: Klassificeret på navn og grenen rundt om dem — IKKE på et observeret
#: artefakt. Det står her, så forskellen mellem målt og antaget er synlig:
#: bliver en af dem ramt, skal klassificeringen efterprøves mod dens artefakt.
_INFERRED: Final[dict[str, str]] = {
    "generate_narrative_identity": INNER_LIFE,
    "propose_identity_evolution": INNER_LIFE,
    "evaluate_self_experiments": INNER_LIFE,
    "generate_emergent_goal": INNER_LIFE,
    "generate_curriculum": INNER_LIFE,
    "detect_consent_reaction": INNER_LIFE,
    "check_seed_activation": INNER_LIFE,
}

_BY_ACTION: Final[dict[str, str]] = {**_OBSERVED, **_INFERRED}


def purpose_for_action(action_type: str) -> str:
    """Formålet med et slag ud fra dets handlingstype.

    Ukendte typer bliver ``ukendt`` — ikke en gættet klasse. En ny gren skal
    klassificeres bevidst, og `tests/test_heartbeat_purpose.py` fælder når
    koden får en `action_type` der ikke findes her.
    """
    key = str(action_type or "").strip()
    if not key:
        return UNKNOWN
    return _BY_ACTION.get(key, UNKNOWN)


def known_action_types() -> frozenset[str]:
    """Alle klassificerede handlingstyper — til vagten mod tavs forældelse."""
    return frozenset(_BY_ACTION)


def action_types_in(purpose: str) -> frozenset[str]:
    """Handlingstyperne i én klasse."""
    return frozenset(k for k, v in _BY_ACTION.items() if v == purpose)


def is_real_purpose(purpose: str) -> bool:
    """True for de fire formål — False for bogføring, tomgang og ukendt."""
    return purpose in REAL_PURPOSES


def describe() -> dict[str, object]:
    """Klassificeringen som data — til docs, tests og værktøjer."""
    return {
        "purposes": list(ALL_PURPOSES),
        "real_purposes": list(REAL_PURPOSES),
        "observed": {p: sorted(action_types_in(p)) for p in ALL_PURPOSES},
        "inferred": sorted(_INFERRED),
        "counts": {p: len(action_types_in(p)) for p in ALL_PURPOSES},
    }
