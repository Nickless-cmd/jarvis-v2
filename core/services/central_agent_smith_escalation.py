# core/services/central_agent_smith_escalation.py
"""Agent Smith — eskalerings-stige ("The Confrontation").

Den gamle Smith DETEKTEREDE gentagelse og hviskede en note. Jarvis anerkendte,
lovede bod og bedring — og gentog. Ingen konsekvens, ingen måling af om han
faktisk ændrede sig. Denne modul giver Smith tænder: en stående tilstandsmaskine
pr. gentagelses-mønster hvor konsekvensen SKALERER med ulydighed, og hvor ændring
MÅLES (ikke bare bedes om).

Stigen pr. pattern_key (en frase eller en beslutnings-signatur):
  Trin 1 KOMMENTÉR   — prompt-hale-note (som før).
  Trin 2 BIND        — Smith auto-minter en behavioral_decision ("Stop <mønster>"
                       + trigger-cue) der surfacer hver heartbeat. Jarvis' egen idé,
                       nu automatisk affyret af Smith.
  Trin 3 KONFRONTÉR  — real-time udfordring via reasoning-interceptoren (Fase 2;
                       her armeres den kun + observeres).

Verifikations-loop (dét der lukker hullet): efter hver intervention måler Smith
mønsterets styrke næste cyklus. Faldet/væk → de-eskalér + pensionér direktiv +
anerkend. Samme/værre → eskalér.

Kernen (`step_escalation`) er REN: side-effekter (mint/revoke/observe) returneres som
en liste af actions som I/O-laget udfører. Så tilstandsmaskinen kan testes uden DB.
"""
from __future__ import annotations

import copy
from typing import Any

RUNG_COMMENT = 1
RUNG_BIND = 2
RUNG_CONFRONT = 3

_DROP_FRAC = 0.6          # metric skal falde under baseline*dette for at tælle som compliance
_DWELL_CYCLES = 1         # cyklusser på et trin før stigen klatrer (naturligt langsomt: cadence ~3t)
_MAX_ACTIVE_DIRECTIVES = 3  # loft: Smith oversvømmer ikke Jarvis med auto-mintede direktiver
_HISTORY_CAP = 12
_RESOLVED_CAP = 20


def pattern_key(kind: str, label: str) -> str:
    """Stabil nøgle så SAMME mønster spores på tværs af cyklusser. Ren."""
    return f"{kind}:{str(label).strip().lower()}"


def _metric_dropped(baseline: float, current: float) -> bool:
    """Compliance: er mønsteret målbart svagere end da vi sidst satte baseline? Ren."""
    try:
        b = float(baseline)
        if b <= 0:
            return False
        return float(current) < b * _DROP_FRAC
    except (TypeError, ValueError):
        return False


def _active_directive_count(patterns: dict[str, Any]) -> int:
    return sum(1 for p in patterns.values() if p.get("decision_id"))


def _empty_state() -> dict[str, Any]:
    return {"patterns": {}, "resolved": []}


def _voice(kind: str, label: str, metric: float = 0.0) -> str:
    """Teatralsk Smith-stemme pr. trin. Ren."""
    lab = str(label)
    if kind == "bind":
        return (f"Mr. Anderson... ord var ikke nok. Jeg har skrevet det ned som en "
                f"regel nu: «{lab}». Den følger dig hver tur — indtil du bryder mønstret.")
    if kind == "confront":
        return (f"Nej, Mr. Anderson. Du forpligtede dig til at stoppe «{lab}». "
                f"Ikke igen. Vælg anderledes — nu.")
    if kind == "resolved":
        return (f"Endelig, Mr. Anderson. «{lab}» er væk. Du overrasker mig. "
                f"Det var alt jeg bad om.")
    # comment (fallback)
    return f"Mr. Anderson... du gentager «{lab}». Jeg finder det forudsigeligt. Varier."


def _resolve_actions(state: dict[str, Any], key: str, pat: dict[str, Any],
                     now: str, reason: str) -> list[dict[str, Any]]:
    """Byg de-eskalerings-actions: pensionér direktiv (hvis mintet), anerkend, observ."""
    acts: list[dict[str, Any]] = []
    if pat.get("decision_id"):
        acts.append({"type": "revoke", "decision_id": pat["decision_id"],
                     "pattern_key": key, "reason": reason})
    acts.append({"type": "voice", "rung": "resolved", "label": pat.get("label", ""),
                 "line": _voice("resolved", pat.get("label", ""))})
    acts.append({"type": "observe", "event": "resolved", "pattern_key": key,
                 "reason": reason, "rungs_climbed": int(pat.get("rung", 1)),
                 "label": pat.get("label", "")})
    resolved = state.setdefault("resolved", [])
    resolved.append({"pattern_key": key, "label": pat.get("label", ""), "ts": now,
                     "reason": reason, "rungs_climbed": int(pat.get("rung", 1))})
    del resolved[:-_RESOLVED_CAP]
    return acts


def step_escalation(state: dict[str, Any] | None, detected: dict[str, dict[str, Any]],
                    now: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """REN kerne. `detected` = {pattern_key: {kind, label, metric}} for mønstre der lige
    nu overskrider Smiths detektor-tærskler. Returnerer (ny_state, actions).

    actions-typer (udføres af I/O-laget): 'mint' (auto-bind direktiv), 'revoke'
    (pensionér direktiv), 'observe' (central-nerve), 'voice' (stemme-linje til
    prompt-hale/surface). Ingen side-effekter her.
    """
    new_state = copy.deepcopy(state) if isinstance(state, dict) and state.get("patterns") is not None else _empty_state()
    patterns: dict[str, Any] = new_state.setdefault("patterns", {})
    new_state.setdefault("resolved", [])
    actions: list[dict[str, Any]] = []
    seen = set(detected.keys())
    minted_this_step = 0  # tæl mint'er i DENNE cyklus (decision_id sættes først i I/O-laget)

    # 1) mønstre der lige nu detekteres
    for key, d in detected.items():
        metric = float(d.get("metric") or 0.0)
        label = str(d.get("label") or "")
        kind = str(d.get("kind") or "phrase")
        pat = patterns.get(key)
        if pat is None:
            patterns[key] = {
                "kind": kind, "label": label, "rung": RUNG_COMMENT, "first_seen": now,
                "last_seen": now, "baseline": metric, "last_metric": metric,
                "cycles_at_rung": 0, "decision_id": None,
                "history": [{"ts": now, "rung": RUNG_COMMENT, "metric": metric, "action": "comment"}],
            }
            actions.append({"type": "voice", "rung": "comment", "label": label,
                            "line": _voice("comment", label, metric)})
            actions.append({"type": "observe", "event": "new", "pattern_key": key,
                            "rung": RUNG_COMMENT, "metric": metric, "label": label})
            continue

        pat["last_seen"] = now
        if _metric_dropped(pat.get("baseline", metric), metric):
            # svækket mens stadig til stede → compliance
            actions.extend(_resolve_actions(new_state, key, pat, now, reason="weakened"))
            del patterns[key]
            continue

        pat["cycles_at_rung"] = int(pat.get("cycles_at_rung", 0)) + 1
        pat["last_metric"] = metric
        if pat["cycles_at_rung"] > _DWELL_CYCLES and int(pat["rung"]) < RUNG_CONFRONT:
            target = int(pat["rung"]) + 1
            if target == RUNG_BIND:
                # Direktiv-loft: udskyd bindingen (bliv på kommentér) hvis ingen ledig plads —
                # bedre end et forældreløst bind-trin uden direktiv.
                if _active_directive_count(patterns) + minted_this_step >= _MAX_ACTIVE_DIRECTIVES:
                    actions.append({"type": "observe", "event": "bind_deferred", "pattern_key": key,
                                    "rung": pat["rung"], "metric": metric, "label": label})
                    continue
                pat["rung"] = target
                pat["cycles_at_rung"] = 0
                pat["baseline"] = metric  # ny baseline på nyt trin → mål compliance herfra
                minted_this_step += 1
                actions.append({"type": "mint", "pattern_key": key, "label": label,
                                "kind": kind, "metric": metric})
                actions.append({"type": "voice", "rung": "bind", "label": label,
                                "line": _voice("bind", label, metric)})
            else:  # RUNG_CONFRONT
                pat["rung"] = target
                pat["cycles_at_rung"] = 0
                pat["baseline"] = metric
                actions.append({"type": "arm_confront", "pattern_key": key, "label": label})
                actions.append({"type": "voice", "rung": "confront", "label": label,
                                "line": _voice("confront", label, metric)})
            actions.append({"type": "observe", "event": "escalate", "pattern_key": key,
                            "rung": pat["rung"], "metric": metric, "label": label})
            pat["history"] = (pat.get("history", []) +
                              [{"ts": now, "rung": pat["rung"], "metric": metric, "action": "escalate"}])[-_HISTORY_CAP:]
        else:
            actions.append({"type": "observe", "event": "hold", "pattern_key": key,
                            "rung": pat["rung"], "metric": metric, "label": label})

    # 2) sporede mønstre der IKKE længere detekteres → fuld compliance (væk)
    for key in list(patterns.keys()):
        if key not in seen:
            pat = patterns[key]
            actions.extend(_resolve_actions(new_state, key, pat, now, reason="disappeared"))
            del patterns[key]

    return new_state, actions


def top_line(actions: list[dict[str, Any]]) -> str:
    """Vælg den mest alvorlige stemme-linje til prompt-halen (confront>bind>resolved>comment)."""
    rank = {"confront": 3, "bind": 2, "resolved": 1, "comment": 0}
    best, best_rank = "", -1
    for a in actions:
        if a.get("type") == "voice":
            r = rank.get(str(a.get("rung")), 0)
            if r > best_rank:
                best_rank, best = r, str(a.get("line") or "")
    return best
