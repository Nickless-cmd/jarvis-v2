"""Prompt-cluster (Den Intelligente Central) — Phase 1: live on/off + trace for de
prompt-sektioner der bygger Jarvis' visible prompt.

prompt_contract.py byggede ~73 sektioner blindt og skar støj via en HARDCODET blacklist
(_DIAGNOSTIC_NOISE_LABELS) — ændringer krævede kode + deploy, og INGEN kunne se HVORFOR en
sektion blev droppet. Dette modul giver prompten samme nervesystem som resten:
  - **Live on/off pr. sektion** uden genstart (central_switches scope="prompt_section").
  - **Trace** pr. build (central.observe → hvad kom med, hvad blev droppet og hvorfor).

BEVIDST AFGRÆNSET (Phase 1): de to risici Jarvis selv flagged — latency (per-sektion
decide()) og cache-brud (graderede sektioner der skifter størrelse) — er UNDGÅET. Vi
ændrer IKKE sektions-indhold og kalder IKKE decide() pr. sektion; vi gør kun include/drop-
beslutningen synlig + live-styrbar. Overrides loades i ÉN prefix-query pr. build, så
normaltilfældet (ingen override) koster nul ekstra latency og bevarer adfærd 1:1.

Gradering (YELLOW=kondensér), 8→1-konsolidering og budget-gradering er Phase 2+ — først
når Phase 1 producerer trace-data om hvilke sektioner der faktisk brænder tokens.
"""
from __future__ import annotations

import json
import time

_SCOPE = "prompt_section"
_KEY_PREFIX = "flag:central.switch.prompt_section."

# ── Sektion-policy (udskilt fra prompt_contract.py, Boy Scout 2026-06-23) ──
# Naturlig hjem her hos section_enabled: hvilke sektioner er diagnostik-STØJ
# der droppes by default (kan live-overstyres pr. sektion). Var build-lokale
# set-literaler i prompt_contract; samlet her så al sektion-policy bor ét sted.
DIAGNOSTIC_NOISE_LABELS: frozenset[str] = frozenset({
    "self-monitor warnings",
    "metacognition signals",
    "R2 gate telemetry",
    "decision adherence gate",
    "reasoning tier recommendation",
    "reasoning escalation recommendation",
    "context window degradation signal",
    "rule engine conclusions",
    "causal alerts",
    "causal narrative",
    "priors from your own data",
    # 2026-06-22 round 2 — cut per Jarvis' own review of his prompt:
    "conversation continuity (always-on)",  # "Ny samtale ×5" tells him nothing
    "loop-compliance self-check",          # heed-rate telemetry, not for him
    "cross-session arc",                    # "Ny samtale ×5" tells him nothing
    "session topics (always-on)",           # keyword counts ("NEJ ×14") ≠ awareness
    "forgetting nudge",                     # a rule, belongs in guidance not signal
    "meta-learning weekly retrospective teaser",  # unread memo, don't burn tokens
    "rules learned from arcs",              # repeated retrospective noise
    "markdown formatting",                  # already in guidance rules
    "no tool-result echo",                  # already in guidance rules
    # 2026-06-22 round 3 — Jarvis' second review:
    "curiosity-budget idle-window invitation",  # "5/5 tilbage" = mikrostyring; gør implicit
    "jarvis brain summary",  # merged into "brain facts" (one relevance-ranked section)
})

# Tail-anchored sektioner der ligeledes er støj (håndteres via _tail_add).
TAIL_NOISE_LABELS: frozenset[str] = frozenset({
    "causal patterns",          # "agentic_round_start → tool.completed (803×)"
    "pattern counterfactuals",  # same family of self-evident repetition
    "room entities",            # entity *counts*; real room-sense now in [INDRE LIV]
})


def load_overrides() -> dict[str, bool]:
    """Læs ALLE eksplicit satte prompt-sektion-switches i ÉN query (pr. build).

    Tom dict i normaltilfældet → nul per-sektion-opslag, default-adfærd uændret. Best-effort;
    enhver DB-fejl → tom dict (= ren default-adfærd, ingen brik)."""
    out: dict[str, bool] = {}
    try:
        from core.runtime.db import connect
        now = time.time()
        with connect() as conn:
            rows = conn.execute(
                "SELECT cache_key, value_json FROM shared_cache "
                "WHERE cache_key LIKE ? AND expires_at > ?",
                (_KEY_PREFIX + "%", now),
            ).fetchall()
        for key, value_json in rows:
            label = str(key)[len(_KEY_PREFIX):]
            try:
                v = json.loads(value_json)
            except Exception:
                continue
            if isinstance(v, dict) and "enabled" in v:
                out[label] = bool(v["enabled"])
    except Exception:
        pass
    return out


def section_enabled(label: str, *, blacklisted: bool, overrides: dict[str, bool]) -> bool:
    """Skal denne prompt-sektion med?

    Eksplicit override (Bjørn/MC via central_switches) vinder. Ellers default = paritet med
    den gamle hardcodede blacklist: blacklisted → OFF, alt andet → ON."""
    if label in overrides:
        return overrides[label]
    return not blacklisted


def observe_build(*, lane: str, included: int, dropped_disabled: list[str],
                  dropped_budget: list[str],
                  dropped_error: list[tuple[str, str]] | None = None) -> None:
    """Ét central.observe pr. prompt-build → trace af hvad der kom med + hvorfor noget
    blev droppet: switch-disabled vs budget-evicted vs FEJL (sektion-builder kastede).

    dropped_error er den tredje kanal (2026-06-23): før forsvandt en sektion der
    fejlede tavst (lokalt except: pass pr. sektion, så én dårlig sektion ikke dræber
    hele prompten) — INGEN kunne se HVILKEN sektion eller HVORFOR. Nu synlig i Centralen
    så vi ikke skal lede og teste i blinde, og adaptiv læring kan se hvilke builders der
    er ustabile over tid. Self-safe; kaster aldrig."""
    errs = list(dropped_error or [])
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "prompt", "nerve": "assembly", "lane": str(lane or ""),
            "included": int(included),
            "dropped_disabled": list(dropped_disabled)[:40],
            "dropped_budget": list(dropped_budget)[:40],
            "dropped_error": [{"section": s, "error": e} for s, e in errs[:40]],
            "error_count": len(errs),
        })
    except Exception:
        pass


def observe_section_error(label: str, error: object, *, lane: str = "") -> None:
    """En enkelt prompt-sektion-builder kastede → observe straks (synlig + pollbar).
    Kaldes fra prompt_contract's except-blokke. Self-safe; kaster ALDRIG ind i build."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "prompt", "nerve": "section_error", "lane": str(lane or ""),
            "section": str(label or ""),
            "error": f"{type(error).__name__}: {error}"[:200],
        })
    except Exception:
        pass


def set_section(label: str, enabled: bool) -> dict:
    """Slå en prompt-sektion ON/OFF LIVE (ingen genstart) — Bjørn/MC-kaldbar.
    Eksempel: set_section('R2 gate telemetry', True) gen-aktiverer en blacklistet sektion;
    set_section('brain facts', False) slukker en aktiv sektion. Gælder fra næste prompt-build."""
    from core.services import central_switches
    return central_switches.set_enabled(_SCOPE, str(label), bool(enabled))


def list_overrides() -> dict[str, bool]:
    """Read-only projektion af aktive overrides (til MC/debug)."""
    return load_overrides()
