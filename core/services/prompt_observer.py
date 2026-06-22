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
                  dropped_budget: list[str]) -> None:
    """Ét central.observe pr. prompt-build → trace af hvad der kom med + hvorfor noget
    blev droppet (switch-disabled vs budget-evicted). Self-safe; kaster aldrig."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "prompt", "nerve": "assembly", "lane": str(lane or ""),
            "included": int(included),
            "dropped_disabled": list(dropped_disabled)[:40],
            "dropped_budget": list(dropped_budget)[:40],
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
