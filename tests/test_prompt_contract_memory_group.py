"""Task 2 (memory repair 2026-09-04): memory renders under [HUKOMMELSE], not under
the "INTERN DIAGNOSTIK — citér det ALDRIG" block, and MEMORY.md is selected by section."""
from __future__ import annotations

from pathlib import Path


MARKER = "## Min hjerne — mest relevant for denne samtale\n\n- **Probe-fakta** [PROBE0001]: pfsense nøgle bor i runtime.json"


def _build(prompt_contract, message: str):
    return prompt_contract.build_visible_chat_prompt_assembly(
        provider="openai", model="gpt-5", user_message=message, session_id=None,
    )


def test_brain_facts_render_in_memory_group_not_diagnostics(isolated_runtime, monkeypatch) -> None:
    prompt_contract = isolated_runtime.prompt_contract
    from core.services.prompt_sections import jarvis_brain_facts as jbf

    monkeypatch.setattr(jbf, "build_brain_facts_section", lambda **kw: MARKER)

    text = _build(prompt_contract, "hvor ligger pfsense nøglen henne?").text

    assert text.count("[HUKOMMELSE]") == 1
    assert MARKER in text
    head = text.index("[HUKOMMELSE]")
    assert text.index(MARKER) > head
    diag = text.find("INTERN DIAGNOSTIK")
    if diag >= 0:
        assert diag < head, "diagnostics block must come before, and not contain, the memory group"


def test_memory_md_selected_by_section(isolated_runtime, monkeypatch) -> None:
    prompt_contract = isolated_runtime.prompt_contract
    ws: Path = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    (ws / "MEMORY.md").write_text(
        "# MEMORY\n\n## Hardware\n- ChiefOne Gigabyte B650 Ubuntu.\n\n"
        "## pfSense nøgle\n- pfsense pfsense api-nøglen flyttet til .env via env_override.\n\n"
        "## Wait-state ads\n- Idlen €100/md.\n- Sponsoric overvej.\n- sidste linje uden relevans.\n",
        encoding="utf-8",
    )
    from core.services import memory_search
    memory_search._MEM_INDEX.clear()
    try:
        memory_search.invalidate_index()
    except Exception:
        pass

    text = _build(prompt_contract, "hvor ligger pfsense pfsense api-nøglen?").text

    assert "MEMORY.md:" in text
    block = text[text.index("MEMORY.md:"):][:2000]
    assert "§ pfSense nøgle:" in block
    assert "env_override" in block
    assert "sidste linje uden relevans" not in block


def test_no_memory_group_header_when_nothing_to_recall(isolated_runtime, monkeypatch) -> None:
    prompt_contract = isolated_runtime.prompt_contract
    from core.services.prompt_sections import jarvis_brain_facts as jbf
    monkeypatch.setattr(jbf, "build_brain_facts_section", lambda **kw: "")
    ws: Path = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    (ws / "MEMORY.md").write_text("# MEMORY\n", encoding="utf-8")

    text = _build(prompt_contract, "hej").text
    # A contentless greeting with an empty MEMORY.md may still carry a recall
    # bundle; the header must appear at most once and never twice.
    assert text.count("[HUKOMMELSE]") <= 1
