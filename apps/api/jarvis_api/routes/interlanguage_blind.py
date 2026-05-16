"""Interlanguage validation — Bjørn blind dommer UI route.

Phase 3+4 spec §4. Bjørn ser én expression ad gangen, vælger forfatter.
Ingen metadata-leak under sessionen.

Endpoints:
- GET  /interlanguage-blind                — HTML UI
- POST /interlanguage-blind/api/start      — start ny session (genererer trials)
- GET  /interlanguage-blind/api/next       — næste ubevarede trial
- POST /interlanguage-blind/api/answer     — submit svar
- GET  /interlanguage-blind/api/progress   — fremgang + accuracy
- POST /interlanguage-blind/api/finish     — gem free-text observations
- GET  /interlanguage-blind/api/confusion  — confusion-matrix (slut-skærm)

Modes:
- ?mode=demo — Bjørn træner sig selv på random eksisterende expressions
- ?mode=real — kun når Phase 2 er færdig (dag 7)

Spec: docs/superpowers/specs/2026-05-16-interlanguage-validation-phase3-4-design.md
"""
from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from core.runtime.db import connect
from core.runtime.db_interlanguage_blind import (
    create_alpha_trial,
    create_delta_trial,
    get_confusion_matrix,
    get_next_unanswered,
    get_progress,
    store_free_text_observations,
    submit_answer,
)

router = APIRouter(prefix="/interlanguage-blind", tags=["interlanguage-blind"])

# Per spec §4 — α har 5 peers (uden +JP-cohorts) for ikke at over-loade
# Bjørn med "lyder de ens?"-trials. δ-trials sammenligner +JP vs -alone.
ALPHA_PEERS = ["jarvis", "claude", "glm", "ollama_local", "random"]
ALPHA_TRIALS_PER_SESSION = 50
DELTA_TRIALS_PER_SESSION = 25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_expressions_by_peer(peer_id: str, limit: int) -> list[dict[str, Any]]:
    """Hent op til limit random expressions fra peer."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT expression_id, expression_text
               FROM interlanguage_practice
               WHERE peer_id = ? AND length(expression_text) >= 3
               ORDER BY RANDOM() LIMIT ?""",
            (peer_id, limit),
        ).fetchall()
    return [{"id": r["expression_id"], "text": r["expression_text"]} for r in rows]


def _generate_alpha_trials(session_id: str, mode: str) -> int:
    """Generér 50 α-trials — 10 fra hver af 5 peers, shuffled."""
    pool: list[tuple[dict[str, str], str]] = []  # (expression, true_peer_id)
    per_peer = ALPHA_TRIALS_PER_SESSION // len(ALPHA_PEERS)
    for peer in ALPHA_PEERS:
        exprs = _fetch_expressions_by_peer(peer, per_peer)
        for e in exprs:
            pool.append((e, peer))
    random.shuffle(pool)
    for idx, (expr, true_peer) in enumerate(pool, start=1):
        create_alpha_trial(
            session_id=session_id,
            trial_index=idx,
            expression_id=expr["id"],
            expression_text=expr["text"],
            true_peer_id=true_peer,
            mode=mode,
        )
    return len(pool)


def _generate_delta_trials(session_id: str, mode: str, start_idx: int) -> int:
    """Generér 25 δ-trials — anchor (jarvis) + 2 candidates (1 +JP, 1 -alone)."""
    jarvis_expressions = _fetch_expressions_by_peer("jarvis", 100)
    if not jarvis_expressions:
        return 0
    pairs = [("claude_jp", "claude"), ("glm_jp", "glm")]
    trials_made = 0
    for i in range(DELTA_TRIALS_PER_SESSION):
        if i >= len(jarvis_expressions):
            break
        anchor = jarvis_expressions[i]
        jp_peer, alone_peer = pairs[i % 2]
        jp_pool = _fetch_expressions_by_peer(jp_peer, 1)
        alone_pool = _fetch_expressions_by_peer(alone_peer, 1)
        if not jp_pool or not alone_pool:
            continue  # ikke nok data — skip denne trial
        jp_cand = jp_pool[0]
        alone_cand = alone_pool[0]
        # Random A/B swap (anti-position-bias)
        if random.random() < 0.5:
            cand_a, cand_b = jp_cand, alone_cand
            jp_position = "A"
            peer_a, peer_b = jp_peer, alone_peer
        else:
            cand_a, cand_b = alone_cand, jp_cand
            jp_position = "B"
            peer_a, peer_b = alone_peer, jp_peer
        create_delta_trial(
            session_id=session_id,
            trial_index=start_idx + i + 1,
            anchor_id=anchor["id"],
            anchor_text=anchor["text"],
            candidate_a_id=cand_a["id"],
            candidate_a_text=cand_a["text"],
            candidate_a_peer_id=peer_a,
            candidate_b_id=cand_b["id"],
            candidate_b_text=cand_b["text"],
            candidate_b_peer_id=peer_b,
            jp_position=jp_position,
            mode=mode,
        )
        trials_made += 1
    return trials_made


def _strip_peer_from_trial(trial: dict[str, Any]) -> dict[str, Any]:
    """Fjern peer-id og other-metadata fra trial-dict før vi sender til frontend.
    Bjørn må IKKE se sandheden under blind-sessionen.
    """
    safe_keys = {
        "trial_id", "trial_type", "trial_index", "mode",
        "expression_text",
        "anchor_expression_text",
        "candidate_a_text", "candidate_b_text",
        "presented_at",
    }
    return {k: trial.get(k) for k in safe_keys if k in trial}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class StartSessionRequest(BaseModel):
    session_id: str
    mode: str = "demo"  # 'demo' or 'real'


@router.post("/api/start")
def start_session(body: StartSessionRequest) -> JSONResponse:
    """Start ny blind-dommer session.

    Genererer 50 α-trials + 25 δ-trials, sat i tilfældig rækkefølge.
    Hvis session-ID allerede har trials, error 409.
    """
    if body.mode not in ("demo", "real"):
        raise HTTPException(400, "mode skal være 'demo' eller 'real'")
    with connect() as conn:
        existing = conn.execute(
            "SELECT COUNT(*) AS cnt FROM interlanguage_blind_trials WHERE session_id = ?",
            (body.session_id,),
        ).fetchone()
    if existing and existing["cnt"]:
        raise HTTPException(409, f"session_id '{body.session_id}' eksisterer allerede ({existing['cnt']} trials)")
    n_alpha = _generate_alpha_trials(body.session_id, body.mode)
    n_delta = _generate_delta_trials(body.session_id, body.mode, start_idx=n_alpha)
    return JSONResponse({
        "session_id": body.session_id,
        "mode": body.mode,
        "alpha_trials": n_alpha,
        "delta_trials": n_delta,
        "total": n_alpha + n_delta,
    })


@router.get("/api/next")
def next_trial(session_id: str = Query(...)) -> JSONResponse:
    """Hent næste ubevarede trial i sessionen — uden true-peer-id leak."""
    trial = get_next_unanswered(session_id=session_id)
    if trial is None:
        return JSONResponse({"done": True, "trial": None})
    return JSONResponse({"done": False, "trial": _strip_peer_from_trial(trial)})


class AnswerRequest(BaseModel):
    trial_id: str
    answer: str


@router.post("/api/answer")
def submit_answer_route(body: AnswerRequest) -> JSONResponse:
    """Submit svar. Returnerer correctness men IKKE forkert/rigtigt-besked.

    Frontend må vælge selv om den vil vise feedback (skal IKKE for real-mode).
    Vi returnerer den faktiske correct-værdi men frontend skjuler den.
    """
    try:
        result = submit_answer(trial_id=body.trial_id, user_answer=body.answer)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return JSONResponse({"saved": True, "correct": result["correct"]})


@router.get("/api/progress")
def progress(session_id: str = Query(...)) -> JSONResponse:
    return JSONResponse(get_progress(session_id=session_id))


class FinishRequest(BaseModel):
    session_id: str
    free_text: str = ""


@router.post("/api/finish")
def finish_session(body: FinishRequest) -> JSONResponse:
    if body.free_text:
        store_free_text_observations(session_id=body.session_id, text=body.free_text)
    confusion = get_confusion_matrix(session_id=body.session_id)
    return JSONResponse({"saved": True, "confusion_matrix": confusion})


@router.get("/api/confusion")
def confusion(session_id: str = Query(...)) -> JSONResponse:
    return JSONResponse(get_confusion_matrix(session_id=session_id))


# ---------------------------------------------------------------------------
# Static HTML
# ---------------------------------------------------------------------------

_HTML_PATH = Path(__file__).parent / "interlanguage_blind_ui.html"


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def serve_ui() -> HTMLResponse:
    if not _HTML_PATH.exists():
        return HTMLResponse("<h1>UI ikke fundet</h1>", status_code=500)
    return HTMLResponse(_HTML_PATH.read_text(encoding="utf-8"))
