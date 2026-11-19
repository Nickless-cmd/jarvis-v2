"""Nedflytning paa LEVERINGSSIGNAL, ikke kapabilitet.

MAALT 18/11-2026 paa koersler der FAKTISK fik wt_write_file:
    copilot-premium/claude-sonnet-5  ok=9  leveringsfejl=19 (58 %)
    codex-cli/default                ok=17 leveringsfejl=0
    claude-cli/sonnet                ok=19 leveringsfejl=0
Fitness-porten (probe_score/follows) saa ruten som «egnet».
"""
from __future__ import annotations

import pytest

from tests.test_agent_model_policy import pol, PREMIUM, FREE, BJORN, ANDEN  # noqa: F401

TAELLING = {PREMIUM: (9, 19)}


@pytest.fixture
def maalt(monkeypatch):
    monkeypatch.setattr("core.services.agent_model_fitness._levering_taelling",
                        lambda p, m, rolle: TAELLING.get((p, m), (0, 0)))


def test_rute_med_58_pct_leveringsfejl_nedflyttes_for_skriveroller_men_ikke_for_laeseroller(
        pol, maalt):
    pol.cands(PREMIUM, FREE)               # PREMIUM staar som nummer 0
    skriver = pol.route(ANDEN, role="executor")
    laeser = pol.route(ANDEN, role="researcher")

    # (a) skriverollen sendes ikke foerst til ruten med 58 % fejl ...
    assert (skriver["provider"], skriver["model"]) != PREMIUM
    # ... men den er nedflyttet, ikke fjernet
    assert (skriver["candidates"][-1]["provider"], skriver["candidates"][-1]["model"]) == PREMIUM

    # (b) rolle-afgraenset: laeserollen bruger stadig ruten
    assert (laeser["provider"], laeser["model"]) == PREMIUM


def test_tynd_stikproeve_nedflytter_ikke(pol, monkeypatch):
    monkeypatch.setattr("core.services.agent_model_fitness._levering_taelling",
                        lambda p, m, rolle: (1, 3))      # 75 %, men n=4
    pol.cands(PREMIUM, FREE)
    assert pol.route(ANDEN, role="executor")["model"] == PREMIUM[1]
