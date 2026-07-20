"""Tests for core.tools.tool_scoping — rolle/scope allowlist-logik."""
from __future__ import annotations

from core.tools.tool_scoping import (
    allowed_tool_names,
    filter_tool_definitions,
    tool_scope,
    current_tool_scope,
    CHAT_MODE_TOOLS_BASE,
    CHAT_MODE_OWNER_EXTRA,
    OWNER_ONLY_TOOLS,
)

# Et repræsentativt udsnit af tool-navne på tværs af kategorier.
ALL = [
    "web_search", "analyze_image", "remember_this", "read_mood",
    "search_jarvis_brain", "read_file", "search", "find_files",
    "bash", "write_file", "operator_bash", "dispatch_to_claude_code",
    "schedule_recurring", "get_weather",
]


class TestChatScope:

    def test_owner_chat_gets_base_plus_file_reads(self):
        allow = allowed_tool_names(role="owner", scope="chat", all_names=ALL)
        assert "web_search" in allow
        assert "remember_this" in allow
        assert "read_file" in allow and "search" in allow and "find_files" in allow
        # owner beholder owner-only der er i allowlisten
        assert "search_jarvis_brain" in allow

    def test_member_chat_no_file_reads_no_owner_only(self):
        # Member chat = permission_engine(member, chat) ∩ navne (matrixen).
        allow = allowed_tool_names(role="member", scope="chat", all_names=ALL)
        assert "web_search" in allow
        assert "remember_this" in allow       # hukommelse-write tilladt (eget WS)
        assert "read_file" not in allow        # ingen fil-læsning for member
        assert "search" not in allow
        assert "search_jarvis_brain" not in allow  # native/brain er owner-only

    def test_chat_blocks_actions_for_all(self):
        for role in ("owner", "member", ""):
            allow = allowed_tool_names(role=role, scope="chat", all_names=ALL)
            assert "bash" not in allow
            assert "write_file" not in allow
            assert "operator_bash" not in allow
            assert "dispatch_to_claude_code" not in allow
            assert "schedule_recurring" not in allow

    def test_empty_role_treated_as_owner_in_chat(self):
        allow = allowed_tool_names(role="", scope="chat", all_names=ALL)
        assert "read_file" in allow  # unbound legacy → owner-agtig


class TestNonChatScope:

    def test_owner_unrestricted(self):
        allow = allowed_tool_names(role="owner", scope="", all_names=ALL)
        assert allow == set(ALL)

    def test_member_unbounded_is_fail_closed_cowork(self):
        # KONSOLIDERET (Fase 4.1): member uden scope → fail-closed til cowork-sættet
        # (permission_engine), IKKE længere "alt minus owner-only". Cowork-sættet
        # er plans/todos/proposals/kanal — ingen af test-listens web/fil/handle-tools.
        allow = allowed_tool_names(role="member", scope="", all_names=ALL)
        assert "bash" not in allow
        assert "write_file" not in allow
        assert "search_jarvis_brain" not in allow
        assert "web_search" not in allow   # web er chat/code, ikke cowork
        assert "read_file" not in allow

    def test_member_cowork_gets_cowork_set(self):
        from core.services.permission_engine import allowed_tools as _perm
        cowork = set(_perm(role="member", mode="cowork"))
        names = list(cowork) + ["bash", "web_search"]
        allow = allowed_tool_names(role="member", scope="cowork", all_names=names)
        assert allow == cowork  # præcis permission_engine-sættet, intet andet

    def test_guest_gets_nothing(self):
        allow = allowed_tool_names(role="guest", scope="chat", all_names=ALL)
        assert allow == set()


class TestFilterDefinitions:

    def test_filters_definitions_by_name(self):
        defs = [
            {"function": {"name": "web_search"}},
            {"function": {"name": "bash"}},
            {"function": {"name": "read_file"}},
        ]
        out = filter_tool_definitions(defs, role="member", scope="chat")
        names = {d["function"]["name"] for d in out}
        assert names == {"web_search"}  # bash owner-only, read_file owner-extra


class TestScopeContextVar:

    def test_context_manager_sets_and_resets(self):
        assert current_tool_scope() == ""
        with tool_scope("chat"):
            assert current_tool_scope() == "chat"
        assert current_tool_scope() == ""


class TestAllowlistSanity:

    def test_base_and_owner_extra_disjoint(self):
        assert not (CHAT_MODE_TOOLS_BASE & CHAT_MODE_OWNER_EXTRA)

    def test_owner_extra_are_read_only_files(self):
        assert CHAT_MODE_OWNER_EXTRA == {"read_file", "search", "find_files"}

    def test_no_action_tools_in_base(self):
        for t in ("bash", "write_file", "edit_file", "operator_bash", "schedule_recurring"):
            assert t not in CHAT_MODE_TOOLS_BASE


class TestCodeScope:
    CODE_ALL = [
        "read_file", "write_file", "edit_file", "search", "find_files", "bash",
        "operator_read_file", "operator_write_file", "operator_bash",
        "operator_glob", "operator_grep", "operator_list_dir",
        "dispatch_to_claude_code", "web_search", "godnat_unrelated",
    ]

    def test_owner_code_gets_container_workstation_dispatch(self):
        allow = allowed_tool_names(role="owner", scope="code", all_names=self.CODE_ALL)
        assert {"read_file", "write_file", "edit_file", "bash", "search", "find_files"} <= allow
        assert {"operator_read_file", "operator_write_file", "operator_bash"} <= allow
        assert "dispatch_to_claude_code" in allow

    def test_member_code_operator_plus_scoped_files_no_server_shell(self):
        # KONSOLIDERET (Fase 4.1, matrixen): member code = operator_* (egen maskine)
        # + scoped server-filer (read/write/edit/find, path-jailes i Fase 4-dispatch)
        # + web. IKKE server-bash, IKKE dispatch (owner-only).
        allow = allowed_tool_names(role="member", scope="code", all_names=self.CODE_ALL)
        assert {"operator_read_file", "operator_write_file", "operator_bash",
                "operator_glob", "operator_grep", "operator_list_dir"} <= allow
        assert {"read_file", "write_file", "edit_file", "find_files"} <= allow  # scoped 🔒
        assert "bash" not in allow                  # server-shell = owner-only
        assert "dispatch_to_claude_code" not in allow
        assert "search" not in allow                # ikke i member-code-sættet

    def test_code_excludes_unrelated(self):
        for role in ("owner", "member"):
            allow = allowed_tool_names(role=role, scope="code", all_names=self.CODE_ALL)
            assert "godnat_unrelated" not in allow


def test_is_local_execution_tool() -> None:
    from core.tools.tool_scoping import is_local_execution_tool
    assert is_local_execution_tool("operator_bash") is True
    assert is_local_execution_tool("operator_read_file") is True
    assert is_local_execution_tool("dispatch_to_claude_code") is True
    assert is_local_execution_tool("web_search") is False
    assert is_local_execution_tool("") is False


# ── Spor A: is_tool_allowed (serverside håndhævelses-prædikat) ───────────────
def test_is_tool_allowed_owner_gets_everything():
    from core.tools.tool_scoping import is_tool_allowed
    assert is_tool_allowed(role="owner", scope="chat", name="bash")
    assert is_tool_allowed(role="owner", scope="code", name="operator_bash")


def test_is_tool_allowed_unbound_is_trusted_internal():
    # role="" = daemon/system/unbound → må alt (interne kald låses ikke ude).
    from core.tools.tool_scoping import is_tool_allowed
    assert is_tool_allowed(role="", scope="", name="bash")


def test_is_tool_allowed_member_chat_curated():
    from core.tools.tool_scoping import is_tool_allowed
    assert is_tool_allowed(role="member", scope="chat", name="web_search")
    assert not is_tool_allowed(role="member", scope="chat", name="bash")


def test_is_tool_allowed_guest_denied_all():
    from core.tools.tool_scoping import is_tool_allowed
    assert not is_tool_allowed(role="guest", scope="chat", name="web_search")
    assert not is_tool_allowed(role="guest", scope="code", name="operator_bash")


def test_member_code_scope_allows_operator_but_empty_scope_denies():
    """Regression (live 2026-06-21): Mikkel (member) i code mode fik
    operator_bash tilbudt men afvist med tool_not_permitted, fordi
    tool-scope-ContextVar'en var '' ved execute_tool's rolle-gate (mens
    rollen propagerede). Gaten SKAL tillade member+code men afvise member+''.
    Fixet (visible_runs: gen-assertér scope før copy_context) sikrer at
    scope='code' faktisk når gaten."""
    from core.tools.tool_scoping import is_tool_allowed
    assert is_tool_allowed(role="member", scope="code", name="operator_bash")
    # '' (mistet scope) MÅ afvise — ellers ville code-tools lække til chat:
    assert not is_tool_allowed(role="member", scope="", name="operator_bash")
    assert not is_tool_allowed(role="member", scope="chat", name="operator_bash")


def test_computer_use_policy_failopen_is_logged(caplog):
    """Auth-cluster trace (2026-06-22): hvis computer-use-policy kaster, må
    operator-tools IKKE filtreres (fail-open backstop) — men det skal nu LOGGES,
    ikke ske stille."""
    import logging
    from unittest.mock import patch
    from core.tools import tool_scoping as ts
    with patch("core.services.computer_use_policy.computer_use_enabled",
               side_effect=RuntimeError("boom")):
        with caplog.at_level(logging.WARNING):
            out = ts._apply_computer_use_policy({"operator_bash", "web_search"})
    assert out == {"operator_bash", "web_search"}  # fail-open: uændret sæt
    assert any("computer-use-policy fejlede" in r.message for r in caplog.records)


class TestOwnerMobileBridgeGate:
    """Bjørn 2026-07-01: owner får operator/bro-tools i chat KUN når en desk-bro er paret."""

    def test_owner_chat_no_bridge_no_operator(self, monkeypatch):
        import core.tools.tool_scoping as ts
        monkeypatch.setattr(ts, "_owner_has_live_bridge", lambda: False)
        allow = allowed_tool_names(role="owner", scope="chat", all_names=ALL)
        assert "operator_bash" not in allow

    def test_owner_chat_with_bridge_gets_operator(self, monkeypatch):
        import core.tools.tool_scoping as ts
        monkeypatch.setattr(ts, "_owner_has_live_bridge", lambda: True)
        allow = allowed_tool_names(role="owner", scope="chat", all_names=ALL)
        assert "operator_bash" in allow           # broen er paret → tilladt i chat
        assert "web_search" in allow              # normale chat-tools uændret

    def test_member_chat_with_bridge_still_no_operator(self, monkeypatch):
        import core.tools.tool_scoping as ts
        monkeypatch.setattr(ts, "_owner_has_live_bridge", lambda: True)
        allow = allowed_tool_names(role="member", scope="chat", all_names=ALL)
        assert "operator_bash" not in allow       # gaten er KUN for owner


class TestLocalExecOnlyTools:
    """`task`/explore-subagent har ingen server-executor → må KUN annonceres i et
    local_tool_exec-run (jarvis-code Path B). Ellers kunne modellen kalde et værktøj
    serveren ikke kan udføre. Regression-guard for Path B tool-advertisement."""

    ALL_T = ALL + ["task"]

    def _has_task(self, role, scope, local):
        import core.tools.tool_scoping as ts
        tok = ts.set_local_exec(local)
        try:
            return "task" in allowed_tool_names(role=role, scope=scope, all_names=self.ALL_T)
        finally:
            ts._local_exec_var.reset(tok)

    def test_owner_code_local_exec_gets_task(self):
        assert self._has_task("owner", "code", True) is True

    def test_owner_code_without_local_exec_no_task(self):
        # desk/container code-mode: ingen klient at forwarde til → task skjult
        assert self._has_task("owner", "code", False) is False

    def test_owner_chat_never_gets_task(self):
        assert self._has_task("owner", "chat", True) is False

    def test_owner_cowork_without_local_exec_no_task(self):
        # autonom/cowork catch-all (result = names) må ikke lække task
        assert self._has_task("owner", "", False) is False

    def test_member_code_local_exec_no_task(self):
        # subagent-dispatch er owner-only
        assert self._has_task("member", "code", True) is False

    def test_task_is_local_execution_tool(self):
        from core.tools.tool_scoping import is_local_execution_tool
        assert is_local_execution_tool("task") is True
