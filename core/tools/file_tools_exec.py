"""Fil-tool executors (read_file / write_file / edit_file / read_tool_result /
read_self_docs) — udskilt fra simple_tools.py (Boy Scout-reglen, 2026-06-14).

Den naturlige sammenhængende enhed: de generiske fil-læse/skrive/redigér-tools.
Samtidig gjort encryption-aware (§16 Task 3.2) via workspace_crypto, så en members
egen workspace-fil læses/skrives korrekt når den er krypteret (.enc).

Deps der bor i simple_tools (MAX_READ_CHARS, _canonicalize_workspace_target,
classify_file_write) importeres LAZY inde i funktionerne (kald-tid), så der ikke
opstår import-cyklus ved modul-load. Re-eksporteres fra simple_tools for bagudkompat
(dispatch-dict + tests bruger simple_tools._exec_*).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.services.tool_result_store import get_tool_result
from core.services.self_critique_runtime import read_self_docs


def _ws_read_text(path: Path) -> str | None:
    """Læs encryption-aware (member .enc transparent). None hvis intet findes."""
    from core.services.workspace_crypto import read_text_for_path
    return read_text_for_path(path)


def _ws_write_text(path: Path, content: str) -> None:
    """Skriv encryption-aware (member → .enc når ENCRYPT_ON_WRITE on)."""
    from core.services.workspace_crypto import write_text_for_path
    write_text_for_path(path, content)


def _ws_path_exists(path: Path) -> bool:
    """Eksistens encryption-aware: plaintext eller member .enc."""
    if path.exists():
        return True
    from core.services.workspace_crypto import member_user_id_for_path
    return bool(member_user_id_for_path(path)) and Path(str(path) + ".enc").exists()


def _record_active_file(path: str, op: str, args: dict[str, Any]) -> None:
    """Live-highlight: notér at Jarvis (i brugerens kontekst) rører `path`, så
    desk-fil-træet kan markere filen live. Fail-open — må aldrig vælte tool-kaldet."""
    try:
        from core.services.active_file_store import set_active_file
        uid = str(args.get("_runtime_user_id") or args.get("_user_id") or "owner")
        set_active_file(uid, str(path), op)
    except Exception:
        pass


# ── Read-back: gør mutationen selv-bevisende (10. sep 2026) ────────────────
#
# Målt samme dag: R2 heed-rate 17–26%, median 27 minutter fra advarsel til
# første kig. Hintet fandtes ALLEREDE ("kør verify_file_contains") og flyttede
# intet — fordi et hint er en OPFORDRING. `edit_file` returnerede
# `{"status": "ok", "replacements": 1}`: en PÅSTAND fra værktøjet, ikke fra
# disken. Verifikation blev dermed en ekstra handling man skulle VÆLGE midt i
# en arbejdsgang — og den blev valgt fra, fordi næste skridt lå lige for.
#
# Fixet fjerner valget: resultatet bærer nu filstumpen omkring ændringen, læst
# tilbage fra disken EFTER skrivningen. Er diff'en ikke som ventet, ser man det
# i samme sekund man ellers ville have bygget videre på den. Samme flytning som
# `record_surface`-fixet: fjern løgnen ved kilden frem for at advare bagefter.
#
# BEMÆRK (bevidst): `text` er i bro_broker._LOCAL_ONLY_KEYS, så i code-mode
# bliver read-back'en holdt på brugerens maskine — rå filindhold krydser ikke
# (§17.3). Det er meningen; chat-lanen er der hvor heed-raten måles.
_READBACK_MAX_CHARS = 1200


def _safe_readback(path: Path) -> str | None:
    """Læs filen tilbage — selv-sikker. None = den kunne ikke læses.

    None er et SIGNAL, ikke en tavshed: en fil der ikke kan læses tilbage efter
    en skrivning er det stærkeste tegn på at noget er galt. Derfor får den sit
    eget svar i resultatet frem for bare at udelade read-back'en.
    """
    try:
        return _ws_read_text(path)
    except Exception:
        return None


def _disk_readback(
    path: Path, *, start_line: int, span: int = 0, mark: bool = True,
) -> str:
    """Nummereret udsnit af filen som den står på disken EFTER skrivningen.

    `start_line` (0-baseret) er hvor ændringen begynder, `span` hvor mange
    linjer den fylder; der vises ±2 linjer omkring, og de ændrede linjer
    markeres med » så diff'en kan læses direkte. Selv-sikker → "" hvis filen
    ikke kan læses: en read-back må aldrig kunne vælte det kald den beviser.
    """
    fresh = _safe_readback(path)
    if fresh is None:
        return ""
    lines = fresh.split("\n")
    lo = max(0, start_line - 2)
    hi = min(len(lines), start_line + span + 3)
    out: list[str] = []
    for i in range(lo, hi):
        changed = mark and start_line <= i <= start_line + span
        out.append(f"{'»' if changed else ' '}{i + 1:>5}| {lines[i]}")
    block = "\n".join(out)
    if len(block) > _READBACK_MAX_CHARS:
        block = block[:_READBACK_MAX_CHARS] + "\n… (afkortet)"
    return block


def _exec_read_file(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import MAX_READ_CHARS

    path = str(args.get("path") or "").strip()
    if not path:
        return {"error": "path is required", "status": "error"}

    target = Path(path).expanduser().resolve()
    if not _ws_path_exists(target):
        return {"error": f"File not found: {path}", "status": "error"}
    if target.exists() and not target.is_file():
        return {"error": f"Not a file: {path}", "status": "error"}

    try:
        text = _ws_read_text(target)
    except PermissionError:
        return {"error": f"Permission denied: {path}", "status": "error"}
    if text is None:
        return {"error": f"File not found: {path}", "status": "error"}

    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS - 1] + "…"

    # Record read for read-before-write guard
    # Note: tools receive _runtime_session_id (not _session_id) — fall back
    # through both keys so the guard tracks reads correctly regardless of
    # caller convention.
    try:
        from core.services.read_before_write_guard import record_read
        _session_id = (
            args.get("_runtime_session_id")
            or args.get("_session_id")
            or "default"
        )
        record_read(str(target), session_id=str(_session_id))
    except Exception:
        pass

    _record_active_file(str(target), "read", args)
    return {"text": text, "path": str(target), "size": len(text), "status": "ok"}


def _exec_read_tool_result(args: dict[str, Any]) -> dict[str, Any]:
    result_id = str(args.get("result_id") or "").strip()
    if not result_id:
        return {"error": "result_id is required", "status": "error"}

    # K11: den der spoerger gives med, saa en handle fra en ANDEN brugers
    # session ikke kan hentes ved at kende dens id.
    record = get_tool_result(result_id, user_id=str(
        args.get("_runtime_user_id") or args.get("_user_id") or "") or None)
    if not record:
        return {"error": f"Tool result not found: {result_id}", "status": "error"}

    return {
        "status": "ok",
        "text": str(record.get("result") or "") or "[empty tool result]",
        "result_id": result_id,
        "tool_name": str(record.get("tool_name") or ""),
        "arguments": dict(record.get("arguments") or {}),
        "summary": str(record.get("summary") or ""),
        "created_at": str(record.get("created_at") or ""),
    }


def _exec_read_self_docs(args: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(args.get("doc_id") or "").strip()
    include_history = bool(args.get("include_history") or False)
    max_chars_per_doc_raw = args.get("max_chars_per_doc")
    kwargs: dict[str, Any] = {
        "doc_id": doc_id,
        "include_history": include_history,
    }
    if max_chars_per_doc_raw is not None:
        kwargs["max_chars_per_doc"] = max(500, int(max_chars_per_doc_raw))
    try:
        return read_self_docs(**kwargs)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_write_file(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _canonicalize_workspace_target

    path = str(args.get("path") or "").strip()
    content = str(args.get("content") or "")
    if not path:
        return {"error": "path is required", "status": "error"}

    target = Path(path).expanduser().resolve()
    target, redirected_from = _canonicalize_workspace_target(target)

    # Execution-cluster 🔒 GENNEM Den Intelligente Central (SECURITY): fil-klassifikation
    # + read-before-write konsolideret til ÉT traced gate-kald (classify FØR rbw, paritet).
    _session_id = (
        args.get("_runtime_session_id")
        or args.get("_session_id")
        or "default"
    )
    from core.services.gate_execution import check_file
    _ec = check_file(str(target), session_id=str(_session_id), kind="write")

    if _ec.classification == "blocked":
        return {"error": f"Write blocked for safety: {path}", "status": "blocked"}

    if _ec.classification == "approval":
        return {
            "status": "approval_needed",
            "message": f"Writing to {path} requires your approval. Please confirm in chat.",
            "path": str(target),
            "content_preview": content[:200] + ("…" if len(content) > 200 else ""),
        }

    if _ec.classification == "guard_blocked":
        return {"status": "guard_blocked", "error": _ec.reason}

    # Auto-approved (workspace files)
    #
    # DURABEL TILSTAND (Fase 3, K3): ingen bliver spurgt om denne skrivning,
    # men den ÆNDRER noget. Uden posten kan et nedbrud midt i ikke skelnes fra
    # en skrivning der aldrig skete. `recorded` kaster aldrig — kaldet koerer
    # uanset — men den tier heller ikke.
    from core.services.invocation_record import recorded
    with recorded("write_file", {"path": str(target)},
                  session_id=str(_session_id or "")):
        target.parent.mkdir(parents=True, exist_ok=True)
        _ws_write_text(target, content)
    result = {"status": "ok", "path": str(target), "bytes_written": len(content.encode("utf-8"))}
    # ── Read-back fra disken (se read-back-blokken i toppen af filen) ──────
    # Før var `bytes_written` en PÅSTAND fra værktøjet. Nu bærer resultatet
    # også filens faktiske begyndelse, læst tilbage EFTER skrivningen — og
    # `readback` siger om disken indeholder PRÆCIS det vi skrev.
    _fresh = _safe_readback(target)
    result["readback"] = (_fresh == content)
    if _fresh is None:
        result["text"] = (
            f"Wrote {target} ({result['bytes_written']} bytes)  "
            "⚠ filen kunne IKKE læses tilbage fra disken — tjek den"
        )
    else:
        result["line_count"] = _fresh.count("\n") + 1
        _head = _disk_readback(target, start_line=0, span=0, mark=False)
        _txt = (
            f"Wrote {target} ({result['bytes_written']} bytes, "
            f"{result['line_count']} lines)"
        )
        if not result["readback"]:
            _txt += "  ⚠ readback afviger fra det skrevne — tjek filen"
        result["text"] = f"{_txt}\n\nreadback fra disk (første linjer):\n{_head}"
    if redirected_from:
        result["redirected_from"] = redirected_from
        result["note"] = f"Path redirected to canonical workspace location: {target}"
    try:
        from core.services.self_mutation_lineage import record_self_mutation
        record_self_mutation(target_path=str(target), change_type="write")
    except Exception:
        pass
    _record_active_file(str(target), "write", args)
    return result


def _exec_edit_file(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _canonicalize_workspace_target

    path = str(args.get("path") or "").strip()
    old_text = str(args.get("old_text") or "")
    new_text = str(args.get("new_text") or "")
    replace_all = bool(args.get("replace_all", False))
    expected_replacements = args.get("expected_replacements")
    if not path or not old_text:
        return {"error": "path and old_text are required", "status": "error"}

    target = Path(path).expanduser().resolve()
    target, redirected_from = _canonicalize_workspace_target(target)

    # Execution-cluster 🔒 GENNEM Centralen (SECURITY): klassifikation via gate (edit har
    # historisk ingen read-before-write — bevaret med kind="edit").
    from core.services.gate_execution import check_file
    _ec = check_file(str(target), kind="edit")

    if _ec.classification == "blocked":
        return {"error": f"Edit blocked for safety: {path}", "status": "blocked"}

    if _ec.classification == "approval":
        return {
            "status": "approval_needed",
            "message": f"Editing {path} requires your approval. Please confirm in chat.",
            "path": str(target),
            "old_text_preview": old_text[:100],
            "new_text_preview": new_text[:100],
        }

    if not _ws_path_exists(target):
        return {"error": f"File not found: {path}", "status": "error"}

    content = _ws_read_text(target) or ""
    if old_text not in content:
        return {"error": "old_text not found in file", "status": "error"}

    count = content.count(old_text)
    if count > 1 and not replace_all:
        return {
            "error": f"old_text matches {count} locations — be more specific, "
                     f"or pass replace_all=true to rename every occurrence",
            "status": "error",
            "match_count": count,
        }

    if expected_replacements is not None:
        try:
            expected = int(expected_replacements)
        except Exception:
            return {"error": "expected_replacements must be an integer", "status": "error"}
        if count != expected:
            return {
                "error": f"expected {expected} matches but found {count}",
                "status": "error",
                "match_count": count,
            }

    replacements = count if replace_all else 1
    # Hvor i filen lander ændringen? Alt FØR matchet er uændret, så
    # linjenummeret er det samme før og efter skrivningen — derfor kan
    # read-back'en nedenfor ramme vinduet uden at søge i den nye tekst
    # (og dermed også vise en SLETNING, hvor new_text er tom).
    _start_line = content[: content.find(old_text)].count("\n")
    new_content = content.replace(old_text, new_text, -1 if replace_all else 1)
    # DURABEL TILSTAND (Fase 3, K3) — samme grund som i skrivningen ovenfor.
    # En edit er endda vaerre at miste: den er en DELVIS aendring, saa «skete
    # den?» kan ikke besvares ved at kigge paa om filen findes.
    from core.services.invocation_record import recorded
    with recorded("edit_file", {"path": str(target), "replacements": replacements},
                  session_id=str(args.get("_runtime_session_id")
                                 or args.get("_session_id") or "")):
        _ws_write_text(target, new_content)
    try:
        from core.services.self_mutation_lineage import record_self_mutation
        record_self_mutation(target_path=str(target), change_type="edit")
    except Exception:
        pass
    result = {"status": "ok", "path": str(target), "replacements": replacements}
    # ── Read-back fra disken (se read-back-blokken i toppen af filen) ──────
    # En edit er en DELVIS ændring — «skete den?» kan ikke besvares ved at se
    # om filen findes. Derfor: læs filen tilbage og vis udsnittet omkring
    # ændringen, nummereret, så diff'en kan læses direkte i resultatet.
    _fresh = _safe_readback(target)
    if _fresh is None:
        # Filen kunne ikke læses tilbage EFTER en edit — den fandtes før.
        # Det er ikke tavshed, det er det stærkeste faresignal vi kan give.
        result["readback"] = False
        result["text"] = (
            f"Edited {target} ({replacements} "
            f"replacement{'s' if replacements != 1 else ''})  "
            "⚠ filen kunne IKKE læses tilbage fra disken — tjek den"
        )
    else:
        _ok = (new_text in _fresh) if new_text else (old_text not in _fresh)
        result["readback"] = _ok
        _block = _disk_readback(
            target, start_line=_start_line, span=new_text.count("\n"),
        )
        if _block:
            _txt = (
                f"Edited {target} ({replacements} "
                f"replacement{'s' if replacements != 1 else ''})"
            )
            if not _ok:
                _txt += "  ⚠ ændringen står IKKE i readback'en — tjek filen"
            result["text"] = f"{_txt}\n\nreadback fra disk:\n{_block}"
    if redirected_from:
        result["redirected_from"] = redirected_from
        result["note"] = f"Path redirected to canonical workspace location: {target}"
    _record_active_file(str(target), "write", args)
    return result
