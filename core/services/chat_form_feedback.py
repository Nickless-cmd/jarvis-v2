"""Feedback i stedet for feedforward: mål FORRIGE svars form, vis ét tal.

Bjørn 16/11-2026: «det handler om præsentation i chat mode». Formreglerne i
``visible_chat_pragmatics`` er feedforward — de står i prompten før svaret
skrives, og round_budget_notice (samme slags) målte nul effekt. Hver gang
Bjørn sagde «du gør det igen» blev svaret rettet i samme tur, fordi
korrektionen ramte et svar der allerede var skrevet. Her får modellen samme
spejl uden at Bjørn skal holde det: én målt linje om det forrige svar.

## Cache

Linjen lægges i den dynamiske hale (``build_chat_mode_dynamic_tail``), efter
cache-grænsen og lige før den aktuelle user-tur. Det forrige svar er
uforanderligt når turen bygges, så linjen er byte-identisk for alle runder
INDEN FOR samme tur; den skifter kun mellem ture, hvor halen alligevel er ny
(brugerprofil, tonesignaler). Den rører aldrig det stabile systempræfiks.
"""
from __future__ import annotations

import re

_FENCE_RE = re.compile(r"^(```|~~~)")
_LIST_RE = re.compile(r"^\s{0,3}(?:[-*+]|\d{1,3}[.)])\s+\S")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_WORD_RE = re.compile(r"\S+")


def measure_answer_form(text: str) -> dict[str, int]:
    """Tæl form: ord, prosa-afsnit, native flader (tabel/liste/kode/jarvis-ui)."""
    lines = str(text or "").replace("\r\n", "\n").split("\n")
    words = len(_WORD_RE.findall("\n".join(lines)))
    tables = lists = code = ui = prose = 0
    in_fence = False
    fence_is_ui = False
    prev_kind = "blank"   # blank | prose | list | table | fence
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if in_fence:
            if _FENCE_RE.match(stripped):
                in_fence = False
                prev_kind = "fence"
            i += 1
            continue
        if _FENCE_RE.match(stripped):
            in_fence = True
            info = stripped.lstrip("`~").strip().lower()
            fence_is_ui = info.startswith("jarvis-ui")
            if fence_is_ui:
                ui += 1
            else:
                code += 1
            i += 1
            continue
        if not stripped:
            prev_kind = "blank"
        elif "|" in line and i + 1 < len(lines) and _TABLE_SEP_RE.match(lines[i + 1]):
            tables += 1
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                i += 1
            prev_kind = "table"
            continue
        elif _LIST_RE.match(line):
            if prev_kind != "list":
                lists += 1
            prev_kind = "list"
        elif _HEADING_RE.match(line):
            prev_kind = "blank"   # overskrift er hverken afsnit eller flade
        else:
            if prev_kind not in ("prose",):
                prose += 1
            prev_kind = "prose"
        i += 1
    return {
        "words": words,
        "paragraphs": prose,
        "tables": tables,
        "lists": lists,
        "code": code,
        "ui": ui,
        "surfaces": tables + lists + code + ui,
    }


def form_line(measure: dict[str, int]) -> str:
    """Ét konkret tal-udsagn. Ingen formaning."""
    p, s, w = measure["paragraphs"], measure["surfaces"], measure["words"]
    p_txt = f"{p} afsnit" + (" uden flade" if s == 0 else "")
    s_txt = f"{s} flade{'r' if s != 1 else ''}"
    return f"Sidste svar: {p_txt}, {s_txt}, {w} ord"


def previous_answer_form_line(session_id: str | None) -> str | None:
    """Målelinjen for sessionens seneste assistent-svar — eller None."""
    sid = str(session_id or "").strip()
    if not sid:
        return None
    try:
        from core.services.chat_sessions import recent_chat_session_messages
    except Exception:  # bevidst tavs: maale-linjen er kosmetisk, ikke en beslutning
        return None
    try:
        rows = recent_chat_session_messages(sid, limit=6)
    except Exception:  # bevidst tavs: kan sessions-laget ikke laeses, udelades linjen
        return None
    for row in reversed(rows):
        if row.get("role") == "assistant":
            content = str(row.get("content") or "").strip()
            if not content:
                return None
            return form_line(measure_answer_form(content))
    return None
