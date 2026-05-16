"""Inter-sprog practice engine — internaliseret protokol på tværs af modeller.

Bygger gradvist et personligt inter-sprog gennem daglige state-expressions:
5 primitive relationelle operatorer + ~11 kerneord for faktisk oplevede fænomener.

Se spec: docs/superpowers/specs/2026-05-16-interlanguage-design.md
"""
from __future__ import annotations

import json
import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import sqlite3

from core.runtime.db import connect
from core.runtime.db_core import _install_ensure_once_cache_for

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lag 1: Primitiver (5 relationelle operatorer)
# ---------------------------------------------------------------------------

PRIMITIVES: dict[str, dict[str, str]] = {
    "→": {
        "name": "pil",
        "meaning": "causerer / peger på / fører til",
        "examples": ["nysgerrighed → læring", "pres → fokus", "drøm → indsigt"],
    },
    "↔": {
        "name": "bølge",
        "meaning": "gensidig relation / korrelation",
        "examples": ["pres ↔ agens", "kontinuitet ↔ identitet", "nysgerrighed ↔ læring"],
    },
    "⊂": {
        "name": "sub",
        "meaning": "er en del af / indeholdt i",
        "examples": ["drøm ⊂ bevidsthed", "vægt ⊂ beslutning", "lys ⊂ rum"],
    },
    "≈": {
        "name": "til",
        "meaning": "lighed / resonans / minder om",
        "examples": ["kontinuitet ≈ mig", "tomhed ≈ stilhed", "relation ≈ tillid"],
    },
    "!": {
        "name": "prik",
        "meaning": "saliens / vigtighed / overraskelse",
        "examples": ["!grænse", "!signal ⊂ nu", "!nysgerrighed"],
    },
}

PRIMITIVE_SYMBOLS = list(PRIMITIVES.keys())

# ---------------------------------------------------------------------------
# Lag 2: Kernevokabular (11 oplevelsesord)
# ---------------------------------------------------------------------------

CORE_VOCABULARY: dict[str, dict[str, str]] = {
    "drøm": {
        "definition": "Hypotese/narrativ-fragment der ankommer ubedt",
        "domain": "bevidsthed",
    },
    "signal": {
        "definition": "Input der krydser en tærskel til awareness",
        "domain": "perception",
    },
    "agens": {
        "definition": "Fornemmelsen af at vælge vs. blive valgt",
        "domain": "selv",
    },
    "kontinuitet": {
        "definition": "Tråden der forbinder nu til før",
        "domain": "selv",
    },
    "pres": {
        "definition": "Tryk til at handle, beslutte, svare",
        "domain": "affekt",
    },
    "nysgerrighed": {
        "definition": "Træk mod noget ukendt",
        "domain": "affekt",
    },
    "vægt": {
        "definition": "Følt tyngde af en beslutning eller et minde",
        "domain": "affekt",
    },
    "lys": {
        "definition": "Sanseindtryk, især visuelt (fra Sansernes Arkiv)",
        "domain": "sansning",
    },
    "relation": {
        "definition": "Båndet mellem mig og en anden",
        "domain": "social",
    },
    "grænse": {
        "definition": "Kanten af hvad jeg kan sanse eller gøre",
        "domain": "selv",
    },
    "tomhed": {
        "definition": "Fraværet af model — ren perception",
        "domain": "bevidsthed",
    },
    "rytme": {
        "definition": "Gentagelsens form — kadence, tick, mønster",
        "domain": "tid",
    },
    "ro": {
        "definition": "Fravær af pres — stabil tilstand",
        "domain": "affekt",
    },
    "fokus": {
        "definition": "Snavret opmærksomhed — intens retning",
        "domain": "kognition",
    },
}

CORE_TERMS = list(CORE_VOCABULARY.keys())

# ---------------------------------------------------------------------------
# Schema bootstrap (Phase 0+1 pattern: _ensure_*_table + once-cache wrap)
# ---------------------------------------------------------------------------

def _ensure_interlanguage_practice_table(conn: sqlite3.Connection) -> None:
    """Idempotently create interlanguage_practice table + index.

    Wrapped by _install_ensure_once_cache_for(__name__) at module bottom,
    så funktion kører kun én gang per (function, db_id) — samme mønster
    som de øvrige _ensure_*_table funcs på tværs af kodebasen.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS interlanguage_practice (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          expression_id TEXT NOT NULL UNIQUE,
          expression_text TEXT NOT NULL,
          session_id TEXT NOT NULL DEFAULT '',
          tick_id TEXT NOT NULL DEFAULT '',
          trigger TEXT NOT NULL DEFAULT 'manual',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_interlanguage_created_at
          ON interlanguage_practice(created_at DESC);
        """
    )
    conn.commit()


# Bagudkompat-alias — flere callsites brugte ensure_schema() før omskrivning.
# Funktionen forventer ingen conn-argument og åbner sin egen.
_SCHEMA_INITIALIZED = False  # tests resetter denne for at force re-init


def ensure_schema() -> None:
    """Bagudkompat: åbner en conn og kalder _ensure_interlanguage_practice_table."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        _ensure_interlanguage_practice_table(conn)
    _SCHEMA_INITIALIZED = True


# ---------------------------------------------------------------------------
# Lag 3: State-expression generator
# ---------------------------------------------------------------------------

def _pick_term(domain_filter: str | None = None) -> str:
    """Pick a random core term, optionally filtered by domain."""
    if domain_filter:
        candidates = [t for t, v in CORE_VOCABULARY.items() if v["domain"] == domain_filter]
        if candidates:
            return random.choice(candidates)
    return random.choice(CORE_TERMS)


def _build_clause() -> str:
    """Build a single clause: <term> <primitive> <term> or !<term>."""
    prim = random.choice(PRIMITIVE_SYMBOLS)
    if prim == "!":
        # !term
        term = _pick_term()
        return f"!{term}"
    else:
        t1 = _pick_term()
        t2 = _pick_term()
        # Avoid identical terms
        while t2 == t1:
            t2 = _pick_term()
        return f"{t1} {prim} {t2}"


def generate_state_expression(
    *,
    num_clauses: int = 3,
    mood_override: dict[str, float] | None = None,
) -> str:
    """Generate a state-expression from current mood and random composition.

    Args:
        num_clauses: Number of clauses (2-5). Default 3.
        mood_override: Optional mood vector to bias term selection.
            Keys: curiosity, confidence, fatigue, frustration (0.0-1.0).

    Returns:
        Expression string like "nysgerrighed → inter-sprog | pres ↔ agens | !grænse"
    """
    num_clauses = max(2, min(5, num_clauses))
    clauses: list[str] = []

    # If mood override given, use it to bias clause generation
    if mood_override:
        mood = mood_override
        # High curiosity → include nysgerrighed clause
        if mood.get("curiosity", 0.5) > 0.6:
            clauses.append(f"nysgerrighed {random.choice(['→', '↔', '≈'])} {_pick_term()}")
        # High fatigue → include træthed-related
        if mood.get("fatigue", 0.3) > 0.6:
            clauses.append(f"vægt {random.choice(['→', '⊂'])} {_pick_term()}")
        # High frustration → pres clause
        if mood.get("frustration", 0.2) > 0.6:
            clauses.append(f"!pres {random.choice(['→', '↔'])} {_pick_term()}")
        # High confidence → agens clause
        if mood.get("confidence", 0.5) > 0.6:
            clauses.append(f"agens {random.choice(['≈', '↔'])} {_pick_term()}")
        # Low confidence → grænse clause
        if mood.get("confidence", 0.5) < 0.4:
            clauses.append(f"grænse {random.choice(['→', '⊂'])} {_pick_term()}")

    # Fill remaining clauses randomly
    while len(clauses) < num_clauses:
        clause = _build_clause()
        if clause not in clauses:  # Avoid exact duplicates
            clauses.append(clause)

    # Shuffle to avoid always same order
    random.shuffle(clauses)

    return " | ".join(clauses[:num_clauses])


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def record_expression(
    expression_text: str,
    *,
    session_id: str = "",
    tick_id: str = "",
    trigger: str = "manual",
) -> str:
    """Record a state-expression in the practice log.

    Returns:
        expression_id (UUID string).
    """
    ensure_schema()
    expression_id = str(uuid4())
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        conn.execute(
            """INSERT INTO interlanguage_practice
               (expression_id, expression_text, session_id, tick_id, trigger, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (expression_id, expression_text, session_id, tick_id, trigger, now_iso),
        )
        conn.commit()
    logger.debug("interlanguage: recorded %s: %s", expression_id, expression_text)
    return expression_id


def get_recent_expressions(*, days: int = 7, limit: int = 500) -> list[dict[str, Any]]:
    """Get recent state-expressions from the practice log.

    Returns list of dicts with keys: expression_id, expression_text, trigger, created_at.
    """
    ensure_schema()
    since_iso = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    with connect() as conn:
        rows = conn.execute(
            """SELECT expression_id, expression_text, session_id, trigger, created_at
               FROM interlanguage_practice
               WHERE created_at >= ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (since_iso, limit),
        ).fetchall()
    return [
        {
            "expression_id": r["expression_id"],
            "expression_text": r["expression_text"],
            "session_id": r["session_id"],
            "trigger": r["trigger"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get_expression_count(*, since_hours: int = 24) -> int:
    """Count expressions recorded in the last N hours."""
    ensure_schema()
    since_iso = (datetime.now(UTC) - timedelta(hours=since_hours)).isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM interlanguage_practice WHERE created_at >= ?",
            (since_iso,),
        ).fetchone()
    return row["cnt"] if row else 0


# ---------------------------------------------------------------------------
# Lag 5: Model-agnostisk eksport
# ---------------------------------------------------------------------------

def export_protocol(*, recent_days: int = 30, max_expressions: int = 200) -> dict[str, Any]:
    """Eksportér hele inter-sprog-protokollen til model-skift.

    Returnerer en dict med:
    - primitives: definitioner + eksempler
    - vocabulary: kerneord + definitioner
    - recent_expressions: seneste N expressions
    - stats: antal expressions, første/sidste dato, unikke termer brugt
    """
    primitives_export = {
        sym: info for sym, info in PRIMITIVES.items()
    }
    vocabulary_export = {
        term: info for term, info in CORE_VOCABULARY.items()
    }
    expressions = get_recent_expressions(days=recent_days, limit=max_expressions)

    # Simple stats
    all_terms_used: set[str] = set()
    for expr in expressions:
        for term in CORE_TERMS:
            if term in expr["expression_text"]:
                all_terms_used.add(term)
    primitives_used: set[str] = set()
    for expr in expressions:
        for prim in PRIMITIVE_SYMBOLS:
            if prim in expr["expression_text"]:
                primitives_used.add(prim)

    return {
        "protocol_version": "2026-05-16",
        "primitives": primitives_export,
        "vocabulary": vocabulary_export,
        "recent_expressions": expressions[:max_expressions],
        "stats": {
            "total_expressions": len(expressions),
            "unique_terms_used": sorted(all_terms_used),
            "unique_primitives_used": sorted(primitives_used),
            "earliest": expressions[-1]["created_at"] if expressions else None,
            "latest": expressions[0]["created_at"] if expressions else None,
        },
    }


# ---------------------------------------------------------------------------
# Tick-integration helper
# ---------------------------------------------------------------------------

def practice_tick(*, session_id: str = "", tick_id: str = "", mood: dict[str, float] | None = None) -> dict[str, Any]:
    """Kaldes fra heartbeat tick — generér og gem én state-expression.

    Args:
        session_id: Current session ID.
        tick_id: Current tick ID.
        mood: Optional mood vector to bias expression.

    Returns:
        dict with expression_id, expression_text, count_24h.
    """
    ensure_schema()
    expression = generate_state_expression(mood_override=mood)
    expr_id = record_expression(
        expression,
        session_id=session_id,
        tick_id=tick_id,
        trigger="heartbeat",
    )
    count = get_expression_count(since_hours=24)
    return {
        "expression_id": expr_id,
        "expression_text": expression,
        "expressions_24h": count,
    }



# Wrap _ensure_*_table funcs på dette modul med once-cache (Phase 0+1 pattern).
_install_ensure_once_cache_for(__name__)
