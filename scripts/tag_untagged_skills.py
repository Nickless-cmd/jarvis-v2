#!/usr/bin/env python3
"""Batch-tag untagged skills for C2 — Skills meta-tags.

Infers domain/context tags from each skill's description + use_when + name.
Idempotent: only touches skills that have no `tags:` line in frontmatter.
"""
from pathlib import Path
import re

SKILLS_ROOT = Path.home() / ".jarvis-v2" / "skills"

# Domain taxonomy — map keywords to tags
DOMAIN_MAP: list[tuple[set[str], list[str]]] = [
    # (keyword_set, tags)
    ({"banner", "social media", "facebook", "instagram", "youtube", "linkedin", "google display", "print", "ad", "marketing", "brand", "branding", "messaging framework", "brand voice", "style guide", "campaign"},
     ["marketing", "design", "content"]),
    ({"design", "ui", "ux", "frontend", "visual", "art", "canvas", "poster", "layout", "typography", "color", "style", "art direction", "artifact", "component"},
     ["design", "development"]),
    ({"react", "tailwind", "shadcn", "html", "css", "javascript", "jsx", "frontend", "web component", "component"},
     ["development", "frontend"]),
    ({"excel", "spreadsheet", "openpyxl", "xlsm", "invoice", "finance", "budget"},
     ["data", "automation", "office"]),
    ({"docker", "container", "compose", "deployment", "devops", "ci", "cd", "infrastructure"},
     ["devops", "infrastructure"]),
    ({"git", "branch", "worktree", "rebase", "merge", "commit", "version control"},
     ["git", "development"]),
    ({"research", "report", "analysis", "literature", "market", "competitive", "lead", "investor", "customer"},
     ["research", "business"]),
    ({"code review", "pr review", "pull request", "quality", "security", "refactoring", "debug"},
     ["development", "quality"]),
    ({"test", "tdd", "testing", "red-green", "pytest", "unittest", "verification"},
     ["testing", "development"]),
    ({"prompt", "optimization", "specification", "ears", "requirements"},
     ["development", "ai"]),
    ({"web", "scraping", "scraper", "scrapling", "html", "extraction", "crawl"},
     ["web", "automation", "data"]),
    ({"youtube", "video", "download", "audio", "yt-dlp", "hls", "transcribe"},
     ["media", "automation"]),
    ({"markdown", "formatting", "tables", "documentation", "docs", "changelog"},
     ["documentation", "content"]),
    ({"shell", "bash", "pipes", "awk", "sed", "jq", "process", "terminal", "cli", "command"},
     ["development", "automation"]),
    ({"memory", "distillation", "consolidation", "pattern", "promotion"},
     ["memory", "self"]),
    ({"code", "plan", "skill", "superpower", "development", "branch", "subagent", "agent"},
     ["development", "workflow"]),
    ({"mcp", "server", "protocol", "api", "integration", "connect", "connector", "langsmith"},
     ["development", "integration"]),
    ({"slack", "gif", "communication", "internal", "comms", "message", "notification"},
     ["communication", "automation"]),
    ({"resume", "cv", "job", "career", "recruitment", "hr", "hiring"},
     ["business", "content"]),
    ({"domain", "name", "brainstorm", "naming", "startup"},
     ["business", "content"]),
    ({"file", "organizer", "organize", "sort", "cleanup", "archive"},
     ["automation", "data"]),
    ({"raffle", "winner", "contest", "giveaway", "random", "pick"},
     ["automation", "business"]),
    ({"template", "scaffold", "generator", "builder", "create"},
     ["development", "automation"]),
    ({"image", "photo", "enhance", "filter", "effect", "edit"},
     ["design", "media"]),
    ({"video", "download", "converter", "media"},
     ["media", "automation"]),
    ({"meeting", "insight", "notes", "summary", "transcript", "agenda"},
     ["business", "automation"]),
    ({"theme", "color", "scheme", "palette", "skin", "branding"},
     ["design", "development"]),
    ({"skill", "creator", "share", "publish", "install", "superpower"},
     ["development", "workflow"]),
    ({"analytics", "tracking", "metrics", "data", "algorithm"},
     ["data", "business"]),
    ({"canvas", "whiteboard", "diagram", "draw", "illustration"},
     ["design", "content"]),
    ({"artifact", "html", "component", "claude"},
     ["development", "frontend"]),
    ({"growth", "developer", "audit", "score", "evaluation", "assessment"},
     ["research", "business"]),
]

def infer_tags(name: str, description: str, use_when: str) -> list[str]:
    """Infer domain/context tags from skill metadata."""
    combined = f"{name} {description} {use_when}".lower()
    found = set()
    for keywords, tags in DOMAIN_MAP:
        if any(kw in combined for kw in keywords):
            for t in tags:
                found.add(t)
    # Fallback for superpowers/composio prefix
    if not found:
        if name.startswith("superpowers-") or name.startswith("composio-"):
            found.add("development")
            found.add("workflow")
        else:
            found.add("general")
    # Always add 'skill' tag
    found.add("skill")
    return sorted(found)


def update_skill_md(path: Path) -> bool:
    """Add tags to SKILL.md frontmatter. Returns True if changed."""
    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")

    if not lines or lines[0].strip() != "---":
        return False  # No frontmatter — skip

    # Find end of frontmatter
    end = 1
    while end < len(lines) and lines[end].strip() != "---":
        end += 1
    if end >= len(lines):
        return False  # Unclosed frontmatter

    fm = lines[1:end]

    # Check if tags already exist
    if any(l.strip().startswith("tags:") for l in fm):
        return False  # Already tagged

    # Extract name, description, use_when
    name = ""
    description = ""
    use_when = ""
    for l in fm:
        if l.strip().startswith("name:"):
            name = l.split(":", 1)[1].strip().strip('"').strip("'")
        elif l.strip().startswith("description:"):
            description = l.split(":", 1)[1].strip().strip('"').strip("'")
        elif l.strip().startswith("use_when:"):
            use_when = l.split(":", 1)[1].strip().strip('"').strip("'")

    tags = infer_tags(name, description, use_when)

    # Insert tags line after name or at end of frontmatter
    # Find insertion point: after 'name:' line, before 'description:' if possible
    insert_after = 0
    for i, l in enumerate(fm):
        if l.strip().startswith("name:"):
            insert_after = i
            break
    else:
        insert_after = len(fm) - 1

    tag_line = f"tags: [{', '.join(tags)}]"
    fm.insert(insert_after + 1, tag_line)

    # Rebuild
    new_content = "---\n" + "\n".join(fm) + "\n---\n" + "\n".join(lines[end + 1:])
    path.write_text(new_content, encoding="utf-8")
    return True


def main():
    updated = []
    skipped = []
    errors = []

    for d in sorted(SKILLS_ROOT.iterdir()):
        if not d.is_dir():
            continue
        smd = d / "SKILL.md"
        if not smd.exists():
            smd = d / "skill.md"
        if not smd.exists():
            skipped.append((d.name, "no SKILL.md"))
            continue
        try:
            if update_skill_md(smd):
                updated.append(d.name)
            else:
                skipped.append((d.name, "already tagged or no frontmatter"))
        except Exception as e:
            errors.append((d.name, str(e)))

    print(f"✅ Updated: {len(updated)}")
    for name in updated:
        print(f"   - {name}")
    print(f"\n⏭️  Skipped: {len(skipped)}")
    print(f"\n❌ Errors: {len(errors)}")
    for name, err in errors:
        print(f"   - {name}: {err}")


if __name__ == "__main__":
    main()
