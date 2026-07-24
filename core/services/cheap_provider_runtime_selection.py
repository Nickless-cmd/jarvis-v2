from __future__ import annotations

# ── cheap_provider_runtime._selection ────────────────────────────────────────
# Cheap-lane selection / routing / quota / adaptive-priority / failover +
# per-provider runtime-state bookkeeping, extracted from cheap_provider_runtime.py
# (Boy-Scout split, behavior-preserving). Provider dispatch/adapter code lives in
# _adapters.py. The public module `cheap_provider_runtime` re-exports every symbol
# here for import stability and monkeypatch seams.
#
# FACADE SEAM: tests patch cheap_provider_runtime._execute_provider_chat /
# provider_runtime_defaults / record_cheap_provider_invocation and then call a
# selection entry point (smoke_cheap_lane / execute_cheap_lane_via_pool /
# execute_public_safe_cheap_lane). Those three names are resolved via the public
# facade module at call time (through the thin shims below) so the patch on the
# facade reaches this module. Everything else is imported directly.
import json
import itertools as _itertools
from datetime import UTC, datetime, timedelta

from core.costing.ledger import record_cost
from core.eventbus.bus import event_bus
from core.runtime.db import (
    count_cheap_provider_invocations,
    get_cheap_provider_runtime_state,
    list_cheap_provider_runtime_states,
    upsert_cheap_provider_runtime_state,
)
from core.runtime.provider_router import load_provider_router_registry

from core.services.cheap_provider_runtime_adapters import (
    CHEAP_PROVIDER_DEFAULTS,
    CheapProviderError,
    _default_failure_cooldown_seconds,
    _estimate_tokens,
    _execute_public_safe_local_ollama,
    provider_auth_ready,
)


def _facade():
    # Resolve the public facade module lazily so tests that patch
    # cheap_provider_runtime.<name> take effect here (monkeypatch seam).
    import core.services.cheap_provider_runtime as _f
    return _f


def _execute_provider_chat(*args, **kwargs):
    return _facade()._execute_provider_chat(*args, **kwargs)


def provider_runtime_defaults(*args, **kwargs):
    return _facade().provider_runtime_defaults(*args, **kwargs)


def record_cheap_provider_invocation(*args, **kwargs):
    return _facade().record_cheap_provider_invocation(*args, **kwargs)


_QUOTA_RESET_HOURS = 24

# Hot-path TTL caches (2026-05-13). Profile under load showed
# _candidate_adaptive_snapshot + _candidate_quota_snapshot dominating
# CPU due to 30-45 DB queries per surface build, called repeatedly
# by MC polling + awareness builders. These caches keep semantics
# (still re-reads recent state) but eliminate the per-request stampede.
#
# 2026-05-15: migrated from per-process dicts to shared_cache (SQLite-
# backed, cross-worker). Was hit rate ~25% with 4 uvicorn workers —
# each worker had its own dict. Now all 4 workers see the same cache,
# pushing hit rate toward 95%+ for the request-stampede pattern.
_STATUS_SURFACE_TTL_SECONDS = 5.0
_QUOTA_SNAPSHOT_TTL_SECONDS = 2.0
_STATUS_SURFACE_CACHE_KEY = "cheap_lane:status_surface"
_QUOTA_SNAPSHOT_PREFIX = "cheap_lane:quota:"


def cheap_lane_status_surface() -> dict[str, object]:
    # TTL cache (5s) via shared_cache: MC polls this + awareness builders
    # include it. Cross-worker visibility means 4 workers share the same
    # cached surface — was hit rate ~25% with per-process dict, now ~95%.
    from core.services import shared_cache as _sc
    _cached = _sc.get(_STATUS_SURFACE_CACHE_KEY)
    if isinstance(_cached, dict):
        return _cached
    candidates = _configured_cheap_candidates(include_public_proxy=True)
    states = {
        (str(item["provider"]), str(item["model"])): item
        for item in list_cheap_provider_runtime_states(lane="cheap")
    }
    selected = select_cheap_lane_target()
    items: list[dict[str, object]] = []
    for candidate in candidates:
        provider = str(candidate["provider"])
        model = str(candidate["model"])
        state = states.get((provider, model), {})
        quota = _candidate_quota_snapshot(candidate)
        adaptive = _candidate_adaptive_snapshot(candidate, state=state)
        items.append(
            {
                "provider": provider,
                "model": model,
                "auth_profile": str(candidate.get("auth_profile") or ""),
                "priority": int(candidate.get("priority") or 9999),
                "effective_priority": adaptive["effective_priority"],
                "adaptive_penalty": adaptive["adaptive_penalty"],
                "status": str(state.get("status") or quota["status"]),
                "auth_ready": bool(candidate.get("credentials_ready")),
                "quota": quota,
                "cooldown_until": state.get("cooldown_until"),
                "last_error_code": str(state.get("last_error_code") or ""),
                "adaptive": adaptive,
                "selected": (
                    provider == str(selected.get("provider") or "")
                    and model == str(selected.get("model") or "")
                ),
            }
        )
    surface = {
        "active": bool(items),
        "selected_target": selected,
        "provider_count": len(items),
        "providers": items,
    }
    _sc.set(_STATUS_SURFACE_CACHE_KEY, surface, ttl_seconds=_STATUS_SURFACE_TTL_SECONDS)
    return surface


def invalidate_cheap_lane_status_cache() -> None:
    """Force-clear the status-surface and quota caches.

    Call after recording a success/failure if you need MC to reflect
    the change immediately (rare — TTL handles it in <=5s normally).
    Cross-worker invalidation: clears the shared_cache entries so all
    workers see the cleared state on next read.
    """
    from core.services import shared_cache as _sc
    _sc.delete(_STATUS_SURFACE_CACHE_KEY)
    _sc.invalidate_prefix(_QUOTA_SNAPSHOT_PREFIX)


def test_provider_target(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str = "",
    message: str = "Return exactly: cheap-lane-ok",
) -> dict[str, object]:
    started_at = datetime.now(UTC)
    result = _execute_provider_chat(
        provider=provider,
        model=model,
        auth_profile=auth_profile,
        base_url=base_url,
        message=message,
    )
    latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
    return {
        "provider": provider,
        "model": model,
        "auth_profile": auth_profile,
        "latency_ms": latency_ms,
        "text": str(result.get("text") or ""),
        "output_tokens": int(result.get("output_tokens") or 0),
        "cost_usd": float(result.get("cost_usd") or 0.0),
    }


def smoke_cheap_lane(
    *,
    message: str = "Return exactly: cheap-lane-ok",
) -> dict[str, object]:
    candidates = _configured_cheap_candidates(include_public_proxy=False)
    results: list[dict[str, object]] = []
    success_count = 0
    failure_count = 0
    for candidate in candidates:
        provider = str(candidate.get("provider") or "")
        model = str(candidate.get("model") or "")
        auth_profile = str(candidate.get("auth_profile") or "")
        if not bool(candidate.get("credentials_ready")):
            results.append(
                {
                    "provider": provider,
                    "model": model,
                    "auth_profile": auth_profile,
                    "status": "auth-not-ready",
                    "ok": False,
                }
            )
            failure_count += 1
            continue
        started_at = datetime.now(UTC)
        input_tokens = _estimate_tokens(message)
        try:
            probe = test_provider_target(
                provider=provider,
                model=model,
                auth_profile=auth_profile,
                base_url=str(candidate.get("base_url") or ""),
                message=message,
            )
        except CheapProviderError as exc:
            latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
            _register_provider_failure(
                provider=provider,
                model=model,
                auth_profile=auth_profile,
                error=exc,
                smoke_test=True,
            )
            results.append(
                {
                    "provider": provider,
                    "model": model,
                    "auth_profile": auth_profile,
                    "status": exc.code,
                    "ok": False,
                    "latency_ms": latency_ms,
                    "status_code": exc.status_code,
                    "retry_after_seconds": exc.retry_after_seconds,
                    "message": exc.message,
                }
            )
            failure_count += 1
            continue

        output_tokens = int(probe.get("output_tokens") or 0)
        latency_ms = int(probe.get("latency_ms") or 0)
        quality_score = _smoke_quality_score(
            expected="cheap-lane-ok",
            actual=str(probe.get("text") or ""),
        )
        record_cheap_provider_invocation(
            provider=provider,
            model=model,
            auth_profile=auth_profile,
            status="smoke-ok",
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=float(probe.get("cost_usd") or 0.0),
        )
        _record_provider_success(
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            quality_score=quality_score,
            smoke_test=True,
        )
        results.append(
            {
                "status": "ready",
                "ok": True,
                "quality_score": quality_score,
                **probe,
            }
        )
        success_count += 1

    return {
        "ok": failure_count == 0,
        "lane": "cheap",
        "provider_count": len(results),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results,
    }


# ── Task-kind tiering for cheap-lane routing ─────────────────────────────
# The cheap lane has many consumers — relevance scoring, memory selection,
# inner voice, dreams, daemon_llm calls, graph extraction, etc. Without
# tiering, all of them queue behind Groq/NVIDIA/Gemini and burn the best
# free quotas on background work. By the time the visible lane wants real
# inference, the good providers are rate-limited.
#
# task_kind="background"  inner-layer noise. PREFERS public proxies
#                         (OllamaFreeAPI, Arko, OpenCode) so paid quotas
#                         are saved for meaningful work. Falls through to
#                         paid only if every public provider is blocked.
# task_kind="default"     historical behaviour: paid first, public as
#                         fallback. Use this when the call shape isn't
#                         strongly background but still doesn't deserve
#                         visible-lane treatment.
# task_kind="important"   paid only, no public fallback. For council
#                         deliberation, agent reasoning, anywhere quality
#                         matters and we'd rather fail than degrade.

# Anonymous / keyless free aggregators are "public proxies": last-resort,
# backup-tier providers whose free routes are shared, unauthenticated and (per
# their own provider docstrings) may log prompts to training. They must never
# outrank credentialed free providers on default work, and must be dropped for
# "important" work. kilo/ovhcloud/pollinations were added (2026-07-14/15) as
# auth_kind="none" backups but were missing from this list, so they leaked into
# default selection ahead of Groq/Mistral and were never excluded from the
# important tier.
_PUBLIC_PROXY_PROVIDERS = (
    "ollamafreeapi",
    "arko",
    "opencode",
    "kilo",
    "ovhcloud",
    "pollinations",
)

# Round-robin counter so consecutive background calls spread across the
# public-proxy providers rather than draining one. Module-level + thread-
# safe enough for single-process Jarvis runtime; if we ever scale out,
# replace with a DB-backed counter or a hash on request_id.
import itertools as _itertools
_BACKGROUND_ROTATOR = _itertools.cycle(_PUBLIC_PROXY_PROVIDERS)


def _is_public_proxy(provider: str) -> bool:
    return str(provider or "").strip().lower() in _PUBLIC_PROXY_PROVIDERS


def _central_route_shadow() -> bool:
    """Task 9: kør central_route-sammenligning (default OFF → nul overhead)."""
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool("central_route_shadow", False)
    except Exception:
        return False


def _central_route_live() -> bool:
    """Task 9: brug central_route's pick i stedet for den gamle sti (default OFF)."""
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool("central_route_live", False)
    except Exception:
        return False


def _flag_multiprofile() -> bool:
    """Task 6: yield én kandidat pr. (provider, klar auth-profil) i stedet for kun
    registry-entry'ens profil. Default OFF → uændret adfærd (én kandidat pr. model
    med entry'ens auth_profile)."""
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool("cheap_pool_multiprofile_enabled", False)
    except Exception:
        return False


def _flag_profile_roundrobin() -> bool:
    """A (2026-07-24): when multiprofile is on AND a provider has >1 ready auth
    profile (e.g. default + account2), rotate WHICH profile is emitted first per
    call so load splits across the accounts instead of always draining `default`
    (strict-priority-first means the always-first profile wins every call — account2
    then only ever serves as failover and is never actually used). Default OFF →
    byte-identical strict-priority behaviour; flip True = live round-robin, flip
    False = instant rollback."""
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool("cheap_pool_profile_roundrobin_enabled", False)
    except Exception:
        return False


# provider -> next rotation index (module-level, advances once per provider per call).
_PROFILE_RR: dict[str, int] = {}


def _roundrobin_profiles(provider: str, profiles: list[str]) -> list[str]:
    """Rotate ``profiles`` by a per-provider counter so the preferred (first-emitted)
    profile advances each call. len<=1 → unchanged. Deterministic within a call,
    advances across calls → even split over default/account2 for the winning
    provider. Order within the rotation is preserved (stable)."""
    if len(profiles) <= 1:
        return profiles
    i = _PROFILE_RR.get(provider, 0) % len(profiles)
    _PROFILE_RR[provider] = i + 1
    return profiles[i:] + profiles[:i]


def _resolve_proxy(egress: str, endpoints: dict | None = None) -> str | None:
    """Task 8b: map an egress ('home'|'vpn'|'he6') to its proxy endpoint URL.

    home (or falsy) -> None (no proxy, home IP). A non-home egress with no
    configured endpoint is a HARD leak guard: we refuse rather than silently
    fall back to the home IP (that would correlate account2 with default and
    re-introduce the multi-account ban risk this whole routing exists to avoid).
    """
    if not egress or egress == "home":
        return None
    if endpoints is None:
        from core.services.egress_routing import proxy_endpoints
        endpoints = proxy_endpoints()
    ep = endpoints.get(egress)
    if not ep:
        raise RuntimeError(
            f"egress {egress!r} har ingen proxy-endpoint — "
            "nægter at sende account2 over hjemme-IP"
        )
    return ep


def _record_route_divergence(old: dict, new: dict) -> None:
    """Shadow-sammenligning: log/observe når central_route ville vælge noget andet
    end den gamle sti. Data til at beslutte hvornår vi flipper til live."""
    try:
        import logging
        old_p = (str(old.get("provider") or ""), str(old.get("model") or ""))
        new_p = (str(new.get("provider") or ""), str(new.get("model") or ""))
        if old_p != new_p:
            logging.getLogger(__name__).info(
                "central_route shadow-divergens: gammel=%s ny=%s", old_p, new_p)
            from core.services.central_core import central
            central().observe({"cluster": "system", "nerve": "route_shadow",
                               "old_provider": old_p[0], "new_provider": new_p[0]})
    except Exception:
        pass


def _maybe_shadow_compare(old_target: dict) -> None:
    """Shadow-hook før select returnerer. OFF → no-op, byte-identisk."""
    if not _central_route_shadow():
        return
    try:
        from core.services import central_route
        new = central_route.route(lane="cheap")
        _record_route_divergence(old_target, new)
    except Exception:
        pass


def _maybe_central_route_live(
    old_target: dict,
    candidates: list[dict[str, object]],
    kind: str,
    skip_providers: frozenset[str],
) -> dict[str, object]:
    """Task 9 live: når central_route_live er ON henter selection sit pick fra det
    Central-ejede beslutnings-punkt (så BÅDE balancer og selection deler ét beslutnings-
    punkt). OFF → returnér old_target uændret (byte-identisk). Aldrig-tør bevaret: hvis
    routen giver floor eller en (provider, model) vi ikke kan mappe til en sund kandidat,
    beholdes old_target (og execute_cheap_lane_via_pool har stadig floor under sig)."""
    if not _central_route_live():
        return old_target
    try:
        from core.services import central_route
        r = central_route.route(lane="cheap", task={"kind": kind}, exclude=skip_providers)
        if r.get("is_floor"):
            return old_target
        p, m = str(r.get("provider") or ""), str(r.get("model") or "")
        for c in candidates:
            if str(c.get("provider") or "") != p or str(c.get("model") or "") != m:
                continue
            if not bool(c.get("credentials_ready")):
                return old_target
            if _candidate_quota_snapshot(c)["blocked"]:
                return old_target
            adaptive = _candidate_adaptive_snapshot(c)
            return {
                **c,
                "effective_priority": adaptive["effective_priority"],
                "adaptive_penalty": adaptive["adaptive_penalty"],
                "selection_reason": f"central-route-live:{kind}",
                "task_kind": kind,
                "blocked_candidates": old_target.get("blocked_candidates", []),
            }
    except Exception:
        pass
    return old_target


def select_cheap_lane_target(
    *,
    skip_providers: frozenset[str] = frozenset(),
    task_kind: str = "default",
) -> dict[str, object]:
    """Pick a cheap-lane provider. See task_kind notes above for routing.

    Phase B (2026-04-26): public-proxies are kept in the candidate list
    so that callers fall through gracefully instead of collapsing when
    paid quotas are blown.
    Phase C (2026-04-28): task_kind tiering so background callers prefer
    public proxies up front, saving paid quota for meaningful work.
    """
    kind = (task_kind or "default").strip().lower()

    candidates = _configured_cheap_candidates(
        include_public_proxy=True, skip_providers=skip_providers
    )

    # Cost-filter (15. jul): den DIREKTE cheap/daemon-selection er gratis-only —
    # betalte providers (copilot-premium) må ALDRIG vælges her (inderlivet brænder
    # ikke premium-kvote). Betalt kun via central_route(allow_paid) på agent-lanen.
    from core.services.cheap_provider_runtime_adapters import provider_cost_class
    candidates = [c for c in candidates
                  if provider_cost_class(str(c.get("provider") or "")) != "paid"]

    # For "important" calls, drop public proxies entirely.
    if kind == "important":
        candidates = [c for c in candidates if not _is_public_proxy(c.get("provider", ""))]

    # For "default" calls, honour the documented contract ("paid first, public
    # as fallback"): keep credentialed / non-public-proxy providers ahead of the
    # anonymous public proxies, which serve only as graceful last resort.
    # Candidates arrive already priority-sorted, so a stable split preserves the
    # relative order within each group (quota / adaptive state still matters).
    if kind == "default" and candidates:
        non_public = [c for c in candidates if not _is_public_proxy(c.get("provider", ""))]
        public = [c for c in candidates if _is_public_proxy(c.get("provider", ""))]
        candidates = non_public + public

    # For "background" calls, reorder so public proxies come first and rotate
    # which one is preferred this call.
    if kind == "background" and candidates:
        preferred_first = next(_BACKGROUND_ROTATOR)
        public = [c for c in candidates if _is_public_proxy(c.get("provider", ""))]
        paid = [c for c in candidates if not _is_public_proxy(c.get("provider", ""))]
        # Within the public group, put the rotator's choice first; keep the
        # rest in their stable priority order so quota state still matters.
        public.sort(key=lambda c: (
            0 if str(c.get("provider", "")).lower() == preferred_first else 1,
            int(c.get("priority") or 9999),
        ))
        candidates = public + paid

    blocked: list[dict[str, object]] = []
    for candidate in candidates:
        if not bool(candidate.get("credentials_ready")):
            blocked.append(
                {
                    "provider": candidate["provider"],
                    "model": candidate["model"],
                    "reason": "auth-not-ready",
                }
            )
            continue
        quota = _candidate_quota_snapshot(candidate)
        if quota["blocked"]:
            blocked.append(
                {
                    "provider": candidate["provider"],
                    "model": candidate["model"],
                    "reason": quota["status"],
                }
            )
            continue
        adaptive = _candidate_adaptive_snapshot(candidate)
        _target = {
            **candidate,
            "effective_priority": adaptive["effective_priority"],
            "adaptive_penalty": adaptive["adaptive_penalty"],
            "selection_reason": f"healthy-headroom:{kind}",
            "task_kind": kind,
            "blocked_candidates": blocked,
        }
        _maybe_shadow_compare(_target)  # Task 9: shadow-sammenligning (OFF → no-op)
        # Task 9 live: lad central_route vælge blandt de samme kandidater når live er ON.
        return _maybe_central_route_live(_target, candidates, kind, skip_providers)
    return {
        "active": False,
        "lane": "cheap",
        "status": "no-healthy-provider",
        "task_kind": kind,
        "blocked_candidates": blocked,
    }


def execute_cheap_lane_via_pool(
    *,
    message: str,
    skip_providers: frozenset[str] = frozenset(),
    task_kind: str = "default",
    lane: str = "cheap",
) -> dict[str, object]:
    # KERNE-FORRANG (2026-07-22, bevist rod): dette er den NON-VISIBLE/baggrunds-lane.
    # Mens en SYNLIG tur assembler/streamer, venter baggrunds-LLM-arbejde her — ellers
    # sulter dets tråde den synlige turs SSE-læser via GIL-contention (målt: DeepSeek
    # 621ms isoleret → 9052ms under baggrunds-tråde). ALLE callers er non-visible
    # (non_visible_lane_execution / inner_voice_shadow / compact_llm / tool_tagger …)
    # → den synlige tur kalder ALDRIG denne → nul deadlock-risiko. Bounded ~20s.
    # CLAUDE.md: private/cheap lag udrangerer ALDRIG den beskyttede kerne. Flag-gatet.
    try:
        from core.runtime.db_core import get_runtime_state_value as _grs
        _gate_on = _grs("cheap_lane_visible_gate", True)
        _gate_on = True if _gate_on is None else bool(_gate_on)
    except Exception:
        _gate_on = True
    if _gate_on:
        try:
            from core.services.visible_stream_gate import visible_streaming
            import time as _tg
            for _ in range(200):  # bounded ~20s safety cap
                if not visible_streaming():
                    break
                _tg.sleep(0.1)
        except Exception:
            pass
    target = select_cheap_lane_target(
        skip_providers=skip_providers,
        task_kind=task_kind,
    )
    if not bool(target.get("active", True)) or not str(target.get("provider") or "").strip():
        # Spec Fund 4: aldrig rejse ved tom pool — fald til garanteret bund.
        # ÆGTE degraderings-signal (2026-07-16): den kuraterede gratis-pool kunne ikke
        # betjene → faldt til floor. Dette (ikke sunde intra-gratis failovers) er hvad
        # 'gratis-økologi degraderer' skal måle.
        event_bus.publish(
            "runtime.cheap_lane_exhausted",
            {"from_provider": "", "from_model": "", "reason": "no-healthy-provider",
             "resolution": "floor"},
        )
        from core.services.cheap_lane_floor import attempt_floor
        return attempt_floor(message=message, lane=lane, reason="no-healthy-provider")

    provider = str(target.get("provider") or "").strip()
    model = str(target.get("model") or "").strip()
    profile = str(target.get("auth_profile") or "").strip()
    started_at = datetime.now(UTC)
    input_tokens = _estimate_tokens(message)
    try:
        result = _execute_provider_chat(
            provider=provider,
            model=model,
            auth_profile=profile,
            base_url=str(target.get("base_url") or "").strip(),
            message=message,
        )
    except CheapProviderError as exc:
        _register_provider_failure(
            provider=provider,
            model=model,
            auth_profile=profile,
            error=exc,
            smoke_test=False,
        )
        fallback = _fallback_after_failure(
            failed_provider=provider,
            failed_model=model,
        )
        if fallback is not None:
            event_bus.publish(
                "runtime.cheap_lane_provider_failed_over",
                {
                    "from_provider": provider,
                    "from_model": model,
                    "to_provider": fallback["provider"],
                    "to_model": fallback["model"],
                    "reason": exc.code,
                },
            )
            return execute_cheap_lane_via_pool(
                message=message, skip_providers=skip_providers | {provider}, lane=lane,
            )
        # Ingen gratis-fallback tilbage → poolen er UDTØMT (ægte degraderings-signal).
        event_bus.publish(
            "runtime.cheap_lane_exhausted",
            {"from_provider": provider, "from_model": model, "reason": exc.code,
             "resolution": "raise"},
        )
        raise RuntimeError(f"{provider} cheap lane failed: {exc.code}: {exc.message}")

    output_tokens = int(result.get("output_tokens") or _estimate_tokens(result["text"]))
    latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
    record_cheap_provider_invocation(
        provider=provider,
        model=model,
        auth_profile=profile,
        status="completed",
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=float(result.get("cost_usd") or 0.0),
    )
    _record_provider_success(
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        quality_score=None,
        smoke_test=False,
    )
    # 2026-06-09: extract cache hit/miss from result if provider surfaced them
    # (DeepSeek does via prompt_cache_hit_tokens/prompt_cache_miss_tokens).
    _cache_hit = int(result.get("cache_hit_tokens") or result.get("prompt_cache_hit_tokens") or 0)
    _cache_miss = int(result.get("cache_miss_tokens") or result.get("prompt_cache_miss_tokens") or 0)
    record_cost(
        lane=lane,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=float(result.get("cost_usd") or 0.0),
        cache_hit_tokens=_cache_hit,
        cache_miss_tokens=_cache_miss,
    )
    # Observe-only: mål nyhed af DENNE producers output (attribution via cadence-thread-local
    # ellers task_kind) → grundlag for saliens-gating af indre liv. Ren tekst-lighed, self-safe.
    try:
        from core.services import producer_novelty as _pn
        _who = _pn.get_producer() or _pn.infer_caller() or task_kind
        _pn.record_output(_who, str(result.get("text") or ""))
    except Exception:
        pass
    event_bus.publish(
        "runtime.cheap_lane_provider_completed",
        {
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )
    return {
        "lane": "cheap",
        "provider": provider,
        "model": model,
        "status": "completed",
        "execution_mode": "cheap-provider-pool",
        "source": "cheap-provider-runtime",
        "text": str(result["text"]),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": float(result.get("cost_usd") or 0.0),
    }


def _public_safe_candidates() -> list[dict[str, object]]:
    """Build the public-safe candidate pool: ollamafreeapi (lane=cheap)
    plus local ollama (lane=local). Local ollama is included even though
    it's not registered under lane=cheap because the cloud-passthrough
    models there are the actual reliable public-safe path.

    Added 2026-05-14: was selecting only lane=cheap candidates filtered to
    ollamafreeapi, missing the entire local-ollama provider which has
    much better uptime.
    """
    registry = load_provider_router_registry()
    provider_entries = {
        str(item.get("provider") or "").strip(): item
        for item in registry.get("providers") or []
        if bool(item.get("enabled", True))
    }
    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in registry.get("models") or []:
        if not bool(item.get("enabled", True)):
            continue
        provider = str(item.get("provider") or "").strip()
        lane = str(item.get("lane") or "").strip()
        # Accept ollamafreeapi at any lane (was cheap-only), and ollama
        # at lane=local since that's the configured shape today.
        if provider == "ollamafreeapi":
            pass  # accept
        elif provider == "ollama" and lane in {"local", "cheap"}:
            pass  # accept
        else:
            continue
        model = str(item.get("model") or "").strip()
        if not provider or not model:
            continue
        key = (provider, model)
        if key in seen:
            continue
        seen.add(key)
        provider_entry = provider_entries.get(provider, {})
        defaults = provider_runtime_defaults(provider)
        auth_profile = str(provider_entry.get("auth_profile") or "").strip()
        # Local ollama uses auth_mode='none' and isn't in CHEAP_PROVIDER_DEFAULTS
        # — provider_auth_ready would return False even though no auth is
        # needed. Special-case: trust local ollama at base_url when auth_mode
        # is 'none' or empty.
        auth_mode = str(provider_entry.get("auth_mode") or "").strip().lower()
        if provider == "ollama":
            credentials_ready = auth_mode in {"", "none"}
            # Honor per-model priority override from the registry if set,
            # else default to 50 (between top-tier commercial and the
            # ollamafreeapi fallback at 95). Lower is better.
            priority_val = int(item.get("priority") or 50)
        else:
            credentials_ready = provider_auth_ready(
                provider=provider,
                auth_profile=auth_profile,
            )
            priority_val = int(defaults.get("priority") or 9999)
        candidates.append(
            {
                "active": True,
                "lane": "cheap",  # treated as cheap for selection
                "provider": provider,
                "model": model,
                "auth_profile": auth_profile,
                "auth_mode": auth_mode,
                "base_url": str(provider_entry.get("base_url") or defaults.get("base_url") or "").strip(),
                "credentials_ready": credentials_ready,
                "priority": priority_val,
                "rpm_limit": defaults.get("rpm_limit"),
                "daily_limit": defaults.get("daily_limit"),
                "daily_neurons": defaults.get("daily_neurons"),
                "source": "public-safe-pool",
                "updated_at": str(item.get("updated_at") or ""),
            }
        )
    return candidates


def select_public_safe_cheap_lane_target() -> dict[str, object]:
    """Pick the highest-priority ready public-safe provider for cheap-lane work.

    Public-safe = provider where outbound messages don't expose identity
    to a commercial API. Two providers qualify:
      - ollamafreeapi (public proxy, no logging)
      - ollama (local Ollama on 127.0.0.1, including :cloud suffixed
        models which go through Ollama's own passthrough — still under
        Ollama's privacy boundary, not direct commercial API)

    Walks both providers' candidates by base priority (lower = better),
    skipping blocked/unauthorized ones, and returns the first ready hit.
    Updated 2026-05-14: was hardcoded to ollamafreeapi only — ollamafreeapi
    is too often down, so local Ollama is the more reliable public-safe lane.
    """
    candidates = _public_safe_candidates()
    # Prefer local ollama before ollamafreeapi (better uptime), then by priority
    candidates.sort(key=lambda c: (
        0 if c.get("provider") == "ollama" else 1,
        int(c.get("priority") or 9999),
    ))
    for candidate in candidates:
        if not bool(candidate.get("credentials_ready")):
            continue
        quota = _candidate_quota_snapshot(candidate)
        if quota["blocked"]:
            continue
        adaptive = _candidate_adaptive_snapshot(candidate)
        return {
            **candidate,
            "effective_priority": adaptive["effective_priority"],
            "adaptive_penalty": adaptive["adaptive_penalty"],
            "selection_reason": f"public-safe-{candidate.get('provider')}",
        }
    return {
        "active": False,
        "lane": "cheap",
        "status": "no-public-safe-provider",
    }


def execute_public_safe_cheap_lane(*, message: str) -> dict[str, object]:
    target = select_public_safe_cheap_lane_target()
    provider = str(target.get("provider") or "").strip()
    model = str(target.get("model") or "").strip()
    if provider and model:
        profile = str(target.get("auth_profile") or "").strip()
        started_at = datetime.now(UTC)
        try:
            result = _execute_provider_chat(
                provider=provider,
                model=model,
                auth_profile=profile,
                base_url=str(target.get("base_url") or "").strip(),
                message=message,
            )
        except CheapProviderError as exc:
            _register_provider_failure(
                provider=provider,
                model=model,
                auth_profile=profile,
                error=exc,
                smoke_test=False,
            )
        else:
            latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
            _record_provider_success(
                provider=provider,
                model=model,
                latency_ms=latency_ms,
                quality_score=None,
                smoke_test=False,
            )
            return {
                "lane": "cheap",
                "provider": provider,
                "model": model,
                "status": "completed",
                "execution_mode": "public-safe-cheap-provider",
                "source": "cheap-provider-runtime",
                "text": str(result.get("text") or ""),
                "input_tokens": _estimate_tokens(message),
                "output_tokens": int(
                    result.get("output_tokens") or _estimate_tokens(str(result.get("text") or ""))
                ),
                "cost_usd": float(result.get("cost_usd") or 0.0),
            }
    return _execute_public_safe_local_ollama(message=message)


def _configured_cheap_candidates(
    *, include_public_proxy: bool, skip_providers: frozenset[str] = frozenset()
) -> list[dict[str, object]]:
    registry = load_provider_router_registry()
    provider_entries = {
        str(item.get("provider") or "").strip(): item
        for item in registry.get("providers") or []
        if bool(item.get("enabled", True))
    }
    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    emitted: set[tuple[str, str, str]] = set()
    multiprofile = _flag_multiprofile()
    roundrobin = multiprofile and _flag_profile_roundrobin()
    # A (2026-07-24): rotate profile emit-order per provider ONCE per call (shared
    # across the model loop and the static-models loop) so the account split is
    # consistent within a call and advances between calls.
    call_rr: dict[str, list[str]] = {}
    if multiprofile:
        from core.services.auth_profile_scan import ready_profiles_for

    def _profiles_for(prov: str, fallback_profile: str) -> list[str]:
        if not multiprofile:
            return [fallback_profile]
        if roundrobin:
            if prov not in call_rr:
                call_rr[prov] = _roundrobin_profiles(prov, list(ready_profiles_for(prov)))
            return call_rr[prov]
        return list(ready_profiles_for(prov))
    for item in registry.get("models") or []:
        if not bool(item.get("enabled", True)):
            continue
        if str(item.get("lane") or "").strip() != "cheap":
            continue
        provider = str(item.get("provider") or "").strip()
        model = str(item.get("model") or "").strip()
        if provider in ("ollamafreeapi", "arko") and not include_public_proxy:
            # Both are third-party public-proxy lanes — only enabled when
            # callers explicitly opt in (e.g. final-fallback chains).
            continue
        if skip_providers and provider in skip_providers:
            continue
        if not provider or not model:
            continue
        key = (provider, model)
        if key in seen:
            continue
        seen.add(key)
        provider_entry = provider_entries.get(provider, {})
        defaults = provider_runtime_defaults(provider)
        registry_profile = str(provider_entry.get("auth_profile") or "").strip()
        # Multiprofil (flag ON): én kandidat pr. klar auth-profil for provideren.
        # Flag OFF (default): uændret — kun registry-entry'ens egen auth_profile.
        # roundrobin (flag ON): profil-rækkefølgen roteres pr. kald (se _profiles_for).
        auth_profiles = _profiles_for(provider, registry_profile)
        for auth_profile in auth_profiles:
            triple = (provider, model, auth_profile)
            if triple in emitted:
                continue
            emitted.add(triple)
            candidates.append(
                {
                    "active": True,
                    "lane": "cheap",
                    "provider": provider,
                    "model": model,
                    "auth_profile": auth_profile,
                    "auth_mode": str(provider_entry.get("auth_mode") or "").strip(),
                    "base_url": str(provider_entry.get("base_url") or defaults.get("base_url") or "").strip(),
                    "credentials_ready": provider_auth_ready(
                        provider=provider,
                        auth_profile=auth_profile,
                    ),
                    "priority": int(defaults.get("priority") or 9999),
                    "rpm_limit": defaults.get("rpm_limit"),
                    "daily_limit": defaults.get("daily_limit"),
                    "daily_neurons": defaults.get("daily_neurons"),
                    "source": "provider-router-registry",
                    "updated_at": str(item.get("updated_at") or ""),
                }
            )
    # Phase D (2026-05-14): also inject models from provider defaults' static_models
    # for providers that have no explicit model entries in the registry.
    # This lets us remove redundant model entries for providers like opencode
    # whose models are already declared in CHEAP_PROVIDER_DEFAULTS.
    for provider_name, provider_cfg in CHEAP_PROVIDER_DEFAULTS.items():
        static_models = provider_cfg.get("static_models") or []
        if not static_models:
            continue
        provider_entry = provider_entries.get(provider_name, {})
        registry_profile = str(provider_entry.get("auth_profile") or "").strip()
        # Multiprofil (flag ON): iterér klare auth-profiler; OFF: kun entry-profilen.
        # roundrobin deler samme call_rr så profil-splittet er konsistent i kaldet.
        static_profiles = _profiles_for(provider_name, registry_profile)
        for sm in static_models:
            key = (provider_name, sm)
            if key in seen:
                continue
            if skip_providers and provider_name in skip_providers:
                continue
            if provider_name in ("ollamafreeapi", "arko") and not include_public_proxy:
                continue
            seen.add(key)
            for auth_profile in static_profiles:
                triple = (provider_name, sm, auth_profile)
                if triple in emitted:
                    continue
                emitted.add(triple)
                candidates.append(
                    {
                        "active": True,
                        "lane": "cheap",
                        "provider": provider_name,
                        "model": sm,
                        "auth_profile": auth_profile,
                        "auth_mode": str(provider_entry.get("auth_mode") or "").strip(),
                        "base_url": str(
                            provider_entry.get("base_url")
                            or provider_cfg.get("base_url")
                            or ""
                        ).strip(),
                        "credentials_ready": provider_auth_ready(
                            provider=provider_name,
                            auth_profile=auth_profile,
                        ),
                        "priority": int(provider_cfg.get("priority") or 9999),
                        "rpm_limit": provider_cfg.get("rpm_limit"),
                        "daily_limit": provider_cfg.get("daily_limit"),
                        "daily_neurons": provider_cfg.get("daily_neurons"),
                        "source": "provider-defaults-static-models",
                        "updated_at": "",
                    }
                )
    candidates.sort(
        key=lambda item: (
            _candidate_adaptive_snapshot(item)["effective_priority"],
            str(item.get("updated_at") or ""),
        )
    )
    # Routable-filter (2026-07-14): hold betalte providers (deepseek routable=False)
    # ude af den routbare cheap-pool — kun de gratis modeller tager last. deepseek
    # bevares som nød-bund (cheap_lane_floor), ikke i normal routing.
    from core.services.cheap_provider_runtime_adapters import is_routable_provider
    candidates = [c for c in candidates
                  if is_routable_provider(str(c.get("provider") or ""))]
    return candidates


def _candidate_quota_snapshot(candidate: dict[str, object]) -> dict[str, object]:
    provider = str(candidate["provider"])
    model = str(candidate["model"])
    # TTL cache via shared_cache (2026-05-15): SQLite-backed so all 4
    # workers see the same cached quota state. Quota counts barely move
    # on the 2s timescale, and MC polling + awareness builders hammer
    # this repeatedly.
    from core.services import shared_cache as _sc
    _qkey = f"{_QUOTA_SNAPSHOT_PREFIX}{provider}/{model}"
    _cached = _sc.get(_qkey)
    if isinstance(_cached, dict):
        return _cached
    state = get_cheap_provider_runtime_state(provider=provider, model=model) or {}
    now = datetime.now(UTC)
    cooldown_until_raw = str(state.get("cooldown_until") or "").strip()
    cooldown_active = False
    if cooldown_until_raw:
        try:
            cooldown_active = datetime.fromisoformat(cooldown_until_raw) > now
        except ValueError:
            cooldown_active = False
    minute_since = (now - timedelta(minutes=1)).isoformat()
    day_since = (now - timedelta(hours=_QUOTA_RESET_HOURS)).isoformat()
    requests_last_minute = count_cheap_provider_invocations(
        provider=provider,
        since=minute_since,
    )
    requests_last_day = count_cheap_provider_invocations(
        provider=provider,
        since=day_since,
    )
    rpm_limit = candidate.get("rpm_limit")
    daily_limit = candidate.get("daily_limit")
    rpm_exhausted = isinstance(rpm_limit, int) and requests_last_minute >= rpm_limit
    daily_exhausted = isinstance(daily_limit, int) and requests_last_day >= daily_limit
    status = "ready"
    if cooldown_active:
        status = "cooldown-active"
    elif rpm_exhausted:
        status = "rpm-exhausted"
    elif daily_exhausted:
        status = "daily-exhausted"
    snapshot = {
        "status": status,
        "blocked": cooldown_active or rpm_exhausted or daily_exhausted,
        "cooldown_active": cooldown_active,
        "cooldown_until": cooldown_until_raw or None,
        "requests_last_minute": requests_last_minute,
        "requests_last_day": requests_last_day,
        "rpm_limit": rpm_limit,
        "daily_limit": daily_limit,
        "daily_neurons": candidate.get("daily_neurons"),
    }
    _sc.set(_qkey, snapshot, ttl_seconds=_QUOTA_SNAPSHOT_TTL_SECONDS)
    return snapshot


def _fallback_after_failure(*, failed_provider: str, failed_model: str) -> dict[str, object] | None:
    # Explicitly exclude the just-failed provider from the fallback query. The
    # failed provider gets a cooldown via _register_provider_failure, but the
    # quota snapshot is TTL-cached (2s, added 2026-05-13 dafb5535). Without the
    # skip, a re-selection inside that cache window still sees the failed
    # provider as "ready", re-picks it, and this function wrongly returns None
    # → failover is defeated and the caller raises instead of falling over.
    # Skipping by provider makes the "is there ANOTHER provider" query correct
    # regardless of cache freshness.
    target = select_cheap_lane_target(skip_providers=frozenset({failed_provider}))
    provider = str(target.get("provider") or "")
    model = str(target.get("model") or "")
    if provider and model and (provider, model) != (failed_provider, failed_model):
        return target
    return None


def _candidate_adaptive_snapshot(
    candidate: dict[str, object],
    *,
    state: dict[str, object] | None = None,
) -> dict[str, object]:
    current_state = state or get_cheap_provider_runtime_state(
        provider=str(candidate["provider"]),
        model=str(candidate["model"]),
    ) or {}
    metadata = _decode_state_metadata(current_state)
    base_priority = int(candidate.get("priority") or 9999)
    success_count = int(metadata.get("success_count") or 0)
    failure_count = int(metadata.get("failure_count") or 0)
    smoke_success_count = int(metadata.get("smoke_success_count") or 0)
    smoke_failure_count = int(metadata.get("smoke_failure_count") or 0)
    avg_latency_ms = float(metadata.get("avg_latency_ms") or 0.0)
    avg_quality_score = float(metadata.get("avg_quality_score") or 1.0)
    total_runs = success_count + failure_count
    success_ratio = 1.0 if total_runs <= 0 else success_count / total_runs
    total_smokes = smoke_success_count + smoke_failure_count
    smoke_success_ratio = 1.0 if total_smokes <= 0 else smoke_success_count / total_smokes
    quality_penalty = max(0.0, (1.0 - avg_quality_score) * 8.0)
    reliability_penalty = max(0.0, (1.0 - success_ratio) * 10.0)
    smoke_penalty = max(0.0, (1.0 - smoke_success_ratio) * 8.0)
    latency_penalty = min(6.0, avg_latency_ms / 1200.0)
    adaptive_penalty = int(round(quality_penalty + reliability_penalty + smoke_penalty + latency_penalty))
    return {
        "base_priority": base_priority,
        "effective_priority": base_priority + adaptive_penalty,
        "adaptive_penalty": adaptive_penalty,
        "success_count": success_count,
        "failure_count": failure_count,
        "smoke_success_count": smoke_success_count,
        "smoke_failure_count": smoke_failure_count,
        "success_ratio": round(success_ratio, 4),
        "smoke_success_ratio": round(smoke_success_ratio, 4),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "avg_quality_score": round(avg_quality_score, 4),
    }


def _record_provider_success(
    *,
    provider: str,
    model: str,
    latency_ms: int,
    quality_score: float | None,
    smoke_test: bool,
) -> None:
    current_state = get_cheap_provider_runtime_state(provider=provider, model=model) or {}
    metadata = _decode_state_metadata(current_state)
    success_count = int(metadata.get("success_count") or 0) + 1
    smoke_success_count = int(metadata.get("smoke_success_count") or 0) + (1 if smoke_test else 0)
    avg_latency_ms = _rolling_average(
        current_avg=float(metadata.get("avg_latency_ms") or 0.0),
        current_count=int(metadata.get("success_count") or 0),
        new_value=float(latency_ms),
    )
    avg_quality_score = float(metadata.get("avg_quality_score") or 1.0)
    quality_count = int(metadata.get("quality_count") or 0)
    if quality_score is not None:
        avg_quality_score = _rolling_average(
            current_avg=avg_quality_score,
            current_count=quality_count,
            new_value=float(quality_score),
        )
        quality_count += 1
    upsert_cheap_provider_runtime_state(
        provider=provider,
        model=model,
        status="ready",
        auth_ready=True,
        quota_limited=False,
        cooldown_until=None,
        last_error_code="",
        last_error_message="",
        last_success_at=datetime.now(UTC).isoformat(),
        metadata_json=json.dumps(
            {
                **metadata,
                "protocol": provider_runtime_defaults(provider).get("protocol"),
                "success_count": success_count,
                "smoke_success_count": smoke_success_count,
                "avg_latency_ms": avg_latency_ms,
                "avg_quality_score": avg_quality_score,
                "quality_count": quality_count,
            },
            ensure_ascii=False,
        ),
    )


def _register_provider_failure(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    error: CheapProviderError,
    smoke_test: bool = False,
) -> None:
    now = datetime.now(UTC)
    cooldown_until = None
    quota_limited = False
    auth_ready = provider_auth_ready(provider=provider, auth_profile=auth_profile)
    current_state = get_cheap_provider_runtime_state(provider=provider, model=model) or {}
    metadata = _decode_state_metadata(current_state)
    if error.code in {"rate-limited", "quota-exhausted", "credits-exhausted"}:
        quota_limited = True
        retry_after = error.retry_after_seconds or _default_failure_cooldown_seconds(error.code)
        cooldown_until = (now + timedelta(seconds=retry_after)).isoformat()
    elif error.code == "auth-rejected":
        auth_ready = False
    elif error.code in {"provider-blocked", "provider-error", "model-not-found", "model-unavailable", "request-failed"}:
        retry_after = error.retry_after_seconds or _default_failure_cooldown_seconds(error.code)
        cooldown_until = (now + timedelta(seconds=retry_after)).isoformat()
    record_cheap_provider_invocation(
        provider=provider,
        model=model,
        auth_profile=auth_profile,
        status="failed",
        error_code=error.code,
        error_message=error.message,
        retry_after_seconds=error.retry_after_seconds,
    )
    upsert_cheap_provider_runtime_state(
        provider=provider,
        model=model,
        status=error.code,
        auth_ready=auth_ready,
        quota_limited=quota_limited,
        cooldown_until=cooldown_until,
        last_error_code=error.code,
        last_error_message=error.message,
        last_failure_at=now.isoformat(),
        metadata_json=json.dumps(
            {
                **metadata,
                "failure_count": int(metadata.get("failure_count") or 0) + 1,
                "smoke_failure_count": int(metadata.get("smoke_failure_count") or 0)
                + (1 if smoke_test else 0),
                "status_code": error.status_code,
                "retry_after_seconds": error.retry_after_seconds,
            },
            ensure_ascii=False,
        ),
    )
    event_bus.publish(
        "runtime.cheap_lane_provider_failed",
        {
            "provider": provider,
            "model": model,
            "code": error.code,
            "retry_after_seconds": error.retry_after_seconds,
            "status_code": error.status_code,
        },
    )


def _decode_state_metadata(state: dict[str, object]) -> dict[str, object]:
    raw = state.get("metadata_json")
    if not raw:
        return {}
    try:
        decoded = json.loads(str(raw))
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _rolling_average(*, current_avg: float, current_count: int, new_value: float) -> float:
    if current_count <= 0:
        return float(new_value)
    return ((current_avg * current_count) + new_value) / float(current_count + 1)


def _smoke_quality_score(*, expected: str, actual: str) -> float:
    normalized_expected = _normalize_probe_text(expected)
    normalized_actual = _normalize_probe_text(actual)
    if normalized_actual == normalized_expected:
        return 1.0
    if normalized_expected and normalized_expected in normalized_actual:
        return 0.9
    return 0.4


def _normalize_probe_text(value: str) -> str:
    text = str(value or "").strip().strip("\"'`")
    return " ".join(text.lower().split())
