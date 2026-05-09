"""Skill Engine tools — Jarvis skill system.

Tools for listing, invoking, creating, editing, and deleting skills.
Wraps core/services/skill_engine.py.

Skills are SKILL.md directories compatible with Claude Code and OpenClaw.
"""
from __future__ import annotations

from typing import Any

from core.services import skill_engine


def _exec_skill_list(args: dict[str, Any]) -> dict[str, Any]:
    """List all loaded skills, optionally filtered by tag."""
    tag = args.get("tag") or None
    if tag:
        tag = str(tag).strip()
    skills = skill_engine.list_skills(tag=tag)
    return {
        "status": "ok",
        "count": len(skills),
        "skills": skills,
    }


def _exec_skill_invoke(args: dict[str, Any]) -> dict[str, Any]:
    """Get a skill's instructions for prompt injection."""
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    result = skill_engine.get_skill_instructions(name)
    if result.get("status") == "error":
        return result
    return {
        "status": "ok",
        "skill": result,
        "note": (
            f"Skill '{name}' loaded. Instructions injected into context. "
            f"Use its instructions as guidance for the current task."
        ),
    }


def _exec_skill_create(args: dict[str, Any]) -> dict[str, Any]:
    """Create a new skill on disk."""
    name = str(args.get("name") or "").strip()
    description = str(args.get("description") or "").strip()
    instructions = str(args.get("instructions") or "").strip()
    use_when = str(args.get("use_when") or "").strip()
    raw_tags = args.get("tags")
    tags = []
    if raw_tags:
        if isinstance(raw_tags, list):
            tags = [str(t).strip() for t in raw_tags if str(t).strip()]
        elif isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
    return skill_engine.create_skill(
        name=name,
        description=description,
        instructions=instructions,
        use_when=use_when,
        tags=tags,
    )


def _exec_skill_delete(args: dict[str, Any]) -> dict[str, Any]:
    """Delete a skill from disk."""
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    return skill_engine.delete_skill(name)


def _exec_skill_search(args: dict[str, Any]) -> dict[str, Any]:
    """Search skills by keyword."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}
    results = skill_engine.search_skills(query)
    return {
        "status": "ok",
        "count": len(results),
        "results": results,
    }


def _exec_skill_get(args: dict[str, Any]) -> dict[str, Any]:
    """Get full detail on a single skill."""
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    skill = skill_engine.get_skill(name)
    if not skill:
        return {"status": "error", "error": f"skill '{name}' not found"}
    return {
        "status": "ok",
        "skill": {
            "name": skill.name,
            "description": skill.description,
            "use_when": skill.use_when,
            "tags": skill.tags,
            "instructions": skill.instructions,
            "frontmatter": skill.frontmatter,
            "path": str(skill.path) if skill.path else None,
            "has_scripts": skill.has_scripts,
            "has_templates": skill.has_templates,
            "has_references": skill.has_references,
            "loaded_at": skill.loaded_at,
        },
    }


def _exec_skill_reload(args: dict[str, Any]) -> dict[str, Any]:
    """Force-reload all skills from disk."""
    return skill_engine.reload_skills()


# ── Tool definitions ───────────────────────────────────────────────────

SKILL_ENGINE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "skill_list",
            "description": (
                "List all installed skills. Optionally filter by tag. "
                "Skills are SKILL.md directories compatible with Claude Code and OpenClaw."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Optional tag filter, e.g. 'web', 'pdf', 'analysis'",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_get",
            "description": "Get full detail on a single skill including its instructions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name (folder name, lowercase).",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_invoke",
            "description": (
                "Load a skill's instructions into your context. "
                "Use this when you want to activate a skill's knowledge for the current task. "
                "The skill's instructions become available as guidance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name to invoke.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_create",
            "description": (
                "Create a new skill. Requires a name (lowercase, kebab-case), "
                "description, and instructions. Optionally: use_when trigger text "
                "and tags. Creates SKILL.md in ~/.jarvis-v2/skills/<name>/."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique skill name. Lowercase, kebab-case, e.g. 'pdf-extract'.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Short description of what the skill does.",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Full markdown instructions for the skill. This is what gets injected when invoked.",
                    },
                    "use_when": {
                        "type": "string",
                        "description": "Optional natural-language trigger, e.g. 'when the user asks to extract text from a PDF'.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for organization, e.g. ['web', 'scraping'].",
                    },
                },
                "required": ["name", "description", "instructions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_delete",
            "description": "Permanently delete a skill and all its files from disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name to delete.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_search",
            "description": "Search across all skill names, descriptions, and instructions by keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword to search for.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_reload",
            "description": "Force-reload all skills from disk. Use after adding skills manually.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# ── Handler map ────────────────────────────────────────────────────────

SKILL_ENGINE_TOOL_HANDLERS: dict[str, Any] = {
    "skill_list": _exec_skill_list,
    "skill_get": _exec_skill_get,
    "skill_invoke": _exec_skill_invoke,
    "skill_create": _exec_skill_create,
    "skill_delete": _exec_skill_delete,
    "skill_search": _exec_skill_search,
    "skill_reload": _exec_skill_reload,
}
