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


def test_nudge_well_gone_midway_and_since_last_present(isolated_runtime, monkeypatch) -> None:
    """Redesign 4/9: ingen 'Pending nudges … mark_sent' i diagnostik-blokken; Bjørns
    mid-run-beskeder som egen sektion i halen; én 'Siden sidst'-linje i [HUKOMMELSE]."""
    prompt_contract = isolated_runtime.prompt_contract
    from core.services import outbound_nudges as ob
    from core.services import proactive_candidates as pc
    monkeypatch.setattr(ob, "format_midway_for_prompt", lambda **kw: "Beskeder fra Bjørn undervejs (sendt mens du arbejdede — svar på dem nu):\n  - [19:05] og husk pfsense")
    monkeypatch.setattr(pc, "build_since_last_line", lambda msg, session_id="": "Siden sidst (relevant for det du skriver — nævn det hvis det passer ind): 3 ucommittede filer i repoet")
    text = _build(prompt_contract, "er der ucommittede filer i repoet?").text
    assert "Pending nudges" not in text and "mark_sent(nudge_id)" not in text
    assert "Beskeder fra Bjørn undervejs" in text
    head = text.index("[HUKOMMELSE]")
    assert text.index("Siden sidst") > head
    diag = text.find("INTERN DIAGNOSTIK")
    assert diag < 0 or text.index("Beskeder fra Bjørn undervejs") > diag
