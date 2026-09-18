"""Artefakter: de filer Jarvis har skrevet og rettet i en mappe, paa tvaers af samtaler.

Bjoern 18/9-2026: venstre panel i code mode manglede en artefakt-menu, «det skal
bygges fra bunden». Paa tvaers af samtaler: i code mode er det MAPPEN der er
arbejdet, ikke den enkelte traad.

## Hvorfor ikke dispatch-tabellen

Det eksisterende «artefakt»-begreb (mobilens ArtifactsScreen, `/api/dispatches`)
staar paa `claude_dispatch_audit`. Maalt paa CT105 18/9: den tabel har NUL
raekker, nogensinde — den fyldes kun naar Jarvis bruger `dispatch_to_claude_code`,
og det goer han ikke. En menu bygget paa den ville vaere tom for altid.

Det han faktisk laver, ligger i hvert svars `content_json`. Maalt samme aften:
905 fil-kald (624 `edit_file`, 272 `write_file`, 17 via broen), nøglen hedder
ALTID `path`, stierne er absolutte, og 540 af dem ligger under
`/media/projects/jarvis-v2`.

## Ingen `limit` paa scanningen

Et vindue over de seneste N beskeder ville skjule halen — den faelde har huset
gaaet i fire gange. I stedet filtrerer SQL'en paa mappens sti i `content_json`,
og ALLE matchende beskeder laeses. Svaret siger hvor mange der blev scannet, saa
et tal der ser lavt ud kan kontrolleres.

## Linjetal

Tælles som serverens `file_tools_exec.linjetal` og desks `diffStat`: hele
blokke, ikke minimal diff. Samme handling skal vise samme tal overalt.
"""
from __future__ import annotations

import json
from typing import Any

_FIL_VAERKTOEJER = ("edit_file", "write_file", "multi_edit")


def _linjer(s: str) -> int:
    if not s:
        return 0
    return s.count("\n") + (0 if s.endswith("\n") else 1)


def _diff(navn: str, inp: dict[str, Any]) -> tuple[int, int]:
    """(tilfoejet, fjernet) ud af kaldets argumenter — samme regel som desk."""
    if navn == "edit_file":
        return (_linjer(str(inp.get("new_text") or inp.get("new_string") or "")),
                _linjer(str(inp.get("old_text") or inp.get("old_string") or "")))
    if navn == "multi_edit":
        plus = minus = 0
        for e in inp.get("edits") or inp.get("items") or []:
            if isinstance(e, dict):
                plus += _linjer(str(e.get("new_text") or e.get("new_string") or ""))
                minus += _linjer(str(e.get("old_text") or e.get("old_string") or ""))
        return (plus, minus)
    if navn == "write_file":
        # KUN tilfoejet. Argumenterne siger ikke hvad der stod i filen foer.
        return (_linjer(str(inp.get("content") or inp.get("file_text") or "")), 0)
    return (0, 0)


def _rod(root: str) -> str:
    """Navngivne server-roedder → sti. Alt andet bruges som det er."""
    r = (root or "").strip()
    try:
        if r == "repo":
            from core.runtime.config import PROJECT_ROOT
            return str(PROJECT_ROOT)
        if r == "jarvis-v2":
            from core.runtime.config import JARVIS_HOME
            return str(JARVIS_HOME)
    except Exception:
        return ""
    return r


def _under(sti: str, rod: str) -> bool:
    return sti == rod or sti.startswith(rod + "/")


def list_artifacts(root: str, *, limit: int = 200) -> dict[str, Any]:
    """Filer Jarvis har rørt under `root`, nyeste først, én raekke pr. fil."""
    rod = _rod(root).rstrip("/")
    # En tom eller alt for kort rod ville matche alt, og saa er listen ikke
    # længere «den her mappe». Hellere tomt end forkert.
    if len(rod) < 2 or not rod.startswith("/"):
        return {"ok": False, "root": rod, "error": "ingen gyldig mappe", "artifacts": [], "scanned": 0}

    from core.runtime.db import connect

    pr_fil: dict[str, dict[str, Any]] = {}
    scannet = 0
    with connect() as conn:
        rows = conn.execute(
            "SELECT session_id, created_at, content_json FROM chat_messages"
            " WHERE role = 'assistant' AND content_json LIKE ?"
            " ORDER BY id DESC",
            ("%" + rod + "%",),
        ).fetchall()
        for session_id, created_at, cj in rows:
            scannet += 1
            try:
                blokke = json.loads(cj or "[]")
            except Exception:
                continue
            if not isinstance(blokke, list):
                continue
            for b in blokke:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                navn = str(b.get("name") or "").removeprefix("operator_")
                if navn not in _FIL_VAERKTOEJER:
                    continue
                inp = b.get("input") if isinstance(b.get("input"), dict) else {}
                sti = str(inp.get("path") or "").strip()
                if not sti or not _under(sti, rod):
                    continue
                plus, minus = _diff(navn, inp)
                post = pr_fil.get(sti)
                if post is None:
                    # Beskederne laeses nyeste foerst, saa den foerste forekomst
                    # ER den seneste berøring af filen.
                    post = pr_fil[sti] = {
                        "path": sti,
                        "rel": sti[len(rod):].lstrip("/"),
                        "last_at": str(created_at or ""),
                        "session_id": str(session_id or ""),
                        "last_tool": navn,
                        "edits": 0, "add": 0, "del": 0,
                        "sessions": set(),
                    }
                post["edits"] += 1
                post["add"] += plus
                post["del"] += minus
                post["sessions"].add(str(session_id or ""))

        titler: dict[str, str] = {}
        sids = {p["session_id"] for p in pr_fil.values() if p["session_id"]}
        if sids:
            ph = ",".join("?" * len(sids))
            try:
                for sid, titel in conn.execute(
                    f"SELECT session_id, title FROM chat_sessions WHERE session_id IN ({ph})",
                    tuple(sids),
                ).fetchall():
                    titler[str(sid)] = str(titel or "")
            except Exception:
                titler = {}

    ud = sorted(pr_fil.values(), key=lambda p: p["last_at"], reverse=True)
    for p in ud:
        p["session_count"] = len(p.pop("sessions"))
        p["session_title"] = titler.get(p["session_id"], "")
    return {
        "ok": True,
        "root": rod,
        "scanned": scannet,
        "total": len(ud),
        "artifacts": ud[: max(1, int(limit))],
    }
