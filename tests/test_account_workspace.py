from pathlib import Path

from apps.api.jarvis_api.routes.account import _summarize_dir, build_workspace_overview


def test_summarize_dir_counts_files_and_bytes(tmp_path):
    (tmp_path / "a.txt").write_text("hello")       # 5 bytes
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("world!")  # 6 bytes
    files, total = _summarize_dir(tmp_path)
    assert files == 2
    assert total == 11


def test_summarize_dir_missing_dir_is_zero(tmp_path):
    files, total = _summarize_dir(tmp_path / "nope")
    assert (files, total) == (0, 0)


def test_build_workspace_overview(tmp_path):
    (tmp_path / "MEMORY.md").write_text("x" * 20)
    ov = build_workspace_overview(
        "u1",
        ws_dir=lambda uid: tmp_path,
        should_encrypt=lambda uid: True,
        is_trusted=lambda uid, kind, root: False,
    )
    assert ov["files"] == 1
    assert ov["disk_bytes"] == 20
    assert ov["encrypted"] is True
    assert ov["trusted"] is False
    assert ov["path_name"] == Path(tmp_path).name
