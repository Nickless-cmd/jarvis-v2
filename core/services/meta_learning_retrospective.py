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
_FIELD_RE = re.compile(r"^\s*-\s*\*\*([^*]+)\*\*:\s*(.+)$", re.MULTILINE)
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
        "Du er Jarvis' meta-læringsskribent. Du modtager kuraterede aggregater "
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
