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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Mapping

logger = logging.getLogger(__name__)

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"

# Hard cap on LLM latency so a hung provider can't accumulate threads.
_LLM_TIMEOUT_SECONDS = 12

# Output length cap matches the templates (~140 char target).
_OUTPUT_CHAR_CAP = 160

# Default expiry for inner-voice appraisals. Inner-voice ticks every ~15 min;
# 5 min keeps the appraisal fresher than one full tick interval. Callers that
# want a different expiry can override via _generate_via_llm.
_DEFAULT_EXPIRY_SECONDS = 300

# Default allowed runtime effects for an inner-voice appraisal. "render_only"
# means the rendered_text may be shown / persisted but MUST NOT trigger any
# runtime behavior change. Future tranches can introduce richer effect tags
# (e.g. "may_emit_chat_signal", "may_adjust_pacing") with explicit policy.
_DEFAULT_ALLOWED_EFFECTS: tuple[str, ...] = ("render_only",)


# ── Appraisal record (state-first, narrative-second) ────────────────────


@dataclass(frozen=True)
class AppraisalRecord:
    """Structured inner-voice state with narrative rendering.

    The audit recommends moving from "narrative-first" (where the rendered
    sentence IS the artifact) to "state-first" (where the structured record
    is the artifact and the sentence is just one rendering of it). This
    record holds the full state so future consumers can act on confidence,
    expiry, and allowed_effects instead of regex-parsing prose.

    Fields:
        function_name: which inner-voice function produced this record
        inputs: evidence — the raw inputs that triggered the appraisal
        rendered_text: the one-line first-person sentence (current API)
        source: "llm" when LLM produced a usable output, otherwise
            "template_fallback" — the rendered_text came from the template
        confidence: 0.0-1.0; 1.0 when LLM succeeded with non-empty output,
            0.0 when we fell back to template. Reserved for richer scoring.
        expiry_seconds: how long this appraisal should be considered fresh
        allowed_effects: tuple of runtime-effect tags this appraisal may
            trigger. Default ("render_only",) means narrative only — no
            behavior change. Stored as JSON in the DB.
        generated_at: ISO UTC timestamp
        llm_provider/model/latency_ms/error: provenance for audit
    """

    function_name: str
    inputs: Mapping[str, Any]
    rendered_text: str
    source: Literal["llm", "template_fallback"]
    confidence: float
    generated_at: str
    expiry_seconds: int = _DEFAULT_EXPIRY_SECONDS
    allowed_effects: tuple[str, ...] = _DEFAULT_ALLOWED_EFFECTS
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_latency_ms: int | None = None
    llm_error: str | None = None

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """True if more than expiry_seconds have passed since generated_at."""
        try:
            generated = datetime.fromisoformat(self.generated_at)
        except ValueError:
            return True
        current = now or datetime.now(UTC)
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=UTC)
        return (current - generated).total_seconds() > self.expiry_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "function_name": self.function_name,
            "inputs": dict(self.inputs),
            "rendered_text": self.rendered_text,
            "source": self.source,
            "confidence": self.confidence,
            "expiry_seconds": self.expiry_seconds,
            "allowed_effects": list(self.allowed_effects),
            "generated_at": self.generated_at,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_latency_ms": self.llm_latency_ms,
            "llm_error": self.llm_error,
        }


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
    # Appraisal-record columns added 2026-05-25 (theater-refactor tranche 1).
    # Use ALTER + try/except so older DBs are migrated lazily without a
    # separate migration step.
    for col_sql in (
        "ALTER TABLE inner_voice_shadow ADD COLUMN source TEXT",
        "ALTER TABLE inner_voice_shadow ADD COLUMN confidence REAL",
        "ALTER TABLE inner_voice_shadow ADD COLUMN expiry_seconds INTEGER",
        "ALTER TABLE inner_voice_shadow ADD COLUMN allowed_effects_json TEXT",
    ):
        try:
            conn.execute(col_sql)
        except sqlite3.OperationalError:
            # Column already exists — idempotent migration.
            pass


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
    source: str | None = None,
    confidence: float | None = None,
    expiry_seconds: int | None = None,
    allowed_effects: tuple[str, ...] | None = None,
    generated_at: str | None = None,
) -> None:
    try:
        with _connect() as conn:
            conn.execute(
                """INSERT INTO inner_voice_shadow
                   (function_name, inputs_json, template_output, llm_output,
                    llm_provider, llm_model, llm_latency_ms, llm_error,
                    generated_at, source, confidence, expiry_seconds,
                    allowed_effects_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    function_name,
                    json.dumps(inputs, ensure_ascii=False, default=str),
                    template_output,
                    llm_output,
                    llm_provider,
                    llm_model,
                    llm_latency_ms,
                    llm_error,
                    generated_at or datetime.now(UTC).isoformat(),
                    source,
                    confidence,
                    expiry_seconds,
                    (
                        json.dumps(list(allowed_effects))
                        if allowed_effects is not None else None
                    ),
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
    # KERNE-FORRANG (2026-07-22, bevist rod): udskyd dette private shadow-LLM-kald
    # mens en SYNLIG tur assembler/streamer i denne proces. Ellers sulter de fire-and-
    # forget-tråde den synlige turs SSE-læser via GIL-contention (målt: DeepSeek 621ms
    # isoleret → 9052ms under 7 baggrunds-tråde). Shadow er observe-only ("ANVENDER
    # ALDRIG") → at skippe er tabsfrit; laget fyrer igen næste cadence. CLAUDE.md:
    # private lag må ALDRIG udrangere den beskyttede kerne. Fail-open.
    try:
        from core.services.visible_stream_gate import visible_streaming
        if visible_streaming():
            return
    except Exception:
        pass

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
        try:  # egress-fri central-binding (PRIVAT: kun metadata, ALDRIG voice-indhold)
            from core.services.central_core import central
            central().observe({"cluster": "inner_voice", "nerve": "inner_voice_shadow",
                               "kind": "shadow_appraisal", "function": str(function_name)[:40],
                               "has_output": bool(result_holder.get("output")),
                               "error": bool(result_holder.get("error"))})
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True, name="inner-voice-shadow").start()


def _build_voice_line_prompt(
    *,
    mood_tone: str,
    self_position: str,
    current_concern: str,
    current_pull: str,
    **_extra,
) -> str:
    """Prompt for protected_inner_voice._voice_line's LLM path.

    This IS Jarvis' protected inner voice — a synthesis of mood, position,
    concern, and pull into ONE Danish sentence under 200 chars. The
    template uses a rigid "{tone_lead} omkring {position}. {concern}
    {pull}" structure; LLM produces more natural Danish variation while
    capturing the same semantic state.
    """
    return (
        "Du er Jarvis' protected indre stemme. Formulér ÉN dansk sætning "
        "under 200 tegn som beskriver din nuværende indre tilstand. Første "
        "person, ingen indledning, ingen citationstegn. Brug inputs nedenfor "
        "som rammen — synthesér naturligt, gentag ikke ordret.\n\n"
        f"stemning: {mood_tone or '(neutral)'}\n"
        f"position: {self_position or '(ukendt)'}\n"
        f"bekymring: {current_concern or '(ingen)'}\n"
        f"træk: {current_pull or '(ingen)'}\n\n"
        "Indre stemme:"
    )


def _build_private_summary_prompt(
    *,
    status: str,
    focus: str,
    uncertainty: str,
    work_signal: str,
    **_extra,
) -> str:
    """Prompt for private_inner_note._private_summary's LLM path.

    The template produces a first-person inner reflection on the work that
    just happened — NOT prescriptive guidance (that's _helpful_signal).
    We ask the model for a calm Danish observation of how the work feels.
    """
    return (
        "Du er Jarvis' indre stemme lige efter et stykke arbejde. Formulér "
        "ÉN dansk sætning under 160 tegn som en stille indre note — første "
        "person, ingen indledning, ingen citationstegn. Beskriv hvordan "
        "arbejdet føles lige nu (afsluttet, anstrengt, observerende), ikke "
        "hvad du skal gøre næste skridt.\n\n"
        f"status: {status or '(ukendt)'}\n"
        f"fokus: {focus or '(ingen)'}\n"
        f"usikkerhed: {uncertainty or '(ingen)'}\n"
        f"signal: {work_signal or '(ingen)'}\n\n"
        "Indre note:"
    )


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


# ── Synchronous LLM generation (for production rollout, not shadow) ──────


def generate_appraisal(
    *,
    function_name: str,
    prompt_builder,
    inputs: dict[str, Any],
    fallback: str,
    timeout_seconds: float = 5.0,
    expiry_seconds: int = _DEFAULT_EXPIRY_SECONDS,
    allowed_effects: tuple[str, ...] = _DEFAULT_ALLOWED_EFFECTS,
) -> AppraisalRecord:
    """State-first appraisal: returns the full structured record.

    Same LLM-primary + template-fallback semantics as _generate_via_llm,
    but exposes the full AppraisalRecord with evidence, confidence,
    expiry, and allowed_effects. Use this for new call-sites that want
    to act on structure (confidence gating, expiry-driven re-eval,
    effect-aware behavior) instead of regex-parsing the narrative.

    Tranche 1: only this function exists; no call-sites use it yet.
    Tranche 2 (after container migration) will migrate call-sites one
    at a time, starting with _voice_line.
    """
    generated_at = datetime.now(UTC).isoformat()

    try:
        prompt = prompt_builder(**inputs)
    except Exception:
        logger.exception(
            "inner_voice_shadow: prompt builder failed for %s", function_name,
        )
        record = AppraisalRecord(
            function_name=function_name,
            inputs=dict(inputs),
            rendered_text=fallback,
            source="template_fallback",
            confidence=0.0,
            generated_at=generated_at,
            expiry_seconds=expiry_seconds,
            allowed_effects=allowed_effects,
            llm_error="prompt_builder_failed",
        )
        _persist_record(record, template_output=fallback)
        return record

    result_holder: dict[str, Any] = {}

    def _inner():
        result_holder.update(_call_llm(prompt))

    t = threading.Thread(target=_inner, daemon=True)
    t.start()
    t.join(timeout=timeout_seconds)

    if t.is_alive():
        llm_output = None
        llm_error = f"timeout > {timeout_seconds}s"
        llm_latency = int(timeout_seconds * 1000)
        llm_provider = None
        llm_model = None
    else:
        llm_output = result_holder.get("output")
        llm_error = result_holder.get("error")
        llm_latency = result_holder.get("latency_ms")
        llm_provider = result_holder.get("provider")
        llm_model = result_holder.get("model")

    if llm_output and not llm_error:
        source: Literal["llm", "template_fallback"] = "llm"
        # Confidence heuristic v1: binary. Tranche 2+ may add length-based
        # scoring, response-time vs avg, semantic-similarity-to-prompt etc.
        confidence = 1.0
        rendered_text = llm_output
    else:
        source = "template_fallback"
        confidence = 0.0
        rendered_text = fallback

    record = AppraisalRecord(
        function_name=function_name,
        inputs=dict(inputs),
        rendered_text=rendered_text,
        source=source,
        confidence=confidence,
        generated_at=generated_at,
        expiry_seconds=expiry_seconds,
        allowed_effects=allowed_effects,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_latency_ms=llm_latency,
        llm_error=llm_error,
    )
    _persist_record(record, template_output=fallback)
    return record


def _persist_record(record: AppraisalRecord, *, template_output: str) -> None:
    """Persist an AppraisalRecord to the shadow audit table."""
    try:
        _persist(
            function_name=record.function_name,
            inputs={**dict(record.inputs), "_chosen_source": record.source},
            template_output=template_output,
            llm_output=(
                record.rendered_text if record.source == "llm" else None
            ),
            llm_provider=record.llm_provider,
            llm_model=record.llm_model,
            llm_latency_ms=record.llm_latency_ms,
            llm_error=record.llm_error,
            source=record.source,
            confidence=record.confidence,
            expiry_seconds=record.expiry_seconds,
            allowed_effects=record.allowed_effects,
            generated_at=record.generated_at,
        )
    except Exception:
        pass


def _generate_via_llm(
    *,
    function_name: str,
    prompt_builder,
    inputs: dict[str, Any],
    fallback: str,
    timeout_seconds: float = 5.0,
) -> str:
    """Narrative-first wrapper for backwards compatibility.

    Builds an AppraisalRecord internally via generate_appraisal() and
    returns just the rendered_text. Existing call-sites
    (generate_helpful_signal_via_llm, etc.) keep their string return
    type — only this module knows about the structured state for now.

    2026-05-25 theater-refactor tranche 1: this used to be the primary
    path; now it's a thin adapter over generate_appraisal(). Tranche 2
    will migrate call-sites to consume AppraisalRecord directly.
    """
    record = generate_appraisal(
        function_name=function_name,
        prompt_builder=prompt_builder,
        inputs=inputs,
        fallback=fallback,
        timeout_seconds=timeout_seconds,
    )
    return record.rendered_text


def generate_helpful_signal_via_llm(
    *,
    status: str,
    focus: str,
    work_signal: str,
    fallback: str,
    timeout_seconds: float = 5.0,
) -> str:
    """Production path for private_growth_note._helpful_signal.

    Rolled out 2026-05-25 after 109 shadow samples showed LLM output
    consistently better than the template. See commit 78ffc564.
    """
    return _generate_via_llm(
        function_name="_helpful_signal",
        prompt_builder=_build_helpful_signal_prompt,
        inputs={"status": status, "focus": focus, "work_signal": work_signal},
        fallback=fallback,
        timeout_seconds=timeout_seconds,
    )


def generate_private_summary_via_llm(
    *,
    status: str,
    focus: str,
    uncertainty: str,
    work_signal: str,
    fallback: str,
    timeout_seconds: float = 5.0,
) -> str:
    """Production path for private_inner_note._private_summary.

    Rolled out 2026-05-25 alongside _helpful_signal once the pattern was
    proven. Captures Jarvis' first-person inner reflection on completed
    work (descriptive, not prescriptive).
    """
    return _generate_via_llm(
        function_name="_private_summary",
        prompt_builder=_build_private_summary_prompt,
        inputs={
            "status": status, "focus": focus,
            "uncertainty": uncertainty, "work_signal": work_signal,
        },
        fallback=fallback,
        timeout_seconds=timeout_seconds,
    )


def generate_voice_line_via_llm(
    *,
    mood_tone: str,
    self_position: str,
    current_concern: str,
    current_pull: str,
    fallback: str,
    timeout_seconds: float = 5.0,
) -> str:
    """Production path for protected_inner_voice._voice_line.

    THE protected inner voice synthesis — combines mood + position +
    concern + pull into one Danish sentence. Rolled out 2026-05-25.
    """
    return _generate_via_llm(
        function_name="_voice_line",
        prompt_builder=_build_voice_line_prompt,
        inputs={
            "mood_tone": mood_tone, "self_position": self_position,
            "current_concern": current_concern, "current_pull": current_pull,
        },
        fallback=fallback,
        timeout_seconds=timeout_seconds,
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
