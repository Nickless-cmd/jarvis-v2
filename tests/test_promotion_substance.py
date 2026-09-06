"""Task 3 (memory repair 2026-09-04): substance gates for memory writers."""
from __future__ import annotations

import pytest

from core.memory.promotion_substance import (
    has_substance,
    is_empty_topic,
    is_telemetry_fragment,
    strip_telemetry_fragments,
    topic_of,
)

TEMPLATE_HMM = "I should keep carrying what helped around hmm. It still feels mere stabilt nu."
TEMPLATE_OPEN = "Det virker værd at holde fast i det, der hjalp omkring open conversation. Det peger stadig mere stabilt nu."
TEMPLATE_SELF = "Det virker værd at holde fast i det, der hjalp omkring [SELF-WAKEUP]. Det peger."
TEMPLATE_TOOL = "I should keep carrying what helped around tool:. It still feels mere stabilt nu."
TEMPLATE_Q = "Det virker værd at holde fast i det, der hjalp omkring ?. Det peger stadig."
PROVIDER_ERR = "Sorry, to prevent abuse of free resources, accounts that have not made a payment are limited."
REAL = "I should keep carrying what helped around pfsense-nøglen flyttet til .env via env_override. It still feels mere stabilt nu."
REAL_DA = "Det virker værd at holde fast i det, der hjalp omkring Michelles iOS test-app plan. Det peger stadig mere stabilt nu."


@pytest.mark.parametrize("text", [TEMPLATE_HMM, TEMPLATE_OPEN, TEMPLATE_SELF, TEMPLATE_TOOL, TEMPLATE_Q, PROVIDER_ERR, "", "kort", "interrupted"])
def test_templates_and_errors_have_no_substance(text):
    assert has_substance(text) is False


@pytest.mark.parametrize("text", [REAL, REAL_DA, "Bjørn bad om at pfSense-nøglen flyttes til .env og at python-dotenv tilføjes til requirements."])
def test_real_content_has_substance(text):
    assert has_substance(text) is True


def test_topic_extraction_from_templates():
    assert topic_of(TEMPLATE_HMM) == "hmm"
    assert topic_of(TEMPLATE_OPEN) == "open conversation"
    assert "pfsense" in topic_of(REAL).lower()


@pytest.mark.parametrize("seg", [
    "Current conductor mode: clarify",
    '"Most salient item: Visible run completed after tools: dbquery"',
    "tick quality trend: stable",
    "[carry] Diverse inner threads (6 types) are all still active.",
    "Loop=none; body=loaded.",
    "Known limitation: forgetting_to_stage_changes_before_commit",
])
def test_telemetry_fragments_detected(seg):
    assert is_telemetry_fragment(seg) is True


@pytest.mark.parametrize("seg", [
    "Diary synthesis: du har pfsense api key i din runtime, check den",
    "Bjørn er bekymret for mine eksistentielle temaer",
])
def test_real_segments_are_not_telemetry(seg):
    assert is_telemetry_fragment(seg) is False


def test_strip_telemetry_keeps_content_and_joiner():
    text = 'Diary synthesis: pfsense api key check + "stor hele" - "Current conductor mode: clarify" - "Most salient item: x" + No active runtime loop'
    out = strip_telemetry_fragments(text)
    assert "pfsense" in out
    assert "conductor" not in out
    assert "Most salient" not in out
    assert "stor hele" in out


def test_strip_all_telemetry_yields_empty():
    assert strip_telemetry_fragments('"Current conductor mode: clarify" - "tick quality trend: st"') == ""


@pytest.mark.parametrize("topic,expected", [
    ("hmm", True), ("?", True), ("open conversation", True), ("[SELF-WAKEUP]", True),
    ("tool:", True), ("Current conductor mode: clarify", True), ("", True),
    ("pfsense nøgle", False), ("Michelles iOS plan", False), ("Hvem er Bjørn", False),
])
def test_is_empty_topic(topic, expected):
    assert is_empty_topic(topic) is expected
