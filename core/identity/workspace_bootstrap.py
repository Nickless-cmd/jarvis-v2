from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.runtime.config import WORKSPACES_DIR, WORKSPACE_TEMPLATES_DIR

TEMPLATE_DIR = WORKSPACE_TEMPLATES_DIR
LOGGER = logging.getLogger(__name__)
REQUIRED_WORKSPACE_FILES = (
    "SOUL.md",
    "IDENTITY.md",
    "STANDING_ORDERS.md",
    "USER.md",
    "TOOLS.md",
    "SKILLS.md",
    "MEMORY.md",
    "HEARTBEAT.md",
)
OPTIONAL_WORKSPACE_FILES = (
    "VISIBLE_LOCAL_MODEL.md",
    "VISIBLE_CHAT_RULES.md",
    "VISIBLE_RELEVANCE.md",
    "VISIBLE_MEMORY_SELECTION.md",
    "INNER_VOICE.md",
    "MILESTONES.md",
)


@dataclass(slots=True)
class WorkspaceBootstrapResult:
    workspace_dir: Path
    created_files: list[str]
    existing_files: list[str]

    def summary(self) -> dict[str, object]:
        return {
            "workspace": str(self.workspace_dir),
            "created_files": self.created_files,
            "existing_files": self.existing_files,
        }


def _resolve_workspace_name(name: str) -> str:
    """Resolve 'default' to current contextvar workspace if one is bound.

    This is the pivot that makes 66 hardcoded ensure_default_workspace()
    calls automatically honor per-user context. If name is explicitly
    something other than 'default', caller wins.
    """
    if name != "default":
        return name
    try:
        from core.identity.workspace_context import current_workspace_name
        return current_workspace_name() or "default"
    except Exception:
        return "default"


def ensure_default_workspace(name: str = "default") -> Path:
    resolved = _resolve_workspace_name(name)
    return bootstrap_workspace(name=resolved).workspace_dir


def ensure_layered_memory_dirs(name: str = "default") -> dict[str, Path]:
    resolved = _resolve_workspace_name(name)
    workspace_dir = Path(WORKSPACES_DIR) / resolved
    workspace_dir.mkdir(parents=True, exist_ok=True)
    memory_dir = workspace_dir / "memory"
    daily_dir = memory_dir / "daily"
    curated_dir = memory_dir / "curated"
    daily_dir.mkdir(parents=True, exist_ok=True)
    curated_dir.mkdir(parents=True, exist_ok=True)
    return {
        "workspace_dir": workspace_dir,
        "memory_dir": memory_dir,
        "daily_dir": daily_dir,
        "curated_dir": curated_dir,
    }


def workspace_memory_paths(name: str = "default") -> dict[str, Path]:
    resolved = _resolve_workspace_name(name)
    dirs = ensure_layered_memory_dirs(name=resolved)
    workspace_dir = dirs["workspace_dir"]
    today = datetime.now(UTC).date().isoformat()
    return {
        "workspace_dir": workspace_dir,
        "user": workspace_dir / "USER.md",
        "curated_memory": workspace_dir / "MEMORY.md",
        "daily_memory": dirs["daily_dir"] / f"{today}.md",
        "memory_dir": dirs["memory_dir"],
        "daily_dir": dirs["daily_dir"],
        "curated_dir": dirs["curated_dir"],
    }


def append_daily_memory_note(
    note: str,
    *,
    name: str = "default",
    source: str = "session",
) -> Path | None:
    """Append a short note to today's daily memory file.

    Daily memory is for short-lived session context — what happened
    today, what was discussed, what is fresh in mind. It is read into
    visible prompts as a separate sidecar to MEMORY.md so Jarvis has
    today's context without needing the full long-term memory file
    every turn.

    Notes auto-rotate by date (one file per UTC day). Old daily files
    accumulate in memory/daily/ and can be migrated to memory/curated/
    or pruned by a separate consolidation pass.
    """
    cleaned = " ".join(str(note or "").split()).strip()
    if not cleaned:
        return None
    paths = workspace_memory_paths(name=name)
    daily_path: Path = paths["daily_memory"]
    try:
        daily_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%H:%M")
        line = f"- [{timestamp}] [{source}] {cleaned}"
        if daily_path.exists():
            existing = daily_path.read_text(encoding="utf-8", errors="replace")
            # De-dupe: skip if exact-line already there (without timestamp)
            existing_normalized = {
                " ".join(l.split()).split("] ", 2)[-1].strip()
                for l in existing.splitlines()
                if l.strip().startswith("- [")
            }
            if cleaned in existing_normalized:
                return daily_path
            new_content = existing.rstrip() + "\n" + line + "\n"
        else:
            header = (
                f"# Daily memory — {datetime.now(UTC).date().isoformat()}\n\n"
                "Short-lived session notes. Auto-rotated daily.\n\n"
            )
            new_content = header + line + "\n"
        daily_path.write_text(new_content, encoding="utf-8")
    except Exception:
        LOGGER.warning(
            "Failed to append daily memory note",
            extra={
                "workspace": name,
                "target_path": str(daily_path),
                "source": source,
            },
            exc_info=True,
        )
        return None
    return daily_path


def read_daily_memory_lines(
    *,
    name: str = "default",
    limit: int = 12,
) -> list[str]:
    """Read the most recent daily memory notes (today only).

    Accepts both formats:
    - `- [HH:MM] [source] note` (from append_daily_memory_note)
    - `- session_id: ...` / `- carried: ...` etc (from end_of_run consolidation)

    Returns a bounded list of bullet lines from today's file. Used by
    prompt builders to inject today's context into visible prompts as
    a sidecar to MEMORY.md.
    """
    paths = workspace_memory_paths(name=name)
    daily_path: Path = paths["daily_memory"]
    if not daily_path.exists():
        return []
    try:
        lines: list[str] = []
        for raw in daily_path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = raw.strip()
            if not stripped:
                continue
            # Accept any bullet line, skip section headers and prose
            if stripped.startswith("- ") or stripped.startswith("  - "):
                lines.append(stripped)
        return lines[-max(limit, 1):]
    except Exception:
        LOGGER.warning(
            "Failed to read daily memory lines",
            extra={
                "workspace": name,
                "target_path": str(daily_path),
            },
            exc_info=True,
        )
        return []


def read_recent_daily_memory_lines(
    *,
    name: str = "default",
    days: int = 7,
    limit: int = 24,
) -> list[str]:
    """Read bounded daily memory notes across a recent lookback window.

    The single-day reader is useful for "today's scratchpad", but visible
    continuity needs a short rolling window so reboot/session boundaries do
    not erase context that was only written yesterday or earlier this week.
    """
    dirs = ensure_layered_memory_dirs(name=name)
    daily_dir = dirs["daily_dir"]
    if not daily_dir.exists():
        return []

    today = datetime.now(UTC).date()
    collected: list[str] = []
    for offset in range(max(days, 1)):
        day = today - timedelta(days=offset)
        path = daily_dir / f"{day.isoformat()}.md"
        if not path.exists():
            continue
        try:
            day_lines: list[str] = []
            for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = raw.strip()
                if not stripped:
                    continue
                if stripped.startswith("- ") or stripped.startswith("  - "):
                    day_lines.append(stripped)
            for line in reversed(day_lines):
                collected.append(f"{day.isoformat()}: {line}")
                if len(collected) >= max(limit, 1):
                    return list(reversed(collected))
        except Exception:
            LOGGER.warning(
                "Failed to read recent daily memory lines",
                extra={
                    "workspace": name,
                    "target_path": str(path),
                },
                exc_info=True,
            )
            continue
    return list(reversed(collected))


def bootstrap_workspace(name: str = "default") -> WorkspaceBootstrapResult:
    workspace_dir = Path(WORKSPACES_DIR) / name
    workspace_dir.mkdir(parents=True, exist_ok=True)

    created_files: list[str] = []
    existing_files: list[str] = []

    for filename in REQUIRED_WORKSPACE_FILES:
        src = TEMPLATE_DIR / filename
        if not src.exists():
            raise FileNotFoundError(f"Missing required workspace template: {src}")

        dest = workspace_dir / filename
        if dest.exists():
            existing_files.append(filename)
            continue

        shutil.copy2(src, dest)
        created_files.append(filename)

    for filename in OPTIONAL_WORKSPACE_FILES:
        src = TEMPLATE_DIR / filename
        if not src.exists():
            continue

        dest = workspace_dir / filename
        if dest.exists():
            existing_files.append(filename)
            continue

        shutil.copy2(src, dest)
        created_files.append(filename)

    ensure_layered_memory_dirs(name=name)

    return WorkspaceBootstrapResult(
        workspace_dir=workspace_dir,
        created_files=created_files,
        existing_files=existing_files,
    )


def bootstrap_user_workspace(workspace_name: str, *, display_name: str = "") -> WorkspaceBootstrapResult:
    """Bootstrap a per-user workspace. Unlike bootstrap_workspace(),
    this creates MEMORY.md and USER.md as EMPTY stubs rather than copying
    from template — each user starts with a clean relation.

    SOUL.md, IDENTITY.md, STANDING_ORDERS.md etc. are copied from template
    (fælles personlighed, per-user relation).

    Raises FileNotFoundError if template files are missing.
    Safe to call repeatedly — existing files are preserved.
    """
    name = str(workspace_name or "").strip()
    if not name:
        raise ValueError("bootstrap_user_workspace: workspace_name is required")

    workspace_dir = Path(WORKSPACES_DIR) / name
    workspace_dir.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    existing: list[str] = []

    # Identity files (shared personality) — copy from template
    _SHARED_IDENTITY_FILES = (
        "SOUL.md", "IDENTITY.md", "STANDING_ORDERS.md",
        "TOOLS.md", "SKILLS.md", "HEARTBEAT.md",
    )
    for filename in _SHARED_IDENTITY_FILES:
        src = TEMPLATE_DIR / filename
        if not src.exists():
            LOGGER.warning("bootstrap_user_workspace: template missing: %s", filename)
            continue
        dest = workspace_dir / filename
        if dest.exists():
            existing.append(filename)
            continue
        shutil.copy2(src, dest)
        created.append(filename)

    # Per-user relation files — EMPTY stubs, not template content
    user_md = workspace_dir / "USER.md"
    if not user_md.exists():
        stub = f"# {display_name or name}\n\n_Jeg kender endnu ikke denne bruger._\n"
        user_md.write_text(stub, encoding="utf-8")
        created.append("USER.md")
    else:
        existing.append("USER.md")

    memory_md = workspace_dir / "MEMORY.md"
    if not memory_md.exists():
        memory_md.write_text("# MEMORY\n\n_Ingen erindringer endnu._\n", encoding="utf-8")
        created.append("MEMORY.md")
    else:
        existing.append("MEMORY.md")

    # Optional identity extensions (copy if present)
    for filename in OPTIONAL_WORKSPACE_FILES:
        src = TEMPLATE_DIR / filename
        if not src.exists():
            continue
        dest = workspace_dir / filename
        if dest.exists():
            existing.append(filename)
            continue
        shutil.copy2(src, dest)
        created.append(filename)

    ensure_layered_memory_dirs(name=name)

    return WorkspaceBootstrapResult(
        workspace_dir=workspace_dir,
        created_files=created,
        existing_files=existing,
    )
