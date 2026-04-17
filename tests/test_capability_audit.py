from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.capability_audit import compute_reachability, parse_imports, score_service


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
