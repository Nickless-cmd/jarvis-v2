"""Tests for core/services/prompt_sections/private_layer_sections.py.

Udskilt fra prompt_contract.py (4.732 linjer) 2026-09-02 efter Boy Scout-reglen.
Seks funktioner der alle gør nøjagtig det samme: spørger ét privat undersystem
om en promptblok.

Kontrakten er den de deler, og den eneste der virkelig betyder noget:
**et privat lag må aldrig kunne vælte prompt-bygningen.** Fejler undersystemet,
forsvinder blokken — og Jarvis svarer uden den frem for slet ikke at svare.
De private lag må ifølge CLAUDE.md aldrig overtrumfe den beskyttede kerne;
her er den regel gjort til kode.
"""

from __future__ import annotations

import pytest

import core.services.prompt_sections.private_layer_sections as pls

_SEKTIONER = (
    ("_visible_chronicle_context_section",
     "core.services.chronicle_engine.get_chronicle_context_for_prompt"),
    ("_visible_dream_residue_section",
     "core.services.dream_distillation_daemon.get_dream_residue_for_prompt"),
    ("_visible_unconscious_temperature_field_section",
     "core.services.unconscious_temperature_field.build_unconscious_temperature_hint"),
)


@pytest.mark.parametrize("navn,kilde", _SEKTIONER)
class TestDelteKontrakt:
    def test_indhold_gives_videre(self, monkeypatch, navn: str, kilde: str) -> None:
        monkeypatch.setattr(kilde, lambda *a, **k: "en blok", raising=False)
        assert getattr(pls, navn)() == "en blok"

    def test_tomt_bliver_til_none(self, monkeypatch, navn: str, kilde: str) -> None:
        """Tom streng må ikke ende som en tom sektion i prompten."""
        monkeypatch.setattr(kilde, lambda *a, **k: "", raising=False)
        assert getattr(pls, navn)() is None

    def test_et_privat_lag_maa_ikke_vaelte_prompten(
            self, monkeypatch, navn: str, kilde: str) -> None:
        monkeypatch.setattr(
            kilde, lambda *a, **k: (_ for _ in ()).throw(RuntimeError("lag nede")),
            raising=False)
        assert getattr(pls, navn)() is None


class TestVisualMemory:
    """Den ene der samler flere kilder — delvis fejl må koste delvis blok."""

    def test_kilder_samles(self, monkeypatch) -> None:
        monkeypatch.setattr("core.services.visual_memory.get_latest_visual_memory_for_prompt",
                            lambda: "SYN", raising=False)
        monkeypatch.setattr("core.services.ambient_sound_daemon.get_latest_ambient_sound_for_prompt",
                            lambda: "LYD", raising=False)
        ud = pls._visible_visual_memory_section() or ""
        assert "SYN" in ud and "LYD" in ud

    def test_en_doed_sans_koster_kun_sig_selv(self, monkeypatch) -> None:
        monkeypatch.setattr("core.services.visual_memory.get_latest_visual_memory_for_prompt",
                            lambda: (_ for _ in ()).throw(RuntimeError("kamera nede")),
                            raising=False)
        monkeypatch.setattr("core.services.ambient_sound_daemon.get_latest_ambient_sound_for_prompt",
                            lambda: "LYD", raising=False)
        assert "LYD" in (pls._visible_visual_memory_section() or "")


class TestReEksport:
    def test_prompt_contract_eksporterer_dem_stadig(self) -> None:
        """Bagudkompatibilitet: udskillelsen må ikke brække kaldesteder."""
        import core.services.prompt_contract as pc
        for navn in ("_visible_chronicle_context_section", "_visible_dream_residue_section",
                     "_visible_unconscious_temperature_field_section",
                     "_visible_response_style_hint_section", "_visible_current_pull_section",
                     "_visible_visual_memory_section"):
            assert callable(getattr(pc, navn)), navn
