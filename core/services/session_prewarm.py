"""Session-aware DeepSeek prefix cache warming (prewarm-on-return).

ROD (målt 2026-07-21): DeepSeeks prefix-cache af en sessions [system][historik]
UDLØBER under inaktivitet (~30-120 min). Første besked efter en pause prefiller
derfor hele ~32k-prompten fra bunden (cache-hit 16-48% vs 86-88% varm) → de
oplevede >10s. Den eksisterende ``scripts/primary_cache_warmer.py`` holder KUN
system-prefixen varm (via throwaway-session ``__prewarm__``) — aldrig en ægte
sessions historik. Så system-delen er 99.6% men sessions-historikken dør i pauser.

Dette modul varmer en KONKRET sessions fulde prefix [system][historik] når
brugeren vender tilbage (desk composer-fokus / jarvis-code input-fokus), så den
NÆSTE ægte besked rammer cachen i stedet for cold prefill. Byte-identisk prefix
med en ægte tur: vi genbruger den samme message-builder som visible-lanen selv
(``_build_visible_chat_messages_for_github`` inkl. DYNAMIC_TAIL_SENTINEL-splittet),
sender med ``max_tokens=1`` og smider svaret væk.

Self-safe: kaster ALDRIG, blokerer aldrig en tur, forurener aldrig sessionen
(ingen besked persisteres, ingen run oprettes, ingen eventbus-tur). Fire-and-forget.

Kun DeepSeek (eneste visible provider med prefix-disk-cache). Kill-switch:
runtime-state ``session_prewarm_enabled`` (default True).
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any, Callable
from urllib import error as urllib_error
from urllib import request as urllib_request

logger = logging.getLogger("session_prewarm")

_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
_ENABLED_KEY = "session_prewarm_enabled"
# Pr. session. MÅLT 24/10-2026: 45 s var for kort. Desk kalder /chat/warm på
# composer-fokus, så den fyrede 140 kald/time — $2,49 i døgnet — på at varme en
# cache der allerede havde 99,7 % hit (median). Modulets egen begrundelse siger
# at DeepSeeks prefix-cache udløber efter 30-120 min; at varme hvert 45. sekund
# kan derfor pr. definition ikke redde noget, den ikke allerede har.
# 20 min er stadig under udløbsvinduet, så en ægte pause-prewarm rammer, og
# dobbelt-fyring (fokus + første tastetryk) bliver stadig slået sammen til ét.
_COOLDOWN_S = 1200.0
_MAX_TOKENS = 1     # vi vil kun varme prefixen, ikke generere

# Per-session sidste-warm-stempel (in-process throttle).
_last_warm: dict[str, float] = {}
_last_warm_lock = threading.Lock()


def session_prewarm_enabled() -> bool:
    """Kill-switch via runtime-state (default True). Self-safe."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_ENABLED_KEY, True)
        return bool(v) if v is not None else True
    except Exception:
        return True


def _should_warm(session_id: str) -> bool:
    """Throttle pr. session: skip hvis varmet < _COOLDOWN_S siden."""
    now = time.monotonic()
    with _last_warm_lock:
        last = _last_warm.get(session_id)
        if last is not None and (now - last) < _COOLDOWN_S:
            return False
        _last_warm[session_id] = now
        # bounded: undgå ubegrænset vækst
        if len(_last_warm) > 512:
            for _k in sorted(_last_warm, key=_last_warm.get)[:256]:
                _last_warm.pop(_k, None)
    return True


def _deepseek_key() -> str | None:
    try:
        from core.runtime.secrets import read_runtime_key
        k = read_runtime_key("deepseek_api_key", env_override="DEEPSEEK_API_KEY")
        return str(k) if k else None
    except Exception:
        return None


def _post_deepseek(api_key: str, payload: dict[str, Any], *, timeout_s: int = 20) -> dict[str, Any] | None:
    """Minimal POST til deepseek /chat/completions. Returnerer body-dict eller None."""
    url = f"{_DEEPSEEK_BASE_URL}/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        logger.debug("session_prewarm: deepseek HTTP %s", getattr(exc, "code", "?"))
        return None
    except Exception as exc:
        logger.debug("session_prewarm: deepseek POST fejlede: %s", exc)
        return None


def warm_session_prefix(
    session_id: str,
    *,
    provider: str = "deepseek",
    # Tom = «den model den synlige lane bruger». Et haardkodet navn her ville
    # kunne drive fra `settings.visible_model_name` — og en warmer der varmer
    # en anden model end den der svarer, varmer ingenting. (Maalt 1/10-2026.)
    model: str = "",
    user_id: str = "",
    role: str = "owner",
    workspace_name: str = "bjorn",
    force: bool = False,
) -> dict[str, Any]:
    """Varm en sessions [system][historik]-prefix i DeepSeeks disk-cache.

    Bygger NØJAGTIG samme messages som en ægte visible-tur (samme builder +
    sentinel-split), sender med max_tokens=1 og kasserer svaret. Ingen
    persistering, ingen run, ingen tur. Self-safe — kaster aldrig.

    Returnerer en observability-dict: {status, cache_hit_tokens,
    cache_miss_tokens, input_tokens, elapsed_ms, reason?}.
    """
    if not model:
        from core.runtime.settings import load_settings
        from core.services.deepseek_modelnavne import KANONISK_FLASH
        model = str(load_settings().visible_model_name or "").strip() or KANONISK_FLASH

    from core.services.deepseek_modelnavne import kanoniser_model
    model = kanoniser_model(provider, model)

    t0 = time.monotonic()
    out: dict[str, Any] = {"status": "skipped", "session_id": session_id}
    try:
        sid = str(session_id or "").strip()
        if not sid:
            out["reason"] = "no-session"
            return out
        # Kun deepseek har den prefix-disk-cache vi varmer. Andre providere
        # (ollama:cloud = 0% cache; openai-compat = ingen/anden cache) → no-op.
        if str(provider or "").strip().lower() != "deepseek":
            out["reason"] = "provider-not-deepseek"
            return out
        if not session_prewarm_enabled():
            out["reason"] = "disabled"
            return out
        if not force and not _should_warm(sid):
            out["reason"] = "throttled"
            return out

        api_key = _deepseek_key()
        if not api_key:
            out["reason"] = "no-api-key"
            return out

        # Kontekst SKAL sættes: message-builderen bygger assembly'en som bruger
        # current_user_id() til recall/awareness. Uden det ville prefixen afvige
        # fra brugerens ægte tur → cachen ville ikke matche.
        from core.identity.workspace_context import set_context, reset_context
        from core.services.visible_model import _build_visible_chat_messages_for_github

        token = set_context(
            workspace_name=workspace_name or "bjorn",
            user_id=str(user_id or ""),
            role=str(role or "owner"),
            session_id=sid,
        )
        # is_prewarm_active()-flaget (tråd-lokalt) neutraliserer bivirkninger af
        # assembly-build'et: FREMFOR ALT auto_compact (så en cache-warm ALDRIG
        # compacter brugerens session) + telemetri. Se prompt_contract.py:1724.
        try:
            from core.services import assembly_prewarm as _apw
            _apw._local.prewarm_active = True
        except Exception:
            _apw = None
        try:
            messages = _build_visible_chat_messages_for_github(
                "(prewarm)", session_id=sid, provider="deepseek", model=model,
            )
        finally:
            try:
                if _apw is not None:
                    _apw._local.prewarm_active = False
            except Exception:
                pass
            try:
                reset_context(token)
            except Exception:
                pass

        if not messages:
            out["reason"] = "no-messages"
            return out

        # Thinking SLÅS FRA på warm-kaldet (vi genererer ikke, kun prefill-varme).
        # Prefixen (input-tokens) er uændret af thinking-flaget → cachen matcher stadig
        # den ægte tur uanset dens thinking-mode.
        extra: dict[str, Any] = {}
        try:
            from core.services.cheap_provider_runtime_adapters import deepseek_request_for_thinking_mode
            model, extra = deepseek_request_for_thinking_mode(model, "fast")
        except Exception:
            extra = {}

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": _MAX_TOKENS,
            "temperature": 0.0,
            "stream": False,
        }
        if isinstance(extra, dict):
            payload.update(extra)

        body = _post_deepseek(api_key, payload)
        if not body:
            out["status"] = "error"
            out["reason"] = "deepseek-call-failed"
            return out

        usage = body.get("usage") or {}
        hit = int(usage.get("prompt_cache_hit_tokens") or 0)
        miss = int(usage.get("prompt_cache_miss_tokens") or 0)
        inp = int(usage.get("prompt_tokens") or (hit + miss))
        outp = int(usage.get("completion_tokens") or 0)

        # Regnskab: eget provider-label så det er adskilt fra ægte trafik + fra
        # primary_cache_warmer (system-only). lane=primary så det tælles i den
        # synlige cache-metrik.
        # 24/10-2026: labelen ``session_cache_warmer`` findes IKKE som nøgle i
        # PRICING-tabellen, og ``record_cost`` beregner selv prisen på
        # ``(provider, model)`` når kalderen ikke giver en. Resultatet var 0,0:
        # målt over alle 25 kald 21.-22. juli blev 431.187 input-tokens bogført
        # som $0,00 — en udgift der fandtes men var usynlig i regnskabet.
        # Prisen beregnes derfor på DeepSeeks eget (provider, model) og sendes
        # med, mens labelen bevares så warmer-forbruget kan skelnes fra ægte
        # trafik. ``primary_cache_warmer`` gør det samme i sit script.
        try:
            from core.costing.ledger import record_cost
            from core.services.llm_pricing import compute_cost_usd

            _cost = compute_cost_usd(
                "deepseek", model,
                cache_hit_tokens=hit, cache_miss_tokens=miss,
                output_tokens=outp, input_tokens=inp,
            )
            if _cost <= 0.0 and (hit + miss) > 0:
                # Ukendt model-streng → compute_cost_usd giver 0,0, og udgiften
                # forsvinder tavst igen (målt 24/10: 'visible-placeholder' i
                # test-settings gav præcis det). Hellere en støjende linje end
                # et regnskab der ser gratis ud.
                logger.warning(
                    "session prewarm: kunne ikke prise model=%r (%d tokens) — "
                    "udgiften bogføres som 0,0", model, hit + miss,
                )
            record_cost(
                lane="primary", provider="session_cache_warmer", model=model,
                input_tokens=inp, output_tokens=outp, cost_usd=_cost,
                cache_hit_tokens=hit, cache_miss_tokens=miss,
                user_id=str(user_id or ""),
            )
        except Exception:
            pass

        out.update({
            "status": "ok",
            "cache_hit_tokens": hit,
            "cache_miss_tokens": miss,
            "input_tokens": inp,
        })
        return out
    except Exception as exc:
        out["status"] = "error"
        out["reason"] = f"{type(exc).__name__}: {exc}"[:200]
        return out
    finally:
        out["elapsed_ms"] = int((time.monotonic() - t0) * 1000)


def warm_session_prefix_async(
    session_id: str,
    **kwargs: Any,
) -> None:
    """Fire-and-forget: kør warm_session_prefix i en GENBRUGT daemon-tråd.

    Blokerer aldrig kalderen (endpoint returnerer straks). Self-safe.

    ROD (målt 18/10-2026): denne funktion startede en NY tråd pr. kald. Hver
    tråd åbner sin egen thread-lokale SQLite-forbindelse (``db_core._conn_pool``
    er ``threading.local()``), og ``sqlite3`` nægter at lade en anden tråd lukke
    den. Målt i drift: ``session-prewarm`` stod for 172 af api-processens 374
    pool-fødsler på 9 minutter — 46 %, mere end nogen anden tråd. Warmeren kaldes
    per chat-tur, så det var ~én ny forbindelse pr. tur oveni selve turen.

    Fixet er samme mønster som cadence-workerne (04fe9b08f) og heartbeat-puljen:
    én langlivet tråd med egen kø. Tråden — og dermed dens DB-forbindelse —
    genbruges, og den udløber efter ``_WORKER_TTL_S`` uden arbejde, så antallet
    falder tilbage til nul i stille perioder.
    """
    def _run() -> None:
        try:
            res = warm_session_prefix(session_id, **kwargs)
            if res.get("status") == "ok":
                logger.info(
                    "session_prewarm: session=%s hit=%s miss=%s in=%s %dms",
                    session_id[:16], res.get("cache_hit_tokens"), res.get("cache_miss_tokens"),
                    res.get("input_tokens"), res.get("elapsed_ms", 0),
                )
        except Exception:
            logger.debug("session_prewarm: async warm fejlede", exc_info=True)

    try:
        _dispatch(_run)
    except Exception:
        logger.debug("session_prewarm: kunne ikke aflevere warm-opgave", exc_info=True)


# ---------------------------------------------------------------------------
# Genbrugt worker-tråd (18/10-2026)
# ---------------------------------------------------------------------------
#
# Hvorfor ikke ThreadPoolExecutor: dens workers er NON-daemon, og dens
# atexit-handler joiner dem ved interpreter-exit — en warm der hænger på et
# DeepSeek-kald ville kunne blokere en genstart. Rå daemon-tråde gør ikke.
#
# Designet er heartbeat-puljens (heartbeat_runtime._daemon_pool_*), men holdt
# lokalt: denne fil må ikke importere heartbeat-laget for at varme en cache.
#   - Er tråden ledig, får den opgaven (genbrug → samme DB-forbindelse).
#   - Er den optaget, får opgaven sin EGEN tråd. En warm der hænger må aldrig
#     blokere den næste brugers warm — det ville gøre en optimering til en
#     flaskehals.
#   - En tråd der ikke bliver færdig inden sin deadline gives ALDRIG tilbage
#     til puljen; den dør efter TTL.
_WORKER_TTL_S = 30.0
_WORKER_LOCK = threading.Lock()
_WORKER_IDLE: list[tuple[threading.Thread, "queue.Queue"]] = []
_WORKER_STATS: dict[str, int] = {"spawned": 0, "reused": 0}


def _worker_loop(task_q: "queue.Queue") -> None:
    """Kør opgaver fra egen kø indtil TTL udløber uden nyt arbejde."""
    while True:
        try:
            item = task_q.get(timeout=_WORKER_TTL_S)
        except queue.Empty:
            # Dobbelt-tjek under låsen: en submitter kan have lagt en opgave i
            # vinduet mellem at vi fik Empty og nu. Fjern os selv fra _IDLE og
            # afslut KUN hvis køen stadig er tom.
            with _WORKER_LOCK:
                try:
                    item = task_q.get_nowait()
                except queue.Empty:
                    for i, (_t, q) in enumerate(_WORKER_IDLE):
                        if q is task_q:
                            _WORKER_IDLE.pop(i)
                            break
                    return
        if item is None:
            return
        try:
            item()
        except Exception:
            # opgaven fanger selv; sidste værn mod at dræbe workeren
            pass


def _dispatch(job: Callable[[], None]) -> None:
    """Giv opgaven til den ledige worker — eller føds en frisk.

    Opgaven lægges i køen MENS låsen holdes. Ellers kan en tråd der er ved at
    udløbe sin TTL nå at fjerne sig selv og dø i vinduet mellem at vi tog den
    fra _IDLE og til vi lagde opgaven — og så ville opgaven aldrig blive løst.

    Tråden lægges SELV tilbage i puljen når opgaven er færdig. Det er dét der
    gør genbrug muligt: uden tilbagelægningen ville hvert kald føde en ny tråd —
    og dermed en ny DB-forbindelse — præcis som før fixet.
    """
    with _WORKER_LOCK:
        while _WORKER_IDLE:
            t, q = _WORKER_IDLE.pop()
            if not t.is_alive():
                continue  # død eller døende — smid væk, prøv næste
            q.put_nowait(_wrap(job, t, q))
            _WORKER_STATS["reused"] += 1
            return
        q = queue.Queue(maxsize=1)
        t = threading.Thread(
            target=_worker_loop,
            args=(q,),
            name="session-prewarm",
            daemon=True,
        )
        t.start()
        q.put_nowait(_wrap(job, t, q))
        _WORKER_STATS["spawned"] += 1


def _wrap(job: Callable[[], None], t: threading.Thread, q: "queue.Queue") -> Callable[[], None]:
    """Pak opgaven ind med tilbagelægning til puljen — også når den fejler."""
    def _wrapped() -> None:
        try:
            job()
        finally:
            _release_worker(t, q)
    return _wrapped


def _release_worker(t: threading.Thread, q: "queue.Queue") -> None:
    """Læg tråden tilbage i puljen, så næste kald kan genbruge den."""
    with _WORKER_LOCK:
        _WORKER_IDLE.append((t, q))


def _worker_stats() -> dict[str, int]:
    """Observability: hvor mange tråde er født vs. genbrugt. Self-safe."""
    with _WORKER_LOCK:
        return {**_WORKER_STATS, "idle": len(_WORKER_IDLE)}
