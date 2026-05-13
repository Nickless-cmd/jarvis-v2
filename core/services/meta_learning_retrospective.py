"""Meta-læring retrospective generator — Phase 1 (AGI track #3).

Genererer ugentligt retrospektiv-memo via cheap-lane LLM. Syntetiserer
aktivitet fra 5 AGI-spor til prosa-fortælling med citationsnøgler +
struktureret hypothesis-blok (0-3 kandidater).

Schema-bootstrap lives here (not in db.py) per Boy Scout Rule.

See spec: docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.db import connect
from core.runtime.settings import load_settings
from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane
from core.services.identity_composer import identity_prompt_prefix

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

_SCHEMA_INITIALIZED = False


def ensure_schema() -> None:
    """Idempotently create learning_memos table + index."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS learning_memos (
              memo_id TEXT PRIMARY KEY,
              ts TEXT NOT NULL,
              period_start TEXT NOT NULL,
              period_end TEXT NOT NULL,
              narrative TEXT NOT NULL,
              hypothesis_candidates_json TEXT NOT NULL,
              aggregator_snapshot_json TEXT NOT NULL,
              model_used TEXT,
              acknowledged_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_learning_memos_ts
              ON learning_memos(ts);
            """
        )
        conn.commit()
    _SCHEMA_INITIALIZED = True


# ---------------------------------------------------------------------------
# Prompt builder + markdown parser
# ---------------------------------------------------------------------------

_HYPOTHESIS_HEADER = "## Hypothesis Candidates"
_KANDIDAT_RE = re.compile(r"###\s+Kandidat\s+(\d+):\s*(.*)$", re.MULTILINE)
_FIELD_RE = re.compile(r"^\s*-\s*\*\*([^*]+?):?\*\*:?\s*(.+)$", re.MULTILINE)
_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n?(.*?)\n?```", re.DOTALL)


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text


def _build_retrospective_prompt(
    *,
    period_start: str,
    period_end: str,
    aggregator_snapshot: dict[str, Any],
) -> str:
    """Build the cheap-lane prompt for weekly retrospective memo."""
    snapshot_json = json.dumps(aggregator_snapshot, ensure_ascii=False, indent=2, default=str)
    return (
        f"{identity_prompt_prefix()}' meta-læringsskribent. Du modtager kuraterede aggregater "
        "for sidste 7 dages aktivitet på 5 AGI-spor. Din opgave er at producere "
        "et kort, indsigtsfuldt retrospektiv-memo i to dele.\n"
        "\n"
        "DEL 1: Prosa-analyse (300-500 ord).\n"
        "- Skriv som Jarvis selv ville reflektere (1.-person, dansk, varm tone).\n"
        "- Fokuser på 2-3 mønstre der træder frem. Ikke et resumé af alt.\n"
        "- Hver konkret reference SKAL inkludere en citationsnøgle: plan_id, "
        "prediction_id, obs_id, eller ISO-datotid. Læseren skal kunne grave i "
        "det via curiosity-tools.\n"
        "- Inkluder MINDST én outlier-observation — hvad var ekstremt i den uge?\n"
        "\n"
        f"DEL 2: {_HYPOTHESIS_HEADER} (0-3 entries).\n"
        "- Hvis ugen var rolig eller ingen reelle mønstre fremtræder, returnér "
        "TOM blok (skriv kort note som '(Ingen hypoteser denne uge — "
        "datagrundlaget er for spinkelt.)' i stedet for kandidater).\n"
        "- Hvis 1-3 testbare hypoteser findes, formatér hver præcis sådan:\n"
        "  ### Kandidat N: <kort statement>\n"
        "  - **Observation:** <konkret mønster, citationsnøgle>\n"
        "  - **Hypotese:** <hvis X, så Y>\n"
        "  - **Success-kriterium:** <hvordan vi måler>\n"
        "  - **Sample-størrelse:** <antal observationer der skal til, kun heltal>\n"
        "\n"
        "Returnér KUN markdown — ingen JSON-wrappere, ingen forklarende tekst "
        "udenfor selve memoet. Vi parser markdown direkte.\n"
        "\n"
        f"Periode: {period_start} → {period_end}\n"
        "\n"
        "AGGREGATER (JSON):\n"
        f"{snapshot_json}\n"
    )


def _parse_memo_markdown(text: str) -> dict[str, Any]:
    """Parse cheap-lane markdown output into narrative + hypothesis_candidates.

    Defensive: if hypothesis-section parse fails, narrative is preserved
    and hypothesis_candidates is [].
    """
    if not text or not text.strip():
        return {"status": "ok", "narrative": "", "hypothesis_candidates": []}

    raw = _strip_markdown_fence(text)
    if _HYPOTHESIS_HEADER in raw:
        idx = raw.find(_HYPOTHESIS_HEADER)
        narrative = raw[:idx].strip()
        hypo_section = raw[idx + len(_HYPOTHESIS_HEADER):].strip()
    else:
        narrative = raw.strip()
        hypo_section = ""

    candidates: list[dict[str, Any]] = []
    if hypo_section:
        matches = list(_KANDIDAT_RE.finditer(hypo_section))
        for i, m in enumerate(matches):
            kandidat_num = int(m.group(1))
            statement = m.group(2).strip()
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(hypo_section)
            body = hypo_section[body_start:body_end]

            fields: dict[str, str] = {}
            for f in _FIELD_RE.finditer(body):
                key = f.group(1).strip().lower()
                val = f.group(2).strip()
                fields[key] = val

            observation = fields.get("observation", "")
            hypothesis = fields.get("hypotese", "") or fields.get("hypothesis", "")
            success_criterion = (
                fields.get("success-kriterium", "")
                or fields.get("success criterion", "")
            )
            sample_raw = (
                fields.get("sample-størrelse", "")
                or fields.get("sample size needed", "")
                or fields.get("sample-storrelse", "")
            )
            sample_size = 0
            sample_match = re.search(r"\d+", sample_raw)
            if sample_match:
                try:
                    sample_size = int(sample_match.group(0))
                except ValueError:
                    sample_size = 0

            if not statement and not observation and not hypothesis:
                continue

            candidates.append({
                "id": f"hyp-{kandidat_num}",
                "statement": statement,
                "observation": observation,
                "hypothesis": hypothesis,
                "success_criterion": success_criterion,
                "sample_size_needed": sample_size,
            })

    return {
        "status": "ok",
        "narrative": narrative,
        "hypothesis_candidates": candidates[:3],
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _persist_memo(
    *,
    memo_id: str,
    ts: str,
    period_start: str,
    period_end: str,
    narrative: str,
    hypothesis_candidates: list[dict[str, Any]],
    aggregator_snapshot: dict[str, Any],
    model_used: str,
) -> str:
    """Insert a new memo row. Returns memo_id."""
    ensure_schema()
    with connect() as conn:
        conn.execute(
            "INSERT INTO learning_memos "
            "(memo_id, ts, period_start, period_end, narrative, "
            " hypothesis_candidates_json, aggregator_snapshot_json, "
            " model_used, acknowledged_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (
                memo_id, ts, period_start, period_end, narrative,
                json.dumps(hypothesis_candidates, ensure_ascii=False, default=str),
                json.dumps(aggregator_snapshot, ensure_ascii=False, default=str),
                model_used,
            ),
        )
        conn.commit()
    return memo_id


def fetch_latest_unacknowledged_memo() -> dict[str, Any] | None:
    """Return the most recent memo with acknowledged_at IS NULL, or None."""
    ensure_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM learning_memos "
            "WHERE acknowledged_at IS NULL "
            "ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["hypothesis_candidates"] = json.loads(d.get("hypothesis_candidates_json") or "[]")
    except (json.JSONDecodeError, ValueError):
        d["hypothesis_candidates"] = []
    return d


def fetch_memo_by_id(memo_id: str) -> dict[str, Any] | None:
    ensure_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM learning_memos WHERE memo_id = ?", (memo_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["hypothesis_candidates"] = json.loads(d.get("hypothesis_candidates_json") or "[]")
    except (json.JSONDecodeError, ValueError):
        d["hypothesis_candidates"] = []
    return d


def list_recent_memos(limit: int = 5) -> list[dict[str, Any]]:
    ensure_schema()
    limit = max(1, min(int(limit), 50))
    with connect() as conn:
        rows = conn.execute(
            "SELECT memo_id, ts, period_start, period_end, model_used, "
            "       acknowledged_at, length(narrative) AS narrative_length "
            "FROM learning_memos ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def acknowledge_memo(memo_id: str) -> bool:
    """Mark memo as acknowledged. Returns True if a row was updated."""
    ensure_schema()
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE learning_memos SET acknowledged_at = ? "
            "WHERE memo_id = ? AND acknowledged_at IS NULL",
            (now_iso, memo_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def _meta_learning_enabled() -> bool:
    try:
        return bool(load_settings().meta_learning_enabled)
    except Exception:
        return True  # fail-open


def _safe_publish(family_event: str, payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(family_event, payload)
    except Exception as exc:
        logger.debug("meta_learning: event publish failed: %s", exc)


def generate_weekly_retrospective(*, now: datetime) -> dict[str, Any]:
    """Generate a weekly retrospective memo for the 7 days ending at `now`."""
    if not _meta_learning_enabled():
        return {"status": "disabled", "note": "meta_learning is disabled"}

    period_end = now
    period_start = now - timedelta(days=7)

    from core.services.meta_learning_aggregator import (
        aggregate_world_model,
        aggregate_plan_revision,
        aggregate_curiosity,
        aggregate_skill_chain_phase2,
        aggregate_tool_invention,
    )

    try:
        snapshot = {
            "world_model": aggregate_world_model(since=period_start, until=period_end),
            "plan_revision": aggregate_plan_revision(since=period_start, until=period_end),
            "curiosity": aggregate_curiosity(since=period_start, until=period_end),
            "skill_chain_phase2": aggregate_skill_chain_phase2(since=period_start, until=period_end),
            "tool_invention": aggregate_tool_invention(since=period_start, until=period_end),
        }
    except Exception as exc:
        logger.warning("generate_weekly_retrospective: aggregator failed: %s", exc)
        return {"status": "error", "reason": f"aggregator error: {exc}"}

    prompt = _build_retrospective_prompt(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        aggregator_snapshot=snapshot,
    )

    try:
        cheap_result = execute_public_safe_cheap_lane(message=prompt)
    except Exception as exc:
        logger.warning("generate_weekly_retrospective: cheap-lane failed: %s", exc)
        return {"status": "error", "reason": f"cheap-lane error: {exc}"}

    response_text = str(cheap_result.get("text") or "")
    model_used = str(cheap_result.get("model") or "")

    parsed = _parse_memo_markdown(response_text)
    narrative = parsed.get("narrative", "").strip()
    if not narrative:
        return {
            "status": "error",
            "reason": "cheap-lane returned empty narrative",
            "raw_response_excerpt": response_text[:200],
        }

    memo_id = f"memo-{uuid4().hex[:12]}"
    ts_iso = now.isoformat()
    candidates = parsed.get("hypothesis_candidates", [])

    _persist_memo(
        memo_id=memo_id,
        ts=ts_iso,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        narrative=narrative,
        hypothesis_candidates=candidates,
        aggregator_snapshot=snapshot,
        model_used=model_used,
    )

    _safe_publish("cognitive_meta_learning.memo_generated", {
        "memo_id": memo_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "hypothesis_count": len(candidates),
        "narrative_length": len(narrative),
        "model_used": model_used,
    })

    return {
        "status": "ok",
        "memo_id": memo_id,
        "ts": ts_iso,
        "narrative": narrative,
        "hypothesis_candidates": candidates,
        "model_used": model_used,
    }


# ---------------------------------------------------------------------------
# Awareness rendering (priority 39 in prompt_contract)
# ---------------------------------------------------------------------------

_TEASER_NARRATIVE_CHARS = 200


def _format_period_for_display(period_start: str, period_end: str) -> str:
    """Render period as 'YYYY-MM-DD to YYYY-MM-DD' for awareness display."""
    def _date(iso: str) -> str:
        try:
            return datetime.fromisoformat(iso).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return iso[:10] if iso else "?"
    return f"{_date(period_start)} to {_date(period_end)}"


def format_latest_unacknowledged_memo_for_awareness() -> str:
    """Render a short teaser for the most recent unacknowledged memo."""
    if not _meta_learning_enabled():
        return ""
    memo = fetch_latest_unacknowledged_memo()
    if not memo:
        return ""

    narrative = str(memo.get("narrative") or "")
    teaser = narrative[:_TEASER_NARRATIVE_CHARS].rstrip()
    if len(narrative) > _TEASER_NARRATIVE_CHARS:
        teaser += "..."

    period_disp = _format_period_for_display(
        str(memo.get("period_start") or ""),
        str(memo.get("period_end") or ""),
    )
    n_hypotheses = len(memo.get("hypothesis_candidates") or [])
    memo_id = str(memo.get("memo_id") or "")

    return (
        f"Ugentligt meta-læringsmemo (period {period_disp}), "
        f"unacknowledged:\n{teaser}\n"
        f"Hypothesis-kandidater: {n_hypotheses}. "
        f"Tool: read_learning_memo(memo_id='{memo_id}')."
    )
