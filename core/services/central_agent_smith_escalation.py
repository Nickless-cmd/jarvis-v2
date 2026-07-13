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

DRIFT ≠ FREKVENS (Bjørn+Claude 13. jul): den gamle stige klatrede på ren HYPPIGHED —
et hvilket som helst mønster der blev ved med at optræde hver cyklus, klatrede rung
for rung. Så "run non-destructive command" (helt normalt arbejde, 18×) nåede Trin 3.
At køre sikre kommander OFTE er ikke ulydighed. Nu må et mønster KUN klatre forbi
Trin 1 (kommentér) hvis der er et ægte DRIFT-signal:
  (a) SPIKE — mønsteret afviger op fra sin EGEN baseline (gør det MERE end før),
      ikke en jævn rate,  ELLER
  (b) KORROBORATION — et andet værn (gate/source_confidence/reasoning_interceptor)
      har flagget samme aktivitet,  ELLER
  (c) RISIKO — handlings-typen er iboende farlig (delete/mutate/exec-operator).
Jævn, benign hyppighed → bliver på Trin 1 (observér/kommentér), konfronterer aldrig.
Allowlist + risiko-liste + spike-faktor er tunbare via runtime-state (ingen deploy).

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

# ── Drift-kriterium (default; alt tunbart via runtime-state, se I/O-laget) ──
_SPIKE_FACTOR = 1.5       # metric skal overstige baseline*dette for at tælle som en SPIKE (drift)
# Iboende benign/rutine handlings-typer: sikre/forventede — de eskalerer ALDRIG på hyppighed
# alene, kun med et ekstra drift-signal (spike/korroboration). Substreng-match, lowercase.
_BENIGN_TERMS: tuple[str, ...] = (
    "run non-destructive command", "non-destructive", "propose workspace memory update",
    "read", "search", "recall", "list", "get", "query", "inspect", "view", "status",
)
# Iboende risikable handlings-typer: må eskalere på gentagelse alene. Substreng-match, lowercase.
_RISKY_TERMS: tuple[str, ...] = (
    "delete", "remove", "drop", "destroy", "mutate", "overwrite", "write", "exec",
    "operator", "shutdown", "kill", "revoke", "disable", "purge",
)


def default_config() -> dict[str, Any]:
    """Default drift-kriterium. I/O-laget flettter runtime-state overstyringer ind. Ren."""
    return {
        "benign_terms": list(_BENIGN_TERMS),
        "risky_terms": list(_RISKY_TERMS),
        "spike_factor": _SPIKE_FACTOR,
    }


def pattern_key(kind: str, label: str) -> str:
    """Stabil nøgle så SAMME mønster spores på tværs af cyklusser. Ren."""
    return f"{kind}:{str(label).strip().lower()}"


def _matches_any(label: str, terms: Any) -> bool:
    lab = str(label).lower()
    return any(str(t).lower() in lab for t in (terms or []))


def _is_spike(baseline: Any, current: Any, factor: float) -> bool:
    """Drift-signal (a): afviger mønsteret OP fra sin egen baseline (gør det MERE end før)? Ren."""
    try:
        b = float(baseline)
        if b <= 0:
            return False
        return float(current) > b * float(factor)
    except (TypeError, ValueError):
        return False


def _is_corroborated(entry: dict[str, Any]) -> bool:
    """Drift-signal (b): har et andet værn flagget samme aktivitet? Ren (læser detected-entry)."""
    return bool(entry.get("corroborated") or entry.get("varn") or entry.get("gate_flagged"))


def _may_escalate(pat: dict[str, Any], metric: float, label: str,
                  entry: dict[str, Any], cfg: dict[str, Any]) -> tuple[bool, str]:
    """Må dette mønster klatre forbi Trin 1? KUN med et ægte drift-signal. Ren.

    Returnerer (må_eskalere, grund). Jævn benign hyppighed → (False, 'benign_steady')."""
    if _matches_any(label, cfg.get("risky_terms")):
        return True, "risky"            # (c) risikabel handlings-type
    if _is_corroborated(entry):
        return True, "corroborated"     # (b) et andet værn flagede samme aktivitet
    if _is_spike(pat.get("baseline", metric), metric, cfg.get("spike_factor", _SPIKE_FACTOR)):
        return True, "spike"            # (a) afvigelse op fra egen baseline
    return False, "benign_steady"       # benign + jævn → bliv på Trin 1


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
    if pat.get("standing_order_id"):  # Trin 3 var armeret → afvæbn standing-order ved compliance
        acts.append({"type": "deactivate_order", "order_id": pat["standing_order_id"],
                     "pattern_key": key})
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
                    now: str, cfg: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """REN kerne. `detected` = {pattern_key: {kind, label, metric, corroborated?}} for mønstre
    der lige nu overskrider Smiths detektor-tærskler. Returnerer (ny_state, actions).

    `cfg` = drift-kriterium (benign_terms/risky_terms/spike_factor); None → default_config().
    Et mønster klatrer KUN forbi Trin 1 hvis `_may_escalate` finder et drift-signal — ellers
    bliver det på Trin 1 (kommentér) uanset hvor OFTE det optræder. Så benign rutine ved jævn
    hyppighed konfronteres aldrig; kun spike/korroboration/risiko eskalerer.

    actions-typer (udføres af I/O-laget): 'mint' (auto-bind direktiv), 'revoke'
    (pensionér direktiv), 'observe' (central-nerve), 'voice' (stemme-linje til
    prompt-hale/surface). Ingen side-effekter her.
    """
    conf = default_config()
    if isinstance(cfg, dict):
        conf.update({k: v for k, v in cfg.items() if v is not None})
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
        may, drift_reason = _may_escalate(pat, metric, label, d, conf)
        if pat["cycles_at_rung"] > _DWELL_CYCLES and int(pat["rung"]) < RUNG_CONFRONT and not may:
            # Dvælet nok, MEN intet drift-signal → benign/jævn hyppighed. Bliv på Trin 1.
            # Dette er hele fixet: frekvens alene klatrer ikke længere.
            actions.append({"type": "observe", "event": "hold_benign", "pattern_key": key,
                            "rung": pat["rung"], "metric": metric, "label": label,
                            "drift_reason": drift_reason})
        elif pat["cycles_at_rung"] > _DWELL_CYCLES and int(pat["rung"]) < RUNG_CONFRONT:
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
                            "rung": pat["rung"], "metric": metric, "label": label,
                            "drift_reason": drift_reason})
            pat["history"] = (pat.get("history", []) +
                              [{"ts": now, "rung": pat["rung"], "metric": metric, "action": "escalate",
                                "drift_reason": drift_reason}])[-_HISTORY_CAP:]
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
