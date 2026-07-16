"""Global leaky-bucket rate cap FORAN den non-visible cheap-lane pool.

Multi-profile + fallback øger antallet af gratis-provider-kald den autonome
(ikke-synlige) lane kan lave. Denne modul er et HÅRDT globalt loft — uafhængigt
af enhver enkelt slots health — så en runaway ikke kan forstærkes gennem poolen.

To ruller:
  * request-vindue: max REQ_PER_MIN kald pr. rullende 60s.
  * token-budget:   max TOKENS_PER_DAY tokens pr. rullende 24t.

`allow(tokens)` bruger 1 request + `tokens` tokens hvis BEGGE ruller har plads;
ellers False. Rejser ALDRIG. Klokken er injicerbar via `_now()` for tests.

Council finding #5.
"""

from __future__ import annotations

import time

REQ_PER_MIN = 120           # requests per rolling minute
TOKENS_PER_DAY = 5_000_000  # token budget per rolling day

_WINDOW_SEC = 60.0
_DAY_SEC = 86_400.0

# Modul-global tilstand (nulstilles af reset()).
_req_count = 0
_req_window_start = 0.0
_tok_used = 0
_tok_day_start = 0.0


def _now() -> float:
    """Wall-clock i sekunder. Monkeypatchbar i tests."""
    return time.time()


def reset() -> None:
    """Nulstil alle buckets (til tests + boot)."""
    global _req_count, _req_window_start, _tok_used, _tok_day_start
    now = _now()
    _req_count = 0
    _req_window_start = now
    _tok_used = 0
    _tok_day_start = now


def allow(tokens: int = 0) -> bool:
    """Forbrug 1 request + `tokens` tokens hvis begge buckets har plads; ellers
    False. Refill lineært efter forløbet tid. Uafhængig af slot-health. Rejser
    aldrig.
    """
    global _req_count, _req_window_start, _tok_used, _tok_day_start
    try:
        now = _now()

        # Rullende 60s request-vindue: nulstil tælleren når vinduet er udløbet.
        if now - _req_window_start >= _WINDOW_SEC:
            _req_count = 0
            _req_window_start = now

        # Rullende 24t token-vindue: nulstil forbruget når dagen er udløbet.
        if now - _tok_day_start >= _DAY_SEC:
            _tok_used = 0
            _tok_day_start = now

        want_tokens = tokens if tokens > 0 else 0

        # Tjek begge lofter FØR forbrug — enten begge går igennem eller ingen.
        if _req_count + 1 > REQ_PER_MIN:
            return False
        if _tok_used + want_tokens > TOKENS_PER_DAY:
            return False

        _req_count += 1
        _tok_used += want_tokens
        return True
    except Exception:
        # Aldrig knæk den autonome loop pga. en cap-fejl.
        return False
