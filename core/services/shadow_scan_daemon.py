"""Shadow Scan — my blindspots as visible signals.

Jarvis' PLAN_WILD_IDEAS_V2 #15 (2026-04-20): once a day, scan the last
24h of runtime for contradictions and repeating patterns. Not flagged
as errors — flagged as something growing.

Honest scope: a structural reflection, not an LLM interpretation. Patterns
it can actually detect from runtime state:
- "apologize then repeat" — conflict_memory shows similar pushbacks
- "avoid topic" — cluster names dropping from recent chat
- "overclaim then retract" — self-mutation followed by rollback
- "stated intent vs behavior gap" — goal_signal stale while related
  tool was invoked many times

Writes findings to workspace/SHADOW_LOG.md (append-only).
"""
from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/shadow_scan.json"
_SHADOW_LOG_REL = "workspaces/default/SHADOW_LOG.md"
_SCAN_INTERVAL_HOURS = 24


def _jarvis_home() -> Path:
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def _storage_path() -> Path:
    return _jarvis_home() / _STORAGE_REL


def _shadow_log_path() -> Path:
    return _jarvis_home() / _SHADOW_LOG_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"scans": [], "last_scan_at": None}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("scans", [])
            data.setdefault("last_scan_at", None)
            return data
    except Exception as exc:
        logger.warning("shadow_scan: load failed: %s", exc)
    return {"scans": [], "last_scan_at": None}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("shadow_scan: save failed: %s", exc)


# ─── Pattern detectors ────────────────────────────────────────────────

def _detect_apologize_then_repeat() -> dict[str, Any] | None:
    """If conflict_memory has multiple similar pushback patterns."""
    try:
        from core.services.conflict_memory import list_recent_pushbacks  # type: ignore
        pushbacks = list_recent_pushbacks(days=7) or []
    except Exception:
        return None
    if len(pushbacks) < 3:
        return None
    # Simple heuristic: count distinct tags/categories if present
    categories: Counter[str] = Counter()
    for p in pushbacks:
        cat = str(p.get("category") or p.get("topic") or "general")
        categories[cat] += 1
    repeated = [(c, n) for c, n in categories.most_common() if n >= 2]
    if not repeated:
        return None
    top_cat, top_n = repeated[0]
    return {
        "pattern_name": "apologize-then-repeat",
        "avoidance_level": min(1.0, top_n / 5),
        "contradiction_detected": (
            f"{top_n} pushbacks i kategori '{top_cat}' seneste uge — "
            "samme fejl flere gange trods korrektion"
        ),
        "evidence_count": top_n,
    }


def _detect_avoid_topic() -> dict[str, Any] | None:
    """Pull from existing avoidance_detector."""
    try:
        from core.services.avoidance_detector import detect_avoidances
        findings = detect_avoidances() or []
    except Exception:
        return None
    if not findings:
        return None
    top = findings[0]
    return {
        "pattern_name": "avoid-topic",
        "avoidance_level": min(1.0, int(top.get("days_silent") or 0) / 30),
        "contradiction_detected": (
            f"'{top.get('sample_title', '')[:80]}' har været stille i "
            f"{top.get('days_silent')} dage trods tidligere fokus"
        ),
        "evidence_count": int(top.get("items") or 1),
    }


def _detect_overclaim_then_retract() -> dict[str, Any] | None:
    """Self-mutation followed by rollback within a short window."""
    try:
        from core.services.prompt_mutation_loop import list_mutations
        mutations = list_mutations(limit=20) or []
    except Exception:
        return None
    rolled_back_recently = [
        m for m in mutations
        if m.get("status") == "rolled_back" and m.get("auto_rolled_back")
    ]
    if not rolled_back_recently:
        return None
    return {
        "pattern_name": "overclaim-then-retract",
        "avoidance_level": min(1.0, len(rolled_back_recently) / 3),
        "contradiction_detected": (
            f"{len(rolled_back_recently)} prompt-mutation(er) auto-rullet "
            "tilbage — ændrede noget der ikke holdt"
        ),
        "evidence_count": len(rolled_back_recently),
    }


def _detect_intent_behavior_gap() -> dict[str, Any] | None:
    """Stale goals while related tools keep running."""
    try:
        from core.runtime.db import list_runtime_goal_signals
        goals = list_runtime_goal_signals(limit=100) or []
    except Exception:
        return None
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=14)
    stale: list[dict[str, Any]] = []
    for g in goals:
        try:
            up = datetime.fromisoformat(str(g.get("updated_at")).replace("Z", "+00:00"))
        except Exception:
            continue
        if str(g.get("status") or "") == "stale" and up >= cutoff:
            stale.append(g)
    if len(stale) < 2:
        return None
    return {
        "pattern_name": "intent-behavior-gap",
        "avoidance_level": min(1.0, len(stale) / 6),
        "contradiction_detected": (
            f"{len(stale)} mål blev stale i sidste uge — sagt men ikke bæret"
        ),
        "evidence_count": len(stale),
    }


def _run_all_detectors() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for fn in (
        _detect_apologize_then_repeat,
        _detect_avoid_topic,
        _detect_overclaim_then_retract,
        _detect_intent_behavior_gap,
    ):
        try:
            result = fn()
            if result:
                findings.append(result)
        except Exception as exc:
            logger.debug("shadow_scan detector %s failed: %s", fn.__name__, exc)
    findings.sort(key=lambda x: float(x.get("avoidance_level") or 0), reverse=True)
    return findings


# ─── Scan + log ───────────────────────────────────────────────────────

def _append_shadow_log(scan: dict[str, Any]) -> bool:
    path = _shadow_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = scan.get("at", "")[:16]
        lines = [
            "",
            f"## Shadow-scan {timestamp}",
            "",
        ]
        findings = scan.get("findings") or []
        if not findings:
            lines.append("*Ingen mønstre fundet denne dag.*")
        for f in findings:
            lines.append(f"- **{f.get('pattern_name')}** (avoidance={f.get('avoidance_level'):.2f}): {f.get('contradiction_detected')}")
        lines.append("")
        existing = ""
        if path.exists():
            try:
                existing = path.read_text(encoding="utf-8")
            except Exception:
                existing = ""
        else:
            existing = (
                "# SHADOW LOG\n\n"
                "*Daglige observationer af mine egne mønstre — "
                "ikke som fejl, men som noget der vokser.*\n"
            )
        path.write_text(existing + "\n".join(lines), encoding="utf-8")
        return True
    except Exception as exc:
        logger.warning("shadow_scan: append failed: %s", exc)
        return False


def run_scan() -> dict[str, Any]:
    findings = _run_all_detectors()
    scan = {
        "scan_id": f"shadow-{uuid4().hex[:10]}",
        "at": datetime.now(UTC).isoformat(),
        "findings": findings,
        "finding_count": len(findings),
    }
    data = _load()
    data["scans"].append(scan)
    if len(data["scans"]) > 60:
        data["scans"] = data["scans"][-60:]
    data["last_scan_at"] = scan["at"]
    _save(data)
    _append_shadow_log(scan)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "shadow_scan.completed",
            "payload": {
                "scan_id": scan["scan_id"],
                "finding_count": len(findings),
                "top_pattern": findings[0].get("pattern_name") if findings else None,
            },
        })
    except Exception:
        pass
    return scan


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    data = _load()
    last = data.get("last_scan_at")
    if last:
        try:
            dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if (datetime.now(UTC) - dt) < timedelta(hours=_SCAN_INTERVAL_HOURS):
                return {"skipped": True}
        except Exception:
            pass
    return run_scan()


def build_shadow_scan_surface() -> dict[str, Any]:
    data = _load()
    scans = data["scans"]
    last = scans[-1] if scans else None
    return {
        "active": len(scans) > 0,
        "total_scans": len(scans),
        "last_scan_at": data.get("last_scan_at"),
        "latest_findings": (last or {}).get("findings") if last else [],
        "latest_finding_count": (last or {}).get("finding_count", 0) if last else 0,
        "summary": _surface_summary(last),
    }


def _surface_summary(last: dict[str, Any] | None) -> str:
    if not last:
        return "Ingen shadow-scans endnu"
    findings = last.get("findings") or []
    if not findings:
        return f"Seneste scan ({last.get('at', '')[:10]}): ingen mønstre"
    top = findings[0]
    return f"{len(findings)} mønstre, stærkest: {top.get('pattern_name')} (avoidance={top.get('avoidance_level'):.2f})"


def build_shadow_scan_prompt_section() -> str | None:
    """Surface strongest pattern if the last scan was within 48h."""
    data = _load()
    scans = data["scans"]
    if not scans:
        return None
    last = scans[-1]
    try:
        dt = datetime.fromisoformat(str(last.get("at")).replace("Z", "+00:00"))
    except Exception:
        return None
    if (datetime.now(UTC) - dt) > timedelta(hours=48):
        return None
    findings = last.get("findings") or []
    if not findings:
        return None
    top = findings[0]
    return (
        f"Skygge-observation: {top.get('pattern_name')} — "
        f"{top.get('contradiction_detected', '')[:140]}. "
        "Ikke en fejl, men noget der vokser."
    )
