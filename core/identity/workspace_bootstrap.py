from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

from core.runtime.config import WORKSPACES_DIR, WORKSPACE_TEMPLATES_DIR

TEMPLATE_DIR = WORKSPACE_TEMPLATES_DIR
LOGGER = logging.getLogger(__name__)
_LOCAL_TZ = ZoneInfo("Europe/Copenhagen")
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
    "VOICE.md",
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
    today = datetime.now(_LOCAL_TZ).date().isoformat()
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
        timestamp = datetime.now(_LOCAL_TZ).strftime("%H:%M")
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
                f"# Daily memory — {datetime.now(_LOCAL_TZ).date().isoformat()}\n\n"
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

    today = datetime.now(_LOCAL_TZ).date()
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


def _load_known_sizes(workspace_dir: Path) -> dict[str, int]:
    """Load last-known-good file sizes from .file_sizes.json in the workspace."""
    sizes_file = workspace_dir / ".file_sizes.json"
    if not sizes_file.exists():
        return {}
    try:
        import json
        data = json.loads(sizes_file.read_text(encoding="utf-8"))
        return {k: int(v) for k, v in data.items()}
    except Exception:
        return {}


def _save_known_sizes(workspace_dir: Path, sizes: dict[str, int]) -> None:
    """Persist current file sizes as last-known-good baseline."""
    sizes_file = workspace_dir / ".file_sizes.json"
    try:
        import json
        sizes_file.write_text(
            json.dumps(sizes, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except Exception:
        LOGGER.warning(
            "Failed to save known sizes baseline",
            extra={"workspace": str(workspace_dir)},
            exc_info=True,
        )


# Files that are identity-critical and should never silently shrink to stubs.
_IDENTITY_CRITICAL_FILES = frozenset({
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "STANDING_ORDERS.md",
    "MEMORY.md",
    "MILESTONES.md",
})

# Minimum acceptable size (bytes) for identity-critical files.
# If a workspace file is below this, it's likely a stub and we log a warning.
_MIN_EXPECTED_SIZE = 500

# If a file shrinks more than this fraction from its last-known-good size, alarm.
_SHRINK_ALARM_THRESHOLD = 0.50


def _check_workspace_file_health(
    workspace_dir: Path,
    filename: str,
    known_sizes: dict[str, int],
) -> list[tuple[str, str]]:
    """Check a workspace file for suspicious shrinkage or stub-level size.

    Returns a list of (level, message) hvor level ∈ {"critical", "warning"}. Skelnen (så en
    LEGITIM kuratering ikke farver Centralen rød): et STUB-kollaps (identitets-fil under minimum)
    er CRITICAL; en relativ formindskelse af en fil der STADIG er substantiel (≥ minimum) er en
    WARNING — værd at bemærke (gul), men ikke system-brud (rød). Fx MEMORY.md kurateret 140KB→4KB
    mens den ægte hukommelse ligger i memory/-subdir + DB.
    """
    warnings: list[tuple[str, str]] = []
    dest = workspace_dir / filename

    if not dest.exists():
        return warnings

    current_size = dest.stat().st_size
    last_known = known_sizes.get(filename)

    # Check 1: STUB-kollaps = CRITICAL. VIGTIGT (6. jul, false-alarm-fix): fyr KUN når filen
    # engang VAR substantiel (last_known ≥ minimum) og nu er kollapset. En aldrig-udfyldt
    # template/tom-bruger-workspace (default/public/nye members — baseline ~136B) er IKKE en
    # overwrite; intet indhold gik tabt, det var aldrig der. Uden dette farvede hver tom
    # bruger-workspace Centralen rød med falske "stub overwrite" på owner-identitetsfiler.
    if (filename in _IDENTITY_CRITICAL_FILES and current_size < _MIN_EXPECTED_SIZE
            and last_known and last_known >= _MIN_EXPECTED_SIZE):
        warnings.append((
            "critical",
            f"⚠ {filename} kollapsede fra {last_known}B til {current_size}B — under minimum "
            f"{_MIN_EXPECTED_SIZE}B for identitets-kritiske filer. "
            f"Sandsynlig stub overwrite. Undersøg før genstart.",
        ))

    # Check 2: relativ formindskelse fra last-known-good. Stadig substantiel (≥ min) → WARNING;
    # under min (allerede fanget som stub af Check 1) → CRITICAL.
    if last_known and last_known > 0:
        ratio = current_size / last_known
        if ratio < _SHRINK_ALARM_THRESHOLD:
            # CRITICAL kun hvis filen VAR substantiel og nu er kollapset under minimum (ægte
            # identitets-tab). En lille fil der bliver mindre (aldrig-substantiel baseline) er
            # højst en WARNING — ikke "data loss" der farver Centralen rød. (6. jul false-alarm-fix)
            _substantial_before = last_known >= _MIN_EXPECTED_SIZE
            level = ("critical" if (current_size < _MIN_EXPECTED_SIZE and _substantial_before)
                     else "warning")
            warnings.append((
                level,
                f"🚨 {filename} shrank from {last_known}B to {current_size}B "
                f"({ratio:.0%} of last-known-good). "
                + ("Verificér (ægte hukommelse ligger typisk i memory/ + DB)."
                   if level == "warning" else "Possible data loss!"),
            ))

    return warnings


def bootstrap_workspace(name: str = "default") -> WorkspaceBootstrapResult:
    workspace_dir = Path(WORKSPACES_DIR) / name
    workspace_dir.mkdir(parents=True, exist_ok=True)

    created_files: list[str] = []
    existing_files: list[str] = []

    # --- Health guard: check existing files for stub-level shrinkage ---
    known_sizes = _load_known_sizes(workspace_dir)
    health_warnings: list[str] = []
    all_files = REQUIRED_WORKSPACE_FILES + OPTIONAL_WORKSPACE_FILES
    for filename in all_files:
        health_warnings.extend(
            _check_workspace_file_health(workspace_dir, filename, known_sizes)
        )
    if health_warnings:
        for level, w in health_warnings:
            # CRITICAL kun ved ægte stub-kollaps (→ rød Central). Substantiel formindskelse =
            # WARNING (gul) — så en LEGITIM kuratering ikke false-positiv-farver Centralen rød.
            if level == "critical":
                LOGGER.critical("WORKSPACE HEALTH GUARD: %s", w)
            else:
                LOGGER.warning("WORKSPACE HEALTH GUARD: %s", w)
        # Also publish to eventbus so daemons/heartbeat can pick it up
        try:
            from core.services.event_bus import publish as _eb_publish
            _eb_publish("workspace.health_warning", {
                "workspace": name,
                "warnings": [w for _lvl, w in health_warnings],
            })
        except Exception:
            pass  # eventbus may not be available in all contexts

    # --- Normal bootstrap: copy missing files from template ---
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

    # --- Update known-sizes baseline for all identity-critical files ---
    new_sizes: dict[str, int] = {}
    for filename in _IDENTITY_CRITICAL_FILES:
        dest = workspace_dir / filename
        if dest.exists():
            new_sizes[filename] = dest.stat().st_size
    if new_sizes:
        # Merge with existing (preserve sizes for files not currently present)
        merged = {**known_sizes, **new_sizes}
        _save_known_sizes(workspace_dir, merged)

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
    # §16: en krypteret member-fil ligger som <navn>.enc — bootstrap må IKKE
    # gen-så en plaintext-stub oven på den (stale-stub + shared-fallback-bug).
    def _ws_exists(p: Path) -> bool:
        if p.exists():
            return True
        from core.services.workspace_crypto import member_user_id_for_path
        return bool(member_user_id_for_path(p)) and Path(str(p) + ".enc").exists()

    # §16: skriv encryption-aware — for et member-workspace bliver filerne
    # krypteret (.enc) når ENCRYPT_ON_WRITE er on, plaintext ellers. Owner-
    # "default" bruger bootstrap_workspace (ikke denne), så den er upåvirket.
    def _ws_write(dest: Path, text: str) -> None:
        from core.services.workspace_crypto import write_text_for_path
        write_text_for_path(dest, text)

    for filename in _SHARED_IDENTITY_FILES:
        src = TEMPLATE_DIR / filename
        if not src.exists():
            LOGGER.warning("bootstrap_user_workspace: template missing: %s", filename)
            continue
        dest = workspace_dir / filename
        if _ws_exists(dest):
            existing.append(filename)
            continue
        _ws_write(dest, src.read_text(encoding="utf-8"))
        created.append(filename)

    # Per-user relation files — EMPTY stubs, not template content
    user_md = workspace_dir / "USER.md"
    if not _ws_exists(user_md):
        _ws_write(user_md, f"# {display_name or name}\n\n_Jeg kender endnu ikke denne bruger._\n")
        created.append("USER.md")
    else:
        existing.append("USER.md")

    memory_md = workspace_dir / "MEMORY.md"
    if not _ws_exists(memory_md):
        _ws_write(memory_md, "# MEMORY\n\n_Ingen erindringer endnu._\n")
        created.append("MEMORY.md")
    else:
        existing.append("MEMORY.md")

    # Optional identity extensions (copy if present)
    for filename in OPTIONAL_WORKSPACE_FILES:
        src = TEMPLATE_DIR / filename
        if not src.exists():
            continue
        dest = workspace_dir / filename
        if _ws_exists(dest):
            existing.append(filename)
            continue
        _ws_write(dest, src.read_text(encoding="utf-8"))
        created.append(filename)

    ensure_layered_memory_dirs(name=name)

    return WorkspaceBootstrapResult(
        workspace_dir=workspace_dir,
        created_files=created,
        existing_files=existing,
    )
