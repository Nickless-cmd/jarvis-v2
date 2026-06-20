"""@mention-parsing for team-sessioner (Teams-feature, spec 2026-06-20 §5.2-5.3).

Ren logik: find @navn i en beskedtekst, klassificér @jarvis (→ trigger Jarvis) vs
@medlem (→ notificér personen). Wires ind i den synlige run-trigger + proactive_
router i Fase 2c/3. Holdt som en lille, testbar enhed uden side-effekter.
"""
from __future__ import annotations

import re

from core.services.teams import JARVIS_USER_ID

# @navn: bogstaver/tal/_/-/. (dækker user-id'er + 'jarvis'). Word-boundary foran @.
_MENTION_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9_.\-]+)")


def extract_mentions(text: str) -> list[str]:
    """Rå @-tokens i teksten (lowercased, dedupe, rækkefølge bevaret)."""
    out: list[str] = []
    for m in _MENTION_RE.findall(text or ""):
        tok = m.lower()
        if tok not in out:
            out.append(tok)
    return out


def parse_mentions(text: str, member_ids: list[str]) -> dict:
    """Klassificér mentions mod et teams medlemskab.

    Returnerer {"jarvis": bool, "members": [user_id]}. @jarvis → jarvis=True.
    @<medlem> → med i members (kun hvis det matcher et faktisk medlem; ukendte
    @navne ignoreres). Case-insensitivt match mod member_ids.
    """
    toks = extract_mentions(text)
    members_lc = {m.lower(): m for m in (member_ids or [])}
    jarvis = JARVIS_USER_ID.lower() in toks
    hit: list[str] = []
    for t in toks:
        if t == JARVIS_USER_ID.lower():
            continue
        real = members_lc.get(t)
        if real and real not in hit:
            hit.append(real)
    return {"jarvis": jarvis, "members": hit}


def should_jarvis_respond(text: str, *, is_reply_to_jarvis: bool = False) -> bool:
    """v1 (summoned baseline, spec §5.2): Jarvis svarer i en team-session KUN når
    han kaldes — @jarvis nævnt ELLER beskeden er et svar på Jarvis. v2 (interjection-
    motor) skifter denne funktions indmad ud med en billig-model-dommer."""
    if is_reply_to_jarvis:
        return True
    return JARVIS_USER_ID.lower() in extract_mentions(text)
