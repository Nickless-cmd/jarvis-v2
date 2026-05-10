"""Skill Engine tools — Jarvis skill system.

Tools for listing, invoking, creating, editing, and deleting skills.
Wraps core/services/skill_engine.py.

Skills are SKILL.md directories compatible with Claude Code and OpenClaw.
"""
from __future__ import annotations

import logging
from typing import Any

from core.services import skill_engine
from core.services.skill_security_scanner import (
    format_scan_report,
    scan_skill_file,
    ScanResult,
)
from pathlib import Path as _Path
from core.tools.skill_import_scanner import scan_skill_directory

logger = logging.getLogger(__name__)

# ── Intent matching (Fase 4) ──────────────────────────────────────────

_INTENT_MATCH_THRESHOLD_DEFAULT = 0.15
_INTENT_MATCH_MAX_SUGGESTIONS = 3


def _suggest_skills_for_query(
    query: str,
    threshold: float = _INTENT_MATCH_THRESHOLD_DEFAULT,
    max_results: int = _INTENT_MATCH_MAX_SUGGESTIONS,
) -> list[dict[str, Any]]:
    """Match a user query against all installed skills' use_when + description.

    Uses hf_embed (sentence-transformers/all-MiniLM-L6-v2) for semantic
    similarity. Returns skills scoring above threshold, ranked by score.
    """
    skills = skill_engine.list_skills()
    if not skills:
        return []

    # Build candidate strings: "use_when: <text> description: <text> name: <name>"
    # Prioritise use_when as the primary match target
    skill_texts: list[tuple[str, str]] = []  # (skill_name, combined_text)
    for s in skills:
        parts = []
        if s.get("use_when"):
            parts.append(f"use_when: {s['use_when']}")
        if s.get("description"):
            parts.append(f"description: {s['description']}")
        if s.get("name"):
            parts.append(f"name: {s['name']}")
        combined = " | ".join(parts)
        skill_texts.append((s["name"], combined))

    if not skill_texts:
        return []

    candidates = [text for _, text in skill_texts]

    try:
        from core.tools.hf_inference_tools import semantic_similarity
        result = semantic_similarity(
            source=query,
            candidates=candidates,
        )
    except Exception as exc:
        logger.warning("skill_suggest: semantic_similarity failed: %s", exc)
        return []

    if result.get("status") != "ok":
        return []

    ranked = result.get("ranked", [])
    suggestions = []
    for r in ranked:
        score = r.get("score", 0.0)
        if score < threshold:
            continue
        idx = candidates.index(r["candidate"])  # find which skill this is
        skill_name = skill_texts[idx][0]
        suggestions.append({
            "name": skill_name,
            "score": round(score, 4),
            "candidate": r["candidate"][:120],
        })

    return suggestions[:max_results]


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


def _exec_skill_suggest(args: dict[str, Any]) -> dict[str, Any]:
    """Suggest skills relevant to a user query via semantic matching."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}
    threshold = args.get("threshold", _INTENT_MATCH_THRESHOLD_DEFAULT)
    if isinstance(threshold, (int, float)):
        threshold = float(threshold)
    else:
        threshold = _INTENT_MATCH_THRESHOLD_DEFAULT
    max_results = args.get("max_results", _INTENT_MATCH_MAX_SUGGESTIONS)
    if isinstance(max_results, int):
        max_results = min(max(max_results, 1), 10)
    else:
        max_results = _INTENT_MATCH_MAX_SUGGESTIONS

    suggestions = _suggest_skills_for_query(
        query=query,
        threshold=threshold,
        max_results=max_results,
    )
    return {
        "status": "ok",
        "query": query,
        "threshold": threshold,
        "count": len(suggestions),
        "suggestions": suggestions,
        "note": (
            f"Found {len(suggestions)} skill matches. "
            f"Call skill_invoke on one to activate it."
        ) if suggestions else "No skills matched the query — try a lower threshold or create one.",
    }


# ── Import (Fase 5) ────────────────────────────────────────────────────

def _exec_skill_import(args: dict[str, Any]) -> dict[str, Any]:
    """Import a skill from a local path (directory or zip archive).

    Supports:
    - A directory containing SKILL.md (Claude Code / OpenClaw format)
    - A .zip archive containing a skill directory with SKILL.md
    - A GitHub-style 'user/repo' shorthand (fetches from GitHub)
    """
    source = str(args.get("source") or "").strip()
    if not source:
        return {"status": "error", "error": "source is required — path to directory, .zip, or 'user/repo'"}

    name_override = str(args.get("name") or "").strip()

    from pathlib import Path
    import shutil
    import tempfile
    import zipfile

    src_path = Path(source).expanduser()
    is_zip = source.endswith(".zip") or (src_path.is_file() and source.endswith(".zip"))

    # Determine skill directory
    skill_dir = None
    temp_dir = None  # track for cleanup

    try:
        if is_zip:
            # Extract zip to temp
            temp_dir = Path(tempfile.mkdtemp(prefix="skill_import_"))
            with zipfile.ZipFile(src_path, "r") as zf:
                zf.extractall(temp_dir)
            # Find SKILL.md in extracted contents
            skill_dir = _find_skill_dir_in_tree(temp_dir)
            if not skill_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return {"status": "error", "error": "no SKILL.md found in zip archive"}
        elif src_path.is_dir():
            skill_dir = src_path
        elif src_path.is_file() and src_path.name.upper() == "SKILL.MD":
            skill_dir = src_path.parent
        else:
            return {"status": "error", "error": f"source not found: {source}"}

        # Verify SKILL.md exists
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            skill_md = skill_dir / "skill.md"
        if not skill_md.exists():
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {"status": "error", "error": f"no SKILL.md in {skill_dir}"}

        # ── Security scan ──────────────────────────────────────────
        scan_result = scan_skill_directory(skill_dir)
        if scan_result.get("status") == "error":
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "status": "error",
                "error": f"skill scanner failed: {scan_result.get('error')}",
            }

        if scan_result["risk"] == "critical":
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "status": "error",
                "error": "IMPORT BLOCKED — critical security risk",
                "scan_result": scan_result,
                "verdict": scan_result["verdict"],
                "findings": scan_result["findings"],
                "hint": "This skill contains malware patterns. Do not import.",
            }

        if scan_result["risk"] in ("high", "medium"):
            # Return scan result for user review — import can proceed
            # but user sees warnings. We still continue the import.
            pass

        # Parse to validate and get name
        parsed = skill_engine._parse_skill_md(skill_md)
        if not parsed:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {"status": "error", "error": f"failed to parse {skill_md}"}

        target_name = name_override or parsed.name
        target_dir = skill_engine.SKILLS_ROOT / target_name

        if target_dir.exists():
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "status": "error",
                "error": f"skill '{target_name}' already exists",
                "existing_path": str(target_dir),
                "hint": "pass name=<alias> to import under a different name, or delete the existing skill first",
            }

        # Copy skill tree
        shutil.copytree(skill_dir, target_dir, dirs_exist_ok=False)

        # Verify copy
        copied_md = target_dir / "SKILL.md"
        if not copied_md.exists():
            copied_md = target_dir / "skill.md"
        if not copied_md.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
            return {"status": "error", "error": "copy verification failed"}

    except Exception as exc:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return {"status": "error", "error": f"import failed: {exc}"}

    # Cleanup temp
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Reload skills
    reload_result = skill_engine.reload_skills()

    # Collect details
    imported = skill_engine.get_skill(target_name)
    details = {}
    if imported:
        details = {
            "name": imported.name,
            "description": imported.description,
            "use_when": imported.use_when,
            "tags": imported.tags,
            "has_scripts": imported.has_scripts,
            "has_templates": imported.has_templates,
            "has_references": imported.has_references,
        }

    result = {
        "status": "ok",
        "name": target_name,
        "path": str(target_dir),
        "source": source,
        "details": details,
        "skills_loaded": reload_result.get("count", 0),
        "note": f"Skill '{target_name}' imported successfully from {source}",
    }

    # Include scan findings if any were found
    if scan_result["risk"] in ("high", "medium"):
        result["scan_warning"] = True
        result["scan_risk"] = scan_result["risk"]
        result["scan_severity"] = scan_result["severity_score"]
        result["scan_findings"] = scan_result["findings"]
        result["scan_verdict"] = scan_result["verdict"]
        result["note"] += (
            f"\n⚠️  Scanner fandt {scan_result['finding_count']} issue(s) "
            f"(risk: {scan_result['risk']}, score: {scan_result['severity_score']}). "
            f"{scan_result['verdict']}"
        )

    return result


def _find_skill_dir_in_tree(root: Path) -> Path | None:
    """Walk a directory tree and find the first directory containing SKILL.md."""
    for child in sorted(root.iterdir()):
        if child.is_dir():
            if (child / "SKILL.md").exists() or (child / "skill.md").exists():
                return child
            # Recurse one level for common zip structures
            for sub in sorted(child.iterdir()):
                if sub.is_dir() and ((sub / "SKILL.md").exists() or (sub / "skill.md").exists()):
                    return sub
    # Check root itself
    if (root / "SKILL.md").exists() or (root / "skill.md").exists():
        return root
    return None


def _exec_skill_import_from_url(args: dict[str, Any]) -> dict[str, Any]:
    """Import a skill from a remote URL (GitHub raw, ClawHub, or any SKILL.md URL).

    Supports:
    - Raw SKILL.md URL: https://raw.githubusercontent.com/.../SKILL.md
    - GitHub shorthand: 'user/repo' (fetches from GitHub)
    - ClawHub URL: https://clawhub.com/... (tbd)
    - Generic URL pointing to a skill directory or SKILL.md
    """
    url = str(args.get("url") or "").strip()
    if not url:
        return {"status": "error", "error": "url is required"}

    import urllib.request
    import tempfile
    from pathlib import Path

    name_override = str(args.get("name") or "").strip()
    temp_dir = Path(tempfile.mkdtemp(prefix="skill_url_import_"))

    try:
        # Handle GitHub shorthand: user/repo
        if "/" in url and not url.startswith(("http://", "https://")):
            parts = url.split("/")
            if len(parts) == 2:
                # Try to fetch SKILL.md from GitHub (try main, then master)
                import urllib.error
                for branch in ("main", "master"):
                    github_url = (
                        f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/{branch}/SKILL.md"
                    )
                    try:
                        req = urllib.request.Request(
                            github_url,
                            headers={"User-Agent": "Jarvis-v2/1.0"},
                        )
                        with urllib.request.urlopen(req, timeout=15) as resp:
                            status = resp.status
                            if status == 200:
                                content = resp.read().decode("utf-8")
                                break
                    except urllib.error.HTTPError:
                        continue
                else:
                    # Neither branch worked — return error, don't fall through
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return {
                        "status": "error",
                        "error": f"GitHub user/repo '{url}' not found (checked main + master branches)",
                    }

                # It's a single SKILL.md, infer name from repo
                inferred_name = name_override or parts[1]
                skill_dir = temp_dir / inferred_name
                skill_dir.mkdir(parents=True, exist_ok=True)
                (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
                # Create empty subdirs
                (skill_dir / "scripts").mkdir(exist_ok=True)
                (skill_dir / "templates").mkdir(exist_ok=True)
                (skill_dir / "references").mkdir(exist_ok=True)
                # Now import this directory
                import shutil as shutil2
                target_name = inferred_name
                target_dir = skill_engine.SKILLS_ROOT / target_name
                if target_dir.exists():
                    shutil2.rmtree(temp_dir, ignore_errors=True)
                    return {"status": "error", "error": f"skill '{target_name}' already exists"}

                # ── Security pre-scan ──
                scan_result = scan_skill_file(skill_dir / "SKILL.md")
                if scan_result and scan_result.has_critical:
                    shutil2.rmtree(temp_dir, ignore_errors=True)
                    return {
                        "status": "error",
                        "error": f"SECURITY BLOCKED: skill '{target_name}' has critical security issues",
                        "security_scan": {
                            "findings": [
                                {
                                    "pattern": f.pattern_name,
                                    "description": f.description,
                                    "severity_label": "CRITICAL",
                                    "line": f.line_number,
                                    "match": f.match_text[:120],
                                }
                                for f in scan_result.findings
                                if f.severity >= 7
                            ],
                        },
                    }

                shutil2.copytree(skill_dir, target_dir, dirs_exist_ok=False)
                skill_engine.reload_skills()
                imported = skill_engine.get_skill(target_name)
                shutil2.rmtree(temp_dir, ignore_errors=True)
                return {
                    "status": "ok",
                    "name": target_name,
                    "path": str(target_dir),
                    "source": url,
                    "details": {
                        "name": imported.name if imported else target_name,
                        "description": imported.description if imported else "",
                        "use_when": imported.use_when if imported else "",
                        "tags": imported.tags if imported else [],
                    } if imported else {},
                    "note": f"Skill '{target_name}' imported from GitHub {url}",
                }

        # Generic URL fetch — try to get a SKILL.md
        req = urllib.request.Request(url, headers={"User-Agent": "Jarvis-v2/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read().decode("utf-8")
        except Exception as exc:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {"status": "error", "error": f"failed to fetch URL: {exc}"}

        # Check if it's valid SKILL.md
        if "name:" not in content[:500] and "---" not in content[:500]:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "status": "error",
                "error": "URL does not appear to be a SKILL.md file (no frontmatter detected)",
            }

        # Infer name from URL or use override
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        inferred_name = name_override or Path(parsed_url.path).stem.lower().replace("_", "-")

        import shutil
        skill_dir = temp_dir / inferred_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "templates").mkdir(exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)

        # ── Security pre-scan ──
        scan_result = scan_skill_file(skill_dir / "SKILL.md")
        if scan_result and scan_result.has_critical:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "status": "error",
                "error": f"SECURITY BLOCKED: skill '{inferred_name}' has critical security issues",
                "security_scan": {
                    "findings": [
                        {
                            "pattern": f.pattern_name,
                            "description": f.description,
                            "severity_label": "CRITICAL",
                            "line": f.line_number,
                            "match": f.match_text[:120],
                        }
                        for f in scan_result.findings
                        if f.severity >= 7
                    ],
                },
            }

        target_name = inferred_name
        target_dir = skill_engine.SKILLS_ROOT / target_name
        if target_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {"status": "error", "error": f"skill '{target_name}' already exists"}
        shutil.copytree(skill_dir, target_dir, dirs_exist_ok=False)
        skill_engine.reload_skills()
        imported = skill_engine.get_skill(target_name)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {
            "status": "ok",
            "name": target_name,
            "path": str(target_dir),
            "source": url,
            "details": {
                "name": imported.name if imported else target_name,
                "description": imported.description if imported else "",
                "use_when": imported.use_when if imported else "",
                "tags": imported.tags if imported else [],
            } if imported else {},
            "note": f"Skill '{target_name}' imported from {url}",
        }

    except Exception as exc:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"status": "error", "error": f"import from URL failed: {exc}"}


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
    # ── Fase 4: Intent matching ──────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "skill_suggest",
            "description": (
                "Semantic search across all installed skills by matching a user query "
                "against each skill's use_when and description. Uses sentence-transformers "
                "embeddings via HF free tier. Returns skills ranked by relevance score."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User's message or request to match against skills.",
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Minimum similarity score (0.0-1.0). Default 0.55. Lower = more suggestions.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max suggestions to return (1-10, default 3).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    # ── Fase 5: Import ───────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "skill_import",
            "description": (
                "Import a skill from a local path or zip archive. Supports: "
                "directory containing SKILL.md (Claude Code / OpenClaw format), "
                ".zip archive, or a single SKILL.md file. Copies the skill tree "
                "to ~/.jarvis-v2/skills/<name>/."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Path to directory, .zip file, or SKILL.md file.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional override name. Default: folder name from SKILL.md.",
                    },
                },
                "required": ["source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_import_from_url",
            "description": (
                "Import a skill from a remote URL. Supports: GitHub raw SKILL.md URLs, "
                "GitHub 'user/repo' shorthand (fetches from main branch), and generic "
                "URLs pointing to SKILL.md content. Downloads, validates, and installs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to SKILL.md, skill directory, or GitHub shorthand (user/repo).",
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional override name. Default: inferred from URL or SKILL.md.",
                    },
                },
                "required": ["url"],
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
    # Fase 4
    "skill_suggest": _exec_skill_suggest,
    # Fase 5
    "skill_import": _exec_skill_import,
    "skill_import_from_url": _exec_skill_import_from_url,
}
