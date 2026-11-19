"""Hvilken samtale kører vi i? — ét sted, frem for én kopi pr. værktøj.

Der er praecis ÉN ContextVar der baerer svaret: `workspace_context`s
`session_id`. Den saettes af alle tre veje ind — den synlige run-loekke
(`visible_runs.py`), værktøjs-executoren (`visible_tool_exec.py`) og
rutine-runneren (`routine_runner.py`).

## To kilder var doede i månedsvis (maalt 19/11-2026)

Indtil i dag provede denne resolver to andre kilder FOERST:

  * `core.services.visible_run_context` — modulet findes ikke.
  * `core.services.chat_sessions.current_session_id_ctx` — attributten findes ikke.

Begge import-forsoeg fejlede i det stille og faldt videre, saa det saa ud som
om der blev spurgt tre steder. Det gjorde der ikke: kun det tredje forsøg
kunne nogensinde svare. Fejlen var usynlig fordi testen selv opdigtede de to
moduler med `monkeypatch.setitem(sys.modules, ...)` — den bemaalte en
raekkefoelge der ikke kunne indtraeffe i virkeligheden.

Vaernet mod at det sker igen staar i `tests/test_session_context_resolve.py`:
hvert modul og hvert navn der spoerges, skal kunne importeres for rigtigt.

Resolveren har eksisteret siden staged_edits blev bygget, men laa som en
privat funktion i ét værktøjsmodul. Naeste værktøj der havde brug for den
ville have skrevet sin egen — og `staged_edits_tools` gjorde praecis det, med
kun de to doede kilder. Resultatet var at ALLE sessioner delte `_default`.
"""
from __future__ import annotations


def aktiv_session_id(standard: str = "") -> str:
    """Sessionens id, eller `standard` hvis ingen kilde kender den.

    Self-safe: en manglende ContextVar må aldrig kunne vælte det værktøj der
    spurgte. Men «self-safe» betyder ikke «prøv alt muligt» — en kilde der
    ikke findes kan ikke svare, og skal derfor ikke stå her.
    """
    try:
        from core.identity.workspace_context import current_session_id
        sid = (current_session_id() or "").strip()
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
    # Koerslens egen ContextVar foerst (15/9-2026). Gatens globale kender kun
    # autonome koersler og er tom i jarvis-api, hvor de synlige ture koerer —
    # se run_autonomy_context.
    try:
        from core.services.run_autonomy_context import current_run_id
        rid = (current_run_id() or "").strip()
        if rid:
            return rid
    except Exception:
        pass
    try:
        from core.services.run_closure_gate import _get_current_run
        rid = (_get_current_run() or "").strip()
        if rid:
            return rid
    except Exception:
        pass
    return standard
