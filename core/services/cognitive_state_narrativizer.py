"""LLM-based narrativizer for cognitive state lines.

Replaces the hardcoded danish template strings in
`cognitive_state_assembly.py` with LLM-generated narratives grounded
in the actual runtime data. Uses the local lane (cheap LLM) and
caches output by state-fingerprint so we never call the model more
than necessary.

Design principles:
- Real data in, real narrative out — no static fallback templates
  unless the LLM fails entirely.
- Cache by fingerprint of the *input state*, not by time. The
  narrative only changes when the underlying state changes.
- Background refresh: callers always get an immediate cached value;
  refresh happens off the request path.
- Bounded: each line is one short Danish sentence. We never let the
  LLM ramble.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable
from urllib import request as urllib_request

from core.services.text_clip import clip_text

logger = logging.getLogger(__name__)

# Local-lane model used for narrative generation. This stays on the
# Ollama path, but points at the currently selected cloud-backed local
# target so we do not need a resident local 8B model in VRAM.
_NARRATIVIZER_MODEL = "glm-5.1:cloud"
_NARRATIVIZER_BASE_URL = "http://127.0.0.1:11434"
_NARRATIVIZER_TIMEOUT_SECONDS = 25
_NARRATIVIZER_MAX_TOKENS = 80


def _call_narrativizer_llm(system_prompt: str, user_message: str) -> str | None:
    """Call the compact LLM (heartbeat model) for narrative line generation.

    Uses call_compact_llm so the narrativizer automatically follows
    whatever heartbeat model is configured (e.g. Groq) instead of
    being hardcoded to a slow cloud-backed Ollama model.
    """
    try:
        from core.context.compact_llm import call_compact_llm

        prompt = f"{system_prompt}\n\n{user_message}"
        result = call_compact_llm(prompt, max_tokens=_NARRATIVIZER_MAX_TOKENS)
        text = (result or "").strip()
        if not text:
            return None

        # En udbyders fejlbesked maa ALDRIG blive til Jarvis' selvbeskrivelse.
        #
        # FUNDET LIVE 2026-09-01: injektionen `cognitive_state` havde staaende
        #     [COGNITIVE STATE] [SELF] Sorry, to prevent abuse of free
        #     resources, accounts that have not been recharged can only try 10
        #     times... https://console.aihubmix.com/topup
        # Altsaa en regning fra aihubmix skrevet ind i [SELF]-ankeret. Kaeden:
        # primaer-lane fejlede paa tom auth-profil ("Profile name must be a
        # simple non-empty identifier"), kaldet faldt til cheap-lane, ramte
        # aihubmix' gratis-kvote, og fejlteksten blev gemt som hans selv.
        #
        # Samme vagt som provider_error_guard giver den synlige chat (604b3c34)
        # — men DENNE sti gik udenom, og her er indsatsen hoejere: en fejl i
        # chatten er pinlig, en fejl i [SELF] er noget han BAERER videre.
        try:
            from core.services.provider_error_guard import (
                describe, looks_like_provider_error,
            )
            if looks_like_provider_error(text):
                logger.warning(
                    "cognitive_state_narrativizer: udbyder-fejl afvist som "
                    "narrativ (%s)", describe(text))
                return None
        except Exception:
            pass
        return text or None
    except Exception as exc:
        logger.warning("cognitive_state_narrativizer ollama call failed: %s", exc)
        return None

# How long a cached narrative survives without input-state change.
# After this it is considered "stale" and will be regenerated on the
# next read regardless of fingerprint.
_CACHE_TTL_SECONDS = 30 * 60  # 30 min hard cap

# How long we wait before allowing a *new* fingerprint to fire its
# own LLM call (per-line cooldown so we don't hammer ollama).
_PER_LINE_COOLDOWN_SECONDS = 8


@dataclass(slots=True)
class _CachedNarrative:
    fingerprint: str
    narrative: str
    generated_at: float


@dataclass(slots=True)
class _Job:
    """Ét ventende genererings-job. ``seq`` afgør hvilken version der vinder."""

    seq: int
    fingerprint: str
    system_prompt: str
    user_message: str


# line_key → cached narrative
_CACHE: dict[str, _CachedNarrative] = {}
# line_key → seq for det svar der ligger i _CACHE. Et ældre job må ikke
# overskrive et nyere svar der allerede er skrevet.
_CACHE_SEQ: dict[str, int] = {}
_LAST_LLM_CALL_AT: dict[str, float] = {}
_CACHE_LOCK = threading.Lock()
_REFRESH_INFLIGHT: set[str] = set()

# Sekventiel worker (24/10-2026).
#
# FØR: `_generate_in_background` startede én ny daemon-tråd per kald. Fem
# linjer der skiftede state i samme tick gav derfor fem samtidige
# `call_compact_llm`-kæder, som hver byggede hele kandidatlisten (auth-scan +
# `list_cheap_provider_runtime_states`) og konkurrerede om GIL'en. Målt med
# py-spy midt i en byge: fem `Thread-N (_worker)` i samme kæde, 6-9 µs
# CPU-slices, 25.000-30.000 slices pr. tråd, peak 249 %.
#
# NU: én delt worker. Køen er coalescing — højst ét ventende job per
# `line_key`, og det nyeste fingerprint erstatter et ældre ventende job.
# Workeren er daemon, så en langsom LLM-kørsel kan ikke holde processtop
# tilbage; `shutdown()` giver alligevel en kontrolleret afslutning.
_PENDING: dict[str, _Job] = {}
_RUNNING: dict[str, str] = {}  # line_key → fingerprint der kører nu
_WAKE = threading.Event()
_STOP = threading.Event()
_WORKER: threading.Thread | None = None


def _fingerprint(state: dict[str, object]) -> str:
    blob = json.dumps(state, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(blob, usedforsecurity=False).hexdigest()[:16]


def _run_job(line_key: str, job: _Job) -> None:
    """Kør ét job: LLM-kaldet sker UDEN lås, cachen skrives under den."""
    try:
        text = _call_narrativizer_llm(job.system_prompt, job.user_message)
    except Exception as exc:  # pragma: no cover
        logger.warning("cognitive narrativizer LLM call failed: %s", exc)
        text = None
    if not text:
        return
    cleaned = " ".join(text.strip().split())
    if len(cleaned) > 240:
        cleaned = clip_text(cleaned, limit=240)
    with _CACHE_LOCK:
        # Et nyere job kan være kørt færdigt mens dette kald var i gang —
        # så må det gamle svar ikke overskrive det friske.
        if job.seq < _CACHE_SEQ.get(line_key, 0):
            return
        _CACHE_SEQ[line_key] = job.seq
        _CACHE[line_key] = _CachedNarrative(
            fingerprint=job.fingerprint,
            narrative=cleaned,
            generated_at=time.time(),
        )


def _worker_loop() -> None:
    """Tag ét job ad gangen. Aldrig to LLM-kald samtidig."""
    while not _STOP.is_set():
        line_key = ""
        job: _Job | None = None
        with _CACHE_LOCK:
            if _PENDING:
                line_key = next(iter(_PENDING))
                job = _PENDING.pop(line_key)
                _RUNNING[line_key] = job.fingerprint
        if job is None:
            _WAKE.clear()
            with _CACHE_LOCK:
                has_work = bool(_PENDING)
            if not has_work and not _STOP.is_set():
                _WAKE.wait(timeout=0.5)
            continue
        try:
            _run_job(line_key, job)
        except Exception:  # pragma: no cover
            logger.exception(
                "cognitive narrativizer worker fejlede for %s", line_key
            )
        finally:
            with _CACHE_LOCK:
                _RUNNING.pop(line_key, None)
                if line_key not in _PENDING:
                    _REFRESH_INFLIGHT.discard(line_key)


def _ensure_worker_locked() -> None:
    """Start den delte worker hvis den ikke kører. Kaldes med ``_CACHE_LOCK``."""
    global _WORKER
    if _STOP.is_set():
        return
    if _WORKER is not None and _WORKER.is_alive():
        return
    _WORKER = threading.Thread(
        target=_worker_loop,
        name="cognitive-narrativizer",
        daemon=True,
    )
    _WORKER.start()


def _enqueue(
    *,
    line_key: str,
    fingerprint: str,
    system_prompt: str,
    user_message: str,
) -> bool:
    """Læg et job i den delte worker-kø. Seneste fingerprint vinder.

    Returnerer False hvis et nyere job allerede ligger i køen, hvis workeren
    er stoppet, eller hvis enqueue fejlede — i alle tilfælde ryddes
    ``_REFRESH_INFLIGHT`` så linjen ikke hænger permanent som "i gang" uden at
    noget sker.

    24/10-2026: ``_STOP``-tjekket ligger INDE i låsen. Før kunne et job lægges
    i køen efter ``shutdown()``: ``_ensure_worker_locked`` returnerer stille når
    flaget er sat, så jobbet blev stående for evigt og ``_REFRESH_INFLIGHT``
    holdt linjen låst. Tjekket skal være atomisk med ``shutdown()``, som sætter
    flaget under samme lås.
    """
    job = _Job(
        seq=time.monotonic_ns(),
        fingerprint=fingerprint,
        system_prompt=system_prompt,
        user_message=user_message,
    )
    try:
        with _CACHE_LOCK:
            if _STOP.is_set():
                # Workeren er stoppet — intet ville nogensinde tage jobbet.
                # Afvis før det lægges i køen, så der ikke opstår et
                # spøgelsesjob eller en permanent _REFRESH_INFLIGHT-lås.
                return False
            current = _PENDING.get(line_key)
            if current is not None and current.seq > job.seq:
                return False
            _PENDING[line_key] = job
            _REFRESH_INFLIGHT.add(line_key)
            _ensure_worker_locked()
        _WAKE.set()
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "cognitive narrativizer enqueue failed for %s: %s", line_key, exc
        )
        with _CACHE_LOCK:
            _PENDING.pop(line_key, None)
            _REFRESH_INFLIGHT.discard(line_key)
        return False


def _generate_in_background(
    *,
    line_key: str,
    fingerprint: str,
    system_prompt: str,
    user_message: str,
) -> None:
    """Læg genereringen i den delte sekventielle worker-kø.

    Navn og signatur er bevaret fra tråd-per-kald-modellen, så eksisterende
    kald og tests ikke skal ændres — men der startes ikke længere en tråd per
    kald.
    """
    _enqueue(
        line_key=line_key,
        fingerprint=fingerprint,
        system_prompt=system_prompt,
        user_message=user_message,
    )


def shutdown(timeout: float = 5.0) -> None:
    """Stop den delte worker kontrolleret.

    Workeren er daemon, så en igangværende LLM-kørsel kan ikke holde
    processtop tilbage — men vi venter op til ``timeout`` sekunder på at den
    falder til ro, og tømmer køen så ventende jobs ikke startes bagefter.
    """
    global _WORKER
    with _CACHE_LOCK:
        worker = _WORKER
        # 24/10-2026: `_STOP.set()` SKAL ligge inde i låsen — ikke efter den.
        # Før stod den uden for, så en samtidig `_enqueue()` kunne få låsen i
        # vinduet mellem `_REFRESH_INFLIGHT.clear()` og `_STOP.set()`, se
        # `_STOP=False` og lægge et job i køen efter shutdown var begyndt.
        # `_enqueue()` tjekker flaget under samme lås, så placeringen her er
        # det der gør de to atomiske i forhold til hinanden.
        _STOP.set()
        _PENDING.clear()
        _REFRESH_INFLIGHT.clear()
    _WAKE.set()
    if worker is not None:
        worker.join(timeout=timeout)
    with _CACHE_LOCK:
        _WORKER = None


def _reset_for_tests() -> None:
    """Nulstil al tilstand inkl. stop-flaget. Kun til tests."""
    global _WORKER
    shutdown(timeout=2.0)
    with _CACHE_LOCK:
        _CACHE.clear()
        _CACHE_SEQ.clear()
        _LAST_LLM_CALL_AT.clear()
        _PENDING.clear()
        _RUNNING.clear()
        _REFRESH_INFLIGHT.clear()
        _WORKER = None
        _STOP.clear()
        _WAKE.clear()


def narrativize_line(
    *,
    line_key: str,
    state: dict[str, object],
    system_prompt: str,
    user_message_builder: Callable[[], str],
    fallback: str | None = None,
) -> str | None:
    """Return an LLM-narrativized line for this state, or fallback.

    The first time a fingerprint is seen the LLM call is dispatched
    asynchronously and the fallback (or previous cached narrative) is
    returned. Subsequent calls with the same fingerprint return the
    cached narrative immediately.

    Args:
        line_key: Stable identifier for this line type
            (e.g. "body", "affect", "self_anchor").
        state: The actual runtime state dict that this line narrativizes.
        system_prompt: Bounded system instructions for the LLM.
        user_message_builder: Lazy builder for the user message — only
            called when we actually need to fire an LLM call.
        fallback: Optional fallback string if no narrative is cached
            yet. If None, the line is omitted on first cold start.
    """
    fingerprint = _fingerprint(state)
    now = time.time()

    with _CACHE_LOCK:
        cached = _CACHE.get(line_key)
        last_call = _LAST_LLM_CALL_AT.get(line_key, 0.0)
        cache_fresh = (
            cached is not None
            and cached.fingerprint == fingerprint
            and (now - cached.generated_at) < _CACHE_TTL_SECONDS
        )
        cooling = (now - last_call) < _PER_LINE_COOLDOWN_SECONDS
        pending = _PENDING.get(line_key)
        running_fp = _RUNNING.get(line_key)
        if cache_fresh:
            return cached.narrative

        # Coalescing: venter der allerede et job for denne linje med et ANDET
        # fingerprint, erstatter det nye det — uden at tælle som et nyt
        # LLM-kald. Fem linjer kan skifte state mens de venter, og kun det
        # nyeste svar er værd at betale for.
        coalesce = pending is not None and pending.fingerprint != fingerprint
        # Kører der et job for linjen med et andet fingerprint, lægges det nye
        # bagefter i køen i stedet for at gå tabt.
        supersede_running = running_fp is not None and running_fp != fingerprint
        should_dispatch = False
        if coalesce:
            should_dispatch = True
        elif not cooling and (
            supersede_running or (running_fp is None and pending is None)
        ):
            _LAST_LLM_CALL_AT[line_key] = now
            should_dispatch = True

    if should_dispatch:
        try:
            user_message = user_message_builder()
        except Exception as exc:
            logger.warning(
                "cognitive narrativizer user message build failed for %s: %s",
                line_key,
                exc,
            )
            with _CACHE_LOCK:
                _REFRESH_INFLIGHT.discard(line_key)
        else:
            _generate_in_background(
                line_key=line_key,
                fingerprint=fingerprint,
                system_prompt=system_prompt,
                user_message=user_message,
            )

    # Return previous cached narrative if any (even with stale
    # fingerprint) — better than nothing while the new one is
    # generating.
    if cached is not None and cached.narrative:
        return cached.narrative
    return fallback


def cache_snapshot() -> dict[str, dict[str, object]]:
    """Expose current cache state for MC observability."""
    with _CACHE_LOCK:
        return {
            key: {
                "fingerprint": item.fingerprint,
                "generated_at": item.generated_at,
                "narrative": item.narrative,
            }
            for key, item in _CACHE.items()
        }
