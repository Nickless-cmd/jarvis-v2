from __future__ import annotations
from core.services import operator_allowlist as al
from core.tools.simple_tools_operator import _exec_operator_launch_app


def test_observe_default_allows_but_logs(isolated_runtime):
    # Tom allowlist + enforce OFF (default) → tilladt men observed (blokerer ikke flow).
    al.set_allowlist([]); al.set_enforced(False)
    r = al.check_app("/Applications/Safari.app")
    assert r["allowed"] is True and r.get("observed") is True and r["matched"] is False


def test_enforce_blocks_non_allowlisted(isolated_runtime):
    al.set_allowlist(["safari"]); al.set_enforced(True)
    blocked = al.check_app("com.evil.malware")
    assert blocked["allowed"] is False and "allowlist" in blocked["reason"]
    allowed = al.check_app("/Applications/Safari.app")
    assert allowed["allowed"] is True and allowed["matched"] is True


def test_launch_app_honest_deny_when_enforced(isolated_runtime):
    al.set_allowlist(["code"]); al.set_enforced(True)
    r = _exec_operator_launch_app({"path": "/usr/bin/rm-gui-thing", "_runtime_trust_all": True})
    assert r["status"] == "error" and r.get("app_allowlist_denied") is True


def test_add_remove_and_enforce_toggle(isolated_runtime):
    al.set_allowlist([])
    al.add_to_allowlist("vscode")
    assert "vscode" in al.list_allowlist()
    al.remove_from_allowlist("vscode")
    assert "vscode" not in al.list_allowlist()
    assert al.set_enforced(True) is True and al.is_enforced() is True
