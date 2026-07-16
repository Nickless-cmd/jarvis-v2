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

# Sunde statuser der IKKE skal re-probes. ALT andet uden aktiv cooldown regnes som "fast"
# og re-probes — regelen er ikke en hvidliste af fejl-statuser (den vil altid være ufuldstaendig:
# request-failed/auth-rejected/http-410/circuit-open/... kan alle saette sig fast), men det simple
# invariant: "ikke sund + ingen aktiv cooldown = fast". Selv rate-limited/quota-exhausted kan
# ende fast hvis cooldownen udloeb uden at status blev nulstillet (provideren blev aldrig gen-kaldt).
_HEALTHY_STATUSES = frozenset({"ready", "ok"})
_PROBE_MESSAGE = "ping"


def _stale_targets(limit: int) -> list[tuple[str, str]]:
    """(provider, model) der skal re-probes. To kilder:

    1. State-row fast: KONFIGURERET provider der IKKE er sund og IKKE har aktiv cooldown
       → heler aldrig selv (router skipper → gen-kaldes aldrig → status fast).
    2. Zero-row (16.jul, HF-fælde): konfigureret+routbar+gratis provider UDEN nogen
       state-row overhovedet. Usynlig for selektoren (0 ready models) OG for kilde 1
       (loopet nedenfor itererer kun EKSISTERENDE rows). Resultat: aldrig valgt → aldrig
       probet → aldrig en row → stale for evigt. Vi probe dens static_models ind.

    Kun modeller stadig i static_models (drop pensionerede)."""
    out: list[tuple[str, str]] = []
    try:
        from core.runtime.db_cheap_provider import list_cheap_provider_runtime_states
        from core.services.cheap_provider_runtime_adapters import (
            CHEAP_PROVIDER_DEFAULTS,
            is_routable_provider,
            provider_cost_class,
            provider_runtime_defaults,
        )
        now = datetime.now(UTC)
        seen: set[tuple[str, str]] = set()
        # --- Kilde 1: eksisterende state-rows der er fast ---
        for st in list_cheap_provider_runtime_states(lane="cheap"):
            provider = str(st.get("provider") or "")
            model = str(st.get("model") or "")
            seen.add((provider, model))
            if str(st.get("status") or "ready") in _HEALTHY_STATUSES:
                continue
            cd = str(st.get("cooldown_until") or "").strip()
            if cd:  # aktiv cooldown haandterer den allerede → spring over
                try:
                    if datetime.fromisoformat(cd) > now:
                        continue
                except ValueError:
                    pass
            defaults = provider_runtime_defaults(provider)
            if not defaults:  # ikke laengere konfigureret
                continue
            static = defaults.get("static_models") or []
            if static and model and model not in static:  # pensioneret model
                continue
            out.append((provider, model))
            if len(out) >= limit:
                return out
        # --- Kilde 2: zero-row cheap-kandidater (gratis+routbar, aldrig probet ind) ---
        for provider, cfg in CHEAP_PROVIDER_DEFAULTS.items():
            if provider_cost_class(provider) != "free" or not is_routable_provider(provider):
                continue
            for model in (cfg.get("static_models") or []):
                if (provider, model) in seen:
                    continue
                out.append((provider, model))
                seen.add((provider, model))
                if len(out) >= limit:
                    return out
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
