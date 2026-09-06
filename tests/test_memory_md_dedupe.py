from __future__ import annotations

from scripts.memory_md_dedupe_headings import dedupe_file, dedupe_headings

TEXT = """# MEMORY

## Decisions
- first body line

## Hardware
- gpu

## Decisions
- second body line

## decisions
- third body line
"""


def test_duplicates_merged_into_first_occurrence_preserving_bodies():
    out, merged = dedupe_headings(TEXT)
    assert merged == 2
    assert out.count("## Decisions") == 1
    assert "## decisions" not in out
    dec = out.index("## Decisions")
    hw = out.index("## Hardware")
    assert dec < hw
    for body in ("first body line", "second body line", "third body line"):
        assert body in out
    # bodies of later duplicates land under the first heading, before Hardware
    assert out.index("third body line") < hw


def test_no_duplicates_is_identity():
    text = "# M\n\n## A\n- a\n\n## B\n- b\n"
    out, merged = dedupe_headings(text)
    assert merged == 0
    assert out == text


def test_apply_writes_backup(tmp_path):
    p = tmp_path / "MEMORY.md"
    p.write_text(TEXT, encoding="utf-8")
    merged = dedupe_file(p, apply=True)
    assert merged == 2
    backups = list(tmp_path.glob("MEMORY.md.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == TEXT
    assert p.read_text(encoding="utf-8").count("## Decisions") == 1


def test_dry_run_does_not_write(tmp_path):
    p = tmp_path / "MEMORY.md"
    p.write_text(TEXT, encoding="utf-8")
    dedupe_file(p, apply=False)
    assert p.read_text(encoding="utf-8") == TEXT
    assert not list(tmp_path.glob("MEMORY.md.bak-*"))
