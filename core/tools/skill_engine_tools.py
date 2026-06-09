"""Skill Engine tools — Jarvis skill system.

Tools for listing, invoking, creating, editing, and deleting skills.
Wraps core/services/skill_engine.py.

Skills are SKILL.md directories compatible with Claude Code and OpenClaw.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from core.runtime.settings import load_settings
from core.services import skill_engine
from core.services.skill_security_scanner import (
    scan_skill_directory,
    scan_skill_file,
)
logger = logging.getLogger(__name__)

# ── Intent matching (Fase 4) ──────────────────────────────────────────

_INTENT_MATCH_THRESHOLD_DEFAULT = 0.30
_INTENT_MATCH_MAX_SUGGESTIONS = 3


def _split_bilingual_use_when(text: str) -> list[str]:
    """Split a use_when block into separate language fragments.

    Skill frontmatters often hold both DA and EN trigger lists in one
    multi-line use_when (e.g. `EN: …\n…\nDA: …\n…`). When we embed the
    whole block as one candidate, mixing two languages dilutes the
    similarity score for monolingual queries — an EN-only query gets
    pulled toward the DA half. Splitting yields per-language candidates
    so the max-aggregator below picks the right half.
    """
    if not text:
        return []
    # Strip the language tag at the start of each section if present.
    # Tags we recognize: "EN:", "DA:", "DK:", "ENG:", "DAN:" — case-insensitive.
    chunks: list[str] = []
    current: list[str] = []
    tag_re = re.compile(r"^\s*(EN|DA|DK|ENG|DAN)\s*:", re.IGNORECASE)
    for line in text.splitlines():
        if tag_re.match(line):
            if current:
                chunks.append("\n".join(current).strip())
            current = [tag_re.sub("", line, count=1).strip()]
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current).strip())
    # Filter empties; if no language tags were found, fall back to one chunk.
    chunks = [c for c in chunks if c]
    return chunks or ([text.strip()] if text.strip() else [])


def _suggest_skills_for_query(
    query: str,
    threshold: float = _INTENT_MATCH_THRESHOLD_DEFAULT,
    max_results: int = _INTENT_MATCH_MAX_SUGGESTIONS,
    context_tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Match a user query against all installed skills' use_when + description.

    For each skill, builds *multiple* candidate strings — split bilingual
    use_when into per-language fragments + description fragment + the
    raw skill name — and runs semantic_similarity once over the combined
    pool. Then takes the *max* score per skill.

    Why max-aggregation: a monolingual query (e.g. pure English "fact-check
    this article") gets diluted when the candidate concatenates both DA
    and EN trigger lines. Splitting + max means the EN-only fragment
    competes alone and scores cleanly.

    Uses hf_embed (sentence-transformers/all-MiniLM-L6-v2) for similarity.
    Returns skills scoring above threshold, ranked by score.

    If context_tags is provided, only skills whose tags contain at least
    one of the context tags (case-insensitive) are considered. This lets
    skill_gate pre-filter by domain/context before semantic matching.
    """
    skills = skill_engine.list_skills()
    if not skills:
        return []

    # ── Context tag pre-filter (C2 — Skills meta-tags) ──────────────
    if context_tags:
        context_tags_lower = [t.strip().lower() for t in context_tags if t.strip()]
        if context_tags_lower:
            filtered: list[dict[str, Any]] = []
            for s in skills:
                skill_tags = [t.lower() for t in (s.get("tags") or [])]
                if any(ct in skill_tags for ct in context_tags_lower):
                    filtered.append(s)
            skills = filtered
            if not skills:
                return []

    # candidate_text -> skill_name (stable; index-based mapping breaks if
    # two skills happen to share a candidate string)
    cand_to_skill: list[tuple[str, str]] = []  # [(candidate_text, skill_name), …]
    for s in skills:
        name = s["name"]
        for fragment in _split_bilingual_use_when(s.get("use_when") or ""):
            cand_to_skill.append((f"use_when: {fragment}", name))
        if s.get("description"):
            cand_to_skill.append((f"description: {s['description']}", name))
        cand_to_skill.append((f"skill name: {name}", name))

    if not cand_to_skill:
        return []

    candidates = [c for c, _ in cand_to_skill]

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

    # Aggregate to per-skill max score. A skill wins via its single best
    # fragment, not via the average of all fragments.
    best_per_skill: dict[str, dict[str, Any]] = {}
    cand_lookup = {cand: skill for cand, skill in cand_to_skill}
    for r in result.get("ranked", []):
        cand = r.get("candidate", "")
        score = float(r.get("score") or 0.0)
        skill_name = cand_lookup.get(cand)
        if not skill_name:
            continue
        existing = best_per_skill.get(skill_name)
        if existing is None or score > existing["score"]:
            best_per_skill[skill_name] = {
                "name": skill_name,
                "score": round(score, 4),
                "candidate": cand[:120],
            }

    suggestions = sorted(
        (s for s in best_per_skill.values() if s["score"] >= threshold),
        key=lambda s: s["score"],
        reverse=True,
    )
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
    # Emit invocation event for dead-skill detection (2026-05-13).
    # Tool Invention adoption-tracking needs to know which skills are
    # actually used after install. Without this, we can't tell an "active"
    # installed skill from dead weight.
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("cognitive_state.skill_invoked", {"name": name})
    except Exception:
        pass
    return {
        "status": "ok",
        "skill": result,
        "note": (
            f"Skill '{name}' loaded. Instructions injected into context. "
            f"Use its instructions as guidance for the current task."
        ),
    }


def _exec_propose_new_skill(args: dict[str, Any]) -> dict[str, Any]:
    """Propose a new skill via the plan-approval flow.

    Validates the proposal up front. If validation fails, returns the
    error to the caller. If validation passes, creates a plan with the
    skill_data payload; when the plan is approved, the install hook
    automatically calls create_skill().
    """
    try:
        if not bool(load_settings().tool_invention_enabled):
            return {"status": "error", "error": "tool_invention disabled"}
    except Exception:
        pass  # fail-open if settings broken

    name = str(args.get("name") or "")
    description = str(args.get("description") or "")
    instructions = str(args.get("instructions") or "")
    use_when = str(args.get("use_when") or "") or description
    tags = list(args.get("tags") or [])

    validation = skill_engine.validate_skill_proposal(
        name=name,
        description=description,
        instructions=instructions,
        use_when=use_when,
        tags=tags,
    )
    if validation.get("status") != "ok":
        return validation

    # Use the normalized name from validation (it lowercases + space→hyphen)
    normalized_name = str(validation.get("name") or name)
    quality_nudges = list(validation.get("quality_nudges") or [])
    quality_score = validation.get("quality_score")

    from core.services.plan_proposals import propose_plan
    result = propose_plan(
        session_id=args.get("session_id"),
        title=f"Ny skill: {normalized_name}",
        why=description,
        steps=[f"Install skill '{normalized_name}' (auto on approval)"],
        skill_data={
            "name": normalized_name,
            "description": description,
            "instructions": instructions,
            "use_when": use_when,
            "tags": tags,
            "quality_nudges": quality_nudges,
            "quality_score": quality_score,
        },
    )
    if result.get("status") == "ok":
        result["quality_nudges"] = quality_nudges
        result["quality_score"] = quality_score
    if result.get("status") == "ok":
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "cognitive_state.skill_proposed",
                {
                    "plan_id": result.get("plan_id"),
                    "name": normalized_name,
                },
            )
        except Exception:
            pass
    return result


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


# ── URL fetch + install helpers (used by skill_import_from_url) ──────

# Hard cap on remote SKILL.md size — defense against OOM via malicious URL.
# A real Claude Code skill is typically 2-30 KB; 500 KB is a generous ceiling.
_MAX_URL_FETCH_BYTES = 500_000


def _fetch_url_capped(url: str, *, timeout: int = 30) -> tuple[str | None, str | None]:
    """Fetch a URL, capped at _MAX_URL_FETCH_BYTES. Returns (content, error)."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Jarvis-v2/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # Read +1 byte over the cap so we can detect oversize responses.
            raw = resp.read(_MAX_URL_FETCH_BYTES + 1)
        if len(raw) > _MAX_URL_FETCH_BYTES:
            return None, (
                f"response exceeds {_MAX_URL_FETCH_BYTES} byte cap — refusing "
                "to import. Skills should be tiny markdown files; oversize "
                "content is suspicious."
            )
        try:
            return raw.decode("utf-8"), None
        except UnicodeDecodeError:
            # Try latin-1 as graceful fallback (rare but legitimate for some
            # non-UTF8 markdown). Still safe — content is text-scanned.
            return raw.decode("utf-8", errors="replace"), None
    except Exception as exc:
        return None, f"fetch failed: {exc}"


def _install_skill_md_content(
    *,
    content: str,
    target_name: str,
    source_label: str,
) -> dict[str, Any]:
    """Stage SKILL.md content in a tempdir, scan, copy to skills root, reload.

    Returns the import-result dict (success or scan-blocked error).
    Caller is responsible for not passing oversize content (we still cap
    defensively).
    """
    import shutil
    import tempfile
    from pathlib import Path

    if len(content.encode("utf-8")) > _MAX_URL_FETCH_BYTES:
        return {
            "status": "error",
            "error": f"SKILL.md content exceeds {_MAX_URL_FETCH_BYTES} byte cap",
        }
    if "name:" not in content[:500] and "---" not in content[:500]:
        return {
            "status": "error",
            "error": "content does not appear to be a SKILL.md file (no frontmatter detected)",
        }

    temp_dir = Path(tempfile.mkdtemp(prefix="skill_install_"))
    try:
        skill_dir = temp_dir / target_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "templates").mkdir(exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)

        target_dir = skill_engine.SKILLS_ROOT / target_name
        if target_dir.exists():
            return {
                "status": "error",
                "error": f"skill '{target_name}' already exists",
                "existing_path": str(target_dir),
            }

        # Security pre-scan via canonical scanner (covers SKILL.md only here
        # since scripts/ is empty for URL installs — directory scan would
        # produce identical results).
        scan_result = scan_skill_file(skill_dir / "SKILL.md")
        if scan_result and scan_result.has_critical:
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

        shutil.copytree(skill_dir, target_dir, dirs_exist_ok=False)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    skill_engine.reload_skills()
    imported = skill_engine.get_skill(target_name)
    return {
        "status": "ok",
        "name": target_name,
        "path": str(skill_engine.SKILLS_ROOT / target_name),
        "source": source_label,
        "details": {
            "name": imported.name if imported else target_name,
            "description": imported.description if imported else "",
            "use_when": imported.use_when if imported else "",
            "tags": imported.tags if imported else [],
        } if imported else {},
        "note": f"Skill '{target_name}' imported from {source_label}",
    }


def _exec_skill_import_from_url(args: dict[str, Any]) -> dict[str, Any]:
    """Import a skill from a remote URL.

    Supports:
    - Raw SKILL.md URL: https://raw.githubusercontent.com/.../SKILL.md
    - GitHub shorthand: 'user/repo' (fetches main → master fallback)
    - Generic URL pointing to a SKILL.md file
    """
    url = str(args.get("url") or "").strip()
    if not url:
        return {"status": "error", "error": "url is required"}

    name_override = str(args.get("name") or "").strip()

    # GitHub shorthand: user/repo
    if "/" in url and not url.startswith(("http://", "https://")):
        parts = url.split("/")
        if len(parts) != 2:
            return {"status": "error", "error": f"invalid GitHub shorthand '{url}' — expected user/repo"}

        content = None
        last_err = None
        for branch in ("main", "master"):
            github_url = (
                f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/{branch}/SKILL.md"
            )
            content, last_err = _fetch_url_capped(github_url, timeout=15)
            if content is not None:
                break
        if content is None:
            return {
                "status": "error",
                "error": f"GitHub user/repo '{url}' not found on main/master ({last_err})",
            }

        target_name = name_override or parts[1]
        return _install_skill_md_content(
            content=content,
            target_name=target_name,
            source_label=f"GitHub {url}",
        )

    # Generic URL
    content, err = _fetch_url_capped(url, timeout=30)
    if content is None:
        return {"status": "error", "error": err}

    from urllib.parse import urlparse
    inferred_name = (
        name_override
        or Path(urlparse(url).path).stem.lower().replace("_", "-")
        or "imported-skill"
    )
    return _install_skill_md_content(
        content=content,
        target_name=inferred_name,
        source_label=url,
    )


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
                        "description": (
                            "Minimum similarity score (0.0-1.0). Default 0.30 after "
                            "per-skill multi-candidate aggregation. Lower if you want "
                            "more suggestions; raise for stricter matching."
                        ),
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
    # Tool Invention Phase 1 (AGI track #9 — added 2026-05-12)
    {
        "type": "function",
        "function": {
            "name": "propose_new_skill",
            "description": (
                "Foreslå en ny skill du selv mener du har brug for. Værktøjet "
                "validerer at navn+content er installerbart, lægger forslaget "
                "som en plan der venter på godkendelse. Når brugeren godkender, "
                "installeres skillen automatisk via skill_engine.create_skill()."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "lowercase, alphanumeric + - + _ (matches ^[a-z0-9][a-z0-9_-]*$)",
                    },
                    "description": {
                        "type": "string",
                        "description": "én sætning om hvad skillen gør",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "SKILL.md body (markdown). Skal være konkret nok til at en frisk session kan følge den.",
                    },
                    "use_when": {
                        "type": "string",
                        "description": "trigger-beskrivelse: hvornår skal denne skill påberåbes? Default = description.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "valgfrie tags til søgbarhed",
                    },
                },
                "required": ["name", "description", "instructions"],
            },
        },
    },
]

# ── Skill versioning tools (C1, surfaced 2026-06-09 by Claude) ──────────


def _exec_skill_history(args: dict[str, Any]) -> dict[str, Any]:
    """Return audit trail for a single skill."""
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    limit = int(args.get("limit") or 50)
    try:
        from core.services import skill_engine
        return skill_engine.get_skill_history(name, limit=limit)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_recent_skill_changes(args: dict[str, Any]) -> dict[str, Any]:
    """Return most recent skill mutations across all skills."""
    limit = int(args.get("limit") or 20)
    try:
        from core.services import skill_engine
        return skill_engine.list_recent_skill_changes(limit=limit)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# Append C1 tool definitions to the main list
SKILL_ENGINE_TOOL_DEFINITIONS.extend([
    {
        "type": "function",
        "function": {
            "name": "skill_history",
            "description": (
                "Get the audit trail (create/update/delete events) for a "
                "single skill, newest first. Useful when you want to know "
                "why a skill behaves the way it does, who changed it, or "
                "when it was last modified. Backed by skill_audit_log."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name (folder name, lowercase).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max entries to return (default 50).",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recent_skill_changes",
            "description": (
                "Return the most recent skill mutations across the whole "
                "library. Useful when you want a quick overview of what "
                "skills have been touched recently — debugging, weekly "
                "review, or 'hvad lavede jeg sidst med skills?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max entries to return (default 20).",
                    },
                },
                "required": [],
            },
        },
    },
])


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
    # Tool Invention Phase 1 (AGI track #9 — 2026-05-12)
    "propose_new_skill": _exec_propose_new_skill,
    # C1 audit trail (surfaced 2026-06-09 by Claude)
    "skill_history": _exec_skill_history,
    "recent_skill_changes": _exec_recent_skill_changes,
}
