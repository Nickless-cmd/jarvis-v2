from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.capability_audit import (
    REPO_ROOT,
    SERVICES_MOVE_COMMIT_PREFIX,
    EntryRoot,
    GitTouchIndex,
    compute_entry_paths,
    compute_reachability,
    discover_module_entries,
    discover_registry_entries,
    discover_systemd_entries,
    git_last_touch,
    parse_imports,
    score_service,
)


def test_parse_imports_handles_standard_forms(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text(
        "\n".join(
            [
                "import core.services.alpha",
                "from core.services import beta",
                "module = __import__('core.services.gamma', fromlist=['x'])",
                "import importlib",
                "plugin = importlib.import_module('core.services.delta')",
            ]
        ),
        encoding="utf-8",
    )

    imports = parse_imports(
        source,
        current_module="tests.example",
        known_modules={
            "core.services.alpha",
            "core.services.beta",
            "core.services.gamma",
            "core.services.delta",
        },
    )

    assert imports == {
        "core.services.alpha",
        "core.services.beta",
        "core.services.gamma",
        "core.services.delta",
    }


def test_reachability_handles_circular_import() -> None:
    graph = {
        "entry": {"core.services.a"},
        "core.services.a": {"core.services.b"},
        "core.services.b": {"core.services.a"},
    }

    reachable, parents = compute_reachability(graph, ["entry"])

    assert {"entry", "core.services.a", "core.services.b"} <= reachable
    assert "entry" in parents["core.services.a"]
    assert "core.services.a" in parents["core.services.b"]


def test_score_all_five_categories() -> None:
    live = {
        "reachable_from_entry": True,
        "test_references": 1,
        "emits_events": False,
        "has_daemon_hook": False,
        "last_modified_days": 10,
        "imported_by_count": 3,
    }
    partial = {
        "reachable_from_entry": True,
        "test_references": 0,
        "emits_events": False,
        "has_daemon_hook": False,
        "last_modified_days": 90,
        "imported_by_count": 1,
    }
    stale = {
        "reachable_from_entry": True,
        "test_references": 0,
        "emits_events": False,
        "has_daemon_hook": False,
        "last_modified_days": 200,
        "imported_by_count": 1,
    }
    suspicious = {
        "reachable_from_entry": False,
        "test_references": 0,
        "emits_events": False,
        "has_daemon_hook": False,
        "last_modified_days": 20,
        "imported_by_count": 2,
    }
    orphan = {
        "reachable_from_entry": False,
        "test_references": 0,
        "emits_events": False,
        "has_daemon_hook": False,
        "last_modified_days": 20,
        "imported_by_count": 0,
    }

    assert score_service(live) == "🟢 LIVE"
    assert score_service(partial) == "🟡 PARTIAL"
    assert score_service(stale) == "🟠 STALE"
    assert score_service(suspicious) == "🔴 SUSPICIOUS"
    assert score_service(orphan) == "⚫ ORPHAN"


def test_git_last_touch_reads_index_and_chains_renames() -> None:
    """A renamed core/services file must report its PRE-rename commit.

    The bulk services-move commit is skipped, so the age comes from the older
    real change at the old path — the behaviour ``git log --follow`` gave, but
    read from the shared index instead of one git call per file.
    """
    now = int(time.time())
    move = f"deadbee {SERVICES_MOVE_COMMIT_PREFIX}"
    index = GitTouchIndex(
        touches={
            "core/services/moved.py": ((now - 3 * 86400, move),),
            "apps/api/jarvis_api/services/moved.py": ((now - 200 * 86400, "abc1234 pre-move change"),),
        },
        renamed_from={"core/services/moved.py": "apps/api/jarvis_api/services/moved.py"},
    )

    age, commit = git_last_touch(REPO_ROOT / "core/services/moved.py", index)

    assert commit == "abc1234 pre-move change"
    assert age == 200


def test_git_last_touch_without_history_returns_none() -> None:
    """A path with no entry in the index reports no history instead of raising."""
    index = GitTouchIndex(touches={}, renamed_from={})

    assert git_last_touch(REPO_ROOT / "core/services/never_tracked.py", index) == (None, "n/a")


# --- indgangs-kilder: hver målt for sig mod en syntetisk repo-fixture -------------

KNOWN = {
    "core.services.guard",
    "core.services.script_job",
    "core.services.cron_job",
    "core.services.shell_job",
    "core.services.registered",
    "core.services.documented_only",
    "core.services.helper",
    "scripts.runner",
    "apps.api.jarvis_api.app",
}


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_systemd_execstart_both_forms_and_ignores_other_lines(tmp_path: Path) -> None:
    _write(tmp_path, "deploy/guard.service", "[Service]\nExecStart=/opt/py/bin/python3 -m core.services.guard\n")
    _write(
        tmp_path,
        "scripts/runner.service",
        "[Service]\nExecStart=/elsewhere/checkout/scripts/runner.py --flag\n",
    )
    _write(
        tmp_path,
        "deploy/api.service",
        "[Service]\nExecStart=/opt/py/bin/uvicorn apps.api.jarvis_api.app:app \\\n  --port 1\n",
    )
    _write(tmp_path, "deploy/other.service", "[Service]\nExecStart=/usr/bin/true\nDescription=python3 -m core.services.helper\n")
    _write(tmp_path, "deploy/guard.timer", "ExecStart=python3 -m core.services.helper\n")

    roots = discover_systemd_entries([tmp_path / "deploy", tmp_path / "scripts"], tmp_path, KNOWN)

    assert sorted(roots) == [
        EntryRoot("systemd:api.service", "apps.api.jarvis_api.app"),
        EntryRoot("systemd:guard.service", "core.services.guard"),
        EntryRoot("systemd:runner.service", "scripts.runner"),
    ]


def test_systemd_without_units_yields_nothing(tmp_path: Path) -> None:
    assert discover_systemd_entries([tmp_path / "missing"], tmp_path, KNOWN) == []


def test_module_entries_count_only_real_command_paths(tmp_path: Path) -> None:
    _write(tmp_path, "scripts/job.sh", "#!/bin/sh\n# python3 -m core.services.helper\n/usr/bin/python3 -m core.services.shell_job\n")
    _write(
        tmp_path,
        "core/services/launcher.py",
        '"""Docs: python3 -m core.services.documented_only"""\n'
        'CMD = "python3 -m core.services.cron_job --once"\n'
        '# python3 -m core.services.helper\n',
    )
    _write(tmp_path, "docs/readme.md", "python3 -m core.services.documented_only\n")
    _write(tmp_path, "core/services/cron_job.py", 'SELF = "python3 -m core.services.cron_job"\n')

    roots = discover_module_entries(tmp_path, KNOWN)

    assert sorted(roots) == [
        EntryRoot("module:-m core.services.cron_job", "core.services.cron_job"),
        EntryRoot("module:-m core.services.shell_job", "core.services.shell_job"),
    ]


def test_registry_tuples_found_in_services_and_apps_only(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "core/services/digest.py",
        'ITEMS = (\n    ("dark_digest", "core.services.registered", "build_surface"),\n'
        '    ("unknown", "core.services.nope", "build_surface"),\n'
        '    ("two_only", "core.services.helper"),\n)\n',
    )
    _write(tmp_path, "tests/t.py", 'X = ("in_tests", "core.services.guard", "f")\n')

    roots = discover_registry_entries(tmp_path, KNOWN)

    assert roots == [EntryRoot("registry:dark_digest", "core.services.registered")]


def test_entry_paths_name_the_way_in_and_mark_transitive() -> None:
    graph = {
        "scripts.runner": {"core.services.helper"},
        "core.services.guard": {"core.services.helper"},
        "core.services.helper": set(),
        "core.services.dead": set(),
    }
    roots = [
        EntryRoot("import:app.py", "scripts.runner"),
        EntryRoot("systemd:guard.service", "core.services.guard"),
    ]

    assert compute_entry_paths(graph, roots) == {
        "scripts.runner": ["import:app.py"],
        "core.services.guard": ["systemd:guard.service"],
        "core.services.helper": ["import:app.py", "systemd:guard.service (transitive)"],
    }
