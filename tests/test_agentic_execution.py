def test_agentic_execution_module_has_no_session_identifier():
    import inspect
    import core.services.agentic_execution as agentic_execution

    assert "session_id" not in inspect.getsource(agentic_execution)


# --- Wire-formatet for værktøjs-transkriptet -------------------------------
# MÅLT 25/10-2026: Ollama og OpenAI er ikke enige om ``arguments``. OpenAI vil
# have en JSON-STRENG, Ollama vil have det OBJEKT den selv gav. OpenAI-formen
# gav HTTP 400 mod 127.0.0.1:11434, og routningen faldt derefter tilbage til en
# udbyder UDEN værktøjer — så rutinen kaldte værktøjet rigtigt, fik resultatet,
# og svarede «jeg har ikke adgang». Testene låser de to formater fast.

def _fang_transkript(monkeypatch, provider: str):
    """Kør driveren med en fanget ``messages``-liste; returnér den."""
    from core.services import non_visible_lane_execution as lane
    from core.services.agentic_execution import (
        AgenticRequest, ToolResult, _ProviderDriver,
    )

    fanget: dict[str, object] = {}

    def falsk(**kwargs):
        fanget["messages"] = kwargs.get("messages")
        fanget["tools"] = kwargs.get("tools")
        fanget["lane"] = kwargs.get("lane")
        return {"output": "ok", "tool_calls": [], "usage": {}}

    monkeypatch.setattr(lane, "execute_with_role_or_fallback", falsk)
    driver = _ProviderDriver()
    driver.complete(AgenticRequest(
        prompt="opgaven",
        provider=provider,
        model="en-model",
        round_number=2,
        prior_results=(
            ToolResult("call-1", "madopskrift", "16 opskrifter",
                       arguments={"soegning": "kylling"}),
        ),
        tools=({"type": "function", "function": {"name": "madopskrift"}},),
    ))
    return fanget


def test_ollama_transkript_echoer_argumenter_som_objekt(monkeypatch):
    fanget = _fang_transkript(monkeypatch, "ollama")
    messages = fanget["messages"]

    assistant = messages[1]
    assert assistant["role"] == "assistant"
    arguments = assistant["tool_calls"][0]["function"]["arguments"]
    # Ollama parser objektet selv — en streng giver HTTP 400.
    assert isinstance(arguments, dict), "Ollama kraever arguments som objekt"
    assert arguments == {"soegning": "kylling"}, "argumenterne skal echoes, ikke tommes"

    svar = messages[2]
    assert svar["role"] == "tool"
    assert svar["content"] == "16 opskrifter"
    # Ollama matcher ikke på id — feltet må ikke sendes i dens wire-format.
    assert "tool_call_id" not in svar


def test_openai_transkript_bruger_streng_og_id(monkeypatch):
    fanget = _fang_transkript(monkeypatch, "deepseek")
    messages = fanget["messages"]

    assistant = messages[1]
    arguments = assistant["tool_calls"][0]["function"]["arguments"]
    assert isinstance(arguments, str), "OpenAI-formatet kraever en JSON-streng"

    svar = messages[2]
    assert svar["tool_call_id"] == "call-1"


def test_vaerktoejskørsel_gaar_paa_primaer_lanen(monkeypatch):
    """En værktøjs-kørsel må ikke falde til cheap-puljen: den tager ikke tools."""
    fanget = _fang_transkript(monkeypatch, "ollama")
    assert fanget["lane"] == "primary"
    assert fanget["tools"], "værktøjsskemaet skal med naar der er et"
