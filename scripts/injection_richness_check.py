"""Rigdoms-gate for injektions-migration (spec 2026-07-05 §7).

richness_ok: er den cachede tekst lige-så-rig-eller-rigere end den direkte build?
Heuristik: cached må ikke tabe mere end 20% af den direkte builds ikke-tomme linjer.
Bruges som fase-gate — fladere output = rollback-signal.
"""
from __future__ import annotations


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]


def richness_ok(*, direct: str, cached: str) -> bool:
    d = _lines(direct)
    if not d:
        return True
    c = _lines(cached)
    return len(c) >= 0.8 * len(d)
