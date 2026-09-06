"""Lightweight prompt-section answer-impact telemetry."""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import asdict, dataclass

_TOKEN_RE = re.compile(r"[A-Za-zÆØÅæøå0-9_]{4,}")
_STOP = frozenset({
    "this", "that", "with", "from", "have", "your", "what", "when", "where",
    "skal", "ikke", "eller", "hvad", "hvor", "vores", "mine", "dette", "denne",
})
_LAST_SECTIONS: dict[str, tuple[float, list[tuple[str, str]]]] = {}
_TTL_S = 900.0


@dataclass(frozen=True, slots=True)
class SectionImpact:
    label: str
    chars: int
    fingerprint: str
    overlap_terms: int
    impact_score: float


def _terms(text: str) -> set[str]:
    return {
        t.lower()
        for t in _TOKEN_RE.findall(str(text or ""))
        if t.lower() not in _STOP
    }


def estimate_section_impact(label: str, section_text: str, answer_text: str) -> SectionImpact:
    section_terms = _terms(section_text)
    answer_terms = _terms(answer_text)
    overlap = len(section_terms & answer_terms)
    denom = max(1, min(len(section_terms), 20))
    digest = hashlib.sha1(str(section_text or "").encode("utf-8")).hexdigest()[:12]
    return SectionImpact(
        label=str(label or ""),
        chars=len(str(section_text or "")),
        fingerprint=digest,
        overlap_terms=overlap,
        impact_score=round(min(1.0, overlap / denom), 3),
    )


def observe_answer_impact(
    *,
    run_id: str,
    answer_text: str,
    sections: list[tuple[str, str]],
) -> list[dict[str, object]]:
    impacts = [
        asdict(estimate_section_impact(label, text, answer_text))
        for label, text in sections
        if str(text or "").strip()
    ]
    if not impacts:
        return []
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("prompt.section_answer_impact", {
            "run_id": str(run_id or ""),
            "answer_chars": len(str(answer_text or "")),
            "sections": impacts[:80],
        })
    except Exception:
        pass
    return impacts


def remember_prompt_sections(*, session_id: str, sections: list[tuple[str, str]]) -> None:
    sid = str(session_id or "").strip()
    if not sid:
        return
    now = time.time()
    _LAST_SECTIONS[sid] = (now, list(sections)[:120])
    for key, (ts, _items) in list(_LAST_SECTIONS.items()):
        if now - ts > _TTL_S:
            _LAST_SECTIONS.pop(key, None)


def observe_last_prompt_answer_impact(
    *,
    session_id: str,
    run_id: str,
    answer_text: str,
) -> list[dict[str, object]]:
    sid = str(session_id or "").strip()
    if not sid:
        return []
    item = _LAST_SECTIONS.get(sid)
    if not item:
        return []
    ts, sections = item
    if time.time() - ts > _TTL_S:
        _LAST_SECTIONS.pop(sid, None)
        return []
    return observe_answer_impact(
        run_id=run_id,
        answer_text=answer_text,
        sections=sections,
    )
