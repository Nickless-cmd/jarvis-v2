"""Agent-løkkens løfte-vagt skal se danske cliffhangere (26/10-2026).

Målt 26/10-2026 på en rigtig Task-agent (asg-1cf81774d262466c, researcher,
read-only-runtime). Den svarede på 1 af 3 spørgsmål og sluttede med:

    «Task schema har kun 5 felter: … Lad mig verificere required-listen.»

Den kaldte intet værktøj bagefter, brugte 5 af 8 tilladte runder, og blev meldt
``completed``. Scout-nudgen i ``run_tool_loop`` fandtes hele tiden og ville have
givet den én runde mere — men den fyrede ikke, fordi ``_promises_action`` ikke
så løftet.

Årsagen er en sproglig asymmetri: ``let me `` stod i ``_PROMISE_EN``, ``lad mig ``
stod ingen steder. Den engelske form var dækket, den danske manglede — samme
fejlklasse som MEMORY-påstanden tidligere samme dag, hvor jeg greppede efter
«godkendt»/«approved» og missede «green-lit».

Testen er et PAR: danske løfter skal fanges, og rene svar må ikke. En vagt der
bare fanger alt er lige så ubrugelig som en der intet fanger — den ville nudge
hver eneste agent for evigt.
"""
from __future__ import annotations

import pytest

from core.services.agent_loop_core import _promises_action

# Den faktiske tekst fra den målte agent. Escape-tegn i kilden ville gøre testen
# afhængig af filens encoding, så den bygges af dele.
MAALT_TEKST = (
    "Task schema har kun 5 felter: description, prompt, subagent_type, model, "
    "run_in_background (linjerne 54-67, f\u00f8r n\u00e6ste _fn linje 72). "
    "Lad mig verificere required-listen."
)


# ── Acceptkriterium 1: den målte tekst skal fanges ──────────────────────────
def test_den_maalte_danske_cliffhanger_fanges():
    assert _promises_action(MAALT_TEKST) is True


# ── Acceptkriterium 2: andre danske cliffhanger-former ──────────────────────
@pytest.mark.parametrize("tekst", [
    "Lad mig verificere required-listen.",
    "Lad mig tjekke det.",
    "Lad mig se p\u00e5 filen.",
    "Lad os unders\u00f8ge det n\u00e6rmere.",
    "Nu tjekker jeg det.",
    "Jeg verificerer lige.",
])
def test_danske_loefter_fanges(tekst):
    assert _promises_action(tekst) is True


# ── Acceptkriterium 3: rene svar maa IKKE fanges ────────────────────────────
@pytest.mark.parametrize("tekst", [
    "Filen har 161 linjer og importerer tre moduler.",
    "Jeg kunne ikke finde filen.",
    "Ja.",
    "",
    "   ",
    "Task-skemaet har 5 felter: description, prompt, subagent_type, model, run_in_background.",
    "Jeg fandt 22 kald i produktionskoden og 31 i hele repoet.",
])
def test_rene_svar_fanges_ikke(tekst):
    assert _promises_action(tekst) is False


# ── Acceptkriterium 4: den engelske form maa ikke regressere ────────────────
@pytest.mark.parametrize("tekst", [
    "Let me verify the required list.",
    "I'll check the file now.",
    "I will look at it.",
])
def test_engelske_loefter_fanges_stadig(tekst):
    assert _promises_action(tekst) is True
