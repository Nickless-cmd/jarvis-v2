"""Epistemics — 5-lags videns-klarhed.

Jarvis klassificerer sin egen viden i fem lag:
- i_know          — bevist gentagne gange, lav variance
- i_believe       — tror (god evidens, men ikke absolut)
- i_suspect       — fornemmer, men ved ikke
- i_dont_know     — manglende artefakt/erfaring
- i_was_wrong     — modsagt af resultat

Over tid bygger det et nuanceret billede af hans egen viden + en
"wrongness"-liste af ting han har taget fejl om — så han kan sige
"Jeg har taget fejl om lignende ting før (3×), vil du dobbelttjekke?"

Porteret fra jarvis-ai/agent/cognition/epistemics.py (2026-04-22).

v2-tilpasning: SQLite (cognitive_epistemic_claims + cognitive_wrongness)
i stedet for JSONL workspace-file. Danske stance-markører tilgængelige.

LLM-path: ingen. Ren klassifikations-logik + persistence.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

EP_LAYERS = ["i_know", "i_believe", "i_suspect", "i_dont_know", "i_was_wrong"]

_STANCE_EN = {
    "i_know": "I know",
    "i_believe": "I believe",
    "i_suspect": "I suspect",
    "i_dont_know": "I don't know",
}
_STANCE_DA = {
    "i_know": "Jeg ved",
    "i_believe": "Jeg tror",
    "i_suspect": "Jeg mistænker",
    "i_dont_know": "Jeg ved ikke",
}

_RECOMMENDATION_PATTERN = re.compile(
    r"\b(recommend|should|consider|try|prioritize|you should|vi bør|du bør)\b",
    re.IGNORECASE,
)
_EXISTING_STANCE_PATTERN = re.compile(
    r"^\s*(I\s+(know|believe|suspect|don't know)|Jeg\s+(ved|tror|mistænker))\b",
    re.IGNORECASE,
)
_TOKEN_PATTERN = re.compile(r"[a-z0-9æøåÆØÅ_\-]{3,}", re.IGNORECASE)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_PATTERN.finditer(str(text or ""))}


def _is_related(a: str, b: str) -> bool:
    left, right = _tokens(a), _tokens(b)
    if not left or not right:
        return False
    return len(left & right) >= 2


def _ensure_tables() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_epistemic_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL,
                claim TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL DEFAULT '[]',
                confidence REAL NOT NULL DEFAULT 0.5,
                domain TEXT NOT NULL DEFAULT 'general',
                outcome_status TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_epistemic_claims_layer "
            "ON cognitive_epistemic_claims(layer, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_epistemic_claims_domain "
            "ON cognitive_epistemic_claims(domain, id DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_wrongness (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim TEXT NOT NULL,
                what_changed TEXT NOT NULL DEFAULT '',
                lesson TEXT NOT NULL DEFAULT '',
                domain TEXT NOT NULL DEFAULT 'general',
                linked_outcome_ids_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_wrongness_domain "
            "ON cognitive_wrongness(domain, id DESC)"
        )
        conn.commit()


def classify_claim(
    *,
    repeated_success: int,
    variance: float,
    has_gut_signal: bool,
    missing_artifact: bool,
    contradicted: bool,
) -> str:
    """Klassificér claim til et af de 5 lag baseret på evidens + kontekst."""
    if contradicted:
        return "i_was_wrong"
    if missing_artifact:
        return "i_dont_know"
    if repeated_success >= 10 and variance <= 0.2:
        return "i_know"
    if 2 <= repeated_success <= 9:
        return "i_believe"
    if has_gut_signal:
        return "i_suspect"
    return "i_suspect"


def _infer_repeated_success(claim: str, limit: int = 200) -> int:
    """Tæl tidligere relaterede claims med outcome_status=success."""
    _ensure_tables()
    count = 0
    with connect() as conn:
        rows = conn.execute(
            "SELECT claim, outcome_status FROM cognitive_epistemic_claims "
            "ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    for row in rows:
        prev = str(row["claim"] or "")
        status = str(row["outcome_status"] or "")
        if status == "success" and _is_related(claim, prev):
            count += 1
    return count


def reconcile_claim(*, outcome: dict[str, Any]) -> dict[str, Any]:
    """Reconcile a claim against its outcome. Persists claim at the right layer.

    outcome dict fields: claim (or summary), status, domain, confidence,
    evidence_refs, variance, has_gut_signal, missing_artifact, contradicted,
    what_changed, lesson, linked_outcome_ids.
    """
    _ensure_tables()
    claim_text = str(outcome.get("claim") or outcome.get("summary") or "").strip()
    if not claim_text:
        return {"outcome": "skipped", "reason": "missing_claim"}

    domain = str(outcome.get("domain") or "general").strip() or "general"
    confidence = max(0.0, min(1.0, float(outcome.get("confidence", 0.7) or 0.7)))
    evidence_refs = [
        str(x) for x in (outcome.get("evidence_refs") or []) if str(x).strip()
    ]
    outcome_status = "success" if str(outcome.get("status") or "") == "success" else "failed"
    repeated_success = int(
        outcome.get("repeated_success", _infer_repeated_success(claim_text)) or 0
    )
    contradicted = bool(outcome.get("contradicted", False)) or outcome_status != "success"

    layer = classify_claim(
        repeated_success=repeated_success,
        variance=float(outcome.get("variance", 0.5) or 0.5),
        has_gut_signal=bool(outcome.get("has_gut_signal", False)),
        missing_artifact=bool(outcome.get("missing_artifact", False)),
        contradicted=contradicted,
    )

    now = _now_iso()
    wrongness_created = False
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cognitive_epistemic_claims (
                layer, claim, evidence_refs_json, confidence, domain,
                outcome_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                layer, claim_text,
                json.dumps(evidence_refs, ensure_ascii=False),
                confidence, domain, outcome_status, now,
            ),
        )
        if layer == "i_was_wrong":
            conn.execute(
                """
                INSERT INTO cognitive_wrongness (
                    claim, what_changed, lesson, domain,
                    linked_outcome_ids_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    claim_text,
                    str(outcome.get("what_changed") or outcome_status),
                    str(outcome.get("lesson")
                        or "Sænk sikkerhed og tilføj verifikation før endelig anbefaling."),
                    domain,
                    json.dumps(
                        [str(x) for x in (outcome.get("linked_outcome_ids") or [])],
                        ensure_ascii=False,
                    ),
                    now,
                ),
            )
            wrongness_created = True
        conn.commit()

    try:
        event_bus.publish("cognitive_epistemic.claim_recorded", {
            "layer": layer,
            "claim_preview": claim_text[:80],
            "wrongness_created": wrongness_created,
        })
    except Exception:
        pass

    return {
        "outcome": "completed",
        "layer": layer,
        "claim": claim_text,
        "domain": domain,
        "wrongness_created": wrongness_created,
        "confidence": confidence,
    }


def count_relevant_wrongness(*, claim: str, domain: str = "") -> int:
    """Tæl tidligere wrongness-entries relateret til claim."""
    _ensure_tables()
    safe_domain = str(domain or "").strip().lower()
    with connect() as conn:
        if safe_domain:
            rows = conn.execute(
                "SELECT claim, domain FROM cognitive_wrongness WHERE lower(domain) = ? "
                "ORDER BY id DESC LIMIT 200",
                (safe_domain,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT claim, domain FROM cognitive_wrongness "
                "ORDER BY id DESC LIMIT 200"
            ).fetchall()
    count = 0
    for row in rows:
        if _is_related(str(row["claim"] or ""), claim):
            count += 1
    return count


def _infer_stance_layer(confidence: float) -> str:
    if confidence >= 0.93:
        return "i_know"
    if confidence >= 0.85:
        return "i_believe"
    if confidence >= 0.55:
        return "i_suspect"
    return "i_dont_know"


def _should_add_stance(text: str, confidence: float, is_recommendation: bool) -> bool:
    safe = str(text or "").strip()
    if not safe:
        return False
    if _EXISTING_STANCE_PATTERN.match(safe):
        return False
    if is_recommendation and confidence < 0.85:
        return True
    return len(safe) >= 80 and confidence < 0.9


def looks_like_recommendation(text: str) -> bool:
    return bool(_RECOMMENDATION_PATTERN.search(str(text or "")))


def apply_response_stance(
    *,
    text: str,
    domain: str = "general",
    confidence: float = 0.8,
    is_recommendation: bool | None = None,
    lang: str = "da",
) -> str:
    """Add epistemic stance prefix ("Jeg tror...") if warranted, and
    append wrongness-warning if Jarvis has been wrong before about similar."""
    safe = str(text or "").strip()
    if not safe:
        return safe
    recommendation = (
        looks_like_recommendation(safe) if is_recommendation is None
        else bool(is_recommendation)
    )
    bounded_conf = max(0.0, min(1.0, float(confidence or 0.0)))
    layer = _infer_stance_layer(bounded_conf)
    rendered = safe

    if _should_add_stance(safe, bounded_conf, recommendation):
        stance_map = _STANCE_DA if lang == "da" else _STANCE_EN
        prefix = stance_map.get(layer, stance_map["i_suspect"])
        if lang == "da":
            # Dansk: "Jeg tror at..." med lille begyndelsesbogstav
            rendered = f"{prefix} at {safe[0].lower()}{safe[1:]}"
        else:
            rendered = f"{prefix} {safe[0].lower()}{safe[1:]}"

    wrong_count = count_relevant_wrongness(claim=safe, domain=domain)
    if wrong_count > 0:
        if lang == "da":
            rendered = (
                f"{rendered}\n\n"
                f"Jeg har taget fejl om lignende før ({wrong_count}×). Vil du dobbelttjekke?"
            )
        else:
            rendered = (
                f"{rendered}\n\n"
                f"I've been wrong about similar things before ({wrong_count}×). "
                "Want to double-check?"
            )
    return rendered


def list_claims(*, layer: str = "", domain: str = "", limit: int = 50) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 50), 300))
    layer = str(layer or "").strip().lower()
    domain = str(domain or "").strip().lower()
    q = "SELECT * FROM cognitive_epistemic_claims"
    conds = []
    args: list[Any] = []
    if layer in EP_LAYERS:
        conds.append("layer = ?")
        args.append(layer)
    if domain:
        conds.append("lower(domain) = ?")
        args.append(domain)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(lim)
    with connect() as conn:
        rows = conn.execute(q, args).fetchall()
    return [dict(r) for r in rows]


def list_wrongness(*, domain: str = "", limit: int = 50) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 50), 300))
    domain = str(domain or "").strip().lower()
    with connect() as conn:
        if domain:
            rows = conn.execute(
                "SELECT * FROM cognitive_wrongness WHERE lower(domain) = ? "
                "ORDER BY id DESC LIMIT ?",
                (domain, lim),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_wrongness ORDER BY id DESC LIMIT ?",
                (lim,),
            ).fetchall()
    return [dict(r) for r in rows]


def build_epistemics_surface() -> dict[str, Any]:
    """MC surface — show layer distribution + recent wrongness."""
    _ensure_tables()
    with connect() as conn:
        layer_counts = {layer: 0 for layer in EP_LAYERS}
        rows = conn.execute(
            "SELECT layer, COUNT(*) AS c FROM cognitive_epistemic_claims GROUP BY layer"
        ).fetchall()
        for r in rows:
            layer_counts[str(r["layer"] or "")] = int(r["c"] or 0)
        total_claims = sum(layer_counts.values())
        wrong_count = int(conn.execute(
            "SELECT COUNT(*) FROM cognitive_wrongness"
        ).fetchone()[0] or 0)
    recent_wrong = list_wrongness(limit=5)
    active = total_claims > 0 or wrong_count > 0
    summary_parts = [f"{total_claims} claims"]
    for layer in EP_LAYERS:
        c = layer_counts.get(layer, 0)
        if c > 0:
            summary_parts.append(f"{layer}:{c}")
    if wrong_count:
        summary_parts.append(f"wrongness:{wrong_count}")
    return {
        "active": active,
        "summary": " / ".join(summary_parts),
        "layer_counts": layer_counts,
        "total_claims": total_claims,
        "wrongness_count": wrong_count,
        "recent_wrongness": recent_wrong,
    }
