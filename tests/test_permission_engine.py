from __future__ import annotations


# ── Owner: alt tilladt, alle modes ──────────────────────────────────────────

def test_owner_all_tools_any_mode() -> None:
    from core.services.permission_engine import is_tool_allowed

    assert is_tool_allowed("anything_at_all", role="owner", mode="chat") is True
    assert is_tool_allowed("restart_self", role="owner", mode="code") is True
    assert is_tool_allowed("stripe_payouts", role="owner", mode="cowork") is True


# ── Guest: ingenting ────────────────────────────────────────────────────────

def test_guest_none() -> None:
    from core.services.permission_engine import allowed_tools, is_tool_allowed

    assert allowed_tools(role="guest", mode="chat") == set()
    assert allowed_tools(role="guest", mode="code") == set()
    assert is_tool_allowed("web_search", role="guest", mode="chat") is False


# ── Member CHAT ─────────────────────────────────────────────────────────────

def test_member_chat_has_web_and_memory_no_native() -> None:
    from core.services.permission_engine import allowed_tools

    t = allowed_tools(role="member", mode="chat")
    assert "web_search" in t
    assert "remember_this" in t
    # Ingen native indre, ingen operator, ingen self-kode
    assert "read_mood" not in t
    assert "operator_bash" not in t
    assert "skill_create" not in t


def test_member_chat_no_cross_agent_recall() -> None:
    # Cross-user recall er privatlivs-grænsen → aldrig member.
    from core.services.permission_engine import is_tool_allowed

    assert is_tool_allowed("cross_agent_recall", role="member", mode="chat") is False


# ── Partner: husstand, ellers medlems-rettigheder ───────────────────────────

def test_partner_has_husadgang_member_does_not() -> None:
    # `partner` er husstand (ROLE_HOUSEHOLD i core/identity/household.py),
    # `member` er ekstern. Bjørn 22/11-2026: «husagang er tilgængelige for
    # både Michelle og jeg.. resten er ikk brugere her i huset, de er externe.»
    # Husadgangen må derfor ikke følge med member-sættet.
    from core.services.permission_engine import is_tool_allowed

    assert is_tool_allowed("home_assistant", role="partner", mode="chat") is True
    assert is_tool_allowed("home_assistant", role="partner", mode="code") is True
    assert is_tool_allowed("home_assistant", role="member", mode="chat") is False
    assert is_tool_allowed("home_assistant", role="member", mode="code") is False
    assert is_tool_allowed("home_assistant", role="guest", mode="chat") is False


def test_partner_otherwise_member_rights() -> None:
    # Partner deler rettigheder med member bortset fra en EKSPLICIT liste af
    # husstands-tillæg. Listen står navngivet her, så en tilføjelse til
    # `_PARTNER_*_EXTRA` ikke kan snige sig ind: testen fejler, og man må skrive
    # værktøjet her OG tage stilling til om member-sættet også skal have det.
    #
    # 25/11-2026: `search_sessions` og `search_chat_history` kom til, fordi
    # Bjørn bad om at husstanden kan søge i EGNE samtaler. De er BEVIDST ikke
    # lagt i member-sættet: member dækker også eksterne brugere, og den
    # udvidelse er en anden beslutning end husstandens. Sikkerheden er uændret
    # i begge tilfælde, fordi begge værktøjer scope-filtererer på den kaldendes
    # eget id — de kan per konstruktion ikke returnere en andens sessioner.
    from core.services.permission_engine import allowed_tools

    tillæg = {"home_assistant", "search_sessions", "search_chat_history"}
    for mode in ("chat", "code"):
        partner = allowed_tools(role="partner", mode=mode)
        member = allowed_tools(role="member", mode=mode)
        assert partner - member == tillæg, mode
        assert not (member - partner), mode
        # Ekstern bruger må stadig ikke søge i samtale-historik.
        assert "search_sessions" not in member, mode
        assert "search_chat_history" not in member, mode


# ── Member CODE ─────────────────────────────────────────────────────────────

def test_member_code_has_operator_not_server_shell() -> None:
    from core.services.permission_engine import is_tool_allowed

    assert is_tool_allowed("operator_bash", role="member", mode="code") is True
    assert is_tool_allowed("operator_write_file", role="member", mode="code") is True
    # Server-side shell/git/self-kode er IKKE member-code
    assert is_tool_allowed("bash", role="member", mode="code") is False
    assert is_tool_allowed("git_status", role="member", mode="code") is False
    assert is_tool_allowed("skill_create", role="member", mode="code") is False
    assert is_tool_allowed("read_mood", role="member", mode="code") is False


def test_member_code_has_scoped_file_tools() -> None:
    from core.services.permission_engine import is_tool_allowed

    assert is_tool_allowed("edit_file", role="member", mode="code") is True
    assert is_tool_allowed("read_file", role="member", mode="code") is True


# ── Member COWORK ───────────────────────────────────────────────────────────

def test_member_cowork_propose_not_approve() -> None:
    from core.services.permission_engine import allowed_tools

    t = allowed_tools(role="member", mode="cowork")
    assert "propose_plan" in t
    assert "todo_add" in t
    # At godkende Jarvis' self-improvement er owner-autoritet
    assert "approve_proposal" not in t
    assert "approve_plan" not in t


# ── Mode-isolation ──────────────────────────────────────────────────────────

def test_member_mode_isolation() -> None:
    from core.services.permission_engine import is_tool_allowed

    # operator_bash er code-only — IKKE i chat
    assert is_tool_allowed("operator_bash", role="member", mode="code") is True
    assert is_tool_allowed("operator_bash", role="member", mode="chat") is False
    # web_search findes i både chat og code
    assert is_tool_allowed("web_search", role="member", mode="chat") is True
    assert is_tool_allowed("web_search", role="member", mode="code") is True


# ── Fail-closed ─────────────────────────────────────────────────────────────

def test_unknown_role_and_mode_fail_closed() -> None:
    from core.services.permission_engine import allowed_tools

    assert allowed_tools(role="hacker", mode="chat") == set()
    assert allowed_tools(role="member", mode="banana") == set()
    assert allowed_tools(role="", mode="") == set()


# ── Path-jail-flag (informativt for Fase 4) ─────────────────────────────────

def test_workspace_jail_flags() -> None:
    from core.services.permission_engine import requires_workspace_jail

    # Memory i chat + fil-tools i code → jailed til eget workspace
    assert requires_workspace_jail("remember_this", role="member", mode="chat") is True
    assert requires_workspace_jail("edit_file", role="member", mode="code") is True
    # Read-only ekstern web er IKKE jailed (ingen workspace-data)
    assert requires_workspace_jail("web_search", role="member", mode="chat") is False
    # Owner er aldrig jailed (egen session)
    assert requires_workspace_jail("edit_file", role="owner", mode="code") is False


# ── Drift-guard: alle member-navne findes faktisk i registry ────────────────

def test_all_member_tool_names_exist_in_registry() -> None:
    from core.services.permission_engine import _all_member_tool_names
    from core.services.tool_catalog import get_tool_definitions

    registry = {
        (d["function"]["name"] if "function" in d else d["name"])
        for d in get_tool_definitions()
    }
    missing = sorted(_all_member_tool_names() - registry)
    assert not missing, f"Member-allowlist refererer ikke-eksisterende tools: {missing}"
