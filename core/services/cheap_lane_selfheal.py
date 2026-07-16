"""cheap_lane_selfheal — cheap-lane maa ALDRIG stale eller doe (Bjoern 16.jul).

En provider kan saette sig fast i en TERMINAL status (unsupported-provider, provider-error,
auth-not-ready, unavailable, missing-provider, empty-response) UDEN en cooldown. Routeren
nedranker/springer den saa over → den gen-kaldes aldrig via den state-opdaterende sti → status
heler ALDRIG, selv efter at det underliggende problem (fx en config-fix) er loest. Klassisk
selv-fastlaast doedvande: copilot-premium ramte det praecist 15-16.jul (config gjort openai-
kompatibel, men state sad fast paa 'unsupported-provider').

cooldown/rpm/daily-baserede statuser (rate-limited, quota-exhausted, ...) er ALLEREDE selv-
helende: cooldown'en udloeber og providereren bliver valgbar igen. Dem roerer vi IKKE. Denne
self-heal re-prober KUN de terminale statuser: et minimalt kald pr. fastlaast (provider, model).
Succes → status=ready + ryddet error/cooldown/quota. Fejl → frisk status + cooldown fra fejlen,
saa cooldown-stien overtager og providereren ikke re-probes i tide (self-throttling).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

# Statuser der IKKE auto-heler via cooldown → skal re-probes for at komme tilbage i poolen.
_TERMINAL_STATUSES = frozenset({
    "unsupported-provider", "provider-error", "provider-blocked",
    "model-not-found", "model-unavailable", "unavailable",
    "missing-provider", "auth-not-ready", "empty-response",
})
_PROBE_MESSAGE = "ping"


def _stale_targets(limit: int) -> list[tuple[str, str]]:
    """(provider, model) for KONFIGUREREDE providere fanget i en terminal status uden aktiv
    cooldown. Kun modeller der stadig er i providerens static_models (drop pensionerede)."""
    out: list[tuple[str, str]] = []
    try:
        from core.runtime.db_cheap_provider import list_cheap_provider_runtime_states
        from core.services.cheap_provider_runtime_adapters import provider_runtime_defaults
        now = datetime.now(UTC)
        for st in list_cheap_provider_runtime_states(lane="cheap"):
            if str(st.get("status") or "") not in _TERMINAL_STATUSES:
                continue
            cd = str(st.get("cooldown_until") or "").strip()
            if cd:  # aktiv cooldown haandterer den allerede → spring over
                try:
                    if datetime.fromisoformat(cd) > now:
                        continue
                except ValueError:
                    pass
            provider = str(st.get("provider") or "")
            model = str(st.get("model") or "")
            defaults = provider_runtime_defaults(provider)
            if not defaults:  # ikke laengere konfigureret
                continue
            static = defaults.get("static_models") or []
            if static and model and model not in static:  # pensioneret model
                continue
            out.append((provider, model))
            if len(out) >= limit:
                break
    except Exception:
        logger.debug("cheap_lane_selfheal: _stale_targets fejlede", exc_info=True)
    return out


def reprobe(provider: str, model: str) -> bool:
    """Minimalt sundheds-probe. Healer state ved succes, saetter frisk cooldown ved fejl.
    Self-safe → False ved fejl."""
    from core.runtime.db_cheap_provider import upsert_cheap_provider_runtime_state as _up
    from core.services.cheap_provider_runtime_adapters import (
        CheapProviderError,
        _default_failure_cooldown_seconds,
        _execute_provider_chat,
        provider_runtime_defaults,
    )
    base_url = str(provider_runtime_defaults(provider).get("base_url") or "")
    now = datetime.now(UTC)
    try:
        _execute_provider_chat(provider=provider, model=model, auth_profile="",
                               base_url=base_url, message=_PROBE_MESSAGE)
        _up(provider=provider, model=model, lane="cheap", status="ready",
            auth_ready=True, quota_limited=False, cooldown_until=None,
            last_error_code="", last_error_message="", last_success_at=now.isoformat())
        return True
    except CheapProviderError as exc:
        cd = (now + timedelta(seconds=_default_failure_cooldown_seconds(str(exc.code)))).isoformat()
        _up(provider=provider, model=model, lane="cheap", status=str(exc.code),
            last_error_code=str(exc.code), last_error_message=str(exc.message)[:200],
            cooldown_until=cd, last_failure_at=now.isoformat())
        return False
    except Exception as exc:
        _up(provider=provider, model=model, lane="cheap", status="provider-error",
            last_error_code="probe-error", last_error_message=str(exc)[:200],
            cooldown_until=(now + timedelta(seconds=900)).isoformat(),
            last_failure_at=now.isoformat())
        return False


def run_selfheal(*, max_probes: int = 6) -> dict:
    """Re-probe op til max_probes fastlaaste providere. Returnér {healed, still_down}."""
    healed: list[str] = []
    still_down: list[str] = []
    for provider, model in _stale_targets(max_probes):
        (healed if reprobe(provider, model) else still_down).append(f"{provider}/{model}")
    out = {"status": "ok", "healed": healed, "still_down": still_down,
           "probed": len(healed) + len(still_down)}
    if healed:
        try:
            from core.services.central_core import central
            central().observe({"cluster": "infra", "nerve": "cheap_lane_selfheal",
                               "healed": healed, "detail": f"{len(healed)} provider(e) genoplivet"})
        except Exception:
            pass
    return out
