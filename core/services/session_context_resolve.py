"""Hvilken samtale kører vi i? — ét sted, frem for én kopi pr. værktøj.

Der er TO ContextVars der kan bære svaret, fordi der er to veje ind:
`visible_run_context` sættes af den synlige run-løkke, og `chat_sessions`'
egen sættes af chat-maskineriet. Ingen af dem er sat i alle tilfælde, og
rækkefølgen betyder noget — den synlige løkke er tættere på det brugeren
kigger på.

Resolveren har eksisteret siden staged_edits blev bygget, men lå som en
privat funktion i ét værktøjsmodul. Næste værktøj der havde brug for den
ville have skrevet sin egen, og så ville de to kunne blive uenige om
rækkefølgen uden at nogen opdagede det.
"""
from __future__ import annotations


def aktiv_session_id(standard: str = "") -> str:
    """Sessionens id, eller `standard` hvis ingen kilde kender den.

    Self-safe hele vejen: en manglende ContextVar må aldrig kunne vælte det
    værktøj der spurgte.
    """
    try:
        from core.services.visible_run_context import current_session_id
        sid = (current_session_id() or "").strip()
        if sid:
            return sid
    except Exception:
        pass
    try:
        from core.services.chat_sessions import current_session_id_ctx
        sid = (current_session_id_ctx() or "").strip()
        if sid:
            return sid
    except Exception:
        pass
    try:
        from core.identity.workspace_context import current_session_id as _wc
        sid = (_wc() or "").strip()
        if sid:
            return sid
    except Exception:
        pass
    return standard


def aktivt_run_id(standard: str = "") -> str:
    """Det run der er i gang lige nu, eller `standard` hvis ingen kender det.

    ## Hvorfor den findes

    Incident 8839 og 6798 (12/9-2026) stod begge med TOMT `run_id` og tomt
    `session_id` — en honesty-gate der fyrede og en exec-guard der blokerede en
    overskrivning af MEMORY.md. Feltet fandtes i `record_central_incident`;
    kalderen sendte det bare ikke. Resultatet: to alvorlige hændelser man ikke
    kan spore til en kørsel, og derfor ikke kan efterforske.

    Run-id'et lever i `run_closure_gate._get_current_run()` — privat, fordi det
    er den modulets eget bogholderi. Denne funktion er den ene offentlige vej
    ind til det, ved siden af `aktiv_session_id`, saa kaldere ikke skal
    importere et privat navn paa tvaers af moduler.

    Self-safe hele vejen: et manglende run maa aldrig kunne vaelte den gate der
    spurgte.
    """
    try:
        from core.services.run_closure_gate import _get_current_run
        rid = (_get_current_run() or "").strip()
        if rid:
            return rid
    except Exception:
        pass
    return standard
