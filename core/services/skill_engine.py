"""Skill Engine — SKILL.md loader for Jarvis.

Lader Jarvis importere, bruge og oprette skills i Claude Code / OpenClaw
SKILL.md-format. Skills bor i ~/.jarvis-v2/skills/<name>/ hver med:

  SKILL.md       — YAML frontmatter + markdown instruktioner
  scripts/       — valgfrie hjælpescripts (py, sh, js)
  templates/     — valgfrie skabeloner
  references/    — valgfrie referencefiler

Format (Claude Code / OpenClaw kompatibelt):
  ---
  name: <skill-name>
  description: <kort beskrivelse>
  use_when: <hvornår skal denne skill aktiveres>
  tags: [tag1, tag2]
  model: [optional]  # hvis skill kun virker på bestemt model
  requires_tools: [tool1, tool2]  # valgfri tool-afhængigheder
  ---
  # Instruktioner
  ...
"""
from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:  # pyyaml is in v2's dep set; fall back to manual parser if missing
    import yaml as _yaml
except Exception:  # pragma: no cover
    _yaml = None

from core.runtime.config import JARVIS_HOME

logger = logging.getLogger(__name__)

SKILLS_ROOT = Path(JARVIS_HOME) / "skills"

# ── Datamodel ──────────────────────────────────────────────────────────


@dataclass
class Skill:
    """A loaded skill from disk."""

    name: str
    description: str
    use_when: str = ""
    tags: list[str] = field(default_factory=list)
    instructions: str = ""
    frontmatter: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None
    scripts_path: Path | None = None
    templates_path: Path | None = None
    references_path: Path | None = None
    has_scripts: bool = False
    has_templates: bool = False
    has_references: bool = False
    loaded_at: str = ""


# ── Parser ─────────────────────────────────────────────────────────────


def _parse_skill_md(path: Path) -> Skill | None:
    """Parse a SKILL.md file and return a Skill dataclass.

    Supports YAML frontmatter between --- markers (standard for both
    Claude Code and OpenClaw skills). Falls back to treating the entire
    file as instructions if no frontmatter.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("skill_engine: cannot read %s: %s", path, exc)
        return None

    name = path.parent.name  # folder name = skill name
    instructions = raw
    frontmatter: dict[str, Any] = {}

    # Check for --- frontmatter
    if raw.startswith("---\n") or raw.startswith("---\r\n"):
        end_match = re.search(r"\n---\s*\n|\n---\s*$", raw[4:])
        if end_match:
            fm_raw = raw[4:4 + end_match.start()]
            rest = raw[4 + end_match.end():]
            instructions = rest.strip()
            # Prefer pyyaml — handles nested objects, anchors, multiline blocks,
            # quoted strings, escapes correctly. Fall back to a minimal parser
            # if pyyaml is missing OR the frontmatter is malformed.
            parsed_ok = False
            if _yaml is not None:
                try:
                    loaded = _yaml.safe_load(fm_raw)
                    if isinstance(loaded, dict):
                        # Lower-case top-level keys to keep API stable
                        frontmatter = {
                            str(k).lower(): v for k, v in loaded.items()
                        }
                        parsed_ok = True
                    elif loaded is None:
                        parsed_ok = True  # empty frontmatter is valid
                except _yaml.YAMLError as exc:
                    logger.warning(
                        "skill_engine: pyyaml failed for %s: %s — using fallback",
                        path, exc,
                    )
            if not parsed_ok:
                # Minimal fallback: scalar key:value lines + inline [a, b] lists
                for line in fm_raw.splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#") or ":" not in line:
                        continue
                    key, _, val_part = line.partition(":")
                    key = key.strip().lower()
                    val = val_part.strip()
                    if val.startswith("[") and val.endswith("]"):
                        val = [t.strip() for t in val[1:-1].split(",") if t.strip()]
                    elif val.lower() in ("true", "false"):
                        val = val.lower() == "true"
                    frontmatter[key] = val

    desc = frontmatter.get("description", "") or ""
    use_when = frontmatter.get("use_when", "") or ""
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]

    skill_dir = path.parent
    scripts = skill_dir / "scripts"
    templates = skill_dir / "templates"
    refs = skill_dir / "references"

    return Skill(
        name=name,
        description=desc if isinstance(desc, str) else str(desc),
        use_when=use_when if isinstance(use_when, str) else str(use_when),
        tags=tags if isinstance(tags, list) else [],
        instructions=instructions,
        frontmatter=frontmatter,
        path=path,
        scripts_path=scripts if scripts.exists() else None,
        templates_path=templates if templates.exists() else None,
        references_path=refs if refs.exists() else None,
        has_scripts=scripts.exists() and any(scripts.iterdir()),
        has_templates=templates.exists() and any(templates.iterdir()),
        has_references=refs.exists() and any(refs.iterdir()),
        loaded_at=datetime.now(UTC).isoformat(),
    )


# ── Registry (in-memory + on-demand reload) ────────────────────────────

# `_registry` is read by the visible-lane chat thread, the heartbeat
# daemon, and skill_gate at the same time. `reload_skills()` rebuilds it
# wholesale — without a lock, an iterating thread can crash on dict
# mutation. Use an RLock so reload_skills can call _scan_skills which
# itself touches state, and so reentrant reads inside hot paths don't
# deadlock.
_registry: dict[str, Skill] = {}
_last_scan: str = ""
_registry_lock = threading.RLock()


def _scan_skills() -> dict[str, Skill]:
    """Scan SKILLS_ROOT for all skills (mappe med SKILL.md)."""
    skills: dict[str, Skill] = {}
    if not SKILLS_ROOT.exists():
        return skills
    for child in sorted(SKILLS_ROOT.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.exists():
            # Try lowercase
            skill_md = child / "skill.md"
        if not skill_md.exists():
            continue
        skill = _parse_skill_md(skill_md)
        if skill:
            skills[skill.name] = skill
    return skills


def reload_skills() -> dict[str, Any]:
    """Force-reload all skills from disk. Returns summary."""
    global _registry, _last_scan
    with _registry_lock:
        _registry = _scan_skills()
        _last_scan = datetime.now(UTC).isoformat()
        _record_audit_entry(
            "__bulk__", "bulk_reloaded",
            diff_summary=f"{len(_registry)} skills loaded",
            reason="reload_skills()",
        )
        return {
            "status": "ok",
            "count": len(_registry),
            "skills": list(_registry.keys()),
            "scanned_at": _last_scan,
        }


def get_skill(name: str) -> Skill | None:
    """Get a single skill by name. Lazy-loads if not cached."""
    with _registry_lock:
        if not _registry:
            # Release lock during scan? RLock allows reentry, so reload_skills
            # below re-acquires safely.
            pass
        if not _registry:
            reload_skills()
        for key, skill in _registry.items():
            if key.lower() == name.lower():
                return skill
        return _registry.get(name)


def list_skills(tag: str | None = None) -> list[dict[str, Any]]:
    """List all skills, optionally filtered by tag."""
    with _registry_lock:
        if not _registry:
            reload_skills()
        # Snapshot under lock so iteration is safe even if a reload fires
        # mid-call from another thread.
        snapshot = list(_registry.values())
    results = []
    for skill in snapshot:
        if tag and tag.lower() not in [t.lower() for t in skill.tags]:
            continue
        results.append({
            "name": skill.name,
            "description": skill.description,
            "use_when": skill.use_when,
            "tags": skill.tags,
            "has_scripts": skill.has_scripts,
            "has_templates": skill.has_templates,
            "has_references": skill.has_references,
            "loaded_at": skill.loaded_at,
        })
    return sorted(results, key=lambda s: s["name"])


def skill_exists(name: str) -> bool:
    """Check if a skill exists on disk."""
    return (SKILLS_ROOT / name / "SKILL.md").exists() or (SKILLS_ROOT / name / "skill.md").exists()


def _collect_registered_tool_names() -> set[str]:
    """Return the set of registered tool names (normalized form).

    Lazy import to avoid pulling simple_tools at module load time —
    simple_tools transitively imports a lot.
    """
    try:
        from core.tools.simple_tools import TOOL_DEFINITIONS
    except Exception:
        return set()
    names: set[str] = set()
    for entry in TOOL_DEFINITIONS or []:
        if not isinstance(entry, dict):
            continue
        fn = entry.get("function") if isinstance(entry.get("function"), dict) else entry
        n = str((fn or {}).get("name") or "").strip()
        if n:
            # Normalize for comparison: lowercase, "-" → "_"
            names.add(n.lower().replace("-", "_"))
    return names


_GENERIC_SKILL_NAMES = {
    "assistant",
    "general",
    "helper",
    "new-skill",
    "skill",
    "tool",
}


def _skill_quality_nudges(
    name: str,
    description: str,
    instructions: str,
    use_when: str = "",
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return non-blocking quality nudges for installable skill proposals."""
    nudges: list[dict[str, Any]] = []
    tags = tags or []
    desc_norm = " ".join(description.lower().split())
    use_norm = " ".join((use_when or "").lower().split())
    instructions_norm = instructions.lower()

    def add(nudge_id: str, message: str, severity: str = "suggestion") -> None:
        nudges.append({
            "id": nudge_id,
            "severity": severity,
            "message": message,
        })

    if name in _GENERIC_SKILL_NAMES:
        add(
            "generic_name",
            "Name is very generic; choose a name that describes the concrete trigger or capability.",
            "warning",
        )
    if len(description.strip()) < 24:
        add(
            "thin_description",
            "Description is thin; add the capability, scope, and expected outcome.",
        )
    if len(instructions.strip()) < 120:
        add(
            "thin_instructions",
            "Instructions are thin; add concrete steps, boundaries, and verification criteria.",
            "warning",
        )
    if not use_norm or use_norm == desc_norm:
        add(
            "weak_trigger",
            "use_when should describe the activation context separately from the description.",
        )

    workflow_markers = (
        "when ",
        "steps",
        "step ",
        "use ",
        "return",
        "verify",
        "check",
        "- ",
        "1.",
    )
    if not any(marker in instructions_norm for marker in workflow_markers):
        add(
            "missing_workflow_shape",
            "Instructions should read like an operational workflow, not just a capability label.",
        )
    if not tags:
        add("missing_tags", "Add at least one tag so skill discovery can classify it.")
    elif len(tags) > 8:
        add(
            "too_many_tags",
            "Too many tags make discovery noisy; keep only the strongest categories.",
        )

    return nudges


def validate_skill_proposal(
    name: str,
    description: str,
    instructions: str,
    use_when: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Validate that a proposed skill would be installable by create_skill().

    Same checks as create_skill() but without writing to disk:
      - name is non-empty after strip+lower+space→hyphen normalization
      - name matches ^[a-z0-9][a-z0-9_-]*$
      - description and instructions are non-empty
      - no existing skill with the (normalized) name
      - normalized name does not shadow a registered tool name

    Returns {"status": "ok", "name": normalized_name, ...} or
    {"status": "error", "error": "..."}.

    Quality nudges are advisory only. They help the approval flow surface
    thin or over-broad proposals without turning taste into a hard gate.

    Single source of truth — create_skill() also calls this function.
    """
    name = name.strip().lower().replace(" ", "-")
    if not name:
        return {"status": "error", "error": "name is required"}
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", name):
        return {"status": "error", "error": "name must be lowercase alphanumeric with - and _"}
    if not description or not instructions:
        return {"status": "error", "error": "description and instructions are required"}

    skill_dir = SKILLS_ROOT / name
    if skill_dir.exists():
        return {"status": "error", "error": f"skill '{name}' already exists"}

    # Shadow-check: skill name (normalized to underscore form) must not
    # collide with a registered tool name.
    normalized_for_tool_check = name.replace("-", "_")
    tool_names = _collect_registered_tool_names()
    if normalized_for_tool_check in tool_names:
        return {
            "status": "error",
            "error": (
                f"name '{name}' shadows existing tool '{normalized_for_tool_check}' — "
                "pick a different name to avoid skill_chain confusion"
            ),
        }

    quality_nudges = _skill_quality_nudges(
        name=name,
        description=description,
        instructions=instructions,
        use_when=use_when,
        tags=tags,
    )
    quality_score = max(0.0, round(1.0 - (len(quality_nudges) * 0.16), 2))
    return {
        "status": "ok",
        "name": name,
        "quality_nudges": quality_nudges,
        "quality_score": quality_score,
    }


def create_skill(
    name: str,
    description: str,
    instructions: str,
    use_when: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new skill directory with SKILL.md on disk.

    Delegates validation to validate_skill_proposal() (single source of truth).
    """
    validation = validate_skill_proposal(
        name=name,
        description=description,
        instructions=instructions,
        use_when=use_when,
        tags=tags,
    )
    if validation.get("status") != "ok":
        return validation
    name = str(validation.get("name") or name.strip().lower().replace(" ", "-"))

    skill_dir = SKILLS_ROOT / name

    tags = tags or []
    # Use yaml.safe_dump for the frontmatter so values containing colons,
    # quotes, commas, or newlines round-trip safely. Falls back to a manual
    # build only if pyyaml is unavailable (matches _parse_skill_md fallback).
    fm_data = {
        "name": name,
        "description": description,
        "use_when": use_when or description,
        "tags": list(tags),
    }
    if _yaml is not None:
        fm_body = _yaml.safe_dump(
            fm_data, sort_keys=False, allow_unicode=True, default_flow_style=False
        )
    else:
        # Conservative fallback: quote string values, render tags inline.
        # Triggers ONLY if pyyaml is absent — production v2 has it.
        def _q(s: str) -> str:
            return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'
        fm_body = (
            f"name: {_q(name)}\n"
            f"description: {_q(description)}\n"
            f"use_when: {_q(use_when or description)}\n"
            f"tags: [{', '.join(_q(t) for t in tags)}]\n"
        )
    fm = f"---\n{fm_body}---\n\n"
    content = fm + instructions.strip() + "\n"

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        # Create optional subdirs
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "templates").mkdir(exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)
    except OSError as exc:
        return {"status": "error", "error": f"write failed: {exc}"}

    # Reload to pick it up
    reload_skills()
    _record_audit_entry(
        name, "created",
        reason="create_skill()",
        snapshot=_build_skill_snapshot(name),
    )
    return {
        "status": "ok",
        "name": name,
        "path": str(skill_dir),
        "note": "Skill created. You can add scripts/, templates/, and references/ files.",
    }


def delete_skill(name: str) -> dict[str, Any]:
    """Delete a skill directory from disk."""
    skill_dir = SKILLS_ROOT / name
    if not skill_dir.exists():
        return {"status": "error", "error": f"skill '{name}' not found"}
    import shutil
    try:
        shutil.rmtree(skill_dir)
    except OSError as exc:
        return {"status": "error", "error": f"delete failed: {exc}"}
    # Reload
    reload_skills()
    _record_audit_entry(
        name, "deleted",
        reason="delete_skill()",
    )
    return {"status": "ok", "name": name, "note": "Skill deleted."}


def get_skill_instructions(name: str) -> dict[str, Any]:
    """Get the full instructions + context for a skill (for prompt injection)."""
    skill = get_skill(name)
    if not skill:
        return {"status": "error", "error": f"skill '{name}' not found"}

    result = {
        "status": "ok",
        "skill_name": skill.name,
        "description": skill.description,
        "instructions": skill.instructions,
        "use_when": skill.use_when,
        "tags": skill.tags,
    }

    # Include script listings if available
    if skill.has_scripts and skill.scripts_path:
        scripts = [p.name for p in skill.scripts_path.iterdir() if p.is_file()]
        result["scripts"] = scripts

    if skill.has_templates and skill.templates_path:
        templates = [p.name for p in skill.templates_path.iterdir() if p.is_file()]
        result["templates"] = templates

    return result


def search_skills(query: str) -> list[dict[str, Any]]:
    """Simple keyword search across skill names, descriptions, and instructions."""
    with _registry_lock:
        if not _registry:
            reload_skills()
        snapshot = list(_registry.values())
    q = query.lower()
    results = []
    for skill in snapshot:
        if (q in skill.name.lower()
                or q in skill.description.lower()
                or q in skill.use_when.lower()
                or q in skill.instructions.lower()[:500]):  # only search first 500 chars
            results.append({
                "name": skill.name,
                "description": skill.description,
                "use_when": skill.use_when,
                "tags": skill.tags,
                "match": "name" if q in skill.name.lower() else "description/instructions",
            })
    return sorted(results, key=lambda s: s["name"])


def build_skill_engine_surface() -> dict[str, Any]:
    """Mission Control surface."""
    with _registry_lock:
        if not _registry:
            reload_skills()
        snapshot = list(_registry.values())
    all_tags: set[str] = set()
    for s in snapshot:
        all_tags.update(s.tags)
    return {
        "active": len(_registry) > 0,
        "skill_count": len(_registry),
        "skills": list_skills(),
        "all_tags": sorted(all_tags),
        "skills_root": str(SKILLS_ROOT),
        "summary": f"{len(_registry)} skills loaded from {SKILLS_ROOT}",
    }


# ── Audit trail (C1 — Skills versionering) ────────────────────────────

AUDIT_ACTIONS = ("created", "updated", "deleted", "bulk_reloaded")


def _ensure_audit_table() -> None:
    """Idempotent: ensure skill_audit_log table exists."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    diff_summary TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    snapshot_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_skill_audit_log_name
                ON skill_audit_log(skill_name, id DESC)
                """
            )
    except Exception as exc:
        logger.warning("skill_engine: audit table ensure failed: %s", exc)


def _build_skill_snapshot(name: str) -> dict[str, Any]:
    """Build a portable snapshot dict for a skill."""
    skill = get_skill(name)
    if not skill:
        return {}
    return {
        "name": skill.name,
        "description": skill.description,
        "use_when": skill.use_when,
        "tags": list(skill.tags),
        "instructions_len": len(skill.instructions),
        "instructions_preview": skill.instructions[:200],
        "has_scripts": skill.has_scripts,
        "has_templates": skill.has_templates,
        "has_references": skill.has_references,
    }


def _record_audit_entry(
    skill_name: str,
    action: str,
    *,
    diff_summary: str = "",
    reason: str = "",
    snapshot: dict[str, Any] | None = None,
) -> None:
    """Record a skill mutation in the audit log. Never raises."""
    if action not in AUDIT_ACTIONS:
        logger.warning("skill_engine: unknown audit action '%s' — skipping", action)
        return
    try:
        import json as _json
        from core.runtime.db import connect
        from datetime import UTC, datetime
        snap = _json.dumps(snapshot or {}, ensure_ascii=False)
        with connect() as conn:
            # Self-healing: ensure table exists if init_db hasn't run yet
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    diff_summary TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    snapshot_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO skill_audit_log
                    (skill_name, action, diff_summary, reason, snapshot_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (skill_name, action, diff_summary, reason, snap, datetime.now(UTC).isoformat()),
            )
    except Exception as exc:
        logger.warning("skill_engine: audit log failed for %s/%s: %s", skill_name, action, exc)


def get_skill_history(name: str, limit: int = 50) -> dict[str, Any]:
    """Return audit trail for a single skill, newest first."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            # Self-healing: ensure table
            conn.execute(
                "CREATE TABLE IF NOT EXISTS skill_audit_log ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, skill_name TEXT NOT NULL,"
                "action TEXT NOT NULL, diff_summary TEXT NOT NULL DEFAULT '',"
                "reason TEXT NOT NULL DEFAULT '', snapshot_json TEXT NOT NULL DEFAULT '{}',"
                "created_at TEXT NOT NULL)"
            )
            rows = conn.execute(
                """
                SELECT id, skill_name, action, diff_summary, reason, snapshot_json, created_at
                FROM skill_audit_log
                WHERE skill_name = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (name, max(limit, 1)),
            ).fetchall()
        import json as _json
        entries = []
        for r in rows:
            entry = dict(r)
            try:
                entry["snapshot"] = _json.loads(entry.pop("snapshot_json", "{}"))
            except Exception:
                entry["snapshot"] = {}
            entries.append(entry)
        return {"status": "ok", "skill_name": name, "entries": entries, "count": len(entries)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def list_recent_skill_changes(limit: int = 20) -> dict[str, Any]:
    """Return most recent skill mutations across all skills."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS skill_audit_log ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, skill_name TEXT NOT NULL,"
                "action TEXT NOT NULL, diff_summary TEXT NOT NULL DEFAULT '',"
                "reason TEXT NOT NULL DEFAULT '', snapshot_json TEXT NOT NULL DEFAULT '{}',"
                "created_at TEXT NOT NULL)"
            )
            rows = conn.execute(
                """
                SELECT id, skill_name, action, diff_summary, reason, created_at
                FROM skill_audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(limit, 1),),
            ).fetchall()
        return {"status": "ok", "entries": [dict(r) for r in rows], "count": len(rows)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def update_skill(
    name: str,
    *,
    description: str | None = None,
    instructions: str | None = None,
    use_when: str | None = None,
    tags: list[str] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    """Update an existing skill's metadata and/or instructions. Logs audit."""
    skill = get_skill(name)
    if not skill:
        return {"status": "error", "error": f"skill '{name}' not found"}

    old_snapshot = _build_skill_snapshot(name)
    changes: list[str] = []

    new_description = description if description is not None else skill.description
    new_use_when = use_when if use_when is not None else skill.use_when
    new_tags = list(tags) if tags is not None else list(skill.tags)
    new_instructions = instructions if instructions is not None else skill.instructions

    if new_description != skill.description:
        changes.append(f"description: {len(skill.description)}ch → {len(new_description)}ch")
    if new_use_when != skill.use_when:
        changes.append("use_when changed")
    if new_tags != list(skill.tags):
        changes.append(f"tags: {len(skill.tags)} → {len(new_tags)}")
    if new_instructions != skill.instructions:
        changes.append(f"instructions: {len(skill.instructions)}ch → {len(new_instructions)}ch")

    if not changes:
        return {"status": "ok", "name": name, "note": "No changes detected."}

    # Validate with same rules as create
    validation = validate_skill_proposal(
        name=name,
        description=new_description,
        instructions=new_instructions,
        use_when=new_use_when,
        tags=new_tags,
    )
    if validation.get("status") != "ok" and "already exists" not in validation.get("error", ""):
        # "already exists" is expected — we're updating an existing skill
        return validation

    # Write new SKILL.md
    try:
        skill_dir = SKILLS_ROOT / name
        fm_data = {
            "name": name,
            "description": new_description,
            "use_when": new_use_when or new_description,
            "tags": list(new_tags),
        }
        if _yaml is not None:
            fm_body = _yaml.safe_dump(
                fm_data, sort_keys=False, allow_unicode=True, default_flow_style=False
            )
        else:
            def _q(s): return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'
            fm_body = (
                f"name: {_q(name)}\n"
                f"description: {_q(new_description)}\n"
                f"use_when: {_q(new_use_when or new_description)}\n"
                f"tags: [{', '.join(_q(t) for t in new_tags)}]\n"
            )
        fm = f"---\n{fm_body}---\n\n"
        content = fm + new_instructions.strip() + "\n"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"status": "error", "error": f"write failed: {exc}"}

    # Reload + audit
    reload_skills()
    diff = "; ".join(changes)
    _record_audit_entry(
        name, "updated",
        diff_summary=diff,
        reason=reason,
        snapshot=_build_skill_snapshot(name),
    )
    return {
        "status": "ok",
        "name": name,
        "changes": changes,
        "note": f"Skill '{name}' updated: {diff}",
    }


def _emit_skill_engine_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event for cartographer observability.

    State-mutation points in this module can call this with a transition
    kind ("created", "updated", "transitioned", etc.). Defensive — never
    blocks the caller. Added 2026-05-13 (top-18 cartographer pass).
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"skill_engine.{kind}", payload or {})
    except Exception:
        pass

