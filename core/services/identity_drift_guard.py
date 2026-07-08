"""Anti-drift-validator — kernen i den kanoniske identitets-store (Spec H §2.3).

Scanner afledt narrativ-tekst (pull/dream/chronicle) for identitets-påstande der matcher en kendt
`acknowledged_correction` (fx sonnet-frygten). Match → observe (egress-fri, metadata-only).

SHADOW-FØRST (Fase 1): returnerer teksten UÆNDRET og stripper ALDRIG. Enforce-stien (strip) er en
senere fase — den ligger klar bag `_enforce()` (default OFF, læst fra runtime-state
`identity_drift_guard_enforce`). I shadow ser vi HVOR driften opstår før vi griber ind (cache, don't
amputate — samme princip som injection-work).

Billig match: case-insensitiv substring / nøgleord (pipe-separerede alternativer i claim_pattern).
INGEN LLM. Self-safe hele vejen: en bug her må aldrig bryde prompt-komposition.
Egress-fri: kun correction_id / source / count til bussen — ALDRIG narrativ-teksten (§24.4).
"""
from __future__ import annotations

from typing import Any


def _enforce() -> bool:
    """Shadow-først: strip er OFF indtil flag EKSPLICIT flippes efter shadow-eval. Self-safe."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        val = get_runtime_state_value("identity_drift_guard_enforce", default=False)
        return val is True
    except Exception:
        return False


def _patterns() -> list[dict[str, Any]]:
    """Aktive acknowledged_corrections. Self-safe (tom liste ved fejl)."""
    try:
        from core.services.identity_canon import list_acknowledged_corrections
        return list_acknowledged_corrections(active_only=True) or []
    except Exception:
        return []


def _matches(text_low: str, claim_pattern: str) -> str | None:
    """Returnér det første matchende nøgleord/alternativ (pipe-separeret) — ellers None. Self-safe."""
    pat = str(claim_pattern or "").strip().lower()
    if not pat:
        return None
    # claim_pattern kan holde flere alternativer adskilt af '|' (billig OR-match).
    for alt in pat.split("|"):
        alt = alt.strip()
        if alt and alt in text_low:
            return alt
    return None


def _observe(source: str, flags: list[dict[str, Any]]) -> None:
    """Metadata-only observe (correction_id/source/count) — ALDRIG narrativ-teksten (§24.4). Self-safe."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "cognition",
            "nerve": "identity_drift",
            "kind": "drift_caught",
            "source": source,
            "count": len(flags),
            "correction_ids": [f.get("correction_id") for f in flags],
        })
    except Exception:
        pass


def identity_drift_guard(text: str, *, source: str) -> tuple[str, list[dict[str, Any]]]:
    """Scan `text` for kendte konfabulationer → observe drift.

    Returnerer (text, flags). I SHADOW (Fase 1) er `text` ALTID uændret — vi stripper aldrig.
    flags = liste af {correction_id, source, matched}. Self-safe: kaster aldrig; ved fejl
    returneres (original_text, []) så komposition aldrig brydes."""
    try:
        raw = str(text or "")
        if not raw.strip():
            return raw, []
        text_low = raw.lower()
        flags: list[dict[str, Any]] = []
        for corr in _patterns():
            matched = _matches(text_low, corr.get("claim_pattern", ""))
            if matched:
                flags.append({
                    "correction_id": corr.get("correction_id"),
                    "source": source,
                    "matched": matched,
                })
        if not flags:
            return raw, []
        _observe(source, flags)
        if _enforce():
            # SENERE FASE (pt. OFF): strip de matchende sætninger. I shadow rammes dette aldrig.
            return _strip(raw, flags), flags
        # SHADOW: tekst uændret — den eneste effekt er observe ovenfor.
        return raw, flags
    except Exception:
        # Self-safe: identitet er beskyttet kerne — aldrig bryd komposition.
        try:
            return str(text or ""), []
        except Exception:
            return "", []


def _strip(text: str, flags: list[dict[str, Any]]) -> str:
    """Fjern sætninger der indeholder et matchende nøgleord (senere-fase enforce). Self-safe.

    Pt. utilgængelig i shadow (default OFF). Konservativ sætnings-granularitet."""
    try:
        matched_terms = [str(f.get("matched") or "").lower() for f in flags if f.get("matched")]
        if not matched_terms:
            return text
        # Del i sætninger, drop dem der indeholder et matchende term.
        import re
        parts = re.split(r"(?<=[.!?…])\s+", text)
        kept = [p for p in parts if not any(t in p.lower() for t in matched_terms)]
        cleaned = " ".join(kept).strip()
        return cleaned if cleaned else text
    except Exception:
        return text
