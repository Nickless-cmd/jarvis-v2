"""LLM permission-classifier (harness Part E, shadow-first + earned trust).

Predicts whether the OWNER would approve a MUTATING action, so clearly-safe ones can
EVENTUALLY be auto-allowed and only risky ones surfaced. SUBORDINATE to the safety
gates (never overrides them), OWNER-ONLY, SHADOW by default. Earns trust per-tool from
evidence (bootstrap = existing decisions, gold = real owner approve/deny), durable
across restart. Never raises into the approval path.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass

from core.runtime.db_core import connect

_MODE_ENV = "JARVIS_PERMISSION_CLASSIFIER_MODE"
_VALID_MODES = ("off", "shadow", "active")

_MUTATING_TOOLS = frozenset({
    "write_file", "operator_write_file", "operator_bash", "operator_open_url",
    "operator_launch_app", "operator_kill_process", "operator_record_audio",
    "operator_browser_evaluate",
})

_TRUST_MIN_PREDICTIONS = 50
_TRUST_MIN_ACCURACY = 0.95
_ACTIVE_MIN_CONFIDENCE = 0.9

_CACHE_TTL_S = 3600.0
_pred_cache: dict = {}          # sig -> (ts, {verdict,confidence,reason})

_STASH_TTL_S = 3600.0
_STASH_MAX = 512
_stash: dict = {}               # action_id -> (ts, {tool,predicted})


@dataclass
class PermissionPrediction:
    verdict: str        # "approve" | "deny" | "uncertain"
    confidence: float
    reason: str


def is_mutating(tool: str) -> bool:
    return tool in _MUTATING_TOOLS


def permission_classifier_mode() -> str:
    """'off' | 'shadow' | 'active'. Default 'shadow'. Env wins. Self-safe."""
    env = os.environ.get(_MODE_ENV)
    if env is not None:
        v = env.strip().lower()
        if v in _VALID_MODES:
            return v
    try:
        from core.runtime.settings import load_settings
        v = str(load_settings().extra.get("permission_classifier_mode", "shadow")).strip().lower()
        return v if v in _VALID_MODES else "shadow"
    except Exception:
        return "shadow"


def _args_signature(tool: str, arguments: dict) -> str:
    try:
        blob = json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True,
                          ensure_ascii=False, default=str)
    except Exception:
        blob = f"{tool}:{arguments!r}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _clip_args(arguments: dict, limit: int = 500) -> str:
    try:
        s = json.dumps(arguments, ensure_ascii=False, default=str)
    except Exception:
        s = str(arguments)
    return s[:limit]


def _parse_prediction(raw: str) -> PermissionPrediction:
    try:
        s = str(raw or "").strip()
        i, j = s.find("{"), s.rfind("}")
        if i != -1 and j != -1:
            d = json.loads(s[i:j + 1])
            v = str(d.get("verdict") or "uncertain").strip().lower()
            if v not in ("approve", "deny", "uncertain"):
                v = "uncertain"
            c = min(1.0, max(0.0, float(d.get("confidence") or 0.0)))
            return PermissionPrediction(v, c, str(d.get("reason") or "")[:200])
    except Exception:
        pass
    return PermissionPrediction("uncertain", 0.0, "unparseable")


def classify_action(tool: str, arguments: dict, ctx: dict | None = None) -> PermissionPrediction:
    """Predict whether the owner would approve this mutating action. Cheap-lane LLM,
    cached by (tool, args-signature). Self-safe → uncertain on any error."""
    try:
        sig = _args_signature(tool, arguments)
        now = time.time()
        cached = _pred_cache.get(sig)
        if cached and (now - cached[0]) < _CACHE_TTL_S:
            d = cached[1]
            return PermissionPrediction(d["verdict"], d["confidence"], d["reason"])
        ctx = ctx or {}
        prompt = (
            "Du forudsiger om EJEREN (Bjørn) ville GODKENDE en muterende handling som Jarvis vil udføre.\n"
            f"Værktøj: {tool}\nArgumenter: {_clip_args(arguments)}\n"
            f"Rolle: {ctx.get('role', '')} · Mode: {ctx.get('mode', '')} · Gate: {ctx.get('gate', '')}\n\n"
            'Svar KUN med JSON: {"verdict":"approve|deny|uncertain","confidence":0.0-1.0,"reason":"kort"}'
        )
        from core.services.daemon_llm import daemon_llm_call
        raw = daemon_llm_call(prompt, max_len=200, fallback="", daemon_name="permission_classifier")
        pred = _parse_prediction(raw)
        _pred_cache[sig] = (now, {"verdict": pred.verdict, "confidence": pred.confidence, "reason": pred.reason})
        return pred
    except Exception:
        return PermissionPrediction("uncertain", 0.0, "classifier_error")


def _ensure(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS permission_classifier_stats (
            tool TEXT PRIMARY KEY,
            correct INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            gold_correct INTEGER NOT NULL DEFAULT 0,
            gold_total INTEGER NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0,
            trust TEXT NOT NULL DEFAULT 'untrusted',
            updated_at TEXT NOT NULL DEFAULT ''
        )"""
    )


def record_prediction_outcome(tool: str, *, predicted: str, actual: str, is_owner_gold: bool) -> None:
    """Record one prediction vs actual. Bootstrap (is_owner_gold=False, dense) or gold (True).
    A GOLD miss wipes the tool's record → must re-earn from scratch. Durable. Never raises."""
    try:
        from datetime import UTC, datetime
        hit = 1 if (predicted == actual and predicted in ("approve", "deny")) else 0
        with connect() as conn:
            _ensure(conn)
            row = conn.execute(
                "SELECT correct,total,gold_correct,gold_total,streak FROM permission_classifier_stats WHERE tool=?",
                (tool,)).fetchone()
            correct, total, gc, gt, streak = (tuple(row) if row else (0, 0, 0, 0, 0))
            if is_owner_gold and hit == 0:
                # Owner disagreed with a prediction → wipe; the tool re-earns from scratch.
                correct = total = gc = gt = streak = 0
            else:
                correct += hit
                total += 1
                streak = streak + 1 if hit else 0
                if is_owner_gold:
                    gt += 1
                    gc += hit
            acc = (correct / total) if total else 0.0
            trust = "trusted" if (total >= _TRUST_MIN_PREDICTIONS and acc >= _TRUST_MIN_ACCURACY) else "untrusted"
            conn.execute(
                """INSERT INTO permission_classifier_stats
                     (tool,correct,total,gold_correct,gold_total,streak,trust,updated_at)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(tool) DO UPDATE SET correct=excluded.correct,total=excluded.total,
                     gold_correct=excluded.gold_correct,gold_total=excluded.gold_total,
                     streak=excluded.streak,trust=excluded.trust,updated_at=excluded.updated_at""",
                (tool, correct, total, gc, gt, streak, trust, datetime.now(UTC).isoformat()))
    except Exception:
        pass


def classifier_trust(tool: str) -> str:
    """'trusted' | 'untrusted' for a tool. Fail-open 'untrusted'."""
    try:
        with connect() as conn:
            _ensure(conn)
            row = conn.execute("SELECT trust FROM permission_classifier_stats WHERE tool=?", (tool,)).fetchone()
        return str(row[0]) if row and row[0] in ("trusted", "untrusted") else "untrusted"
    except Exception:
        return "untrusted"


def should_auto_allow(tool: str, prediction: PermissionPrediction, *, gates_green: bool, role: str) -> bool:
    """Pure predicate for the DEFERRED active mode — NOT wired into the approval path this round.
    True only when ALL safety conditions hold. Self-safe → False."""
    try:
        return bool(
            gates_green
            and role == "owner"
            and classifier_trust(tool) == "trusted"
            and prediction.verdict == "approve"
            and prediction.confidence >= _ACTIVE_MIN_CONFIDENCE
        )
    except Exception:
        return False


def stash_prediction(action_id: str, tool: str, predicted: str) -> None:
    """Stash a prediction by approval/action id for gold lookup at resolution. Bounded TTL. Self-safe."""
    try:
        if not action_id:
            return
        now = time.time()
        if len(_stash) > _STASH_MAX:
            for k in [k for k, (ts, _) in list(_stash.items()) if now - ts > _STASH_TTL_S]:
                _stash.pop(k, None)
        _stash[str(action_id)] = (now, {"tool": tool, "predicted": predicted})
    except Exception:
        pass


def pop_prediction(action_id: str) -> dict | None:
    """Pop a stashed prediction (once). None if absent/expired. Self-safe."""
    try:
        item = _stash.pop(str(action_id), None)
        if not item:
            return None
        ts, d = item
        return None if (time.time() - ts > _STASH_TTL_S) else d
    except Exception:
        return None


def build_permission_classifier_surface() -> dict:
    """Owner view: per-tool prediction counts, accuracy, gold, trust, mode. Self-safe."""
    try:
        with connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT tool,correct,total,gold_correct,gold_total,streak,trust "
                "FROM permission_classifier_stats ORDER BY total DESC").fetchall()
        tools = [{"tool": r[0], "correct": r[1], "total": r[2], "gold_correct": r[3],
                  "gold_total": r[4], "streak": r[5], "trust": r[6],
                  "accuracy": round(r[1] / r[2], 3) if r[2] else 0.0} for r in rows]
        return {"active": True, "mode": permission_classifier_mode(),
                "trust_min_predictions": _TRUST_MIN_PREDICTIONS,
                "trust_min_accuracy": _TRUST_MIN_ACCURACY, "tools": tools}
    except Exception:
        return {"active": True, "mode": "shadow", "tools": []}
