"""
Auto-ensure tests — Layer 2 of the Agentic Test Enforcement.

Automatically detects when a core/ file has been modified and ensures
a corresponding test file exists.  Called *by Jarvis himself* after
finishing an edit (edit_file / stage_edit_file) on a core file.

Workflow:
1. Deterministically maps core/<module>.py → tests/test_<module>.py
2. If test file exists → run pytest on it (catch regressions)
3. If test file missing → generate a skeleton with basic import + sanity test
4. Run pytest on generated skeleton
5. If all green → commit-ready.  If red → report and fix.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKIP_SUFFIXES = ("__init__.py", "__main__.py", "_pb2.py", "_pb2_grpc.py")


def _is_core_file(file_path: Path) -> bool:
    """True if file is under core/ and is a .py file worth testing."""
    try:
        rel = file_path.relative_to(REPO_ROOT)
    except ValueError:
        return False
    if not str(rel).startswith("core/"):
        return False
    if file_path.suffix != ".py":
        return False
    if any(file_path.name.endswith(suf) for suf in SKIP_SUFFIXES):
        return False
    return True


def _expected_test_path(core_path: Path) -> Path | None:
    """Map core/foo/bar.py → tests/test_bar.py."""
    if not _is_core_file(core_path):
        return None
    module_name = core_path.stem
    return REPO_ROOT / "tests" / f"test_{module_name}.py"


def _infer_imports(core_path: Path) -> list[str]:
    """
    Try to infer the top-level imports needed for a test skeleton.
    Scans the AST of the source file for public classes/functions.
    """
    rel = core_path.relative_to(REPO_ROOT)
    module_dotted = str(rel.with_suffix("")).replace("/", ".")

    imports = [f"from {module_dotted} import ("]

    # Try to extract public names via ast
    try:
        import ast

        source = core_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        public: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    public.append(node.name)
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith("_"):
                    public.append(node.name)

        if public:
            imports.append(f"    " + ",\n    ".join(public[:8]) + ",")
        else:
            pass  # will fall through to a bare import
    except SyntaxError:
        pass

    imports.append(")")

    # If nothing was extracted, do a raw import
    if imports[0] == f"from {module_dotted} import (" and imports[-1] == ")":
        # No names were added — just do a module-level import
        return [f"import {module_dotted}"]

    return imports


_SKELETON_TPL = '''"""Tests for {rel_path}."""

from __future__ import annotations

import pytest

{imports}


class Test{suffix}:
    """Basic test suite for {rel_path}."""

    def test_import(self):
        """Verify the module can be imported."""
        {import_assert}

    # --- Add domain-specific tests below ---
'''


def _generate_skeleton(core_path: Path) -> str:
    """
    Generate a minimal but runnable test skeleton for a core module.
    """
    rel = core_path.relative_to(REPO_ROOT)
    module_dotted = str(rel.with_suffix("")).replace("/", ".")
    suffix = core_path.stem.replace("_", " ").title().replace(" ", "")

    imports = _infer_imports(core_path)

    if imports[0].startswith("import "):
        # module_dotted = "core.foo.bar" → use sys.modules or a from-import style
        # Switch to "from core import bar" for a clean local name
        parts = module_dotted.split(".")
        if len(parts) >= 2:
            # Rewrite: import core.foo.bar → from core.foo import bar
            from_pkg = ".".join(parts[:-1])
            local_name = parts[-1]
            imports[0] = f"from {from_pkg} import {local_name}"
            import_assert = f"assert {local_name} is not None"
        else:
            import_assert = f"assert {module_dotted} is not None"
    else:
        import_assert = f"assert True  # module imports ok"

    return _SKELETON_TPL.format(
        rel_path=str(rel),
        imports="\n".join(imports),
        suffix=suffix,
        import_assert=import_assert,
    )


def _run_pytest(test_path: Path) -> subprocess.CompletedProcess:
    """Run pytest on a single test file.  Returns CompletedProcess."""
    return subprocess.run(
        [
            sys.executable or "python3",
            "-m",
            "pytest",
            str(test_path),
            "-v",
            "--tb=short",
            "-x",  # stop on first failure
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def auto_ensure_tests(changed_path: str | Path) -> dict:
    """
    Main entry point.

    Args:
        changed_path: Absolute or relative path to the file that was just edited.

    Returns:
        dict with keys:
            status: "ok" | "created" | "failed" | "skipped"
            test_path: str | None
            pytest_output: str | None
            message: str
    """
    path = Path(changed_path)
    if not path.is_absolute():
        path = REPO_ROOT / path

    if not _is_core_file(path):
        return {
            "status": "skipped",
            "test_path": None,
            "pytest_output": None,
            "message": f"{path.name} is not under core/ — skipped",
        }

    test_path = _expected_test_path(path)
    if test_path is None:
        return {
            "status": "skipped",
            "test_path": None,
            "pytest_output": None,
            "message": f"No test mapping for {path.name}",
        }

    created = False
    if not test_path.exists():
        skeleton = _generate_skeleton(path)
        test_path.write_text(skeleton, encoding="utf-8")
        created = True
        print(f"  🆕 Created {test_path.relative_to(REPO_ROOT)}")

    # Run pytest
    result = _run_pytest(test_path)

    if result.returncode == 0:
        return {
            "status": "created" if created else "ok",
            "test_path": str(test_path.relative_to(REPO_ROOT)),
            "pytest_output": result.stdout,
            "message": f"✅ {test_path.relative_to(REPO_ROOT)} — {_count_tests(result.stdout)} tests green",
        }
    else:
        return {
            "status": "failed",
            "test_path": str(test_path.relative_to(REPO_ROOT)),
            "pytest_output": result.stdout + result.stderr,
            "message": f"❌ {test_path.relative_to(REPO_ROOT)} — pytest failed:\n{result.stderr[:500]}",
        }


def _count_tests(pytest_stdout: str) -> str:
    """Extract the 'X passed' summary from pytest output."""
    for line in pytest_stdout.splitlines():
        if "passed" in line and "failed" not in line:
            parts = line.strip().split()
            return parts[0] if parts else "?"
        if "passed" in line:
            # e.g. "1 passed, 1 failed"
            idx = line.index("passed")
            return line[max(0, idx - 4):idx + 10].strip()
    return "?"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Manual invocation: python3 -m core.tools.auto_ensure_tests core/foo.py
    if len(sys.argv) < 2:
        print("Usage: python3 -m core.tools.auto_ensure_tests <changed_file>", file=sys.stderr)
        sys.exit(1)

    result = auto_ensure_tests(sys.argv[1])
    print(f"\nStatus : {result['status']}")
    print(f"Message: {result['message']}")
    if result.get("pytest_output"):
        print("\n--- pytest output ---")
        print(result["pytest_output"])
    sys.exit(0 if result["status"] in ("ok", "created", "skipped") else 1)
