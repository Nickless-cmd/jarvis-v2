"""Notify-kanaler er per bruger: bucket pr. user_id, ejerens fil uændret."""
from __future__ import annotations

import json

import pytest

from core.identity.workspace_context import set_context, reset_context
from core.tools import notify_out_tools as n


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(n, "_STATE_PATH", tmp_path / "notify_channels.json")
    sent = []
    monkeypatch.setattr(n, "_send_discord", lambda url, m, t: (sent.append(("discord", url)) or {"status": "ok"}))
    monkeypatch.setattr(n, "_send_ntfy", lambda m, t, p: (sent.append(("owner-ntfy", "")) or {"status": "ok"}))
    monkeypatch.setattr(n, "_send_ntfy_url", lambda u, m, t, p: (sent.append(("ntfy", u)) or {"status": "ok"}))
    monkeypatch.setattr("core.identity.owner_resolver.get_owner_discord_id", lambda: "OWNER")
    return sent


class _As:
    def __init__(self, uid, role):
        self.uid, self.role = uid, role

    def __enter__(self):
        self.t = set_context(workspace_name="w", user_id=self.uid, user_display_name="x", role=self.role)

    def __exit__(self, *a):
        reset_context(self.t)


def _add(name, url, kind="discord"):
    assert n._exec_notify_channel_add({"name": name, "type": kind, "url": url})["status"] == "ok"


def test_two_users_each_own_channel(env):
    with _As("A", "member"):
        _add("min", "http://a")
    with _As("B", "member"):
        _add("min", "http://b")
    data = json.loads(n._STATE_PATH.read_text())
    assert data["users"]["A"]["channels"]["min"]["url"] == "http://a"
    assert data["users"]["B"]["channels"]["min"]["url"] == "http://b"
    assert data["channels"] == {}


def test_notification_to_a_does_not_hit_b(env):
    with _As("A", "member"):
        _add("min", "http://a")
    with _As("B", "member"):
        _add("min", "http://b")
        r = n._exec_notify_out({"message": "hej", "channels": ["min"]})
        assert r["status"] == "ok"
        assert env == [("discord", "http://b")]
        # B kan hverken se, sende til eller slette A's kanaler
        assert [c["name"] for c in n._exec_notify_channel_list({})["channels"]] == ["min"]
    with _As("C", "member"):
        assert n._exec_notify_out({"message": "x", "channels": ["min"]})["status"] == "error"
        assert n._exec_notify_channel_delete({"name": "min"})["status"] == "error"
    assert len(env) == 1


def test_member_cannot_use_owner_builtin_ntfy(env):
    with _As("A", "member"):
        assert n._exec_notify_out({"message": "x", "channels": ["ntfy"]})["status"] == "error"
        assert n._exec_notify_channel_list({})["count"] == 0
        _add("ntfy", "http://ntfy/a", "ntfy")
        assert n._exec_notify_out({"message": "x", "channels": ["ntfy"]})["status"] == "ok"
    assert env == [("ntfy", "http://ntfy/a")]


@pytest.mark.parametrize("ctx", [None, ("", ""), ("OWNER", "member"), ("whatever", "owner")])
def test_owner_existing_file_works_unchanged(env, ctx):
    legacy = {"channels": {"bjorn-hook": {"name": "bjorn-hook", "type": "discord", "url": "http://bjorn"}}}
    n._STATE_PATH.write_text(json.dumps(legacy))
    before = n._STATE_PATH.read_text()
    tok = set_context(workspace_name="w", user_id=ctx[0], user_display_name="x", role=ctx[1]) if ctx else None
    try:
        assert n._exec_notify_out({"message": "hej", "channels": ["bjorn-hook", "ntfy"]})["status"] == "ok"
        names = [c["name"] for c in n._exec_notify_channel_list({})["channels"]]
        assert names == ["ntfy", "bjorn-hook"]
    finally:
        if tok:
            reset_context(tok)
    assert env == [("discord", "http://bjorn"), ("owner-ntfy", "")]
    assert n._STATE_PATH.read_text() == before  # ingen migrering, filen urørt


def test_member_channels_invisible_to_owner(env):
    with _As("A", "member"):
        _add("min", "http://a")
    assert [c["name"] for c in n._exec_notify_channel_list({})["channels"]] == ["ntfy"]
    assert n._exec_notify_out({"message": "x", "channels": ["min"]})["status"] == "error"
