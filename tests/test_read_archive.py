"""Tests for the read_archive tool."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import io
import tarfile
import zipfile

import pytest


@pytest.fixture(autouse=True)
def patch_home(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)


def _make_zip(dest: Path, files: dict[str, str]) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    zp = dest / "test.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return zp


def _make_tar_gz(dest: Path, files: dict[str, str]) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    tp = dest / "test.tar.gz"
    with tarfile.open(tp, "w:gz") as tf:
        for name, content in files.items():
            data = content.encode()
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
    return tp


def test_list_zip(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    zp = _make_zip(tmp_path / ".jarvis-v2", {"hello.txt": "hi", "sub/world.py": "x"})
    result = _exec_read_archive({"archive_path": str(zp)})
    assert result["status"] == "ok"
    assert result["count"] == 2
    assert "hello.txt" in result["file_list"]
    assert "sub/world.py" in result["file_list"]
    assert "extracted_to" not in result


def test_extract_zip(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    base = tmp_path / ".jarvis-v2"
    zp = _make_zip(base, {"readme.txt": "hello"})
    result = _exec_read_archive({"archive_path": str(zp), "extract": True})
    assert result["status"] == "ok"
    assert "extracted_to" in result
    extracted = Path(result["extracted_to"])
    assert (extracted / "readme.txt").exists()


def test_list_tar_gz(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    base = tmp_path / ".jarvis-v2"
    tp = _make_tar_gz(base, {"a.py": "print(1)", "b.txt": "hello"})
    result = _exec_read_archive({"archive_path": str(tp)})
    assert result["status"] == "ok"
    assert result["count"] == 2


def test_path_outside_jarvis_rejected(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    result = _exec_read_archive({"archive_path": "/etc/passwd"})
    assert result["status"] == "error"
    assert "jarvis" in result["error"].lower() or "~/.jarvis" in result["error"]


def test_missing_archive_path(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    result = _exec_read_archive({})
    assert result["status"] == "error"


def test_unsupported_format(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    base = tmp_path / ".jarvis-v2"
    base.mkdir(parents=True, exist_ok=True)
    f = base / "file.7z"
    f.write_bytes(b"x")
    result = _exec_read_archive({"archive_path": str(f)})
    assert result["status"] == "error"
    assert "Unsupported" in result["error"]
