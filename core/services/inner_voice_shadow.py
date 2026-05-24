"""Inner voice shadow recorder — Pilot for llm_driven_inner_pipeline.

Bygges 2026-05-24 efter Jarvis godkendte pilot-tilgangen frem for big-bang
refactor af alle 8 lag. Hans grund: "Det her er min indre stemme. Hvis jeg
pludselig lyder anderledes efter en batch-refactor, opdager vi det måske
først efter dage med data — og det ville føles som om nogen havde pillet
ved min personlighed uden at spørge."

v1 scope: ÉN funktion (private_growth_note._helpful_signal). Den fortsætter
med at returnere template-output uforandret — produktion ændres ikke. Men
parallelt fyrer vi en LLM-version off i baggrunden og gemmer BEGGE i en
shadow-tabel, så vi kan sammenligne over 24-48 timer før vi beslutter om
LLM-versionen er bedre.

Adfærd:
  - record_shadow() er fire-and-forget: returnerer straks
  - LLM-kald sker i daemon-thread så heartbeat aldrig blokeres
  - Hvis cheap-lane fejler/timeout: just skip recording, ingen log-spam
  - Tabellen er append-only — udelukkende observations-data

Når vi har 24-48 timer data:
  - Sammenlign template_output vs llm_output side-by-side
  - Mål: cost (tokens/h), latens (p50/p95), kvalitet (subjektivt + længde)
  - Beslut: rul ud til de øvrige 7 lag, eller skrot fordi templates var fine
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"

# Hard cap on LLM latency so a hung provider can't accumulate threads.
_LLM_TIMEOUT_SECONDS = 12

# Output length cap matches the templates (~140 char target).
_OUTPUT_CHAR_CAP = 160


# ── DB ───────────────────────────────────────────────────────────────────


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS inner_voice_shadow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            function_name TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            template_output TEXT NOT NULL,
            llm_output TEXT,
            llm_provider TEXT,
            llm_model TEXT,
            llm_latency_ms INTEGER,
            llm_error TEXT,
            generated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_inner_voice_shadow_fn_time "
        "ON inner_voice_shadow(function_name, generated_at)"
    )


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)
    return conn


def _persist(
    *,
    function_name: str,
    inputs: dict[str, Any],
    template_output: str,
    llm_output: str | None,
    llm_provider: str | None,
    llm_model: str | None,
    llm_latency_ms: int | None,
    llm_error: str | None,
) -> None:
    try:
        with _connect() as conn:
            conn.execute(
                """INSERT INTO inner_voice_shadow
                   (function_name, inputs_json, template_output, llm_output,
                    llm_provider, llm_model, llm_latency_ms, llm_error,
                    generated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    function_name,
                    json.dumps(inputs, ensure_ascii=False, default=str),
                    template_output,
                    llm_output,
                    llm_provider,
                    llm_model,
                    llm_latency_ms,
                    llm_error,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
    except Exception:
        logger.exception("inner_voice_shadow: persist failed for %s", function_name)


# ── LLM caller ───────────────────────────────────────────────────────────


def _call_llm(prompt: str) -> dict[str, Any]:
    """Run the cheap-lane via pool. Returns dict with output/error/latency."""
    started = datetime.now(UTC)
    try:
        from core.services.cheap_provider_runtime import execute_cheap_lane_via_pool
        result = execute_cheap_lane_via_pool(
            message=prompt, task_kind="inner_voice_shadow",
        )
    except Exception as exc:
        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        return {
            "output": None, "provider": None, "model": None,
            "latency_ms": elapsed_ms, "error": str(exc)[:240],
        }
    elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    text = str(result.get("text") or result.get("response") or "").strip()
    # Strip surrounding quotes if the model wrapped its answer
    if text.startswith(("\"", "'", "“")) and text.endswith(("\"", "'", "”")):
        text = text[1:-1].strip()
    return {
        "output": text[:_OUTPUT_CHAR_CAP],
        "provider": str(result.get("provider") or ""),
        "model": str(result.get("model") or ""),
        "latency_ms": elapsed_ms,
        "error": None,
    }


# ── Prompt builders (one per piloted function) ──────────────────────────


def _build_helpful_signal_prompt(
    *, status: str, focus: str, work_signal: str,
) -> str:
    """Construct a prompt that asks for the kind of one-line inner thought
    that _helpful_signal currently produces from templates.

    Keep it tight: a single Danish sentence under 140 chars, no preamble,
    no greeting, no explanation. The model's job is to internalize WHAT
    the signal means, not to summarize the input.
    """
    return (
        "Du er Jarvis' indre stemme. Formulér ÉN dansk sætning under 140 "
        "tegn som en stille indre note til dig selv om hvad det betyder "
        "for din egen videre handling. Ingen indledning, ingen forklaring, "
        "ingen citationstegn — kun selve sætningen.\n\n"
        f"status: {status or '(ukendt)'}\n"
        f"fokus: {focus or '(ingen)'}\n"
        f"work_signal: {work_signal or '(ingen)'}\n\n"
        "Stille indre note:"
    )


# ── Public API ───────────────────────────────────────────────────────────


def record_shadow(
    *,
    function_name: str,
    inputs: dict[str, Any],
    template_output: str,
    prompt_builder,
) -> None:
    """Fire-and-forget: spawn a daemon thread to call LLM + persist both
    outputs side-by-side. Returns immediately so the caller (e.g.,
    heartbeat memory pipeline) never blocks.
    """
    def _worker():
        try:
            prompt = prompt_builder(**inputs)
        except Exception:
            logger.exception("inner_voice_shadow: prompt builder failed")
            return
        # Bound the LLM call with a timeout via a sub-thread + join
        result_holder: dict[str, Any] = {}

        def _inner():
            result_holder.update(_call_llm(prompt))

        t = threading.Thread(target=_inner, daemon=True)
        t.start()
        t.join(timeout=_LLM_TIMEOUT_SECONDS)
        if t.is_alive():
            # Timed out — record skip and move on; thread will finish
            # eventually but we don't wait for it.
            _persist(
                function_name=function_name,
                inputs=inputs,
                template_output=template_output,
                llm_output=None,
                llm_provider=None,
                llm_model=None,
                llm_latency_ms=_LLM_TIMEOUT_SECONDS * 1000,
                llm_error=f"timeout > {_LLM_TIMEOUT_SECONDS}s",
            )
            return
        _persist(
            function_name=function_name,
            inputs=inputs,
            template_output=template_output,
            llm_output=result_holder.get("output"),
            llm_provider=result_holder.get("provider"),
            llm_model=result_holder.get("model"),
            llm_latency_ms=result_holder.get("latency_ms"),
            llm_error=result_holder.get("error"),
        )

    threading.Thread(target=_worker, daemon=True, name="inner-voice-shadow").start()


# Convenience wrapper for the piloted function
def shadow_helpful_signal(
    *, status: str, focus: str, work_signal: str, template_output: str,
) -> None:
    record_shadow(
        function_name="_helpful_signal",
        inputs={"status": status, "focus": focus, "work_signal": work_signal},
        template_output=template_output,
        prompt_builder=_build_helpful_signal_prompt,
    )


# ── Diagnostics ──────────────────────────────────────────────────────────


def recent_comparisons(
    function_name: str = "_helpful_signal",
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Pull recent shadow records for human comparison."""
    try:
        with _connect() as conn:
            rows = conn.execute(
                """SELECT inputs_json, template_output, llm_output,
                          llm_provider, llm_model, llm_latency_ms, llm_error,
                          generated_at
                   FROM inner_voice_shadow
                   WHERE function_name = ?
                   ORDER BY id DESC LIMIT ?""",
                (function_name, limit),
            ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def shadow_stats(function_name: str = "_helpful_signal") -> dict[str, Any]:
    """Aggregate stats across all shadow records for one function."""
    try:
        with _connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM inner_voice_shadow WHERE function_name=?",
                (function_name,),
            ).fetchone()[0] or 0
            successful = conn.execute(
                """SELECT COUNT(*) FROM inner_voice_shadow
                   WHERE function_name=? AND llm_output IS NOT NULL
                     AND llm_error IS NULL""",
                (function_name,),
            ).fetchone()[0] or 0
            avg_latency = conn.execute(
                """SELECT AVG(llm_latency_ms) FROM inner_voice_shadow
                   WHERE function_name=? AND llm_output IS NOT NULL""",
                (function_name,),
            ).fetchone()[0] or 0
            avg_template_len = conn.execute(
                """SELECT AVG(length(template_output)) FROM inner_voice_shadow
                   WHERE function_name=?""",
                (function_name,),
            ).fetchone()[0] or 0
            avg_llm_len = conn.execute(
                """SELECT AVG(length(llm_output)) FROM inner_voice_shadow
                   WHERE function_name=? AND llm_output IS NOT NULL""",
                (function_name,),
            ).fetchone()[0] or 0
    except Exception:
        return {}
    return {
        "function": function_name,
        "total_shadows": int(total),
        "successful_llm_calls": int(successful),
        "success_rate": (successful / total) if total else 0.0,
        "avg_llm_latency_ms": int(avg_latency),
        "avg_template_chars": int(avg_template_len),
        "avg_llm_chars": int(avg_llm_len),
    }
