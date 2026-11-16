"""Ét værktøjs-scope pr. SESSION — ikke ét pr. tur.

Målt 16/11-2026 på Bjørns egen session: værktøjssættet skiftede 38 ↔ 44 ↔ 110
mellem to ture i samme samtale. Årsagen var ikke en tabt ContextVar (den vej
er dækket af `copy_context` i begge pumper, og hvert run er målt internt
stabilt i alle 9–11 runder). Årsagen var at scopet blev udledt PER TUR — af
klientens `mode` og af hvilken rute beskeden kom ind ad: `chat.py` sender
``""`` (ubegrænset) for ejeren, `chat_stream_v2` udleder ``chat``/``code``.

Hvert skift invaliderer hele præfikset. Målt i `cache_telemetry.jsonl`:
cache-hit var **58,7 %** på runden efter et skift mod **96,6 %** ellers — og
skiftet 38 → 110 gav **18 %**.

Reglen her: et EKSPLICIT scope vinder og gemmes; et TOMT arver det gemte. En
samtale der begyndte i chat bliver altså ikke ubegrænset, fordi næste besked
kom ind ad en anden rute, og en code-samtale falder ikke tilbage til det brede
katalog midt i arbejdet. Skifter han selv mode i klienten, vinder det og
bliver den nye faste værdi.

Kill-switch: `settings.session_tool_scope_sticky = False` → scopet udledes
igen pr. tur, og intet gemmes (adfærden før 16/11-2026).

Self-safe: enhver fejl returnerer det kaldte scope uændret. En manglende
state-række må aldrig koste en tur dens værktøjer.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_KEY_PREFIX = "session_tool_scope:"


def sticky_enabled() -> bool:
    """Er scopet fast pr. session? Fail-safe: enhver fejl → til."""
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "session_tool_scope_sticky", True))
    except Exception:  # kan indstillingen ikke læses, vælges den STABILE adfærd — ikke den flakkende
        return True


def _key(session_id: str) -> str:
    return f"{_KEY_PREFIX}{str(session_id or '').strip()}"


def _read(session_id: str) -> str | None:
    """Det gemte scope, eller ``None`` når sessionen ikke har en post.

    ``""`` er en GYLDIG gemt værdi (ubegrænset) og må ikke forveksles med
    «ingen post» — ellers ville en samtale der bevidst kører ubegrænset få sit
    scope opfundet på ny hver tur.
    """
    try:
        from core.runtime.db import get_runtime_state_value
        raw = get_runtime_state_value(_key(session_id), None)
        if isinstance(raw, dict) and "scope" in raw:
            return str(raw.get("scope") or "").strip().lower()
        return None
    except Exception as exc:  # en læsefejl må ikke OPFINDE et scope: tom post = intet gemt
        logger.warning("session_tool_scope: kunne ikke læse for %s: %s", session_id, exc)
        return None


def _write(session_id: str, scope: str) -> None:
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_key(session_id), {"scope": scope})
    except Exception as exc:  # en skrivefejl må ikke koste turen dens værktøjer
        logger.warning("session_tool_scope: kunne ikke gemme for %s: %s", session_id, exc)


def resolve_scope(session_id: str, requested: str) -> str:
    """Det scope turen skal køre med — og den værdi sessionen husker.

    ``requested`` er det scope ruten selv udledte (klientens mode + samtalens
    art). Er det tomt, arves det gemte; er der intet gemt, er svaret tomt
    (ubegrænset), præcis som før.
    """
    sid = str(session_id or "").strip()
    req = str(requested or "").strip().lower()
    if not sid or not sticky_enabled():
        return req
    if req:
        _write(sid, req)
        return req
    stored = _read(sid)
    if stored is None:
        return ""
    if stored != req:
        logger.info(
            "session_tool_scope: %s arver scope=%r (ruten udledte tomt) — "
            "værktøjssættet holdes stabilt gennem turen", sid, stored,
        )
    return stored


def clear(session_id: str) -> None:
    """Glem sessionens scope (tests og eksplicit nulstilling)."""
    sid = str(session_id or "").strip()
    if not sid:
        return
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_key(sid), {})
    except Exception as exc:  # kun tests og eksplicit nulstilling rammer her
        logger.warning("session_tool_scope: kunne ikke rydde %s: %s", sid, exc)
