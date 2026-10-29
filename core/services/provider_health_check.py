"""Provider health check — periodic ping to detect outages early.

Existing reactive infrastructure (circuit breaker, fallback) only learns
a provider is down AFTER a real call fails. Health check ping every 5
min lets us detect outages before they hit user-facing calls.

Pings each enabled cheap_lane provider with a tiny request. Records
status in eventbus. Updates provider_circuit_breaker proactively when
ping fails consistently — so next call doesn't have to discover it.

Cheap: 1 ping per provider per 5 min × 9 providers = 108 calls/hour
total. Each ping is a single token completion → minimal cost.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_PING_TIMEOUT_SECONDS = 5
_HEALTH_STATE_KEY = "provider_health"


# Lightweight reachability check — just ensure the host responds.
# Doesn't do an actual LLM call (would consume quota).
# 2026-06-13: ollamafreeapi fjernet fra ping-rotationen — provideren er død
# (sidste succes ~14. maj; runtime-state viste 'Failed to connect / connection
# timed out / 503 server busy' — IKKE DNS NXDOMAIN, jf. Jarvis' kommentar). De
# 10 døde model-entries er også fjernet fra provider_router.json. Relevance-
# referencen i runtime.json er nu en inert forældreløs.
# 29/10-2026 — PROBEN LØJ OM FEM AF OTTE.
#
# Filen meldte `auth_failed`/`wrong_endpoint` for groq, mistral, gemini, cloudflare
# og opencode. Målt samme dag med providerens EGEN nøgle og EGEN base_url:
#
#     mistral     200   (proben: 401 auth_failed)
#     gemini      200   (proben: 404 wrong_endpoint)
#     opencode    200   (proben: 403 — den pingede opencode.ai, men provideren er LOKAL)
#     groq        200   (proben: 403 «error code: 1010» = Cloudflares UA-blok, ikke nøglen)
#     cloudflare  200   (proben: 404 — /models findes ikke; /ai/models/search gør)
#
# Tre fejl oveni hinanden: (1) proben sendte ALDRIG nøglen, så 401/403 betød
# «vi spurgte uden adgang», ikke «nøglen er død»; (2) URL'erne var håndskrevne og
# var råtnede — gemini og cloudflare pegede på rod-stier, opencode på den forkerte
# vaert; (3) `urllib`s standard-UA blokeres af Cloudflare med 1010.
#
# `provider_router.json` er sandheden om hvor en provider bor (jf.
# `provider_registry_admin`). Denne fil må ikke holde sin egen kopi der kan rådne:
# den læser routeren og bruger `_PING_ENDPOINTS` KUN som fallback når config er
# ulæselig. Nøglen hentes gennem `core.auth.profiles` — samme vej som rigtige kald.
_PING_ENDPOINTS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "nvidia-nim": "https://integrate.api.nvidia.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "mistral": "https://api.mistral.ai/v1",
    "sambanova": "https://api.sambanova.ai/v1",
    "cloudflare": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
    "opencode": "http://127.0.0.1:4199",
}

# Stien der SPØRGER om provideren kan bruges. OpenAI-kompatible svarer på /models;
# Cloudflare gør ikke (405 på GET /models), men har /models/search.
_PROBE_PATH_DEFAULT = "/models"
_PROBE_PATHS: dict[str, str] = {"cloudflare": "/models/search"}

# Cloudflare er den ene hvor routerens base_url ikke er probens rod: routeren peger
# på `.../ai/v1` (inferens-stien), men model-kataloget ligger på `.../ai/models/search`
# — altså FØR `/v1`. Målt 29/10-2026: med `/v1` beholdt gav stien 405, uden gav 200.
_PROBE_TRIM_SUFFIX: dict[str, str] = {"cloudflare": "/v1"}

# Cloudflare blokerer urllib's standard-UA med `403 error code: 1010`. Det er samme
# fælde som ntfy-403'erne (QUICK_FACTS): et 403 kan betyde «du ligner en bot», ikke
# «nøglen er ugyldig». Uden denne header ville groq se død ud med en perfekt nøgle.
_PROBE_UA = "JarvisHealthCheck/1.0 (+https://jarvis.srvlab.dk)"

# Gemini tager ikke `Authorization: Bearer` — den vil have nøglen i denne header.
_GEMINI_KEY_HEADER = "x-goog-api-key"


def _router_config_path() -> Path:
    return Path(
        os.environ.get("JARVIS_CONFIG_DIR") or Path.home() / ".jarvis-v2" / "config"
    ) / "provider_router.json"


def _router_providers() -> dict[str, dict[str, Any]]:
    """provider → {base_url, auth_profile} fra provider_router.json. {} ved fejl."""
    try:
        data = json.loads(_router_config_path().read_text(encoding="utf-8"))
    except Exception:  # bevidst: ulaeselig config falder tilbage paa _PING_ENDPOINTS
        return {}
    out: dict[str, dict[str, Any]] = {}
    for entry in data.get("providers") or []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("provider") or "").strip()
        if name:
            out[name] = entry
    return out


def _load_provider_credentials(provider: str, profile: str) -> dict[str, Any]:
    """Hent providerens nøgle ad samme vej som rigtige kald. {} når den ikke findes.

    Egen funktion så `try` kun dækker ét kald: en manglende eller ulæselig
    auth-profil er «vi har ingen nøgle», ikke en grund til at vælte health-checket.
    """
    try:
        from core.auth.profiles import get_provider_credentials

        return dict(get_provider_credentials(profile=profile, provider=provider) or {})
    except Exception:  # bevidst: ingen/ulaeselig profil = ingen noegle, ikke et crash
        return {}


def _probe_request(provider: str) -> dict[str, Any] | None:
    """Byg URL + headers som et RIGTIGT kald ville gøre. None = ingen base_url.

    ``has_credentials`` skelnes fra ``auth_failed``: at vi ikke HAR en nøgle er en
    anden fejl end at nøglen afvises. Før blev de to slået sammen, så en provider
    uden profil-nøgle blev rapporteret som død.
    """
    entry = _router_providers().get(provider) or {}
    base = str(entry.get("base_url") or "").strip() or _PING_ENDPOINTS.get(provider, "")
    if not base:
        return None

    api_key = ""
    account_id = ""
    profile = str(entry.get("auth_profile") or "").strip() or "default"
    creds = _load_provider_credentials(provider, profile)
    api_key = str(creds.get("api_key") or creds.get("access_token") or "").strip()
    account_id = str(creds.get("account_id") or "").strip()

    if "{account_id}" in base:
        if not account_id:
            return {"url": "", "headers": {}, "has_credentials": False}
        base = base.replace("{account_id}", account_id)

    trim = _PROBE_TRIM_SUFFIX.get(provider)
    if trim and base.rstrip("/").endswith(trim):
        base = base.rstrip("/")[: -len(trim)]

    url = base.rstrip("/") + _PROBE_PATHS.get(provider, _PROBE_PATH_DEFAULT)
    headers = {"User-Agent": _PROBE_UA, "Accept": "application/json"}
    if api_key:
        if provider == "gemini":
            headers[_GEMINI_KEY_HEADER] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"
    return {"url": url, "headers": headers, "has_credentials": bool(api_key)}


def classify_http_code(code: int | None) -> str:
    """HTTP-svar → hvad det BETYDER for om provideren kan bruges.

    28/10-2026: indført fordi ``reachable`` blev sat til ``code < 500``, så 401/403/404
    alle talte som sunde. Målt samme dag: filen meldte 8/8 «reachable» mens groq svarede
    403, mistral 401, opencode 403, gemini 404 og cloudflare 404 — kun tre af otte kunne
    faktisk bruges. Et health-signal der tæller «svarede» som «virker» skjuler netop det
    det findes for at vise.

    Klassifikationen er bevidst grov: den skal kunne læses uden at kende provideren.
    """
    if code is None:
        return "unreachable"
    if 200 <= code < 300:
        return "healthy"
    if code in (401, 403):
        return "auth_failed"      # nøgle mangler/er ugyldig — provideren kan IKKE bruges
    if code == 404:
        return "wrong_endpoint"   # stien findes ikke — ping-URL'en er forkert, ikke provideren
    if code == 429:
        return "rate_limited"     # virker, men tør lige nu
    if 400 <= code < 500:
        return "bad_request"
    return "unreachable"          # 5xx = serveren svarer ikke brugbart


def _ping_host(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """HTTP GET med kort timeout. Returnerer ``status`` (klassificeret) + ``reachable``.

    ``reachable`` bevares for bagudkompatibilitet, men betyder nu «kan bruges», ikke
    «svarede». Forskellen er hele pointen: en 403 er et svar, men ikke et brugbart et.

    29/10-2026: ``headers`` tilføjet. Uden den sendte proben hverken nøgle eller
    User-Agent — så 401/403 målte VORES forespørgsel, ikke providerens helbred.
    """
    started = datetime.now(UTC)
    try:
        req = urllib.request.Request(url, method="GET")
        for navn, vaerdi in (headers or {}).items():
            req.add_header(navn, vaerdi)
        with urllib.request.urlopen(req, timeout=_PING_TIMEOUT_SECONDS) as response:
            code = response.getcode()
        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        status = classify_http_code(code)
        return {"reachable": status == "healthy", "status": status,
                "http_code": code, "latency_ms": elapsed_ms}
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        status = classify_http_code(exc.code)
        return {"reachable": status == "healthy", "status": status,
                "http_code": exc.code, "latency_ms": elapsed_ms}
    except Exception as exc:
        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        return {"reachable": False, "status": "unreachable",
                "error": str(exc)[:120], "latency_ms": elapsed_ms}


def health_check_all_providers() -> dict[str, Any]:
    """Ping every cheap-lane provider once. Returns per-provider status."""
    results: dict[str, Any] = {}
    unreachable: list[str] = []
    for provider in _PING_ENDPOINTS:
        request = _probe_request(provider)
        if request is None:
            results[provider] = {"reachable": False, "status": "no_endpoint",
                                 "http_code": None, "latency_ms": 0}
            unreachable.append(provider)
            continue
        if not request["url"] or not request["has_credentials"]:
            # Vi har ingen nøgle at spørge med. Så kan proben ikke sige noget om
            # provideren — den kan kun sige noget om os. Før blev der alligevel
            # pinget, og 401/403 blev rapporteret som «nøglen er død», selv når
            # vi slet ikke havde sendt en.
            #
            # Bemærk: alle providere i `_PING_ENDPOINTS` kræver en nøgle. Tilføjer
            # man en nøglefri udbyder, skal den vej ind her — ikke gennem et 401.
            results[provider] = {"reachable": False, "status": "no_credentials",
                                 "http_code": None, "latency_ms": 0}
            unreachable.append(provider)
            continue
        result = _ping_host(request["url"], request["headers"])
        results[provider] = result
        if not result.get("reachable"):
            unreachable.append(provider)

    # 28/10-2026: «reachable» betød «svarede», så 401/403/404 talte som sunde. Nu tælles
    # healthy_count kun ved 2xx, og de øvrige navngives med deres årsag — ellers kan man
    # ikke se på filen hvilke providers der faktisk kan bruges.
    by_status: dict[str, list[str]] = {}
    for provider, r in results.items():
        st = str(r.get("status") or "unreachable")
        by_status.setdefault(st, []).append(provider)

    snapshot = {
        "checked_at": datetime.now(UTC).isoformat(),
        "results": results,
        "unreachable": unreachable,
        "healthy_count": len(by_status.get("healthy") or []),
        "reachable_count": len(by_status.get("healthy") or []),
        "total_count": len(_PING_ENDPOINTS),
        "by_status": by_status,
        "auth_failed": by_status.get("auth_failed") or [],
        "wrong_endpoint": by_status.get("wrong_endpoint") or [],
        "rate_limited": by_status.get("rate_limited") or [],
        # 29/10-2026: «vi har ingen nøgle» er ikke «provideren er død». Uden denne
        # kunne en manglende lokal profil læses som en udfaldende udbyder.
        "no_credentials": by_status.get("no_credentials") or [],
        "no_endpoint": by_status.get("no_endpoint") or [],
    }

    try:
        from core.runtime.state_store import save_json
        save_json(_HEALTH_STATE_KEY, snapshot)
    except Exception:
        pass

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "runtime.provider_health_check",
            {"unreachable": unreachable, "reachable_count": snapshot["reachable_count"]},
        )
    except Exception:
        pass

    # B7: provider-helbred synlig i Centralen (degraderede providers var kun i en JSON-fil).
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "provider_health",
                           "reachable": snapshot["reachable_count"],
                           "total": snapshot["total_count"], "unreachable": unreachable})
    except Exception:
        pass

    return snapshot


_PREV_MODELS_KEY = "provider_health:model_counts"
_LATENCY_WARN_MS = 8000


def _cheap_dry_providers() -> list[str]:
    """Providers i cheap-lane-cooldown (tør/quota-blokeret) — fra runtime-state. Self-safe.
    Det er DENNE tilstand der frøs alle daemons i 53t da DeepSeek løb tør (Jarvis-spec)."""
    try:
        from core.runtime.db import list_cheap_provider_runtime_states
        now = datetime.now(UTC)
        dry: list[str] = []
        for s in (list_cheap_provider_runtime_states(lane="cheap") or []):
            cu = str(s.get("cooldown_until") or "").strip()
            if cu:
                try:
                    if datetime.fromisoformat(cu) > now:
                        dry.append(str(s.get("provider") or ""))
                except Exception:
                    pass
        return [d for d in dry if d]
    except Exception:
        return []


def _model_drift() -> list[dict[str, Any]]:
    """Model-drift: en provider der FØR havde modeller men nu har 0 (model udfaset/omdøbt — den
    risiko der har deaktiveret providers). Henter model-lister via list_provider_models, sammen-
    ligner med sidste-set antal i shared_cache. Self-safe → []."""
    drift: list[dict[str, Any]] = []
    try:
        from core.services.cheap_provider_runtime import list_provider_models
        from core.services import shared_cache
        prev = shared_cache.get(_PREV_MODELS_KEY)
        prev = prev if isinstance(prev, dict) else {}
        cur: dict[str, int] = {}
        for provider in _PING_ENDPOINTS:
            try:
                r = list_provider_models(provider=provider) or {}
                models = r.get("models") if isinstance(r.get("models"), list) else []
                status = str(r.get("status") or "").lower()
            except Exception:
                continue
            n = len(models)
            cur[provider] = n
            before = int(prev.get(provider) or 0)
            if before > 0 and n == 0 and status != "error":
                drift.append({"provider": provider, "had": before, "now": 0})
        if cur:
            merged = {**prev, **cur}
            shared_cache.set(_PREV_MODELS_KEY, merged, ttl_seconds=7 * 24 * 3600)
    except Exception:
        pass
    return drift


_PROACTIVE_CODE = "proactive_health"        # mærker cooldowns VI satte (så vi kun rydder vores egne)
_PROACTIVE_COOLDOWN_S = 360                 # 6 min — lige forbi næste 5-min-check (self-korrigerer)


def _spread_load_proactively(reports: dict[str, dict], unreachable: list[str]) -> int:
    """Daemon-load-spredning (Jarvis-spec): sæt PROAKTIVT en kort cooldown på nede providers, så
    cheap-lane-pool'en (der allerede roterer på cooldown) skipper dem FØR en daemon rammer fejlen
    — i stedet for at alle 50 daemons fryser på en tør primær. Ved recovery ryddes KUN vores egen
    proaktive cooldown (ægte quota-cooldowns røres ikke). Self-safe → 0."""
    changed = 0
    try:
        from datetime import timedelta
        from core.runtime.db import (
            get_cheap_provider_runtime_state,
            upsert_cheap_provider_runtime_state,
        )
        now = datetime.now(UTC)
        for provider in reports:
            st = get_cheap_provider_runtime_state(provider=provider) or {}
            cur_cd = str(st.get("cooldown_until") or "").strip()
            cur_code = str(st.get("last_error_code") or "")
            if provider in unreachable:
                # sæt kun proaktiv cooldown hvis der IKKE allerede er en (ægte) cooldown
                if not cur_cd:
                    upsert_cheap_provider_runtime_state(
                        provider=provider, lane="cheap", status="unreachable",
                        cooldown_until=(now + timedelta(seconds=_PROACTIVE_COOLDOWN_S)).isoformat(),
                        last_error_code=_PROACTIVE_CODE,
                        last_error_message="proaktiv health-cooldown: ping fejlede → rut udenom",
                    )
                    changed += 1
            else:
                # genoprettet → ryd KUN hvis det var VORES proaktive cooldown
                if cur_cd and cur_code == _PROACTIVE_CODE:
                    upsert_cheap_provider_runtime_state(
                        provider=provider, lane="cheap", status="ok",
                        cooldown_until=None, last_error_code="",
                        last_error_message="", last_success_at=now.isoformat(),
                    )
                    changed += 1
    except Exception:
        pass
    return changed


def observe_and_flag() -> dict[str, Any]:
    """Kadence-entry (Jarvis-spec 2026-06-23): ping + model-drift + cheap-dry → observe + FLAG
    (nede/degraderet/tør/model-drift) + auto-resolve genoprettede. Bygger på config_drift-mekanik.
    ALDRIG destruktiv — retter ikke config selv. Self-safe."""
    snap = health_check_all_providers()  # eksisterende ping + observe
    results = snap.get("results") or {}
    unreachable = list(snap.get("unreachable") or [])
    degraded = [p for p, r in results.items()
                if isinstance(r, dict) and r.get("reachable") and int(r.get("latency_ms") or 0) > _LATENCY_WARN_MS]
    dry = _cheap_dry_providers()
    drift = _model_drift()
    spread = _spread_load_proactively(results, unreachable)

    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "provider_health",
                           "unreachable": unreachable, "degraded": degraded,
                           "dry_cheap": dry, "model_drift": [d["provider"] for d in drift],
                           "proactive_cooldowns": spread})
    except Exception:
        pass

    # ── flag + auto-resolve (config_drift-mønster) ──────────────────────
    try:
        from core.runtime.db_central_incidents import (
            has_unresolved_message, record_central_incident, resolve_central_incidents,
        )
        for p in unreachable:
            msg = f"provider {p} unreachable — proaktiv ping fejlede (før et brugervendt kald)"
            if not has_unresolved_message(cluster="system", nerve="provider_health", message=msg):
                record_central_incident(cluster="system", nerve="provider_health",
                                        kind="provider_down", severity="error", message=msg)
        if not unreachable:
            resolve_central_incidents(cluster="system", nerve="provider_health")
        for d in drift:
            msg = (f"model-drift: provider {d['provider']} havde {d['had']} modeller, nu 0 "
                   f"— model muligvis udfaset/omdøbt; tjek runtime-config")
            if not has_unresolved_message(cluster="system", nerve="provider_health", message=msg):
                record_central_incident(cluster="system", nerve="provider_health",
                                        kind="model_drift", severity="error", message=msg)
    except Exception:
        pass

    return {"status": "ok", "checked": snap.get("total_count"),
            "unreachable": len(unreachable), "degraded": len(degraded),
            "dry_cheap": len(dry), "model_drift": len(drift),
            "proactive_cooldowns": spread}


def build_provider_health_surface() -> dict[str, Any]:
    """Read-only provider-helbreds-surface til Jarvis Mind / terminal: ÉT kald → ping + tør +
    model-antal pr. provider. Self-safe."""
    snap = latest_health_snapshot()
    results = snap.get("results") if isinstance(snap.get("results"), dict) else {}
    dry = _cheap_dry_providers()
    providers: list[dict[str, Any]] = []
    for name, r in results.items():
        if not isinstance(r, dict):
            continue
        providers.append({
            "provider": name, "ok": bool(r.get("reachable")),
            "degraded": bool(r.get("reachable") and int(r.get("latency_ms") or 0) > _LATENCY_WARN_MS),
            "latency_ms": int(r.get("latency_ms") or 0),
            "model_count": 0,  # ping-surface bærer ikke model-antal (model_drift gør)
        })
    ok = sum(1 for p in providers if p["ok"])
    return {"active": True, "mode": "provider_health",
            "providers": providers, "dry_cheap": dry,
            "checked_at": snap.get("checked_at"),
            "summary": f"{ok}/{len(providers)} providers sunde" if providers else "ingen check endnu"}


def latest_health_snapshot() -> dict[str, Any]:
    """Read most-recent stored snapshot."""
    try:
        from core.runtime.state_store import load_json
        snap = load_json(_HEALTH_STATE_KEY, {})
        if isinstance(snap, dict):
            return snap
    except Exception:
        pass
    return {}


def health_section() -> str | None:
    """Awareness section listing providers that CANNOT be used — not just silent ones.

    2026-05-22 (Claude): dropped the `(check HH:MM:SS)` timestamp suffix.
    It was unique per build and broke DeepSeek's prompt cache at exactly
    the boundary where this section landed in the prompt. The model
    doesn't need the wall-clock time of the check — only the result.
    Time Pin gives the model wall time globally.

    28/10-2026: sektionen listede kun ``unreachable`` (helt tavse hosts). Målt samme dag
    meldte filen 8/8 sunde mens fem svarede med fejlkode — så sektionen var tavs om netop
    det den findes for. Nu nævnes auth-fejl og forkerte endpoints også, med deres årsag.
    """
    snap = latest_health_snapshot()
    unreachable = snap.get("unreachable") or []
    auth_failed = snap.get("auth_failed") or []
    wrong_endpoint = snap.get("wrong_endpoint") or []
    no_credentials = snap.get("no_credentials") or []
    if not (unreachable or auth_failed or wrong_endpoint or no_credentials):
        return None
    parts: list[str] = []
    if auth_failed:
        parts.append(f"auth-fejl ({', '.join(auth_failed)})")
    if wrong_endpoint:
        parts.append(f"forkert endpoint ({', '.join(wrong_endpoint)})")
    if no_credentials:
        parts.append(f"mangler nøgle ({', '.join(no_credentials)})")
    if unreachable:
        parts.append(f"unreachable ({', '.join(unreachable)})")
    healthy = snap.get("healthy_count")
    total = snap.get("total_count")
    head = f"{healthy}/{total} providers brugbare" if healthy is not None and total else "Provider health"
    return f"{head}: " + "; ".join(parts) + ". Cheap-lane fallback chain håndterer routing."


def _exec_run_health_check(args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "snapshot": health_check_all_providers()}


def _exec_get_health_snapshot(args: dict[str, Any]) -> dict[str, Any]:
    snap = latest_health_snapshot()
    if not snap:
        return {"status": "ok", "snapshot": None, "note": "no health check has run yet"}
    return {"status": "ok", "snapshot": snap}


PROVIDER_HEALTH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "provider_health_check",
            "description": (
                "Run a fresh ping against all cheap-lane provider endpoints "
                "(9 providers). Records reachability + latency in eventbus + "
                "state_store. Cheap (~5s total worst case)."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "provider_health_status",
            "description": "Read most-recent stored health snapshot without running new check.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
