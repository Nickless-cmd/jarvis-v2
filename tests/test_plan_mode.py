"""Plan mode er en servertilstand på code-fladen — ikke et tekstpræfiks."""
from __future__ import annotations

import asyncio
from pathlib import Path


def test_plan_mode_persisteres_paa_sessionen(isolated_runtime):
    from core.services.chat_sessions import create_chat_session
    from core.services.plan_mode import session_plan_mode, set_session_plan_mode

    session = create_chat_session(kind="code")
    sid = str(session["id"])
    assert session_plan_mode(sid) is False

    set_session_plan_mode(sid, True)
    assert session_plan_mode(sid) is True
    set_session_plan_mode(sid, False)
    assert session_plan_mode(sid) is False


def test_prompten_findes_kun_i_aktiv_plan_mode():
    from core.services.plan_mode import prompt_section, stream_context

    assert prompt_section() is None

    async def _inside() -> str | None:
        async with stream_context(True):
            return prompt_section()

    prompt = asyncio.run(_inside())
    assert prompt is not None
    assert "må ikke ændre repo" in prompt
    assert "propose_plan" in prompt


def test_plan_mode_tillader_laesning_og_planforslag_men_blokerer_mutation():
    from core.services.plan_mode import stream_context, tool_allowed

    async def _verdicts() -> tuple[bool, ...]:
        async with stream_context(True):
            return (
                tool_allowed("read_file", {"path": "README.md"}),
                tool_allowed("propose_plan", {"title": "Plan"}),
                tool_allowed("bash", {"command": "git status --short"}),
                tool_allowed("write_file", {"path": "x", "content": "y"}),
                tool_allowed("bash", {"command": "echo y > x"}),
                tool_allowed("send_discord_dm", {"text": "hej"}),
            )

    assert asyncio.run(_verdicts()) == (True, True, True, False, False, False)


def test_plan_mode_filtrerer_toolkataloget():
    from core.services.plan_mode import filter_definitions, stream_context

    defs = [
        {"type": "function", "function": {"name": name}}
        for name in ("read_file", "bash", "write_file", "propose_plan")
    ]

    async def _filtered() -> list[str]:
        async with stream_context(True):
            return [d["function"]["name"] for d in filter_definitions(defs)]

    assert asyncio.run(_filtered()) == ["read_file", "bash", "propose_plan"]


def test_planvaerktoejer_er_code_only():
    from core.tools.tool_scoping import allowed_tool_names

    names = ["list_plans", "propose_plan", "revise_plan"]
    assert allowed_tool_names(role="owner", scope="code", all_names=names) == set(names)
    assert allowed_tool_names(role="owner", scope="chat", all_names=names) == set()


def test_stream_request_baerer_plan_mode_som_data_ikke_tekst():
    from apps.api.jarvis_api.routes.chat import ChatStreamRequest

    request = ChatStreamRequest(message="undersøg arkitekturen", plan_mode=True)
    assert request.plan_mode is True
    assert request.message == "undersøg arkitekturen"


def test_chatklienten_har_ingen_falsk_plan_mode():
    source = Path("apps/ui/src/components/chat/Composer.jsx").read_text(encoding="utf-8")
    assert "[Plan mode]" not in source
    assert "composer-plan-btn" not in source

    code_view = Path("apps/jarvis-desk/src/views/CodeView.tsx").read_text(encoding="utf-8")
    chat_view = Path("apps/jarvis-desk/src/views/ChatView.tsx").read_text(encoding="utf-8")
    assert "showPlanMode={true}" in code_view
    assert "showPlanMode={true}" not in chat_view
