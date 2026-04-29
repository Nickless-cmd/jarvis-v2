#!/usr/bin/env python3
"""Regenerate TIER_1_ALWAYS_ON in copilot_tool_pruning.py from 30-day usage data.

Composition rule:
  - Include every tool called >= USAGE_THRESHOLD times in the last 30 days
  - UNION with SAFETY_FLOOR (tools that must always be available regardless of usage)
  - Intersect with the actual registered tool catalog (TOOL_DEFINITIONS) so
    we never list a tool that no longer exists.

Usage:
  python scripts/regenerate_tier1.py            # dry-run, show diff
  python scripts/regenerate_tier1.py --apply    # write the new literal in-place

Run quarterly, or whenever Jarvis' tool habits feel like they've drifted.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import textwrap
from pathlib import Path

USAGE_THRESHOLD = 3  # >= this many invocations in 30 days qualifies
WINDOW_DAYS = 30

# Tools that must always be in Tier 1 regardless of past usage. These are
# the ones whose absence would be a behavioural regression, not a latency
# optimization (loss of voice, loss of approval path, loss of memory, etc.).
SAFETY_FLOOR: frozenset[str] = frozenset({
    # User-facing communication — never lose his voice
    "notify_user", "send_webchat_message", "send_ntfy",
    # Approval/policy infrastructure
    "approve_proposal", "propose_git_commit", "propose_source_edit",
    "list_proposals",
    # Self-knowledge baseline
    "read_self_state", "read_mood", "read_self_docs", "read_chronicles",
    # Memory baseline
    "search_memory", "recall_memories", "memory_upsert_section",
    "memory_check_duplicate", "recall_before_act",
    # File ops baseline
    "read_file", "write_file", "edit_file", "search", "find_files", "bash",
    # Web baseline
    "web_fetch", "web_search",
    # Schedule + initiative
    "schedule_task", "list_initiatives",
    # Git
    "git_status", "git_log", "git_diff",
})

REPO_ROOT = Path(__file__).resolve().parent.parent
PRUNING_FILE = REPO_ROOT / "core" / "tools" / "copilot_tool_pruning.py"
DB_PATH = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"


def load_usage() -> dict[str, int]:
    if not DB_PATH.exists():
        sys.exit(f"runtime DB not found at {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        f"""
        SELECT json_extract(payload_json, '$.tool') AS tool, COUNT(*) AS calls
        FROM events
        WHERE kind = 'tool.invoked'
          AND created_at > datetime('now', '-{WINDOW_DAYS} days')
        GROUP BY tool ORDER BY calls DESC
        """
    ).fetchall()
    return {tool: int(calls) for tool, calls in rows if tool}


def load_registered_tools() -> set[str]:
    sys.path.insert(0, str(REPO_ROOT))
    from core.tools.simple_tools import TOOL_DEFINITIONS  # noqa: E402
    names: set[str] = set()
    for tool in TOOL_DEFINITIONS:
        name = tool.get("name") or tool.get("function", {}).get("name")
        if name:
            names.add(str(name))
    return names


def compute_new_tier1(usage: dict[str, int], registered: set[str]) -> set[str]:
    data_driven = {n for n, c in usage.items() if c >= USAGE_THRESHOLD}
    return (data_driven | SAFETY_FLOOR) & registered


def render_literal(names: set[str]) -> str:
    sorted_names = sorted(names)
    chunks = []
    for i in range(0, len(sorted_names), 4):
        line = ", ".join(f'"{n}"' for n in sorted_names[i:i + 4])
        chunks.append(f"    {line},")
    return "TIER_1_ALWAYS_ON: frozenset[str] = frozenset({\n" + "\n".join(chunks) + "\n})"


def replace_literal_in_file(new_literal: str) -> bool:
    text = PRUNING_FILE.read_text(encoding="utf-8")
    start = text.find("TIER_1_ALWAYS_ON: frozenset[str] = frozenset({")
    if start < 0:
        return False
    # Find the matching close brace by walking forward.
    end = text.find("})", start)
    if end < 0:
        return False
    end += 2  # include the closing '})'
    new_text = text[:start] + new_literal + text[end:]
    PRUNING_FILE.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Write the new literal to copilot_tool_pruning.py",
    )
    args = parser.parse_args()

    usage = load_usage()
    registered = load_registered_tools()
    new_tier1 = compute_new_tier1(usage, registered)

    # Compare to current
    sys.path.insert(0, str(REPO_ROOT))
    from core.tools.copilot_tool_pruning import TIER_1_ALWAYS_ON  # noqa: E402
    current = TIER_1_ALWAYS_ON & registered

    removed = sorted(current - new_tier1)
    added = sorted(new_tier1 - current)

    print(f"Window: last {WINDOW_DAYS} days, threshold: >= {USAGE_THRESHOLD} uses")
    print(f"Registered tools: {len(registered)}")
    print(f"Current Tier 1: {len(current)}")
    print(f"New Tier 1:     {len(new_tier1)}")
    print(f"  - Demoted: {len(removed)}")
    print(f"  - Added:   {len(added)}")
    print()
    if removed:
        print("Demoted (rarely used):")
        for n in removed[:20]:
            print(f"  -  {n}  ({usage.get(n, 0)} uses)")
        if len(removed) > 20:
            print(f"  ... and {len(removed) - 20} more")
        print()
    if added:
        print("Newly promoted (heavily used):")
        for n in added[:20]:
            print(f"  +  {n}  ({usage.get(n, 0)} uses)")
        if len(added) > 20:
            print(f"  ... and {len(added) - 20} more")
        print()

    new_literal = render_literal(new_tier1)
    if args.apply:
        if replace_literal_in_file(new_literal):
            print(f"✓ Updated {PRUNING_FILE.relative_to(REPO_ROOT)}")
        else:
            print("✗ Could not locate TIER_1_ALWAYS_ON literal to replace")
            return 1
    else:
        print("--- Suggested new TIER_1_ALWAYS_ON literal ---")
        print(textwrap.indent(new_literal[:400] + "\n... (truncated)", "  "))
        print()
        print("Re-run with --apply to write it to copilot_tool_pruning.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
