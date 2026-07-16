"""Non-visible (autonomous) LLM fallback chain.

Autonome (ikke-synlige) runs skal forsøge lokal ollama først, og hvis den
fejler (quota/timeout/5xx) falde igennem til den GRATIS cheap-lane pool, og
til sidst til et floor — så den autonome loop aldrig knækker.

Den BETALTE deepseek-API må ALDRIG bruges her (den er kun til den synlige lane).
Synlige / bruger-tilstedeværende runs må ALDRIG bruge denne helper.
"""

from __future__ import annotations

from typing import Any, Callable

from core.runtime.db_core import get_runtime_state_bool
from core.services import non_visible_rate_cap
from core.services.cheap_lane_floor import attempt_floor
from core.services.cheap_provider_runtime_selection import execute_cheap_lane_via_pool

_FALLBACK_FLAG = "non_visible_ollama_fallback_enabled"
_RATE_CAP_FLAG = "non_visible_rate_cap_enabled"


def _fallback_enabled() -> bool:
    """Læs feature-flag; default False. Monkeypatchbar i tests."""
    return get_runtime_state_bool(_FALLBACK_FLAG, False)


def _rate_cap_enabled() -> bool:
    """Læs rate-cap feature-flag; default False. Monkeypatchbar i tests."""
    return get_runtime_state_bool(_RATE_CAP_FLAG, False)


def _observe_central(payload: dict) -> None:
    """Task 15: let observabilitet på ON-stien → Centralens system/cheap_pool.
    Self-safe — må ALDRIG bryde den autonome fallback-routing."""
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "cheap_pool", **payload})
    except Exception:
        pass


def run_non_visible_with_fallback(
    *,
    message: str,
    primary_call: Callable[[], dict[str, Any]],
    run_is_autonomous: bool,
    task_kind: str = "default",
) -> dict[str, Any]:
    """Prøv primary_call() (ollama). Ved fejl: fald til den gratis cheap-lane
    pool, derefter floor. ALDRIG betalt deepseek. ALDRIG for synlige runs.

    max_depth=1: helper kalder ALDRIG sig selv rekursivt.
    """
    # 1) Hard leak-guard: må aldrig ramme den synlige lane.
    assert run_is_autonomous, "non_visible fallback må ALDRIG ramme visible lane"

    # 2) Prøv primær (ollama).
    try:
        return primary_call()
    except Exception:
        # 3) Uden flag: uændret adfærd — re-raise original exception.
        if not _fallback_enabled():
            raise

        # 3a) Hårdt globalt loft FORAN poolen. Uafhængigt af slot-health, så
        #     en runaway ikke kan forstærkes gennem multi-profile + fallback.
        if _rate_cap_enabled() and not non_visible_rate_cap.allow():
            _observe_central({"event": "rate_capped", "lane": "autonomous"})
            return attempt_floor(
                message=message,
                lane="autonomous",
                reason="rate-capped",
            )

        # 3b) Med flag: fald til den gratis pool. Håndtér BEGGE exit-shapes.
        _observe_central({"event": "non_visible_fallback_fired", "lane": "autonomous"})
        try:
            result = execute_cheap_lane_via_pool(
                message=message,
                task_kind=task_kind,
                lane="autonomous",
            )
        except Exception:
            # Pool rejste (RuntimeError m.fl.) — sidste udvej: floor.
            return attempt_floor(
                message=message,
                lane="autonomous",
                reason="pool-exhausted",
            )

        # 5) Betalt-deepseek-guard (defense in depth). Poolen ekskluderer
        #    allerede betalt, men vi asserter det her.
        if isinstance(result, dict) and result.get("provider") == "deepseek":
            return attempt_floor(
                message=message,
                lane="autonomous",
                reason="paid-blocked",
            )

        return result
