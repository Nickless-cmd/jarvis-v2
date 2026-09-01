"""Tests for core/services/cognitive_state_narrativizer.py.

FUNDET LIVE 2026-09-01: injektionen ``cognitive_state`` — den blok Bjørn
kalder «der hvor hans liv er» — havde en regning fra aihubmix stående i sit
``[SELF]``-anker:

    [COGNITIVE STATE] [SELF] Sorry, to prevent abuse of free resources,
    accounts that have not been recharged can only try 10 times...

Kæden: primær-lane fejlede på tom auth-profil, kaldet faldt til cheap-lane,
ramte gratis-kvoten, og fejlteksten blev gemt som hans selvbeskrivelse.

En fejl i chatten er pinlig. En fejl i [SELF] er noget han bærer videre.
"""

from __future__ import annotations

import pytest

import core.services.cognitive_state_narrativizer as nz

AIHUBMIX = (
    "Sorry, to prevent abuse of free resources, accounts that have not been "
    "recharged can only try 10 times. You can increase the free quota after "
    "recharging; https://console.aihubmix.com/topup"
)


class TestProviderErrorNeverBecomesSelf:
    def test_the_real_incident_is_rejected(self, monkeypatch) -> None:
        monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                            lambda *a, **kw: AIHUBMIX, raising=False)
        assert nz._call_narrativizer_llm("system", "user") is None

    @pytest.mark.parametrize("text", [
        "Rate limit exceeded. Please try again later.",
        '{"error": {"message": "insufficient quota"}}',
        "Invalid API key provided.",
    ])
    def test_other_provider_errors_rejected(self, monkeypatch, text: str) -> None:
        monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                            lambda *a, **kw: text, raising=False)
        assert nz._call_narrativizer_llm("system", "user") is None

    def test_a_real_narrative_survives(self, monkeypatch) -> None:
        """Vagten må ikke æde ægte indhold — heller ikke når det er dystert."""
        line = ("Jeg bærer en uro i dag: tråden om auto-commit er ikke lukket, "
                "og jeg mærker det som vægt frem for hast.")
        monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                            lambda *a, **kw: line, raising=False)
        assert nz._call_narrativizer_llm("system", "user") == line

    def test_danish_text_about_quotas_is_kept(self, monkeypatch) -> None:
        """Han skal kunne FORTÆLLE om kvoter uden at blive censureret."""
        line = ("Jeg mærkede at kvoten løb tør hos en udbyder, og jeg valgte "
                "at flytte mig frem for at vente.")
        monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                            lambda *a, **kw: line, raising=False)
        assert nz._call_narrativizer_llm("system", "user") == line

    def test_empty_result_is_none(self, monkeypatch) -> None:
        monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                            lambda *a, **kw: "   ", raising=False)
        assert nz._call_narrativizer_llm("system", "user") is None

    def test_llm_exception_does_not_propagate(self, monkeypatch) -> None:
        def boom(*a, **kw):
            raise RuntimeError("lane nede")
        monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                            boom, raising=False)
        assert nz._call_narrativizer_llm("system", "user") is None

    def test_guard_failure_does_not_block_content(self, monkeypatch) -> None:
        """Kan vagten ikke køre, må den ikke tage indholdet med sig."""
        monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                            lambda *a, **kw: "et ægte narrativ", raising=False)
        monkeypatch.setattr(
            "core.services.provider_error_guard.looks_like_provider_error",
            lambda t: (_ for _ in ()).throw(RuntimeError("vagt nede")),
            raising=False)
        assert nz._call_narrativizer_llm("system", "user") == "et ægte narrativ"
