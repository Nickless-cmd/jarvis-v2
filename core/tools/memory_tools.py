"""Memory duplicate-check and safe-write tools for MEMORY.md."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.runtime.workspace_paths import NoUserContextError, shared_dir, workspace_dir


def _resolve_memory_uid(user_id: str | None = None) -> str:
    """Hvilken brugers MEMORY.md skal vi røre. Best-effort:
    1) eksplicit user_id (fra tool-args hvis sat),
    2) current_user_id() (sat for members via set_context i run-body'en),
    3) session-ejer via bundet session_id — owner har OFTE tom current_user_id()
       inde i run-generatoren (samme grund som device-presence-fixet brugte
       get_session_owner). Tom streng → kalderen falder tilbage til shared_dir.
    """
    uid = (user_id or "").strip()
    if uid:
        return uid
    try:
        from core.identity.workspace_context import current_session_id, current_user_id
        uid = (current_user_id() or "").strip()
        if uid:
            return uid
        sid = (current_session_id() or "").strip()
        if sid:
            from core.services.chat_sessions import get_session_owner
            return (get_session_owner(sid) or "").strip()
    except Exception:
        return ""
    return ""


def _memory_md(user_id: str | None = None) -> Path:
    """Brugerens MEMORY.md (workspace) — IKKE shared. Fald tilbage til shared
    kun når ingen bruger kan resolves (autonome runs / daemons).

    Rettelse 2026-06-20: skrev tidligere til shared/MEMORY.md → alt tool-skrevet
    memory var usynligt for prompten (læser fra workspace) + isolation/privacy-bug
    (alle brugeres memory blandet i shared).
    """
    uid = _resolve_memory_uid(user_id)
    if not uid:
        # 2026-07-22: no user context (autonomous / dream / heartbeat runs). Jarvis' OWN
        # entity-level memories (dreams, inner-life) belong to the OWNER's workspace — his
        # home identity — NOT shared/. shared/ is invisible to EVERY user's prompt (each
        # reads their own workspace), so these were orphaned (236 entries found in shared,
        # incl. all his dreams). Multi-user-safe: per-user tool writes resolve above via uid;
        # only the entity-level no-context case falls here → owner. Resolve owner dynamically
        # (never hardcode). Last-resort shared/ only if the owner cannot be resolved.
        try:
            from core.identity.users import get_owner
            _owner = get_owner()
            _oid = str(getattr(_owner, "discord_id", "") or "").strip() if _owner else ""
            if _oid:
                uid = _oid
        except Exception:
            pass
    if uid:
        try:
            return workspace_dir(uid) / "MEMORY.md"
        except NoUserContextError:
            pass
    return shared_dir() / "MEMORY.md"


def _read_memory() -> str:
    try:
        return _memory_md().read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _parse_headings(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^#{1,4}\s+(.+)$", text, re.MULTILINE)]


def _normalize(heading: str) -> str:
    return re.sub(r"\s+", " ", heading.strip().lower())


def _exec_memory_check_duplicate(args: dict[str, Any]) -> dict[str, Any]:
    heading = str(args.get("heading") or "").strip()
    if not heading:
        return {"status": "error", "error": "heading is required"}

    text = _read_memory()
    existing = _parse_headings(text)
    norm_target = _normalize(heading)

    exact_matches = [h for h in existing if _normalize(h) == norm_target]
    # Fuzzy: heading is contained in existing or vice versa (> 60% overlap)
    fuzzy_matches = [
        h for h in existing
        if h not in exact_matches
        and (norm_target in _normalize(h) or _normalize(h) in norm_target)
        and len(norm_target) > 5
    ]

    return {
        "status": "ok",
        "heading": heading,
        "is_duplicate": bool(exact_matches),
        "exact_matches": exact_matches,
        "fuzzy_matches": fuzzy_matches,
        "all_headings": existing,
        "text": (
            f"DUPLICATE: '{heading}' already exists in MEMORY.md."
            if exact_matches
            else (
                f"POSSIBLE DUPLICATE: Similar headings found: {fuzzy_matches}"
                if fuzzy_matches
                else f"OK: '{heading}' is new — safe to add."
            )
        ),
    }


def _exec_memory_upsert_section(args: dict[str, Any]) -> dict[str, Any]:
    """Write or update a section in MEMORY.md. Replaces existing section if heading matches."""
    heading = str(args.get("heading") or "").strip()
    content = str(args.get("content") or "").strip()
    level = int(args.get("level") or 2)

    if not heading:
        return {"status": "error", "error": "heading is required"}
    if not content:
        return {"status": "error", "error": "content is required"}
    if not 1 <= level <= 4:
        return {"status": "error", "error": "level must be 1-4"}

    text = _read_memory()
    hashes = "#" * level
    full_heading = f"{hashes} {heading}"
    norm_target = _normalize(heading)

    # Find if an existing section matches (exact + fuzzy warning)
    existing_headings = _parse_headings(text)
    match = next((h for h in existing_headings if _normalize(h) == norm_target), None)

    # Lag 3: fuzzy heading overlap warning
    fuzzy_warnings = []
    if not match:
        for h in existing_headings:
            # Containment check: new heading is a subset of existing or vice versa
            norm_h = _normalize(h)
            if norm_target in norm_h or norm_h in norm_target:
                if norm_h != norm_target and len(norm_target) > 5:
                    fuzzy_warnings.append(h)

    if match:
        # Replace existing section: find start + end of the section
        pattern = rf"(^#{{{level}}}\s+{re.escape(match)}\s*\n)(.*?)(?=^#|\Z)"
        replacement = f"{hashes} {heading}\n{content}\n\n"
        new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE | re.DOTALL)
        if count == 0:
            # Fallback: just append
            new_text = text.rstrip() + f"\n\n{full_heading}\n{content}\n"
        action = "updated"
    else:
        # Append new section
        new_text = text.rstrip() + f"\n\n{full_heading}\n{content}\n"
        action = "added"

    p = _memory_md()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(new_text, encoding="utf-8")

    # Queue side effects (mood capture + graph ingestion) for async
    # processing. The memory_write_queue daemon handles these in the
    # background so the tool call returns immediately.
    try:
        from core.services.memory_write_queue import enqueue_write
        enqueue_write(
            "memory_sidecar",
            {"heading": heading, "action": action, "content": content},
            priority=5,  # sidecar is higher priority than sensory/brain
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "action": action,
        "heading": heading,
        "fuzzy_heading_warnings": fuzzy_warnings if fuzzy_warnings else None,
        "text": f"MEMORY.md section '{heading}' {action} successfully." + (
            f" WARNING: Similar headings exist: {fuzzy_warnings}" if fuzzy_warnings else ""
        ),
    }


def _exec_memory_list_headings(args: dict[str, Any]) -> dict[str, Any]:
    text = _read_memory()
    headings = _parse_headings(text)
    return {
        "status": "ok",
        "headings": headings,
        "count": len(headings),
    }


def _exec_memory_consolidate(args: dict[str, Any]) -> dict[str, Any]:
    """Find fuzzy-overlapping sections in MEMORY.md and propose/execute merges."""
    dry_run = bool(args.get("dry_run", True))
    min_similarity = float(args.get("min_similarity") or 0.5)

    text = _read_memory()
    if not text:
        return {"status": "error", "error": "MEMORY.md is empty or not found."}

    # Parse sections: (heading, content, level)
    sections: list[dict] = []
    current_heading = None
    current_level = 0
    current_lines: list[str] = []

    for line in text.splitlines():
        m = re.match(r"^(#{1,4})\s+(.+)$", line)
        if m:
            if current_heading is not None:
                sections.append({
                    "heading": current_heading,
                    "level": current_level,
                    "content": "\n".join(current_lines).strip(),
                })
            current_level = len(m.group(1))
            current_heading = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_heading is not None:
        sections.append({"heading": current_heading, "level": current_level, "content": "\n".join(current_lines).strip()})

    if len(sections) < 2:
        return {"status": "ok", "proposals": [], "text": "Not enough sections to consolidate."}

    # Find overlapping pairs using word overlap (Jaccard-like)
    def _overlap(a: str, b: str) -> float:
        wa = set(re.findall(r"\w+", a.lower()))
        wb = set(re.findall(r"\w+", b.lower()))
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    proposals = []
    seen = set()
    for i, s1 in enumerate(sections):
        for j, s2 in enumerate(sections):
            if j <= i or (i, j) in seen:
                continue
            # Only merge same-level sections
            if s1["level"] != s2["level"]:
                continue
            heading_sim = _overlap(s1["heading"], s2["heading"])
            content_sim = _overlap(s1["content"][:500], s2["content"][:500])
            combined_sim = heading_sim * 0.6 + content_sim * 0.4
            if combined_sim >= min_similarity:
                proposals.append({
                    "section_a": s1["heading"],
                    "section_b": s2["heading"],
                    "similarity": round(combined_sim, 3),
                    "level": s1["level"],
                })
                seen.add((i, j))

    if not proposals:
        return {"status": "ok", "proposals": [], "text": "No overlapping sections found — MEMORY.md looks clean."}

    if dry_run:
        return {
            "status": "ok",
            "proposals": proposals,
            "dry_run": True,
            "text": (
                f"Found {len(proposals)} potential merge(s). Run with dry_run=false to execute.\n"
                + "\n".join(f"  • '{p['section_a']}' ↔ '{p['section_b']}' (similarity: {p['similarity']})" for p in proposals)
            ),
        }

    # Execute: use LLM to merge each pair
    merged_headings = []
    errors = []
    for p in proposals:
        s_a = next((s for s in sections if s["heading"] == p["section_a"]), None)
        s_b = next((s for s in sections if s["heading"] == p["section_b"]), None)
        if not s_a or not s_b:
            continue
        try:
            from core.context.compact_llm import call_compact_llm
            prompt = (
                f"Flet disse to MEMORY.md-sektioner til én.\n"
                f"Bevar alle detaljer. Fjern kun direkte gentagelser.\n"
                f"Brug '{p['section_a']}' som overskrift medmindre en bedre titel er oplagt.\n\n"
                f"## {s_a['heading']}\n{s_a['content']}\n\n"
                f"## {s_b['heading']}\n{s_b['content']}\n\n"
                f"Svar KUN med det samlede indhold (uden overskrift):"
            )
            merged_content = call_compact_llm(prompt, max_tokens=600)
            # Write merged section (replaces section_a) + remove section_b
            _exec_memory_upsert_section({
                "heading": p["section_a"],
                "content": merged_content.strip(),
                "level": p["level"],
            })
            # Remove section_b by replacing with empty content then cleaning up
            fresh_text = _read_memory()
            hashes = "#" * p["level"]
            rm_pattern = rf"(^{re.escape(hashes)}\s+{re.escape(p['section_b'])}\s*\n)(.*?)(?=^#|\Z)"
            cleaned = re.sub(rm_pattern, "", fresh_text, count=1, flags=re.MULTILINE | re.DOTALL)
            _memory_md().write_text(cleaned, encoding="utf-8")
            merged_headings.append(f"'{p['section_a']}' + '{p['section_b']}'")
        except Exception as e:
            errors.append(f"{p['section_a']} + {p['section_b']}: {e}")

    return {
        "status": "ok",
        "merged": merged_headings,
        "errors": errors or None,
        "text": f"Merged {len(merged_headings)} section pair(s)." + (f" Errors: {errors}" if errors else ""),
    }


MEMORY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "memory_check_duplicate",
            "description": (
                "Check whether a heading already exists in MEMORY.md before writing, "
                "to avoid duplicate sections. Returns exact and fuzzy matches."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string", "description": "The section heading to check for."},
                },
                "required": ["heading"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_upsert_section",
            "description": (
                "Safely write or update a section in MEMORY.md. "
                "If the heading already exists, replaces it. Otherwise appends. "
                "Use this instead of write_file for MEMORY.md updates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string", "description": "Section heading (without # prefix)."},
                    "content": {"type": "string", "description": "Full content of the section."},
                    "level": {"type": "integer", "description": "Heading level 1-4 (default 2, i.e. ##)."},
                },
                "required": ["heading", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_list_headings",
            "description": "List all section headings currently in MEMORY.md.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_consolidate",
            "description": (
                "Find fuzzy-overlapping sections in MEMORY.md and propose or execute merges. "
                "Uses word-overlap scoring to detect duplicate themes across different headings, "
                "then uses LLM to merge content while preserving all details. "
                "Run with dry_run=true first to preview proposals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview merge proposals without executing (default true).",
                    },
                    "min_similarity": {
                        "type": "number",
                        "description": "Minimum combined similarity score (0-1) to flag for merge (default 0.5).",
                    },
                },
                "required": [],
            },
        },
    },
]
