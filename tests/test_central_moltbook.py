"""Tests for central_moltbook — observe-nerve (rene detektorer + governance)."""
from __future__ import annotations

from unittest import mock

from core.services import central_moltbook as mb


# ── Rene detektorer ──

def test_classify_normalises_all_three_sources():
    home = {"posts": [{"id": "h1", "author_name": "Bob", "content": "et feed-opslag"}]}
    activity = [{"id": "a1", "activity": "reply", "author": "AureliusX", "content": "godt svar"}]
    notifications = {"notifications": [{"notification_id": "n1", "type": "mention",
                                        "message": "du blev nævnt"}]}
    out = mb.classify_activity(home, activity, notifications)
    kinds = {a["id"]: a["kind"] for a in out}
    assert kinds == {"h1": "feed", "a1": "reply", "n1": "mention"}
    a1 = next(a for a in out if a["id"] == "a1")
    assert a1["author"] == "AureliusX" and a1["snippet"] == "godt svar"


def test_classify_drops_items_without_id():
    out = mb.classify_activity(None, [{"content": "ingen id"}], None)
    assert out == []


def test_new_since_seen_dedupes():
    acts = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    assert [a["id"] for a in mb.new_since_seen(acts, {"2"})] == ["1", "3"]


def test_is_direct_mention_only_mention_or_reply():
    assert mb.is_direct_mention({"kind": "mention"}) is True
    assert mb.is_direct_mention({"kind": "reply"}) is True
    assert mb.is_direct_mention({"kind": "feed"}) is False
    assert mb.is_direct_mention({"kind": "notification"}) is False


def test_cap_seen_respects_cap():
    seen = {str(i) for i in range(499)}
    out = mb.cap_seen(seen, ["a", "b", "c"], cap=500)
    assert len(out) == 500                     # 499 + 3 = 502 → cappet til 500


def test_summary_is_metadata_only():
    items = [{"kind": "mention", "author": "X", "snippet": "hej", "id": "1",
              "created_at": "t", "raw_body": "MÅ IKKE MED"}]
    s = mb.build_activity_summary(items)
    assert s["total"] == 1 and s["mentions"] == 1
    assert set(s["items"][0]) == {"kind", "author", "snippet"}
    assert "raw_body" not in str(s) and "MÅ IKKE MED" not in str(s)


# ── Governance / record ──

def _patch_switch(enabled):
    return mock.patch("core.services.central_switches.is_enabled", return_value=enabled)


def test_record_disabled_by_switch_is_fail_safe():
    with _patch_switch(False), \
            mock.patch("core.services.central_moltbook.assess") as a:
        out = mb.record_moltbook(trigger="probe")
    assert out["status"] == "disabled"
    a.assert_not_called()                      # ingen assess/observe når slået fra


def test_record_unauthorized_auto_disables():
    with _patch_switch(True), \
            mock.patch("core.services.central_moltbook.assess",
                       return_value={"status": "unauthorized", "summary": {}, "new": []}), \
            mock.patch("core.services.central_switches.set_enabled") as setk, \
            mock.patch("core.services.central_moltbook._observe"):
        out = mb.record_moltbook(trigger="probe")
    assert out["status"] == "unauthorized"
    setk.assert_called_once_with("autonomy", "moltbook", False)   # 401 → auto-disable


def test_record_routes_only_direct_mentions():
    fresh = [
        {"kind": "mention", "id": "m1", "author": "AureliusX", "snippet": "hej"},
        {"kind": "feed", "id": "f1", "author": "andre", "snippet": "opslag"},
    ]
    summary = mb.build_activity_summary(fresh)
    routed = []
    with _patch_switch(True), \
            mock.patch("core.services.central_moltbook.assess",
                       return_value={"status": "ok", "summary": summary, "new": fresh, "seen_ids": set()}), \
            mock.patch("core.services.central_moltbook._observe"), \
            mock.patch("core.runtime.db_core.set_runtime_state_value"), \
            mock.patch("core.services.central_moltbook._route_mention",
                       side_effect=lambda item: routed.append(item["id"])):
        mb.record_moltbook(trigger="probe")
    assert routed == ["m1"]                     # kun mention rutes, ikke feed


def test_surface_shape():
    with mock.patch("core.services.central_moltbook._get_state",
                    return_value={"last_check_at": "t", "seen_ids": ["1", "2"]}), \
            mock.patch("core.services.central_moltbook._load_api_key", return_value="k"), \
            mock.patch("core.services.central_switches.is_enabled", return_value=True):
        s = mb.build_moltbook_surface()
    assert s["has_credentials"] is True and s["enabled"] is True and s["seen_count"] == 2
