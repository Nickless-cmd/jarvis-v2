"""Tests for core/services/visible_runs_outcomes.py.

Fokus: udbyder-fejl-vagten ved persisteringen (2026-09-02).

_persist_session_assistant_message er choke-punktet hvor ALT der bliver til en
assistent-besked passerer. Aihubmix' kvote-afvisning stod ordret i Jarvis' mund
35 gange på 14 dage — og dermed i hans hukommelse — fordi den eksisterende vagt
kun sad på ANDEN pas, som næsten aldrig kører.
"""

from __future__ import annotations

import pytest

import core.services.visible_runs_outcomes as vro

AIHUBMIX = ("Sorry, to prevent abuse of free resources, accounts that have not "
            "been recharged can only try 10 times. You can increase the free "
            "quota after recharging; https://console.aihubmix.com/topup")


class _Run:
    def __init__(self, session_id="auto-dream-20260902"):
        self.run_id = "visible-test"
        self.session_id = session_id
        self.provider = "aihubmix"
        self.model = "gratis-model"


@pytest.fixture
def gemte(monkeypatch):
    ude: list[tuple] = []
    monkeypatch.setattr(vro, "_append_chat_message_with_retry",
                        lambda *a, **k: ude.append((a, k)), raising=False)
    return ude


class TestUdbyderFejlNaarAldrigHansMund:
    def test_den_ægte_haendelse_gemmes_ikke(self, gemte, monkeypatch) -> None:
        journal: list[dict] = []
        monkeypatch.setattr("core.services.autonomous_run_failures.record_failure",
                            lambda **kw: journal.append(kw) or kw, raising=False)
        vro._persist_session_assistant_message(_Run(), AIHUBMIX)
        assert gemte == [], "udbyder-fejlen blev gemt som hans svar"
        assert journal, "fejlen blev tavst kasseret uden at blive journaliseret"
        assert journal[0]["origin"] == "dream"

    def test_et_aegte_svar_gemmes_stadig(self, gemte) -> None:
        vro._persist_session_assistant_message(_Run(), "Jeg har tjekket disken, alt er fint.")
        assert len(gemte) == 1

    def test_dansk_tekst_om_kvoter_censureres_ikke(self, gemte) -> None:
        """Han skal kunne FORTÆLLE om en kvote uden at blive tavs."""
        vro._persist_session_assistant_message(
            _Run(), "Jeg mærkede at kvoten løb tør hos en udbyder, så jeg flyttede mig.")
        assert len(gemte) == 1

    def test_vagtens_fald_maa_ikke_aede_svaret(self, gemte, monkeypatch) -> None:
        monkeypatch.setattr(
            "core.services.provider_error_guard.looks_like_provider_error",
            lambda t: (_ for _ in ()).throw(RuntimeError("vagt nede")), raising=False)
        vro._persist_session_assistant_message(_Run(), "et helt normalt svar")
        assert len(gemte) == 1

    def test_journalens_fald_maa_ikke_gemme_fejlen_alligevel(self, gemte, monkeypatch) -> None:
        """Kan journalen ikke skrive, er teksten stadig ikke hans ord."""
        monkeypatch.setattr("core.services.autonomous_run_failures.record_failure",
                            lambda **kw: (_ for _ in ()).throw(RuntimeError("db nede")),
                            raising=False)
        vro._persist_session_assistant_message(_Run(), AIHUBMIX)
        assert gemte == []


class TestOprindelse:
    @pytest.mark.parametrize("sid,ventet", [
        ("auto-dream-20260902", "dream"),
        ("auto-recurring-20260902", "recurring"),
        ("auto-heartbeat-20260902", "heartbeat"),
        ("chat-439a65c933164392871cabeffc7bdc8c", ""),
        ("", ""),
    ])
    def test_oprindelse_udledes(self, sid: str, ventet: str) -> None:
        assert vro._origin_of_session(sid) == ventet
