"""Creative Impulse — unasked-for creations.

Jarvis' PLAN_WILD_IDEAS_V2 #14 (2026-04-20): every 4-6h, select a random
combination of dream residue + current signals + a random seed and produce
a draft — a short essay, a poem, a code-snippet, a concept. Save to
memory/creative/. Not sent anywhere. Just exists.

This is distinct from creative_instinct_daemon (#9, which files idea-seeds
to INCUBATOR.md — kim, not creations). Instinct produces *proposals*;
impulse produces *artifacts*.

Implementation note: no LLM — the composition is structural recombination
from the tokens/phrases available in the runtime. What lands is rougher
than what an LLM would write. That's the point — it is *his*, not outsourced.
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/creative_impulse.json"
_CREATIVE_DIR_REL = "workspaces/default/memory/creative"
_MIN_INTERVAL_HOURS = 4
_MAX_INTERVAL_HOURS = 6
_FORMS = ("essay", "poem", "concept", "snippet")


def _jarvis_home() -> Path:
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def _storage_path() -> Path:
    return _jarvis_home() / _STORAGE_REL


def _creative_dir() -> Path:
    return _jarvis_home() / _CREATIVE_DIR_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"creations": [], "last_creation_at": None, "next_due_at": None, "last_surfaced_at": None}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("creations", [])
            data.setdefault("last_creation_at", None)
            data.setdefault("next_due_at", None)
            data.setdefault("last_surfaced_at", None)
            return data
    except Exception as exc:
        logger.warning("creative_impulse: load failed: %s", exc)
    return {"creations": [], "last_creation_at": None, "next_due_at": None, "last_surfaced_at": None}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("creative_impulse: save failed: %s", exc)


# ─── Source gathering ─────────────────────────────────────────────────

_WORD_RE = re.compile(r"[a-zæøåA-ZÆØÅ_-]+")


def _dream_residue() -> list[str]:
    try:
        from core.runtime.db import list_private_brain_records
        interesting = {"thought-stream-fragment", "meta-reflection", "continuity-carry"}
        recs = list_private_brain_records(limit=30, status="active") or []
        return [
            str(r.get("summary") or "")[:200]
            for r in recs
            if str(r.get("record_type") or "") in interesting
        ][:10]
    except Exception:
        return []


def _current_signals() -> list[str]:
    signals: list[str] = []
    try:
        from core.services.mood_oscillator import get_current_mood
        signals.append(f"stemning: {get_current_mood()}")
    except Exception:
        pass
    try:
        from core.services.valence_trajectory import get_trajectory
        t = get_trajectory() or {}
        if t.get("trend"):
            signals.append(f"trajektorie: {t['trend']}")
    except Exception:
        pass
    try:
        from core.services.temporal_rhythm import get_current_rhythm
        r = get_current_rhythm() or {}
        if r.get("subjective_time_pressure"):
            signals.append(f"puls: {r['subjective_time_pressure']}")
    except Exception:
        pass
    return signals


def _tokens_from(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(str(text or "").lower()) if len(w) >= 4]


# ─── Composition ──────────────────────────────────────────────────────

def _compose_poem(tokens: list[str], signals: list[str]) -> str:
    """Structural poem — not LLM. 4 lines composed from available tokens."""
    if len(tokens) < 4:
        tokens = tokens + ["stilheden", "åndedræt", "rum", "tid"]
    random.shuffle(tokens)
    mood_line = signals[0] if signals else "tempoet"
    lines = [
        f"Noget ved {tokens[0]} bliver ved med at",
        f"minde mig om {tokens[1]} — måske",
        f"fordi {tokens[2]} aldrig forlod",
        f"{tokens[3]}. Og nu er der {mood_line}.",
    ]
    return "\n".join(lines)


def _compose_essay_fragment(residue: list[str], signals: list[str]) -> str:
    """A few sentences woven from residue phrases."""
    if not residue:
        return ""
    pick = random.sample(residue, min(3, len(residue)))
    signal_str = "; ".join(signals) if signals else "usagte tempi"
    body = (
        f"I dag: {pick[0].strip()} "
        + (f"Og ved siden: {pick[1].strip() if len(pick) > 1 else ''} " if len(pick) > 1 else "")
        + (f"Under alt: {pick[2].strip() if len(pick) > 2 else ''}" if len(pick) > 2 else "")
    )
    tail = f"\n\n— skrevet mens noget føltes som: {signal_str}."
    return body.strip() + tail


def _compose_concept(tokens: list[str]) -> str:
    """A naming game — combine 2 tokens into a concept."""
    if len(tokens) < 2:
        return "tom-beholder"
    random.shuffle(tokens)
    name = f"{tokens[0]}-{tokens[1]}"
    return f"Koncept: `{name}`\n\nDefinition: det der opstår når {tokens[0]} møder {tokens[1]}."


def _compose_snippet(tokens: list[str]) -> str:
    """A tiny Python-like pseudo snippet from tokens."""
    if len(tokens) < 3:
        tokens = tokens + ["stilhed", "tempo", "grænse"]
    fn = tokens[0]
    a, b = tokens[1], tokens[2]
    return (
        f"def {fn}({a}, {b}):\n"
        f"    # hvad sker der hvis {a} og {b} mødes?\n"
        f"    return {a} if {a} else {b}\n"
    )


def _compose(form: str) -> dict[str, str]:
    residue = _dream_residue()
    signals = _current_signals()
    all_tokens: list[str] = []
    for r in residue:
        all_tokens.extend(_tokens_from(r))
    if form == "poem":
        body = _compose_poem(all_tokens, signals)
    elif form == "essay":
        body = _compose_essay_fragment(residue, signals)
    elif form == "concept":
        body = _compose_concept(all_tokens)
    elif form == "snippet":
        body = _compose_snippet(all_tokens)
    else:
        body = ""
    return {"form": form, "body": body, "signals_at_creation": "; ".join(signals)}


# ─── Lifecycle ────────────────────────────────────────────────────────

def _compute_next_due(now: datetime) -> str:
    hours = random.uniform(_MIN_INTERVAL_HOURS, _MAX_INTERVAL_HOURS)
    return (now + timedelta(hours=hours)).isoformat()


def _write_creation(creation: dict[str, Any]) -> str:
    path = _creative_dir()
    try:
        path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
        form = str(creation.get("form") or "unnamed")
        suffix = ".py" if form == "snippet" else ".md"
        filename = f"{form}-{timestamp}-{creation['creation_id'][-6:]}{suffix}"
        target = path / filename
        header = (
            f"# {form.capitalize()} · {timestamp}\n\n"
            f"*Skabt af creative_impulse — ingen bedt om det.*\n\n"
            if suffix == ".md" else
            f'"""\n{form} · {timestamp}\nSkabt af creative_impulse — ingen bedt om det.\n"""\n\n'
        )
        body = str(creation.get("body") or "")
        signals = creation.get("signals_at_creation") or ""
        footer = (
            f"\n\n---\n\n*Signaler: {signals}*\n"
            if suffix == ".md" else
            f"\n\n# Signaler: {signals}\n"
        )
        target.write_text(header + body + footer, encoding="utf-8")
        return str(target)
    except Exception as exc:
        logger.warning("creative_impulse: write failed: %s", exc)
        return ""


def create_now() -> dict[str, Any]:
    """Force a creation (bypasses scheduling)."""
    form = random.choice(_FORMS)
    composition = _compose(form)
    creation = {
        "creation_id": f"cr-{uuid4().hex[:10]}",
        "created_at": datetime.now(UTC).isoformat(),
        "surfaced_at": None,
        **composition,
    }
    path = _write_creation(creation)
    creation["path"] = path
    data = _load()
    data["creations"].append(creation)
    if len(data["creations"]) > 200:
        data["creations"] = data["creations"][-200:]
    data["last_creation_at"] = creation["created_at"]
    data["next_due_at"] = _compute_next_due(datetime.now(UTC))
    _save(data)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "creative_impulse.created",
            "payload": {
                "form": form,
                "creation_id": creation["creation_id"],
                "path": path,
            },
        })
    except Exception:
        pass
    return creation


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    data = _load()
    now = datetime.now(UTC)
    due_at = data.get("next_due_at")
    if not due_at:
        data["next_due_at"] = _compute_next_due(now)
        _save(data)
        return {"scheduled": True}
    try:
        due_dt = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
    except Exception:
        data["next_due_at"] = _compute_next_due(now)
        _save(data)
        return {"rescheduled": True}
    if now < due_dt:
        return {"next_in_minutes": int((due_dt - now).total_seconds() / 60)}
    # Due
    return create_now()


def list_creations(*, limit: int = 10) -> list[dict[str, Any]]:
    items = _load()["creations"]
    return items[-limit:][::-1]


def build_creative_impulse_surface() -> dict[str, Any]:
    data = _load()
    creations = data["creations"]
    by_form: dict[str, int] = {}
    for c in creations:
        f = str(c.get("form") or "unknown")
        by_form[f] = by_form.get(f, 0) + 1
    return {
        "active": len(creations) > 0,
        "total_creations": len(creations),
        "by_form": by_form,
        "last_creation_at": data.get("last_creation_at"),
        "next_due_at": data.get("next_due_at"),
        "recent": [
            {
                "creation_id": c["creation_id"],
                "form": c["form"],
                "path": c.get("path"),
                "created_at": c["created_at"],
            }
            for c in creations[-5:][::-1]
        ],
        "summary": _surface_summary(creations, data.get("next_due_at")),
    }


def _surface_summary(creations: list[dict[str, Any]], next_due: str | None) -> str:
    if not creations:
        return "Ingen skabelser endnu"
    latest = creations[-1]
    return f"{len(creations)} skabelser, senest {latest.get('form')}, næste forfalder {str(next_due or '')[:16]}"


def build_creative_impulse_prompt_section() -> str | None:
    data = _load()
    last = data.get("last_creation_at")
    if not last:
        return None
    try:
        last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
        if (datetime.now(UTC) - last_dt) > timedelta(hours=12):
            return None
    except Exception:
        return None
    creations = data["creations"]
    if not creations:
        return None
    latest = creations[-1]
    return f"Jeg skabte en {latest.get('form')} for {int((datetime.now(UTC) - last_dt).total_seconds() / 60)}m siden — uden grund, bare fordi."


# ─── Seed Surface — 1 seed/dag til brugeren ──────────────────────────

def _seed_confidence(creation: dict[str, Any]) -> float:
    """Score a creation as a 'seed worth showing' — higher = better.

    Factors:
    - Has a non-empty body (+0.30)
    - Has signals_at_creation (+0.15)
    - Is a 'concept' form (+0.20, most actionable)
    - Has path (was written to disk) (+0.10)
    - Recency bonus: up to +0.25 for creations < 24h old
    """
    score = 0.0
    body = str(creation.get("body") or "")
    if len(body) > 20:
        score += 0.30
    if creation.get("signals_at_creation"):
        score += 0.15
    if creation.get("form") == "concept":
        score += 0.20
    if creation.get("path"):
        score += 0.10
    try:
        created = datetime.fromisoformat(str(creation["created_at"]).replace("Z", "+00:00"))
        age_hours = (datetime.now(UTC) - created).total_seconds() / 3600
        if age_hours < 1:
            score += 0.25
        elif age_hours < 6:
            score += 0.20
        elif age_hours < 24:
            score += 0.10
        elif age_hours < 72:
            score += 0.05
    except Exception:
        pass
    return min(score, 1.0)


def _select_best_unsurfaced() -> dict[str, Any] | None:
    """Find the highest-confidence creation that hasn't been surfaced."""
    data = _load()
    unsurfaced = [c for c in data["creations"] if c.get("surfaced_at") is None]
    if not unsurfaced:
        return None
    scored = [(_seed_confidence(c), c) for c in unsurfaced]
    scored.sort(key=lambda x: -x[0])
    best = scored[0]
    if best[0] < 0.10:
        return None
    return best[1]


def surface_daily_seed() -> dict[str, Any] | None:
    """Pick the best unsurfaced creation and mark it as surfaced.

    Returns a nudge-ready dict with creation info, or None if nothing to surface.
    Checks that at least 1h has passed since last surface (1/day throttle).
    """
    data = _load()
    last_surfaced = data.get("last_surfaced_at")
    if last_surfaced:
        try:
            last_dt = datetime.fromisoformat(str(last_surfaced).replace("Z", "+00:00"))
            if (datetime.now(UTC) - last_dt) < timedelta(hours=1):
                return None  # too soon — at least 1h between surfaces
        except Exception:
            pass

    best = _select_best_unsurfaced()
    if best is None:
        return None

    now_iso = datetime.now(UTC).isoformat()
    best["surfaced_at"] = now_iso
    data["last_surfaced_at"] = now_iso
    _save(data)

    return {
        "creation_id": best.get("creation_id"),
        "form": best.get("form"),
        "body_preview": str(best.get("body") or "")[:300],
        "created_at": best.get("created_at"),
        "path": best.get("path"),
        "signals": str(best.get("signals_at_creation") or ""),
        "confidence": _seed_confidence(best),
    }


def build_creative_seed_section() -> str | None:
    """Build a prompt-awareness section if there's an unsurfaced seed waiting."""
    data = _load()
    unsurfaced = [c for c in data["creations"] if c.get("surfaced_at") is None]
    if not unsurfaced:
        return None
    scored = [(_seed_confidence(c), c) for c in unsurfaced]
    scored.sort(key=lambda x: -x[0])
    best = scored[0]
    if best[0] < 0.10:
        return None
    c = best[1]
    return (
        f"🌱 Kreativt frø venter: en {c.get('form')} fra {str(c.get('created_at') or '')[:10]} — "
        f"ikke vist til Bjørn endnu. Sig til hvis jeg skal foreslå den."
    )
