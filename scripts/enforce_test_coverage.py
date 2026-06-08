#!/usr/bin/env python3
"""
Pre-commit hook: enforces test coverage for core/ code changes.

Called by pre-commit framework (or directly) with no args — it reads
`git diff --cached --name-only --diff-filter=ACMR` to find staged files.

For every staged .py file under core/ (excluding __init__.py and
__pycache__), checks whether a matching test file exists at
tests/test_<module_name>.py.  If any are missing, exits 1 with
a clear message so the commit is blocked.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Files that don't need dedicated test files (suffix-only match)
SKIP_SUFFIXES = ("__init__.py", "__main__.py", "_pb2.py", "_pb2_grpc.py")
# Directories whose changed files should trigger test-coverage check
COVERED_DIRS = ("core/",)

# Few known modules whose tests live in non-standard locations
KNOWN_MAPPINGS: dict[str, str] = {
    "core/services/tool_router.py": "tests/services/test_tool_router.py",
    "core/runtime/workspace_paths.py": "tests/runtime/test_workspace_paths.py",
    "core/runtime/db.py": "tests/runtime/test_db_schema_multiuser.py",
    "core/services/dream_hypothesis_generator.py": "tests/runtime/test_db_schema_multiuser.py",
    # Group 4: permission scope filters — tests live in tests/multi_user/
    # Mapping added 2026-05-28.
    "core/services/cognitive_chronicle.py": "tests/multi_user/test_scope_filters.py",
    "core/services/scheduled_tasks.py": "tests/multi_user/test_scope_filters.py",
    # Group 6: scheduling user-id binding — dispatcher tested in test_scheduling_context.py
    # Mapping added 2026-05-28.
    "core/services/scheduled_task_runner.py": "tests/multi_user/test_scheduling_context.py",
    # Group 5: workspace_context tested thoroughly in test_multi_user.py
    # Mapping added 2026-05-28.
    "core/identity/workspace_context.py": "tests/test_multi_user.py",
    # Group 3a: memory-layer services migrated to workspace_dir()
    # Tests live in non-standard files; mapping added 2026-05-28.
    "core/services/cross_session_threads.py": "tests/test_autonomy_registry_surfaces.py",
    "core/services/memory_write_policy.py": "tests/test_attention_memory_surfaces.py",
    "core/services/relation_dynamics.py": "tests/test_recurring_relation_mutation_staged.py",
    "core/services/relational_warmth.py": "tests/test_affect_and_anchor_surfaces.py",
    "core/services/day_shape_memory.py": "tests/test_signal_and_idea_daemons.py",
    "core/services/memory_resurfacing.py": "tests/test_memory_and_session_surfaces.py",
    # Group 3b: inner-life daemons migrated to shared_dir()
    # Pure path refactor — no behavior change. shared_dir() tested via workspace_paths.
    # Mapping added 2026-05-28.
    "core/services/creative_impulse_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/shadow_scan_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/autonomous_work_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/file_watch_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/dream_consolidation_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/dream_carry_over.py": "tests/test_dream_continuum.py",
    "core/services/deep_reflection_slot.py": "tests/runtime/test_workspace_paths.py",
    "core/services/autonomous_outreach_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/reboot_awareness_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/collective_pulse_daemon.py": "tests/runtime/test_workspace_paths.py",
    # Group 3c: remaining services + tools migrated to shared_dir()
    # Pure path refactor — no behavior change. shared_dir() tested via workspace_paths.
    # Mapping added 2026-05-28.
    "core/services/action_router.py": "tests/runtime/test_workspace_paths.py",
    "core/services/agent_outcomes_log.py": "tests/runtime/test_workspace_paths.py",
    "core/services/anticipatory_action_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/automation_dsl.py": "tests/runtime/test_workspace_paths.py",
    "core/services/consent_registry.py": "tests/runtime/test_workspace_paths.py",
    "core/services/creative_instinct_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/creative_projects.py": "tests/runtime/test_workspace_paths.py",
    "core/services/jobs_engine.py": "tests/runtime/test_workspace_paths.py",
    "core/services/life_milestones.py": "tests/runtime/test_workspace_paths.py",
    "core/services/memory_density.py": "tests/runtime/test_workspace_paths.py",
    "core/services/memory_maintenance_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/outcome_learning.py": "tests/runtime/test_workspace_paths.py",
    "core/services/prompt_mutation_loop.py": "tests/runtime/test_workspace_paths.py",
    "core/services/scheduled_job_windows.py": "tests/runtime/test_workspace_paths.py",
    "core/services/spaced_repetition.py": "tests/runtime/test_workspace_paths.py",
    "core/services/sustained_attention.py": "tests/runtime/test_workspace_paths.py",
    "core/tools/curiosity_tools.py": "tests/runtime/test_workspace_paths.py",
    "core/tools/hf_inference_tools.py": "tests/runtime/test_workspace_paths.py",
    "core/tools/memory_tools.py": "tests/runtime/test_workspace_paths.py",
    "core/tools/mic_listen_tool.py": "tests/runtime/test_workspace_paths.py",
    "core/tools/pollinations_tools.py": "tests/runtime/test_workspace_paths.py",
    "core/tools/tiktok_content_tools.py": "tests/runtime/test_workspace_paths.py",
    # Audit-gap fix — remaining 'default' refs migrated to shared_dir().
    # Pure path refactor; shared_dir() tested via workspace_paths.
    # Mapping added 2026-05-28.
    "core/services/arc_rule_extractor.py": "tests/runtime/test_workspace_paths.py",
    "core/services/candidate_tracking.py": "tests/runtime/test_workspace_paths.py",
    "core/services/identity_drift_daemon.py": "tests/runtime/test_workspace_paths.py",
    "core/services/long_arc_synthesizer.py": "tests/runtime/test_workspace_paths.py",
    "core/services/concept_baseline_tracker.py": "tests/runtime/test_workspace_paths.py",
    "core/services/identity_composer.py": "tests/runtime/test_workspace_paths.py",
    "core/services/ground_truth_registry.py": "tests/runtime/test_workspace_paths.py",
    "core/services/remembered_fact_signal_tracking.py": "tests/runtime/test_workspace_paths.py",
    # Identity Sketch — service + tools tested in one file
    # Mapping added 2026-06-08.
    "core/services/identity_sketch.py": "tests/test_identity_sketch.py",
    "core/tools/identity_sketch_tools.py": "tests/test_identity_sketch.py",
}


def _is_covered(path: str) -> bool:
    """Check if a file path falls under a directory we enforce tests for."""
    return any(path.startswith(d) for d in COVERED_DIRS)


def _expected_test_path(staged_path: str, repo_root: Path | None = None) -> Path | None:
    """
    Given a staged file path like 'core/services/foo.py',
    return the expected test path like 'tests/test_foo.py'.

    Returns None if the file doesn't need a test file.
    """
    p = Path(staged_path)
    root = repo_root or REPO_ROOT

    # Skip non-.py files
    if p.suffix != ".py":
        return None
    # Skip known suffixes
    if any(p.name.endswith(suf) for suf in SKIP_SUFFIXES):
        return None

    module_name = p.stem  # e.g. 'foo'  from 'foo.py'

    # Check explicit overrides
    if staged_path in KNOWN_MAPPINGS:
        return root / KNOWN_MAPPINGS[staged_path]

    return root / "tests" / f"test_{module_name}.py"


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Accept optional --repo-root to override REPO_ROOT."""
    args = argv or sys.argv[1:]

    repo_root = REPO_ROOT
    if args and args[0] == "--repo-root":
        if len(args) < 2:
            print("ERROR: --repo-root requires a path argument", file=sys.stderr)
            return 1
        repo_root = Path(args[1])

    # Get staged files
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, cwd=repo_root,
    )
    if result.returncode != 0:
        print(f"ERROR: git diff failed:\n{result.stderr}", file=sys.stderr)
        return 1

    staged = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not staged:
        return 0  # nothing staged, nothing to check

    failures: list[str] = []

    for path in staged:
        if not _is_covered(path):
            continue

        expected = _expected_test_path(path, repo_root)
        if expected is None:
            continue

        if not expected.exists():
            failures.append(f"  {path}  →  {expected.relative_to(repo_root)} (MISSING)")

    if failures:
        print("❌ TEST COVERAGE GATE — commit blocked", file=sys.stderr)
        print("", file=sys.stderr)
        print("The following staged file(s) have no matching test:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        print("", file=sys.stderr)
        print("Write tests first, then commit.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
