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

import json
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


def create_skill(
    name: str,
    description: str,
    instructions: str,
    use_when: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new skill directory with SKILL.md on disk."""
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
