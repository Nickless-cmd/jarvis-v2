from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services.paste_store import (
    build_paste_reference,
    cleanup_old_pastes,
    expand_paste_references,
    get_paste,
    parse_paste_reference,
    save_paste,
)


def test_save_get_round_trip(isolated_runtime) -> None:
    text = "line 1\nline 2\nline 3"
    paste_id = save_paste(text)

    stored = get_paste(paste_id)

    assert stored is not None
    assert stored["id"] == paste_id
    assert stored["text"] == text
    assert stored["line_count"] == 3
    assert isinstance(stored["created_at"], str) and stored["created_at"]


def test_save_is_idempotent_same_text_same_id_one_file(isolated_runtime) -> None:
    from core.runtime import config

    text = "some pasted content\nwith a couple lines"
    id_a = save_paste(text)
    id_b = save_paste(text)

    assert id_a == id_b

    files = list(config.PASTE_STORE_DIR.glob("*.json"))
    # Exactly one file for the one paste (idempotent — no duplicate).
    assert len(files) == 1


def test_different_text_different_id(isolated_runtime) -> None:
    id_a = save_paste("aaa")
    id_b = save_paste("bbb")
    assert id_a != id_b


def test_build_and_parse_reference_are_symmetric(isolated_runtime) -> None:
    ref = build_paste_reference("deadbeefdeadbeef", line_count=42)
    assert ref == "[paste:deadbeefdeadbeef +42 linjer]"

    parsed = parse_paste_reference(ref)
    assert parsed == {"paste_id": "deadbeefdeadbeef", "line_count": 42}


def test_parse_reference_embedded_in_content(isolated_runtime) -> None:
    content = "her er min kode:\n[paste:abc123 +10 linjer]\ntak"
    parsed = parse_paste_reference(content)
    assert parsed is not None
    assert parsed["paste_id"] == "abc123"
    assert parsed["line_count"] == 10


def test_get_unknown_id_returns_none(isolated_runtime) -> None:
    assert get_paste("does-not-exist") is None
    assert get_paste("") is None


def test_parse_non_reference_returns_none(isolated_runtime) -> None:
    assert parse_paste_reference("just a normal message") is None
    assert parse_paste_reference("") is None


def test_expand_references_inlines_full_text(isolated_runtime) -> None:
    text = "def foo():\n    return 42\n" * 5
    paste_id = save_paste(text)
    ref = build_paste_reference(paste_id, line_count=text.count("\n"))
    message = f"kan du reviewe dette?\n{ref}"

    expanded = expand_paste_references(message)

    assert text in expanded
    assert ref not in expanded


def test_expand_unknown_id_keeps_reference(isolated_runtime) -> None:
    ref = "[paste:unknownid00000 +7 linjer]"
    message = f"se her: {ref}"
    # Degrade, never crash: unresolvable id → reference kept verbatim.
    assert expand_paste_references(message) == message


def test_expand_no_reference_is_identity(isolated_runtime) -> None:
    message = "helt normal besked uden paste"
    assert expand_paste_references(message) == message


def test_cleanup_old_pastes_removes_stale(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta

    from core.runtime import config

    paste_id = save_paste("old paste content")
    path = config.PASTE_STORE_DIR / f"{paste_id}.json"
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    data["created_at"] = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    path.write_text(json.dumps(data), encoding="utf-8")

    removed = cleanup_old_pastes(max_age_days=7)
    assert removed == 1
    assert get_paste(paste_id) is None
