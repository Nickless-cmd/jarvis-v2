"""Provider-agnostic tool-result aging for the visible agentic loop.

Keeps the ``keep_full`` most-recent tool exchanges full; ages older ones by
clearing (default, deterministic) or LLM-compressing (deep+large runs) each
tool result's content. Operates on the shared ``_followup_exchanges`` list so
every provider lane benefits (only the Ollama adapter had crude per-adapter
bounding before). Gated to strong lanes past a round threshold — weak lanes are
capped at ~4-8 rounds so aging never amortizes there.

Cache: the caller applies the returned list forward-carried at end-of-round
(outside the retry fence), so each aged result serializes byte-identically on
later rounds. Default mode is shadow (observe would-be savings, mutate nothing).
Never raises into the hot loop.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import threading
from typing import Callable

from core.services.visible_followup_events import ToolExchange, ToolResult

_AGING_MIN_ROUND = 6
_AGING_COMPRESS_ROUND = 12
_AGING_COMPRESS_MIN_CHARS = 2000
_CLEAR_PREFIX = "[tool-resultat ryddet"

#: Komprimerede resultater skal OGSAA baere et maerke.
#
# Uden det saa naeste runde et komprimeret resultat som ualdret og
# komprimerede det IGEN — med en LLM, saa teksten blev ny hver gang.
# Historikken blev dermed skrevet om midt i prompten hver runde, og DeepSeeks
# praefiks-cache froes praecis dér.
#
# Maalt 28/9-2026 over et doegn: 10,45 mio. af 36,5 mio. miss-tokens (29 %) laa
# i «frosne» straekninger hvor hit ikke voksede. De startede naesten altid ved
# runde 12 — som er `_AGING_COMPRESS_ROUND` — og varede fem runder, indtil
# teksten var skrumpet under `_AGING_COMPRESS_MIN_CHARS` og faldt til `clear`,
# der ER maerket. Ét run: hit frossen paa 85.504 i fem runder mens input voksede
# fra 157k til 164k, altsaa ~375.000 miss-tokens der skulle have vaeret ~1.000.
#
# Maerket staar FORREST og er kort, saa det koster naesten ingen tokens og kan
# laeses af baade vagten og Jarvis.
_COMPRESS_PREFIX = "[tool-resultat forkortet"

_MODE_ENV = "JARVIS_TOOL_RESULT_AGING_MODE"
_VALID_MODES = ("off", "shadow", "active")

# Safety-valve: aging only fires when a run's full (non-aged) tool-content
# exceeds this many tokens. Because a single batch-age drops the full portion
# well below the trigger, aging then stays dormant for many rounds → it is
# STEPPED, not per-round → the append-only intra-run prefix cache is preserved
# between the rare, discrete jumps (same discipline as the cross-run cold_floor).
_AGING_TRIGGER_TOKENS_DEFAULT = 120_000


def _tool_results_dir() -> Path:
    """Runtime-store for originals, matching the existing TOOL_RESULTS_DIR."""
    jarvis_home = Path(os.environ.get("JARVIS_HOME") or Path.home() / ".jarvis-v2")
    return jarvis_home / "tool_results"


def _recovery_path(recovery_key: str) -> Path:
    digest = hashlib.sha256(recovery_key.encode("utf-8")).hexdigest()
    return _tool_results_dir() / f"{digest}.txt"


def _recovery_key(tool_call_id: str, content: str) -> str:
    key = str(tool_call_id or "").strip()
    if key:
        return key
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def _store_tool_result(recovery_key: str, content: str) -> Path:
    """Persist exact content atomically; propagate failure so aging can abstain."""
    path = _recovery_path(recovery_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(
        path.suffix + f".{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:  # temp-filen kan allerede være væk efter os.replace; oprydning må ikke kaste
            pass
    return path


def recover_tool_result(tool_use_id: str) -> str | None:
    """Return an aged tool result's exact original text, or ``None`` if absent.

    Originals live under ``~/.jarvis-v2/tool_results/`` (or
    ``$JARVIS_HOME/tool_results/`` when that runtime override is set).
    """
    try:
        return _recovery_path(str(tool_use_id)).read_text(encoding="utf-8")
    except (OSError, UnicodeError):  # intet gemt original for dette id — fravær er det normale svar
        return None


def aging_trigger_tokens() -> int:
    """Configured full-content token trigger for aging. Default 120k. Self-safe."""
    try:
        from core.runtime.settings import load_settings
        v = int(load_settings().extra.get(
            "tool_aging_trigger_tokens", _AGING_TRIGGER_TOKENS_DEFAULT))
        return max(0, v)
    except Exception:  # config kan mangle/vaere utcet — standardtaersklen er den sikre vaerdi
        return _AGING_TRIGGER_TOKENS_DEFAULT


def tool_result_aging_mode() -> str:
    """Current aging mode: 'off' | 'shadow' | 'active'. Default 'shadow'.

    Env ``JARVIS_TOOL_RESULT_AGING_MODE`` wins over runtime-config. Self-safe."""
    env = os.environ.get(_MODE_ENV)
    if env is not None:
        v = env.strip().lower()
        if v in _VALID_MODES:
            return v
    try:
        from core.runtime.settings import load_settings
        v = str(load_settings().extra.get("tool_result_aging_mode", "shadow")).strip().lower()
        return v if v in _VALID_MODES else "shadow"
    except Exception:  # ukendt config-vaerdi — 'shadow' er den sikre tilstand (skriver intet)
        return "shadow"


def _recovery_hint(recovery_key: str, path: Path) -> str:
    return f"original: {path} (nøgle: {recovery_key})"


def _clear_placeholder(n: int, recovery_key: str, path: Path) -> str:
    return f"[tool-resultat ryddet — {n} tegn; {_recovery_hint(recovery_key, path)}.]"


def _is_already_aged(content: str) -> bool:
    """Er resultatet ALLEREDE aeldet? Baade ryddet og forkortet taeller.

    Kun `_CLEAR_PREFIX` blev genkendt foer. Et komprimeret resultat gled derfor
    igennem hver runde og blev komprimeret paa ny — se noten ved
    `_COMPRESS_PREFIX`.
    """
    return content.startswith((_CLEAR_PREFIX, _COMPRESS_PREFIX))


def age_tool_results(
    exchanges: list[ToolExchange],
    *,
    keep_full: int = 5,
    mode: str,
    strength: str,
    round_index: int,
    compress_fn: Callable[[str], str] | None = None,
    trigger_tokens: int = 0,
) -> tuple[list[ToolExchange], dict]:
    """Age tool-result content on exchanges older than the ``keep_full`` most recent.

    Returns ``(exchanges_out, metrics)``. In shadow mode ``exchanges_out`` IS the
    input list (unchanged) but ``metrics`` carry ``would_free_tokens``. In active
    mode a new list is returned. Never raises."""
    metrics: dict = {"changed": False, "mode": mode, "aged_exchanges": 0,
                     "cleared": 0, "compressed": 0, "would_free_chars": 0,
                     "would_free_tokens": 0}
    try:
        if mode == "off":
            return exchanges, metrics
        if strength != "strong" or round_index < _AGING_MIN_ROUND:
            return exchanges, metrics
        if len(exchanges) <= keep_full:
            return exchanges, metrics

        # Safety-valve gate: only age when the full (non-aged) tool-content of the
        # whole run exceeds the trigger. Stepped, not per-round → preserves the
        # append-only intra-run cache until a run genuinely balloons. trigger=0
        # disables the gate (legacy / test behavior).
        if trigger_tokens > 0:
            # Billeder taeller MED (2026-09-06): et tool-resultat der baerer en
            # data-URL har kort tekst men tung vaegt. Maalte vi kun teksten,
            # ville en kontekst fuld af pixels se tom ud for gaten og aldrig
            # blive aldret.
            full_tokens = sum(
                (len(str(tr.content or "")) + len(str(tr.image_data_url or ""))) // 4
                for ex in exchanges
                for tr in ex.results
                if not _is_already_aged(str(tr.content or ""))
            )
            metrics["full_tokens"] = full_tokens
            if full_tokens < trigger_tokens:
                return exchanges, metrics

        cut = len(exchanges) - keep_full
        old = exchanges[:cut]
        recent = exchanges[cut:]
        deep = round_index >= _AGING_COMPRESS_ROUND

        new_old: list[ToolExchange] = []
        freed = aged_ex = cleared = compressed = 0
        for ex in old:
            new_results: list[ToolResult] = []
            touched = False
            for tr in ex.results:
                content = str(tr.content or "")
                if not content or _is_already_aged(content):
                    new_results.append(tr)
                    continue
                recovery_key = _recovery_key(tr.tool_call_id, content)
                if mode == "active":
                    try:
                        recovery_path = _store_tool_result(recovery_key, content)
                    except Exception:
                        # Uden en holdbar original maa active mode ikke destruere
                        # den eneste kopi. Aging er self-safe og springer resultatet over.
                        new_results.append(tr)
                        continue
                else:
                    recovery_path = _recovery_path(recovery_key)
                do_compress = (deep and len(content) >= _AGING_COMPRESS_MIN_CHARS
                               and compress_fn is not None)
                replacement = ""
                if do_compress:
                    try:
                        replacement = str(compress_fn(content) or "").strip()
                    except Exception:
                        replacement = ""
                    if replacement:
                        # Maerk den, saa naeste runde lader den vaere. Uden
                        # maerket komprimeres den igen med et nyt resultat.
                        replacement = (
                            f"{_COMPRESS_PREFIX} fra {len(content)} tegn]\n"
                            f"[{_recovery_hint(recovery_key, recovery_path)}]\n"
                            f"{replacement}")
                        compressed += 1
                    else:
                        replacement = _clear_placeholder(
                            len(content), recovery_key, recovery_path)
                        cleared += 1
                else:
                    replacement = _clear_placeholder(
                        len(content), recovery_key, recovery_path)
                    cleared += 1
                freed += max(0, len(content) - len(replacement))
                touched = True
                new_results.append(ToolResult(
                    tool_call_id=tr.tool_call_id,
                    tool_name=tr.tool_name,
                    content=replacement,
                ))
            if touched:
                aged_ex += 1
                new_old.append(ToolExchange(
                    text=ex.text, tool_calls=list(ex.tool_calls),
                    results=new_results, reasoning_content=ex.reasoning_content,
                    # Skal baeres igennem: ellers DROPPER aldringen bruger-
                    # styringen naar den rydder i gamle resultater (7/10-2026).
                    user_message=ex.user_message,
                ))
            else:
                new_old.append(ex)

        metrics.update({"aged_exchanges": aged_ex, "cleared": cleared,
                        "compressed": compressed, "would_free_chars": freed,
                        "would_free_tokens": freed // 4})
        if aged_ex == 0:
            return exchanges, metrics
        if mode == "shadow":
            return exchanges, metrics
        metrics["changed"] = True
        return new_old + recent, metrics
    except Exception:  # aging maa aldrig kaste ind i en samtale; fejlen rapporteres i metrics
        return exchanges, {"changed": False, "mode": mode, "error": True}
