"""Tests for core/services/state_file_retention.py.

Målt 2026-08-30: fire operationelle state-filer havde aldrig fået ryddet —
plan_proposals.json havde 400 poster hvor ALLE var over 7 dage, ældste 125.
Rotationen skal fjerne det der er dødt uden tvivl, og aldrig noget andet.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from core.services.state_file_retention import (
    POLICIES,
    find_orphan_upload_dirs,
    parse_ts,
    prune_all_state_files,
    prune_state_file,
    record_age_days,
    select_expired,
)

NOW = datetime(2026, 8, 30, 12, 0, 0, tzinfo=UTC)


def _iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


class TestParseTs:
    def test_iso_with_offset(self) -> None:
        assert parse_ts("2026-08-30T12:00:00+00:00") == NOW

    def test_z_suffix(self) -> None:
        assert parse_ts("2026-08-30T12:00:00Z") == NOW

    def test_naive_is_treated_as_utc(self) -> None:
        assert parse_ts("2026-08-30T12:00:00") == NOW

    @pytest.mark.parametrize("v", ["", None, "i går", 12345, "2026-13-45"])
    def test_unparseable_is_none(self, v) -> None:
        assert parse_ts(v) is None


class TestRecordAge:
    def test_uses_first_available_field(self) -> None:
        rec = {"created_at": _iso(10), "started_at": _iso(2)}
        # resolved_at/interrupted_at findes ikke → created_at vinder over started_at
        assert record_age_days(rec, NOW) == pytest.approx(10, abs=0.01)

    def test_resolved_at_wins(self) -> None:
        rec = {"resolved_at": _iso(1), "created_at": _iso(99)}
        assert record_age_days(rec, NOW) == pytest.approx(1, abs=0.01)

    def test_no_timestamp_returns_none(self) -> None:
        assert record_age_days({"run_id": "x"}, NOW) is None

    def test_non_dict_returns_none(self) -> None:
        assert record_age_days("ikke en post", NOW) is None


class TestSelectExpired:
    def test_selects_only_old(self) -> None:
        recs = {"gammel": {"created_at": _iso(40)}, "ny": {"created_at": _iso(1)}}
        assert select_expired(recs, max_age_days=30, now=NOW) == ["gammel"]

    def test_boundary_is_exclusive(self) -> None:
        """Præcis på grænsen beholdes — vi trimmer ikke tæt på kanten."""
        recs = {"på_grænsen": {"created_at": _iso(30)}}
        assert select_expired(recs, max_age_days=30, now=NOW) == []

    def test_undated_records_are_always_kept(self) -> None:
        """Vi sletter aldrig noget vi ikke kan datere."""
        recs = {"udateret": {"run_id": "x"}, "gammel": {"created_at": _iso(99)}}
        assert select_expired(recs, max_age_days=30, now=NOW) == ["gammel"]

    def test_empty_input(self) -> None:
        assert select_expired({}, max_age_days=1, now=NOW) == []


class TestPruneStateFile:
    def _write(self, tmp_path, data) -> str:
        p = tmp_path / "f.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return str(p)

    def test_removes_old_keeps_new(self, tmp_path) -> None:
        path = self._write(tmp_path, {
            "a": {"created_at": _iso(100)},
            "b": {"created_at": _iso(100)},
            "c": {"created_at": _iso(1)},
        })
        assert prune_state_file(path, max_age_days=30, now=NOW) == 2
        left = json.loads(open(path, encoding="utf-8").read())
        assert list(left) == ["c"]

    def test_no_expired_leaves_file_untouched(self, tmp_path) -> None:
        path = self._write(tmp_path, {"a": {"created_at": _iso(1)}})
        before = open(path, encoding="utf-8").read()
        assert prune_state_file(path, max_age_days=30, now=NOW) == 0
        assert open(path, encoding="utf-8").read() == before

    def test_missing_file_is_safe(self, tmp_path) -> None:
        assert prune_state_file(str(tmp_path / "nope.json"),
                                max_age_days=1, now=NOW) == 0

    def test_broken_json_is_safe(self, tmp_path) -> None:
        p = tmp_path / "broken.json"
        p.write_text("{ ikke json", encoding="utf-8")
        assert prune_state_file(str(p), max_age_days=1, now=NOW) == 0
        assert p.read_text(encoding="utf-8") == "{ ikke json"

    def test_list_shaped_file_is_left_alone(self, tmp_path) -> None:
        """Filerne er dict[id]→post. En liste er en anden form — rør den ikke."""
        path = self._write(tmp_path, [{"created_at": _iso(99)}])
        assert prune_state_file(path, max_age_days=1, now=NOW) == 0

    def test_the_real_backlog_shape(self, tmp_path) -> None:
        """Ægte form fra pending_approvals.json."""
        path = self._write(tmp_path, {
            "approval-7851adaf76bb": {
                "created_at": _iso(125), "run_id": "visible-x",
                "session_id": "chat-y", "tool_name": "bash", "arguments": {},
            },
            "approval-frisk": {"created_at": _iso(0.5), "tool_name": "bash"},
        })
        assert prune_state_file(path, max_age_days=14, now=NOW) == 1
        assert list(json.loads(open(path, encoding="utf-8").read())) == ["approval-frisk"]


class TestPolicies:
    def test_all_four_backlog_files_are_covered(self) -> None:
        assert set(POLICIES) == {
            "in_flight_runs.json", "agentic_run_checkpoints.json",
            "pending_approvals.json", "plan_proposals.json",
        }

    def test_in_flight_has_the_shortest_window(self) -> None:
        """En tur der har været 'i gang' i dagevis er en zombie."""
        assert POLICIES["in_flight_runs.json"] == min(POLICIES.values())

    def test_windows_are_generous_enough_to_be_safe(self) -> None:
        assert all(v >= 3 for v in POLICIES.values())

    def test_prune_all_never_raises_on_missing_dir(self, monkeypatch, tmp_path) -> None:
        import core.services.state_file_retention as mod
        monkeypatch.setattr(mod, "_state_dir", lambda: str(tmp_path / "findes-ikke"))
        assert prune_all_state_files(now=NOW) == {}


class TestOrphanUploadSelection:
    """Reglen der næsten gik galt.

    166 af 169 upload-filer lå i mapper uden sessions-række — men 7 af de 19
    mapper hørte til sessioner der STADIG havde beskeder i chat_messages, én
    med 3.799. "Ingen sessions-række" er derfor ikke nok; begge dele skal væk.
    """

    def _tree(self, tmp_path, names) -> str:
        root = tmp_path / "uploads"
        root.mkdir()
        for n in names:
            d = root / n
            d.mkdir()
            (d / "vedhaeftning.png").write_bytes(b"x")
        return str(root)

    def test_selects_only_fully_dead_sessions(self, tmp_path) -> None:
        root = self._tree(tmp_path, ["chat-levende", "chat-doed"])
        found = find_orphan_upload_dirs(
            root, session_is_known=lambda s: s == "chat-levende")
        assert found == ["chat-doed"]

    def test_session_with_messages_only_is_kept(self, tmp_path) -> None:
        """Den fælde der ville have kostet vedhæftninger i levende samtaler."""
        root = self._tree(tmp_path, ["chat-uden-raekke-men-med-beskeder"])
        # session_is_known slår BEGGE dele op → returnerer True
        assert find_orphan_upload_dirs(root, session_is_known=lambda s: True) == []

    def test_loose_files_in_root_are_never_selected(self, tmp_path) -> None:
        """Løse filer hører ikke til en session og kan stadig være refereret."""
        root = self._tree(tmp_path, ["chat-doed"])
        (tmp_path / "uploads" / "webcam-bjorn.jpg").write_bytes(b"x")
        assert find_orphan_upload_dirs(root, session_is_known=lambda s: False) == ["chat-doed"]

    def test_lookup_failure_keeps_the_directory(self, tmp_path) -> None:
        """Tvivl → behold. En DB-fejl må aldrig blive til en sletning."""
        def boom(_s):
            raise RuntimeError("db nede")
        root = self._tree(tmp_path, ["chat-x"])
        assert find_orphan_upload_dirs(root, session_is_known=boom) == []

    def test_missing_root_is_safe(self, tmp_path) -> None:
        assert find_orphan_upload_dirs(str(tmp_path / "nope"),
                                       session_is_known=lambda s: False) == []

    def test_empty_root(self, tmp_path) -> None:
        root = tmp_path / "uploads"
        root.mkdir()
        assert find_orphan_upload_dirs(str(root), session_is_known=lambda s: False) == []
