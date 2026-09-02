"""Tests for core/services/autonomous_run_failures.py.

Baggrund: en udbyders fejlbesked blev gemt som Jarvis' EGET svar — 35 gange på
14 dage stod aihubmix' kvote-afvisning ordret i hans mund og dermed i hans
hukommelse. Vagten fandtes, men kun på anden pas, som næsten aldrig kører.

Bjørn 2026-09-02: «de skal ikke lande i hans hukommelse eller mund... ellers
skal de noteres i hans prompt som failed autonome runs, så han er bevidst om at
de er fejlet.»

At kassere teksten er nødvendigt, men ikke nok: så fejler turen usynligt — og
netop dét mønster lod runtime kaste hans egne beslutninger væk i månedsvis.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import core.services.autonomous_run_failures as arf


@pytest.fixture(autouse=True)
def isoleret_state(monkeypatch):
    """Ingen test må røre den rigtige runtime-state."""
    butik: dict = {}
    monkeypatch.setattr(arf, "_kv_get", lambda default: butik.get("v", default))
    monkeypatch.setattr(arf, "_kv_set", lambda value: butik.__setitem__("v", value))
    return butik


def _fejl(**kw):
    d = {"run_id": "visible-abc", "session_id": "auto-dream-20260902",
         "origin": "dream", "provider": "aihubmix", "model": "gratis-model",
         "detail": "kvote opbrugt"}
    d.update(kw)
    return arf.record_failure(**d)


class TestJournalen:
    def test_fejl_journaliseres(self) -> None:
        _fejl()
        poster = arf.recent_failures()
        assert len(poster) == 1
        assert poster[0]["origin"] == "dream"
        assert poster[0]["detail"] == "kvote opbrugt"

    def test_nyeste_foerst(self) -> None:
        _fejl(run_id="en"); _fejl(run_id="to")
        assert [p["run_id"] for p in arf.recent_failures()] == ["to", "en"]

    def test_samme_run_journaliseres_ikke_to_gange(self) -> None:
        _fejl(run_id="samme"); _fejl(run_id="samme", detail="anden tekst")
        poster = arf.recent_failures()
        assert len(poster) == 1
        assert poster[0]["detail"] == "anden tekst"

    def test_journalen_er_afgraenset(self) -> None:
        """En fejlende udbyder må ikke kunne fylde hans prompt."""
        for i in range(40):
            _fejl(run_id="run-%d" % i)
        assert len(arf.recent_failures()) <= arf._MAX_KEPT

    def test_lange_fejltekster_klippes(self) -> None:
        _fejl(detail="x" * 5000)
        assert len(arf.recent_failures()[0]["detail"]) <= arf._MAX_DETAIL_CHARS

    def test_journalisering_kaster_aldrig(self, monkeypatch) -> None:
        """Et værn må aldrig kunne vælte den kørsel det beskytter."""
        monkeypatch.setattr(arf, "_kv_set",
                            lambda v: (_ for _ in ()).throw(RuntimeError("db nede")))
        assert _fejl()["run_id"] == "visible-abc"   # returnerer stadig


class TestPromptBlokken:
    def test_tom_naar_intet_er_sket(self) -> None:
        assert arf.prompt_section() == ""

    def test_fejlen_naevnes(self) -> None:
        _fejl()
        s = arf.prompt_section()
        assert "FEJLEDE AUTONOME KØRSLER" in s
        assert "kvote opbrugt" in s
        assert "dream" in s

    def test_blokken_er_om_ham_ikke_fra_ham(self) -> None:
        """Den må aldrig kunne læses som noget han selv har sagt."""
        _fejl()
        s = arf.prompt_section()
        assert "kasseret" in s
        assert "ikke dine ord" in s
        assert "hukommelse" in s

    def test_lover_ikke_et_vaerktoej_der_ikke_findes(self) -> None:
        """Et hult løfte i prompten er værre end ingen mulighed."""
        _fejl()
        assert "retry_autonomous_run" not in arf.prompt_section()

    def test_gamle_fejl_baeres_ikke_rundt(self) -> None:
        _fejl()
        poster = arf._load()
        poster[0]["at"] = (datetime.now(UTC) - timedelta(days=3)).isoformat()
        arf._kv_set(poster)
        assert arf.prompt_section() == ""

    def test_blokken_har_et_loft(self) -> None:
        for i in range(10):
            _fejl(run_id="r-%d" % i)
        s = arf.prompt_section()
        assert s.count("\n· ") <= arf._PROMPT_MAX_LINES + 1   # +1 = «(+N flere)»
        assert "flere)" in s


class TestGenforsoeg:
    def test_runtime_proever_ikke_af_sig_selv(self) -> None:
        _fejl()
        assert arf.pending_retries() == []

    def test_han_kan_bede_om_det(self) -> None:
        p = _fejl()
        assert arf.request_retry(p["id"]) is True
        assert len(arf.pending_retries()) == 1

    def test_ukendt_id_gør_ingenting(self) -> None:
        _fejl()
        assert arf.request_retry("findes-ikke") is False

    def test_udfoert_genforsoeg_falder_ud_af_koeen(self) -> None:
        p = _fejl()
        arf.request_retry(p["id"])
        arf.mark_retried(p["id"])
        assert arf.pending_retries() == []
