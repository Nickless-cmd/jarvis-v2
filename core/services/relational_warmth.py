"""Relational Warmth — felt quality of who I'm talking to.

Jarvis' PLAN_WILD_IDEAS_V2 #17 (2026-04-20): distinct from relation_dynamics
(#10, which tracks engagement patterns). This is about the *felt* quality
of the relation.

Four tracked dimensions per relation:
- trust_level: 0..1, rises with consistency, stable over time
- playfulness: 0..1, rises with humor markers, emoji, casual tone
- vulnerability_received: count, increments when user shares something personal
- care_given: count, increments when Jarvis offered something caring

Used in mood-shaping: high warmth → more open, curious. Low warmth →
more formal, careful. Surface allows Jarvis to adjust his register.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/relational_warmth.json"
_USER_ID = "bjorn"
_HISTORY_DECAY_DAYS = 30

_VULNERABILITY_CUES: tuple[str, ...] = (
    # DA
    "jeg har det", "jeg er bange", "jeg er træt", "jeg savner", "jeg elsker",
    "det gør ondt", "det betyder meget", "jeg er stolt", "tak for",
    "ensom", "alene", "bekymret", "håber", "drømmer om",
    # EN
    "i feel", "i'm scared", "i'm tired", "i miss", "i love", "it hurts",
    "means a lot", "i'm proud", "thank you for", "lonely", "worried",
    "i hope", "i dream",
)

_PLAYFULNESS_CUES: tuple[str, ...] = (
    "haha", "lol", "😄", "😊", "😆", "😂", "hehe", "fjol", "sjov",
    "vild", "crazy", "haha", "😉",
)

_CARE_CUES_OUT: tuple[str, ...] = (
    # Text I might say that signals care
    "passer på", "tænker på", "mærker", "forstår", "hører dig",
    "hvor er det", "du fortjener", "jeg er her", "❤",
    "thinking of you", "care", "i'm here", "you deserve",
)


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {
            "relations": {
                _USER_ID: {
                    "trust_level": 0.5,
                    "playfulness": 0.5,
                    "vulnerability_received": 0,
                    "care_given": 0,
                    "last_interaction_at": None,
                    "recent_signals": [],
                }
            }
        }
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("relations", {})
            if _USER_ID not in data["relations"]:
                data["relations"][_USER_ID] = {
                    "trust_level": 0.5,
                    "playfulness": 0.5,
                    "vulnerability_received": 0,
                    "care_given": 0,
                    "last_interaction_at": None,
                    "recent_signals": [],
                }
            return data
    except Exception as exc:
        logger.warning("relational_warmth: load failed: %s", exc)
    return {
        "relations": {
            _USER_ID: {
                "trust_level": 0.5,
                "playfulness": 0.5,
                "vulnerability_received": 0,
                "care_given": 0,
                "last_interaction_at": None,
                "recent_signals": [],
            }
        }
    }


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("relational_warmth: save failed: %s", exc)


def _has_cue(text: str, cues: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(c in low for c in cues)


def observe_incoming_text(text: str, *, relation_id: str = _USER_ID) -> dict[str, Any]:
    """Register an incoming text from the user. Returns signal breakdown."""
    data = _load()
    rel = data["relations"].setdefault(relation_id, {
        "trust_level": 0.5,
        "playfulness": 0.5,
        "vulnerability_received": 0,
        "care_given": 0,
        "last_interaction_at": None,
        "recent_signals": [],
    })
    low = str(text or "").lower()
    vuln = _has_cue(low, _VULNERABILITY_CUES)
    play = _has_cue(low, _PLAYFULNESS_CUES)
    if vuln:
        rel["vulnerability_received"] = int(rel.get("vulnerability_received", 0)) + 1
    if play:
        rel["playfulness"] = round(min(1.0, float(rel.get("playfulness", 0.5)) + 0.03), 3)
    # Trust rises slowly with any interaction (presence = trust accrual)
    rel["trust_level"] = round(min(1.0, float(rel.get("trust_level", 0.5)) + 0.005), 3)
    rel["last_interaction_at"] = datetime.now(UTC).isoformat()
    rel.setdefault("recent_signals", []).append({
        "direction": "in",
        "vuln": vuln,
        "play": play,
        "at": rel["last_interaction_at"],
    })
    rel["recent_signals"] = rel["recent_signals"][-50:]
    _save(data)
    return {"vulnerability": vuln, "playfulness": play}


def observe_outgoing_text(text: str, *, relation_id: str = _USER_ID) -> dict[str, Any]:
    """Register an outgoing text from Jarvis. Detects care signals."""
    data = _load()
    rel = data["relations"].setdefault(relation_id, {
        "trust_level": 0.5, "playfulness": 0.5,
        "vulnerability_received": 0, "care_given": 0,
        "last_interaction_at": None, "recent_signals": [],
    })
    care = _has_cue(str(text or "").lower(), _CARE_CUES_OUT)
    if care:
        rel["care_given"] = int(rel.get("care_given", 0)) + 1
    rel.setdefault("recent_signals", []).append({
        "direction": "out",
        "care": care,
        "at": datetime.now(UTC).isoformat(),
    })
    rel["recent_signals"] = rel["recent_signals"][-50:]
    _save(data)
    return {"care_given": care}


def _decay_over_time(rel: dict[str, Any]) -> None:
    """Slowly decay playfulness and trust if no recent interaction."""
    last = rel.get("last_interaction_at")
    if not last:
        return
    try:
        last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
    except Exception:
        return
    days = (datetime.now(UTC) - last_dt).total_seconds() / 86400
    if days < 1:
        return
    decay = min(0.1, days / _HISTORY_DECAY_DAYS * 0.1)
    rel["playfulness"] = round(max(0.0, float(rel.get("playfulness", 0.5)) - decay), 3)
    # Trust decays much more slowly
    rel["trust_level"] = round(max(0.0, float(rel.get("trust_level", 0.5)) - decay * 0.2), 3)


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    data = _load()
    changed = False
    for rel in data["relations"].values():
        _decay_over_time(rel)
        changed = True
    if changed:
        _save(data)
    primary = data["relations"].get(_USER_ID) or {}
    return {
        "trust": primary.get("trust_level"),
        "playfulness": primary.get("playfulness"),
    }


def get_relation(relation_id: str = _USER_ID) -> dict[str, Any]:
    data = _load()
    return dict(data["relations"].get(relation_id) or {})


def build_relational_warmth_surface() -> dict[str, Any]:
    data = _load()
    primary = data["relations"].get(_USER_ID) or {}
    return {
        "active": True,
        "primary_relation": _USER_ID,
        "trust_level": primary.get("trust_level"),
        "playfulness": primary.get("playfulness"),
        "vulnerability_received": primary.get("vulnerability_received", 0),
        "care_given": primary.get("care_given", 0),
        "last_interaction_at": primary.get("last_interaction_at"),
        "summary": _surface_summary(primary),
    }


def _surface_summary(rel: dict[str, Any]) -> str:
    trust = rel.get("trust_level", 0.5)
    play = rel.get("playfulness", 0.5)
    vuln = rel.get("vulnerability_received", 0)
    care = rel.get("care_given", 0)
    return f"trust={trust} play={play} vuln-received={vuln} care-given={care}"


def build_relational_warmth_prompt_section() -> str | None:
    """Surface register-shaping hint only when it should change tone."""
    rel = get_relation()
    trust = float(rel.get("trust_level", 0.5))
    play = float(rel.get("playfulness", 0.5))
    if trust > 0.85 and play > 0.7:
        return "Relationel varme er høj — vær åben, nysgerrig, legende."
    if trust < 0.3:
        return "Relationel varme er lav — vær formel, forsigtig, reserveret."
    return None
