"""Struktureret failure-taksonomi for streaming/followup (spec §11.1 B11, I5).

Dette er den ENE sandhedskilde for HVILKEN slags fejl en streaming-runde led,
og om den er retryable. Fase 1's rund-niveau-retry (§4.1) afhænger af et
struktureret ``failure_kind`` + ``http_status`` — ikke substring-matching på en
fri-tekst ``summary`` (det gamle mønster, B11). Modulet er FOKUSERET og uden
side-effekter, så det kan genbruges af BÅDE ``visible_followup.py`` (adapterne +
dispatcheren) OG ``visible_runs.py`` (pump-except-stien + watchdog'en).

Spejler Codex' ``is_retryable()``-split (spec §1B, §4.2, D11):

- **retryable (samme provider):**
    ``transient_drop``           — stream lukket før done / socket / ConnectionError
    ``http_5xx``                 — 500/502/503/504
    ``http_429``                 — rate-limit
    ``malformed_stream_payload`` — split-UTF-8 / malformet JSON-chunk (A11)
- **provider_stall** (silence/idle-timeout, D11): EGEN kind der IKKE auto-retries
  på SAMME provider — en stallet provider re-trigger blot samme timeout. Skal i
  stedet gå til circuit-breaker/failover (S6). Markeret retryable=False her.
- **fatal (re-sampling hjælper aldrig):**
    ``http_400_overflow``        — context-window / "prompt too long" (S5)
    ``http_4xx``                 — 400/401/403/404/422 invalid_request
    ``invalid_request``          — build-fejl / unsupported-provider / 422-klasse
    ``user_cancel``              — bruger trykkede Cancel

INTET her ERSTATTER endnu nogen eksisterende beslutning — modulet LEVERER blot
funktionen + de kanoniske konstanter. Wiring sker additivt.
"""
from __future__ import annotations

import json
import random
import re
from typing import Final


class FailureKind:
    """Kanoniske failure-kind-strenge (str-const set fremfor Enum så de
    serialiseres trivielt ind i nerver/SSE/incidents uden ``.value``-dans)."""

    # ── retryable på samme provider ──────────────────────────────────────────
    TRANSIENT_DROP: Final = "transient_drop"
    HTTP_5XX: Final = "http_5xx"
    HTTP_429: Final = "http_429"
    MALFORMED_STREAM_PAYLOAD: Final = "malformed_stream_payload"

    # ── stall: retryable-LOOKING men IKKE auto-retry på samme provider (D11) ─
    PROVIDER_STALL: Final = "provider_stall"

    # ── fatal ────────────────────────────────────────────────────────────────
    HTTP_400_OVERFLOW: Final = "http_400_overflow"
    HTTP_4XX: Final = "http_4xx"
    INVALID_REQUEST: Final = "invalid_request"
    USER_CANCEL: Final = "user_cancel"

    # ── ukendt/uklassificeret (konservativt fatal) ──────────────────────────
    UNKNOWN: Final = "unknown"


# Kinds der 4.1 må retry'e på SAMME provider. provider_stall er BEVIDST IKKE her
# (D11): den re-trigger blot samme timeout → circuit-breaker/failover i stedet.
_RETRYABLE_KINDS: Final = frozenset({
    FailureKind.TRANSIENT_DROP,
    FailureKind.HTTP_5XX,
    FailureKind.HTTP_429,
    FailureKind.MALFORMED_STREAM_PAYLOAD,
})


# Substring-signaturer for de tilfælde hvor vi KUN har fri-tekst (legacy
# summary/exception-streng) og ingen struktureret http_status/kind_hint.
# Bevidst smal — kun høj-signal-fragmenter.
_CONTEXT_OVERFLOW_PATTERNS: Final = (
    "prompt is too long",
    "prompt too long",
    "context_length_exceeded",
    "context length",
    "context window",
    "maximum context",
)
_STALL_PATTERNS: Final = (
    "silence",
    "idle",
    "stall",
    "timed out waiting",
    "no bytes",
    "first-byte",
)
_TRANSIENT_PATTERNS: Final = (
    "closed before",
    "connection reset",
    "connection aborted",
    "connection error",
    "broken pipe",
    "stream drop",
    "stream closed",
    "socket",
    "urlerror",
    "remotedisconnected",
    "incompleteread",
    "transient",
)
_MALFORMED_PATTERNS: Final = (
    "malformed",
    "expecting value",
    "jsondecode",
    "invalid json",
    "unicodedecode",
    "codec can't decode",
)
_TIMEOUT_PATTERNS: Final = (
    "timed out",
    "timeout",
    "read timed out",
)

# httpx/urllib status fra fri-tekst når kalderen ikke gav os http_status.
_HTTP_STATUS_RE: Final = re.compile(r"\bhttp\s*(?:error\s*)?(\d{3})\b", re.IGNORECASE)


def _scan_http_status(text: str) -> int | None:
    m = _HTTP_STATUS_RE.search(text or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


def _contains(text: str, needles: tuple[str, ...]) -> bool:
    return any(n in text for n in needles)


def classify_failure(
    *,
    http_status: int | None = None,
    error_text: str = "",
    kind_hint: str = "",
) -> tuple[str, bool]:
    """Klassificér en streaming/followup-fejl → (failure_kind, retryable).

    DEN ENE sandhedskilde for retryability (I5). Ingen anden kode må selv beslutte
    om en fejl er retryable — kald dette.

    Parametre:
      - ``http_status``: HTTP-koden hvis kendt (urllib/httpx). None = ukendt
        (typisk transport-drop / lokal exception).
      - ``error_text``: fejl-/summary-strengen (exception-str eller adapter-summary).
        Bruges til substring-klassifikation når ``http_status``/``kind_hint`` ikke
        er nok (legacy-stier der kun har fri-tekst).
      - ``kind_hint``: et EKSPLICIT hint fra kalderen (fx "user_cancel",
        "provider_stall", "transient_drop", "malformed_stream_payload"). Vinder
        over alt andet når det er et kendt kind — bruges hvor kalderen VED hvad
        der skete (watchdog-silence, bruger-cancel, decoder-exception).

    Returnerer ``(failure_kind, retryable)``. retryable=True KUN for de fire
    same-provider-retryable kinds; provider_stall + alle fatal-kinds → False.
    """
    text = (error_text or "").strip().lower()
    hint = (kind_hint or "").strip().lower()

    # 1) Eksplicit hint vinder (kalderen VED hvad der skete). Kun for kendte kinds.
    _all_kinds = {
        FailureKind.TRANSIENT_DROP, FailureKind.HTTP_5XX, FailureKind.HTTP_429,
        FailureKind.MALFORMED_STREAM_PAYLOAD, FailureKind.PROVIDER_STALL,
        FailureKind.HTTP_400_OVERFLOW, FailureKind.HTTP_4XX,
        FailureKind.INVALID_REQUEST, FailureKind.USER_CANCEL,
    }
    if hint in _all_kinds:
        return hint, hint in _RETRYABLE_KINDS

    # 2) Bruger-cancel (fri-tekst) → fatal, aldrig retry.
    if "cancel" in text or "aborted by user" in text:
        return FailureKind.USER_CANCEL, False

    # 3) Hvis vi ikke fik http_status struktureret, prøv at læse den ud af teksten.
    status = http_status
    if status is None:
        status = _scan_http_status(text)

    # 4) HTTP-status-baseret klassifikation (struktureret > fri-tekst).
    if status is not None:
        if status == 429:
            return FailureKind.HTTP_429, True
        if status in (500, 502, 503, 504):
            return FailureKind.HTTP_5XX, True
        if status >= 500:
            # Andre 5xx (501/505/...) — behandl som transient 5xx-klasse.
            return FailureKind.HTTP_5XX, True
        if status == 400:
            # 400 kan være enten context-overflow (overflow er sin egen S5-kind)
            # eller generisk invalid_request — begge fatal, men distinkte.
            if _contains(text, _CONTEXT_OVERFLOW_PATTERNS):
                return FailureKind.HTTP_400_OVERFLOW, False
            return FailureKind.HTTP_4XX, False
        if status in (401, 403, 404, 422):
            return FailureKind.HTTP_4XX, False
        if 400 <= status < 500:
            return FailureKind.HTTP_4XX, False

    # 5) Ingen status — klassificér på fri-tekst-signatur.
    #    Rækkefølge betyder noget: overflow > malformed > stall > transient >
    #    generisk timeout. (Overflow-strenge kan også indeholde "context" som
    #    ikke skal forveksles med stall.)
    if _contains(text, _CONTEXT_OVERFLOW_PATTERNS):
        return FailureKind.HTTP_400_OVERFLOW, False
    if _contains(text, _MALFORMED_PATTERNS):
        return FailureKind.MALFORMED_STREAM_PAYLOAD, True
    if _contains(text, _STALL_PATTERNS):
        # Silence/idle/first-byte-watchdog → provider_stall (D11): IKKE auto-retry.
        return FailureKind.PROVIDER_STALL, False
    if _contains(text, _TRANSIENT_PATTERNS):
        return FailureKind.TRANSIENT_DROP, True
    if _contains(text, _TIMEOUT_PATTERNS):
        # Et nøgent "timed out" UDEN stall-kontekst behandles konservativt som et
        # forbigående transport-drop (read-timeout midt i en ellers sund stream).
        return FailureKind.TRANSIENT_DROP, True

    # 6) Intet matchede → ukendt. Konservativt FATAL (vi retry'er ikke noget vi
    #    ikke forstår; ellers risikerer vi at brænde budget på en ægte fatal fejl).
    return FailureKind.UNKNOWN, False


def is_retryable_kind(failure_kind: str) -> bool:
    """Er ``failure_kind`` retryable på SAMME provider? (provider_stall = False.)"""
    return (failure_kind or "").strip().lower() in _RETRYABLE_KINDS


# ── Delt backoff-helper (spec §11.2: ÉN sandhedskilde med jitter) ────────────
#
# Spec'en flaggede at den eksisterende ollama-backoff (visible_followup.py) er
# ren eksponentiel UDEN jitter → thundering-herd mod en haltende provider når
# mange runs retry'er i lås. Denne helper er den ENE kilde: både den løftede
# ollama-retry OG Fase 1's rund-niveau-retry (4.1) arver jitter herfra.

# OpenAI-SDK-paritet: min(base · 2^n, cap) + fuld jitter.
_BACKOFF_BASE_S: Final = 0.6
_BACKOFF_CAP_S: Final = 8.0


def compute_backoff_with_jitter(
    attempt: int,
    *,
    base: float = _BACKOFF_BASE_S,
    cap: float = _BACKOFF_CAP_S,
    retry_after: float | None = None,
) -> float:
    """Eksponentiel backoff MED jitter (spec §11.2, OpenAI-SDK-mønster).

    - ``attempt``: 0-indekseret forsøgsnummer (0 = første retry).
    - ``base``/``cap``: ``min(base · 2^attempt, cap)``.
    - ``retry_after``: hvis serveren sendte en (allerede-parset) Retry-After i
      sekunder, brug den som GULV (vi venter mindst så længe), men læg stadig
      jitter på så samtidige runs ikke rammer i lås.

    Returnerer ventetiden i sekunder (≥0). Fuld jitter: et tilfældigt punkt
    mellem 0 og det beregnede tag, så retries spredes (anti-thundering-herd).
    """
    try:
        a = max(0, int(attempt))
    except (TypeError, ValueError):
        a = 0
    raw = min(float(base) * (2 ** a), float(cap))
    # Fuld jitter (AWS "Exponential Backoff And Jitter"): uniform(0, raw).
    delay = random.uniform(0.0, raw) if raw > 0 else 0.0
    if retry_after is not None:
        try:
            floor = max(0.0, float(retry_after))
        except (TypeError, ValueError):
            floor = 0.0
        # Respektér cooldown'en (gulv) men spred stadig med lidt jitter ovenpå.
        delay = max(delay, floor + random.uniform(0.0, min(raw, 1.0)))
    return delay


# ── A11: hærdet line/SSE-decode (spec §1A + §11.1 A11) ───────────────────────
#
# Den EGNE SSE/NDJSON-decoder kunne FØR dræbe streamen mid-turn på to måder:
#   (1) et UTF-8 multibyte-codepoint splittet over en netværks-chunk-grænse
#       (æøå/emoji = Jarvis' normale stemme) → ``raw_line.decode("utf-8")``
#       rejste ``UnicodeDecodeError`` ud af generatoren.
#   (2) en HTTP-200-så-malformet/trunkeret JSON ``data:``-linje → ``json.loads``
#       rejste ``JSONDecodeError`` ud af generatoren.
# Begge var USYNLIGE for rund-niveau-retry'en (4.1): det er generator-exceptions,
# ikke ``FollowupFailed``. Disse to helpers er den ENE delte, self-safe sti, så
# ALLE parse-sites (first-pass ollama, _iter_sse_events, followup-adapteren)
# opfører sig ens.


class MalformedStreamPayload(Exception):
    """Streamen sluttede malformet (trunkeret final-JSON / ingen terminal/``done``)
    EFTER vi har sprunget ≥1 dårlig chunk over. Bæres op som typed retryable
    ``malformed_stream_payload`` så 4.1's rund-retry kan fange den — i modsætning
    til en enkelt-chunk-skip der bare fortsætter på en ellers sund stream."""


def safe_decode_line(raw_line: bytes | str) -> str:
    """Decode én rå stream-linje UDEN nogensinde at rejse.

    ``errors="replace"`` betyder at et split multibyte-codepoint bliver til ét
    erstatnings-tegn (U+FFFD) i stedet for at dræbe hele streamen — et erstattet
    tegn er uendeligt bedre end et dødt svar (spec §11.1 A11, pkt. 1). De fleste
    splits heler desuden af sig selv på næste linje fordi providerne sender hele
    JSON-objekter pr. NDJSON-linje / komplette ``data:``-blokke."""
    if isinstance(raw_line, str):
        return raw_line
    try:
        return raw_line.decode("utf-8", errors="replace")
    except Exception:
        # Bytes der ikke engang kan replace-decodes (ekstremt sjældent) — fald
        # tilbage til latin-1 som ALDRIG rejser, hellere mojibake end dødt stream.
        try:
            return raw_line.decode("latin-1", errors="replace")
        except Exception:
            return ""


def try_parse_json_line(data: str) -> tuple[dict | None, bool]:
    """Parse én JSON ``data:``-streng → ``(payload, ok)``, ALDRIG rejsende.

    - ``(dict, True)``  : gyldigt objekt.
    - ``(None, True)``  : tom/whitespace-streng (ingen fejl — bare ikke noget at parse).
    - ``(None, False)`` : malformet/trunkeret JSON. Kalderen afgør skip-vs-fail:
        en enkelt dårlig chunk midt i en ellers sund stream → SKIP (continue) +
        let observe; men hvis streamen SLUTTER uden terminal/``done`` efter ≥1 skip
        → bæres op som :class:`MalformedStreamPayload` (retryable).

    Returnerer kun ``(dict, True)`` for ægte objekter; en JSON der parser til en
    ikke-dict (liste/tal) tæller som malformet for vores formål."""
    if data is None:
        return None, True
    stripped = data.strip()
    if not stripped:
        return None, True
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None, False
    if isinstance(parsed, dict):
        return parsed, True
    return None, False
