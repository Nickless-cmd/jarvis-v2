"""Rule-engine conclusions — symbolic reasoning surfaced to the LLM.

Bygger bro mellem rule_engine (forward-chaining symbolsk inferens) og
visible-lane prompten. Engine producerer allerede skarpe conclusions
("strong appetite drives focus", "release marker fyret") — denne sektion
formaterer top-N og injecter dem som awareness-line.

Det er det første "neuro-symbolic" lag der faktisk når Jarvis. Han har
haft engine + 36 regler siden commit 8860301 — denne fil får output'et
ud af engine'en og ind i hans bevidsthed.

Design:
  - Læser conclusions fra evaluate_rules(snapshot) — best-effort
  - Top-5 sorteret (engine sorterer allerede på priority_delta + urgency)
  - Kompakt format: "[urgency:domain +Δ] suggestion (rule_name)"
  - Returnerer "" hvis engine fejler eller intet fyrer (ingen noise)
  - Cap'er per-line for at undgå prompt-bloat

Awareness-prioritet: 28 (mellem) — symbolsk reasoning er værd at tjekke,
men ikke kritisk identity. Dropper først hvis budget overflows.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

# Hvor mange conclusions vi viser. 5 er nok til at give Jarvis et bredt
# billede uden at fylde prompten. Engine returnerer allerede sorteret
# efter priority_delta DESC, urgency DESC.
_TOP_N = 5

# TTL-cache for signal-snapshot. list_all_surfaces() er dyr — primært
# fordi runtime_awareness-surface laver mutation-on-read (~10s pr. kald).
# Reglerne behøver ikke millisekund-friskhed på snapshots — 30s er fint.
# Perf-fix 2026-05-08: før dette kostede hver visible-tur ~10s i
# prompt-assembly fordi rule_conclusions trigger'ede full surface-scan.
_SURFACE_CACHE_TTL = 30.0
_surface_cache: dict | None = None
_surface_cache_at: float = 0.0

# Section-result cache. Even with signals cached, evaluate_rules(36 regler
# over full signal-stak) still takes ~7s per call. Symbolic conclusions
# don't need millisecond freshness either — visible-chat reads the
# pre-computed string, refresh happens once per minute.
# Perf-fix 2026-05-12: identified as the dominant awareness section
# (7-10s of the ~7.5s sync gap in prompt assembly).
_SECTION_CACHE_TTL = 180.0  # 3 min — typical active conversation turn gap
_section_cache: str | None = None
_section_cache_at: float = 0.0
_section_cache_lock = None  # initialized lazily; threading.Lock


def _cached_signals() -> dict:
    global _surface_cache, _surface_cache_at
    now = time.monotonic()
    if _surface_cache is not None and (now - _surface_cache_at) < _SURFACE_CACHE_TTL:
        return _surface_cache
    from core.services.signal_surface_router import list_all_surfaces
    _surface_cache = list_all_surfaces()
    _surface_cache_at = now
    return _surface_cache


def invalidate_section_cache() -> None:
    """Force next call to rebuild. Useful for tests + heartbeat-driven refresh."""
    global _section_cache, _section_cache_at
    _section_cache = None
    _section_cache_at = 0.0

# Per-suggestion cap så en lang regel ikke fylder hele sektionen.
_SUGGESTION_MAX_CHARS = 140


def _format_conclusion(c) -> str:
    """One line per conclusion: '[urgency:domain ±Δ] suggestion (rule)'."""
    urgency = (c.urgency or "low").upper()[:4]
    domain = c.target_domain or "?"
    delta = c.priority_delta
    sign = "+" if delta >= 0 else ""
    suggestion = (c.suggestion or "").strip()
    if len(suggestion) > _SUGGESTION_MAX_CHARS:
        suggestion = suggestion[: _SUGGESTION_MAX_CHARS - 1].rstrip() + "…"
    rule_name = c.rule_name or "?"
    return f"  [{urgency:>4}:{domain:<10} {sign}{delta:>3}] {suggestion} ({rule_name})"


def _build_section_uncached() -> str:
    """Compute the section fresh. Slow path — should only run via cache miss."""
    try:
        from core.services.rule_engine import evaluate_rules
    except Exception as exc:
        logger.debug("rule_conclusions: import failed: %s", exc)
        return ""

    try:
        signals = _cached_signals()
        result = evaluate_rules(signals)
    except Exception as exc:
        logger.debug("rule_conclusions: evaluate failed: %s", exc)
        return ""

    if not result.conclusions:
        return ""

    top = result.conclusions[:_TOP_N]
    # Skip the section entirely if all top conclusions are no-op deltas.
    if all(abs(c.priority_delta) < 5 for c in top):
        return ""

    lines = ["🧠 Symbolsk ræsonnering — top-5 regel-konklusioner lige nu:"]
    for c in top:
        lines.append(_format_conclusion(c))
    lines.append(
        "(Disse er forslag fra forward-chaining over signal-stakken. "
        "De er ikke ordrer — du beslutter."
    )
    return "\n".join(lines)


def rule_conclusions_section() -> str:
    """Build the rule-engine conclusions section for prompt injection.

    Cached for _SECTION_CACHE_TTL (60s) so it doesn't dominate the
    synchronous prompt-assembly path. Returns the previous-computed string
    on cache hit; rebuilds on miss. Thread-safe.

    Cache invalidates automatically every 60s, or explicitly via
    invalidate_section_cache().
    """
    global _section_cache, _section_cache_at, _section_cache_lock
    if _section_cache_lock is None:
        import threading
        _section_cache_lock = threading.Lock()

    now = time.monotonic()
    # Fast path: cache hit without lock contention
    if _section_cache is not None and (now - _section_cache_at) < _SECTION_CACHE_TTL:
        return _section_cache

    # Slow path: hold lock to prevent multiple concurrent rebuilds
    with _section_cache_lock:
        # Re-check after acquiring lock (another thread may have rebuilt)
        now = time.monotonic()
        if _section_cache is not None and (now - _section_cache_at) < _SECTION_CACHE_TTL:
            return _section_cache
        _section_cache = _build_section_uncached()
        _section_cache_at = now
        return _section_cache
