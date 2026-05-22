"""Tests for core/tools/auto_ensure_tests.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.tools.auto_ensure_tests import (
    REPO_ROOT,
    _expected_test_path,
    _generate_skeleton,
    _is_core_file,
    auto_ensure_tests,
)


class TestIsCoreFile:
    """Tests for _is_core_file()."""

    def test_core_py_file(self):
        f = REPO_ROOT / "core" / "services" / "claim_scanner.py"
        assert _is_core_file(f) is True

    def test_core_init_py(self):
        f = REPO_ROOT / "core" / "__init__.py"
        assert _is_core_file(f) is False

    def test_non_core_file(self):
        f = REPO_ROOT / "tests" / "test_foo.py"
        assert _is_core_file(f) is False

    def test_non_py_file(self):
        f = REPO_ROOT / "core" / "data.json"
        assert _is_core_file(f) is False

    def test_outside_repo(self):
        f = Path("/tmp/some.py")
        assert _is_core_file(f) is False


class TestExpectedTestPath:
    """Tests for _expected_test_path()."""

    def test_maps_correctly(self):
        core = REPO_ROOT / "core" / "services" / "claim_scanner.py"
        expected = _expected_test_path(core)
        assert expected is not None
        assert expected.name == "test_claim_scanner.py"
        assert expected.parent.name == "tests"

    def test_returns_none_for_init(self):
        core = REPO_ROOT / "core" / "__init__.py"
        assert _expected_test_path(core) is None

    def test_returns_none_for_non_core(self):
        f = REPO_ROOT / "scripts" / "foo.py"
        assert _expected_test_path(f) is None


class TestGenerateSkeleton:
    """Tests for _generate_skeleton()."""

    def test_generates_valid_python(self):
        """Skeleton should be syntactically valid Python."""
        dummy = REPO_ROOT / "core" / "services" / "claim_scanner.py"
        skeleton = _generate_skeleton(dummy)
        compile(skeleton, "<test>", "exec")
        assert "test_import" in skeleton

    def test_includes_correct_class_name(self):
        dummy = REPO_ROOT / "core" / "tools" / "auto_ensure_tests.py"
        skeleton = _generate_skeleton(dummy)
        assert "TestAutoEnsureTests" in skeleton

    def test_includes_import_line(self):
        dummy = REPO_ROOT / "core" / "services" / "claim_scanner.py"
        skeleton = _generate_skeleton(dummy)
        assert "from" in skeleton or "import" in skeleton


class TestAutoEnsureTests:
    """Unit tests for auto_ensure_tests() — avoids subprocess."""

    def test_skips_non_core(self):
        """Should skip files outside core/."""
        result = auto_ensure_tests("/tmp/random.py")
        assert result["status"] == "skipped"

    def test_skips_init(self):
        """Should skip __init__.py."""
        result = auto_ensure_tests(str(REPO_ROOT / "core" / "__init__.py"))
        assert result["status"] == "skipped"

    def test_skips_non_py(self):
        """Should skip non-.py files."""
        result = auto_ensure_tests(str(REPO_ROOT / "core" / "data.json"))
        assert result["status"] == "skipped"

    def test_on_claim_scanner(self):
        """auto_ensure_tests should find existing test for claim_scanner."""
        path = REPO_ROOT / "core" / "services" / "claim_scanner.py"
        result = auto_ensure_tests(str(path))
        # Must NOT be skipped — claim_scanner has a test file
        assert result["status"] in ("ok", "created", "failed"), (
            f"Expected ok/created/failed, got {result['status']}: {result['message']}"
        )
        assert result["test_path"] is not None

    def test_creates_test_for_novel_module(self, tmp_path: Path):
        """Creating a new core module should auto-generate a test skeleton."""
        novel = REPO_ROOT / "core" / f"temp_test_mod_{abs(hash(str(tmp_path))) % 10000}.py"
        test_file = REPO_ROOT / "tests" / f"test_temp_test_mod_{abs(hash(str(tmp_path))) % 10000}.py"
        try:
            novel.write_text("VAL = 42\n")
            result = auto_ensure_tests(str(novel))

            assert result["status"] in ("created", "ok"), (
                f"Expected created/ok, got {result['status']}: {result['message']}"
            )
            assert result["test_path"] is not None

            # Clean up generated test file
            if test_file.exists():
                test_file.unlink()
        finally:
            novel.unlink(missing_ok=True)
            test_file.unlink(missing_ok=True)
