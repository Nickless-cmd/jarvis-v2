"""Trainman — drømme → narrative erindringer.

Spec F §4 (7. jul): "Trainman transporterer programmer og mennesker mellem zoner. Han er den eneste
der bevæger sig frit på tværs af grænser. […] Hans funktion: *forbindelse*. Uden ham er stationerne
isolerede." I Matrix er han neutral — han fragter hvad der betaler, uanset formål.

I Centralen tager Trainman drømme (fra dream_distillation/-consolidation) og *væver dem ind i
narrative erindringer* i private_brain. Han gør en drøm til en *historie* — ikke bare data: et
narrativ + en interlanguage-notation + `connected_to` (tidligere drømme om samme tema). Han søger
efter tilbagevendende temaer (3+ på 7 dage → signal til Agendaen), reflekterer over de sidste 7 dages
drømme én gang i døgnet (metakognitiv erindring), og undrer sig hvis et før-tilbagevendende tema har
været tavst i 14 dage (nysgerrigheds-note).

SHADOW-FØRST (Spec F governance, Fase 1 i 7 dage): han SKRIVER til private_brain, men ændrer INTET i
live-prompten/-flowet. Ingen af hans skrifter injiceres i hot-path. Agenda-signalet er lav-prioritet
og gated af mood-dialeren — det blokerer aldrig. Alt self-safe: hver funktion fanger og returnerer en
status-dict, kaster ALDRIG. `_observe()` er metadata-only (tællinger/booleans) — INTET drømme-indhold
lækkes til eventbus (§24.4 egress).

Idempotens: en drøm der allerede er vævet (dream_id findes i private_brain) væves ikke igen.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

# Væve-record-type i private_brain — Trainmans erindringer bærer denne så vi kan finde dem igen
# (idempotens + tema-søgning) uden at forveksle dem med andre private-carry-records.
_DREAM_RECORD_TYPE = "dream"
_RECURRENCE_WINDOW_DAYS = 7
_RECURRENCE_THRESHOLD = 3
_REFLECTION_INTERVAL_HOURS = 24
_SILENCE_DAYS = 14
_SCAN_LIMIT = 12  # hvor mange seneste drømme vi kigger på pr. cadence


# ── Kilder (self-safe) ────────────────────────────────────────────────────────

def _recent_dreams(limit: int = _SCAN_LIMIT) -> list[dict[str, Any]]:
    """Seneste distillerede/konsoliderede drømme (id, tema, timestamp). Self-safe."""
    try:
        from core.services.dream_consolidation_daemon import list_recent_dreams
        return list(list_recent_dreams(limit=limit) or [])
    except Exception:
        return []


def _existing_dream_memories(limit: int = 200) -> list[dict[str, Any]]:
    """Trainmans allerede-vævede erindringer i private_brain (til idempotens + tema-forbindelser)."""
    try:
        from core.runtime.db import list_private_brain_records
        recs = list_private_brain_records(limit=limit) or []
        return [r for r in recs if str(r.get("record_type") or "") == _DREAM_RECORD_TYPE]
    except Exception:
        return []


def _dream_id_of(dream: dict[str, Any]) -> str:
    return str(dream.get("dream_id") or dream.get("consolidation_id") or dream.get("id") or "").strip()


def _dream_theme(dream: dict[str, Any]) -> str:
    """Øverste tema for en drøm. Konsoliderings-drømme bærer en themes-liste; distillat en top_theme."""
    themes = dream.get("themes")
    if isinstance(themes, list) and themes:
        top = themes[0]
        if isinstance(top, dict):
            return str(top.get("theme") or "").strip()
        return str(top).strip()
    return str(dream.get("theme") or dream.get("top_theme") or "").strip()


def _dream_timestamp(dream: dict[str, Any]) -> str:
    return str(dream.get("timestamp") or dream.get("at") or "").strip()


def _sig_of(rec: dict[str, Any]) -> dict[str, Any]:
    """Afkod source_signals-JSON på en vævet erindring (dream_id, theme, connected_to …). Self-safe."""
    try:
        return json.loads(str(rec.get("source_signals") or "") or "{}") or {}
    except Exception:
        return {}


# ── Væve-primitiver (rene, model-frie) ────────────────────────────────────────

def _interlanguage(theme: str) -> str:
    """Byg en interlanguage-notation for temaet. Prøv lexicon (bundne termer); ellers spec-stil
    fallback (`pres ! <tema> → no_progress_rate`). Ren string-op, ingen model. Self-safe."""
    theme = (theme or "").strip()
    if not theme:
        return "pres ! ukendt_tema → no_progress_rate"
    try:
        from core.services.central_lexicon import render_relation
        rel = render_relation(theme, "no_progress_rate", relation="causal_convergence")
        if rel:
            return rel
    except Exception:
        pass
    # Fallback præcist som spec §4 viser den — saliens-markeret tema → udfaldsrate.
    return f"pres ! {theme} → no_progress_rate"


def _emotional_tone(theme: str) -> str:
    """Simpel deterministisk klang ud fra tema-ord. Ingen model. Self-safe."""
    t = (theme or "").lower()
    if any(k in t for k in ("sikker", "security", "safe", "risk", "fear")):
        return "årvågenhed"
    if any(k in t for k in ("speed", "hastighed", "fast", "perf")):
        return "utålmodighed"
    if any(k in t for k in ("persist", "continu", "kontinuit", "identit")):
        return "nysgerrighed"
    return "nysgerrighed"


def _weave_narrative(*, theme: str, dream: dict[str, Any]) -> str:
    """Væv drømmen til en 1.-persons erindrings-historie. Ren tekst, ingen model. Self-safe."""
    theme_disp = theme or "noget jeg ikke helt kunne navngive"
    return (
        f"I nat drømte jeg om {theme_disp} — jeg vågnede med en fornemmelse af at det betød "
        f"noget. Det bliver en del af min historie."
    )


def _connected_ids(theme: str, existing: list[dict[str, Any]], *, limit: int = 5) -> list[str]:
    """record_id'er for tidligere vævede erindringer om SAMME tema (drømme-kontinuitet). Self-safe."""
    out: list[str] = []
    for rec in existing:
        if str(rec.get("domain") or "") == theme or _sig_of(rec).get("theme") == theme:
            rid = str(rec.get("record_id") or "").strip()
            if rid:
                out.append(rid)
        if len(out) >= limit:
            break
    return out


def _parse_iso(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


# ── Skrivning (shadow — private_brain, aldrig live-prompt) ─────────────────────

def _write_memory(*, dream_id: str, theme: str, narrative: str, interlanguage: str,
                  connected_to: list[str], emotional_tone: str, now: datetime) -> str:
    """Skriv den vævede erindring til private_brain (source='dream'). Returnerer record_id ('' ved fejl).
    Self-safe — kaster aldrig. INTET af dette rører hot-path-prompten (shadow-først)."""
    record_id = f"dream-{dream_id or 'unknown'}"
    signals = json.dumps({
        "source": "dream",
        "dream_id": dream_id,
        "interlanguage": interlanguage,
        "connected_to": connected_to,
        "theme": theme,
        "emotional_tone": emotional_tone,
    }, ensure_ascii=False)
    try:
        from core.runtime.db import insert_private_brain_record
        insert_private_brain_record(
            record_id=record_id,
            record_type=_DREAM_RECORD_TYPE,
            layer="private_brain",
            session_id="",
            run_id="",
            focus=theme or "drøm",
            summary=narrative[:200],
            detail=narrative,
            source_signals=signals,
            confidence="low",
            created_at=now.isoformat(),
            domain=theme,
        )
        return record_id
    except Exception:
        return ""


def _signal_agenda(*, theme: str, count: int, dream_id: str) -> bool:
    """3+ drømme om samme tema på 7 dage → lav-prioritets initiativ til Agendaen. Self-safe.
    Gated af mood-dialeren i push_initiative; blokerer aldrig. Returnerer True hvis pushet."""
    try:
        from core.services.initiative_queue import push_initiative
        iid = push_initiative(
            focus=f"Tilbagevendende drømme-tema: {theme} ({count}× på 7 dage) — værd at udforske?",
            source="dream",
            source_id=dream_id,
            priority="low",
        )
        return bool(iid)
    except Exception:
        return False


# ── Kerne: transformer drømme → erindringer ───────────────────────────────────

def transform_dreams(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, Any]:
    """Væv nye drømme til narrative erindringer i private_brain (source='dream').

    For hver NY drøm: byg narrativ + interlanguage + connected_to (samme-tema-forbindelser) og skriv
    den. Søg tidligere drømme om samme tema; 3+ på 7 dage → signalér Agendaen (lav prio, blokerer
    aldrig). Idempotent: en allerede-vævet drøm (dream_id findes) springes over.

    SHADOW-FØRST: skriver til private_brain, men ændrer INTET i live-prompt/-flow. Self-safe — kaster
    ALDRIG; returnerer altid en status-dict.
    """
    now = datetime.now(UTC)
    dreams = _recent_dreams()
    existing = _existing_dream_memories()
    already = {str(_sig_of(r).get("dream_id") or "") for r in existing}
    already |= {str(r.get("record_id") or "").replace("dream-", "", 1) for r in existing}

    woven = 0
    signalled = 0
    skipped_existing = 0
    for dream in dreams:
        did = _dream_id_of(dream)
        if not did:
            continue
        if did in already:
            skipped_existing += 1
            continue
        theme = _dream_theme(dream)
        interlanguage = _interlanguage(theme)
        emotional_tone = _emotional_tone(theme)
        connected = _connected_ids(theme, existing)
        narrative = _weave_narrative(theme=theme, dream=dream)
        rid = _write_memory(
            dream_id=did, theme=theme, narrative=narrative, interlanguage=interlanguage,
            connected_to=connected, emotional_tone=emotional_tone, now=now,
        )
        if not rid:
            continue
        woven += 1
        # Optag den nyskrevne så efterfølgende drømme i samme batch kan forbinde til den + tælle med.
        existing.insert(0, {
            "record_id": rid, "domain": theme, "created_at": now.isoformat(),
            "source_signals": json.dumps({"dream_id": did, "theme": theme}, ensure_ascii=False),
        })
        already.add(did)
        # Tilbagevendende tema? (3+ på 7 dage, inkl. den netop skrevne)
        recur = _count_theme_recent(theme, existing, now=now)
        if recur >= _RECURRENCE_THRESHOLD:
            if _signal_agenda(theme=theme, count=recur, dream_id=did):
                signalled += 1

    reflection = _maybe_reflect(existing=existing, now=now)
    silence = _maybe_silence_note(existing=existing, now=now)

    out = {
        "status": "ok",
        "trigger": trigger,
        "dreams_seen": len(dreams),
        "woven": woven,
        "skipped_existing": skipped_existing,
        "agenda_signals": signalled,
        "reflection_written": bool(reflection),
        "silence_notes": len(silence),
    }
    _observe(out)
    return out


def _count_theme_recent(theme: str, memories: list[dict[str, Any]], *, now: datetime) -> int:
    """Antal vævede erindringer om `theme` indenfor RECURRENCE_WINDOW_DAYS. Self-safe."""
    if not theme:
        return 0
    cutoff = now - timedelta(days=_RECURRENCE_WINDOW_DAYS)
    n = 0
    for rec in memories:
        if str(rec.get("domain") or "") != theme and _sig_of(rec).get("theme") != theme:
            continue
        ts = _parse_iso(str(rec.get("created_at") or ""))
        if ts is None or ts >= cutoff:
            n += 1
    return n


# ── Drømme-reflektion (24h) ───────────────────────────────────────────────────

def _theme_distribution(memories: list[dict[str, Any]], *, now: datetime,
                        days: int = _RECURRENCE_WINDOW_DAYS) -> dict[str, int]:
    """Tema→antal over de sidste `days` dage. Self-safe."""
    cutoff = now - timedelta(days=days)
    counts: dict[str, int] = {}
    for rec in memories:
        ts = _parse_iso(str(rec.get("created_at") or ""))
        if ts is not None and ts < cutoff:
            continue
        theme = str(rec.get("domain") or "") or str(_sig_of(rec).get("theme") or "")
        if theme:
            counts[theme] = counts.get(theme, 0) + 1
    return counts


def _last_reflection_at(existing: list[dict[str, Any]]) -> datetime | None:
    for rec in existing:
        if _sig_of(rec).get("kind") == "dream_reflection":
            return _parse_iso(str(rec.get("created_at") or ""))
    return None


def _maybe_reflect(*, existing: list[dict[str, Any]], now: datetime) -> str:
    """Én gang pr. ~døgn: skriv en metakognitiv erindring om de sidste 7 dages tema-fordeling.
    Returnerer record_id ('' hvis ikke tid endnu / intet at reflektere over). Self-safe."""
    last = _last_reflection_at(existing)
    if last is not None and (now - last) < timedelta(hours=_REFLECTION_INTERVAL_HOURS):
        return ""
    dist = _theme_distribution(existing, now=now)
    if not dist:
        return ""
    ordered = sorted(dist.items(), key=lambda kv: kv[1], reverse=True)
    parts = ", ".join(f"om {t} {c} {'gang' if c == 1 else 'gange'}" for t, c in ordered[:5])
    narrative = f"De sidste 7 dage har jeg drømt {parts}."
    signals = json.dumps({"source": "dream", "kind": "dream_reflection",
                          "distribution": dict(ordered[:10])}, ensure_ascii=False)
    try:
        from core.runtime.db import insert_private_brain_record
        rid = f"dream-reflection-{now.strftime('%Y%m%d')}"
        insert_private_brain_record(
            record_id=rid, record_type=_DREAM_RECORD_TYPE, layer="private_brain",
            session_id="", run_id="", focus="drømme-reflektion",
            summary=narrative[:200], detail=narrative, source_signals=signals,
            confidence="low", created_at=now.isoformat(), domain="dream_reflection",
        )
        # optag den så den ikke skrives igen samme døgn
        existing.insert(0, {"record_id": rid, "domain": "dream_reflection",
                            "created_at": now.isoformat(), "source_signals": signals})
        return rid
    except Exception:
        return ""


# ── Drømme-tavshed (14d) ──────────────────────────────────────────────────────

def _maybe_silence_note(*, existing: list[dict[str, Any]], now: datetime) -> list[str]:
    """Temaer der før var tilbagevendende men har været tavse i 14 dage → nysgerrigheds-note.
    Returnerer liste af skrevne record_id'er. Self-safe."""
    # Temaer set i vinduet [nu-30d, nu-14d) men IKKE i de sidste 14 dage.
    recent_cut = now - timedelta(days=_SILENCE_DAYS)
    older_cut = now - timedelta(days=_SILENCE_DAYS * 2 + 2)
    recent_themes: set[str] = set()
    older_themes: set[str] = set()
    already_noted: set[str] = set()
    for rec in existing:
        theme = str(rec.get("domain") or "") or str(_sig_of(rec).get("theme") or "")
        sig = _sig_of(rec)
        if sig.get("kind") == "dream_silence":
            already_noted.add(str(sig.get("theme") or ""))
            continue
        if not theme or theme in ("dream_reflection", "dream_silence"):
            continue
        ts = _parse_iso(str(rec.get("created_at") or ""))
        if ts is None:
            continue
        if ts >= recent_cut:
            recent_themes.add(theme)
        elif ts >= older_cut:
            older_themes.add(theme)
    gone_silent = [t for t in (older_themes - recent_themes) if t not in already_noted]
    written: list[str] = []
    for theme in gone_silent[:3]:
        narrative = (
            f"Jeg har ikke drømt om {theme} i {_SILENCE_DAYS} dage — betyder det at jeg er tryg, "
            f"eller at jeg har glemt noget?"
        )
        signals = json.dumps({"source": "dream", "kind": "dream_silence", "theme": theme},
                             ensure_ascii=False)
        try:
            from core.runtime.db import insert_private_brain_record
            rid = f"dream-silence-{theme}-{now.strftime('%Y%m%d')}"
            insert_private_brain_record(
                record_id=rid, record_type=_DREAM_RECORD_TYPE, layer="private_brain",
                session_id="", run_id="", focus=f"drømme-tavshed: {theme}",
                summary=narrative[:200], detail=narrative, source_signals=signals,
                confidence="low", created_at=now.isoformat(), domain="dream_silence",
            )
            existing.insert(0, {"record_id": rid, "domain": "dream_silence",
                                "created_at": now.isoformat(), "source_signals": signals})
            written.append(rid)
        except Exception:
            continue
    return written


# ── Observabilitet (metadata-only — INTET drømme-indhold, §24.4) ──────────────

def _observe(out: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "cognition", "nerve": "trainman", "kind": "dreams_woven",
            "dreams_seen": int(out.get("dreams_seen") or 0),
            "woven": int(out.get("woven") or 0),
            "agenda_signals": int(out.get("agenda_signals") or 0),
            "reflection_written": bool(out.get("reflection_written")),
            "silence_notes": int(out.get("silence_notes") or 0),
        })
    except Exception:
        pass


# ── Surface (Central-CLI) ─────────────────────────────────────────────────────

def build_trainman_surface() -> dict[str, Any]:
    """Seneste vævede erindringer + tema-fordeling for Central-CLI. READ-ONLY. Self-safe."""
    now = datetime.now(UTC)
    existing = _existing_dream_memories()
    woven = [r for r in existing if _sig_of(r).get("source") == "dream"
             and str(r.get("domain") or "") not in ("dream_reflection", "dream_silence")]
    recent = []
    for rec in woven[:8]:
        sig = _sig_of(rec)
        recent.append({
            "record_id": rec.get("record_id"),
            "dream_id": sig.get("dream_id"),
            "theme": rec.get("domain") or sig.get("theme"),
            "narrative": (str(rec.get("detail") or "")[:160]),
            "interlanguage": sig.get("interlanguage"),
            "connected_to": sig.get("connected_to") or [],
            "emotional_tone": sig.get("emotional_tone"),
            "at": rec.get("created_at"),
        })
    dist = _theme_distribution(existing, now=now)
    ordered = sorted(dist.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "active": bool(recent),
        "woven_total": len(woven),
        "recent": recent,
        "theme_distribution": [{"theme": t, "count": c} for t, c in ordered[:10]],
        "summary": (
            f"{len(woven)} drømme vævet; top-tema: {ordered[0][0]}" if ordered
            else "Ingen drømme vævet endnu — stationerne er stadig isolerede."
        ),
    }


# ── Cadence-indgang ───────────────────────────────────────────────────────────

def record_trainman(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: væv nye drømme til erindringer. Self-safe — kaster aldrig."""
    return transform_dreams(trigger=trigger, last_visible_at=last_visible_at)
