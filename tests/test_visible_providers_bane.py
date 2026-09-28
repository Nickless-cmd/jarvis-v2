"""Chat-vælgeren må kun tilbyde den SYNLIGE bane.

Målt på CT105 28/9-2026: provider-registret har 238 poster fordelt på fem
baner — `cheap` 209, `visible` 12, `local` 10, `coding` 6, `inner_enrichment` 1.
Vælgeren viste **98 modeller fra 21 udbydere**, fordi den kun spurgte «er
providerens credentials klar?» og aldrig «hvilken bane hører modellen til».

Med bane-filteret: **15 modeller fra 3 udbydere** — deepseek, ollama,
openai-codex (plus github-copilot når dens profil er koblet).

Bjørn: «den skal kun vise dem der faktisk er tilgængelige i visible lane».

Cheap-lane er ikke i stykker — den er til swarm og council. aihubmix, kilo,
reka, requesty, xkiro, internlm kan alle køre; de er bare ikke dem man taler
med. En vælger der tilbyder dem, tilbyder et valg der ændrer hvem der svarer.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from apps.api.jarvis_api.routes import chat as rute


REGISTER = {
    "models": [
        # den synlige bane
        {"provider": "deepseek", "model": "deepseek-v4-flash", "lane": "visible", "enabled": True},
        {"provider": "deepseek", "model": "deepseek-v4-pro", "lane": "visible", "enabled": True},
        {"provider": "openai-codex", "model": "gpt-5.5", "lane": "visible", "enabled": True},
        # den lokale halvdel — ollama, ogsaa :cloud
        {"provider": "ollama", "model": "deepseek-v4-pro:cloud", "lane": "local", "enabled": True},
        # cheap: maa ALDRIG med
        {"provider": "deepseek", "model": "deepseek-chat", "lane": "cheap", "enabled": True},
        {"provider": "openrouter", "model": "liquid/lfm-2.5:free", "lane": "cheap", "enabled": True},
        {"provider": "mistral", "model": "codestral-latest", "lane": "cheap", "enabled": True},
        {"provider": "groq", "model": "openai/gpt-oss-120b", "lane": "cheap", "enabled": True},
        # andre arbejdsgange
        {"provider": "github-copilot", "model": "gpt-4o", "lane": "coding", "enabled": True},
        {"provider": "ollama", "model": "deepseek-v4.1-flash:cloud", "lane": "inner_enrichment", "enabled": True},
        # slukket i den rigtige bane — skal stadig ud
        {"provider": "deepseek", "model": "deepseek-v4-gammel", "lane": "visible", "enabled": False},
        # uden bane: ukendt hoerer ikke hjemme i vaelgeren
        {"provider": "deepseek", "model": "deepseek-uden-bane", "enabled": True},
    ]
}


@pytest.fixture
def uden_netvaerk(monkeypatch):
    """Ingen live-ollama og ingen credential-opslag — testen måler BANEN."""
    monkeypatch.setattr(rute, "load_provider_router_registry", lambda: REGISTER, raising=False)
    monkeypatch.setattr(rute, "_list_ollama_models_sync", lambda: [], raising=False)
    import core.runtime.provider_router as pr
    monkeypatch.setattr(pr, "load_provider_router_registry", lambda: REGISTER)
    monkeypatch.setattr(pr, "_credentials_ready", lambda **kw: True)
    return REGISTER


def _modeller(ps: list[dict]) -> set[str]:
    return {m for p in ps for m in p["models"]}


def test_kun_visible_og_local_kommer_med(uden_netvaerk):
    ud = rute._list_visible_providers_sync()
    assert _modeller(ud) == {
        "deepseek-v4-flash", "deepseek-v4-pro", "gpt-5.5", "deepseek-v4-pro:cloud",
    }


def test_cheap_lane_er_UDE(uden_netvaerk):
    """Det var hele fejlen: 167 aktive cheap-modeller stod i vælgeren."""
    m = _modeller(rute._list_visible_providers_sync())
    for cheap in ("deepseek-chat", "liquid/lfm-2.5:free", "codestral-latest",
                  "openai/gpt-oss-120b"):
        assert cheap not in m, cheap


def test_samme_provider_kan_have_modeller_i_BEGGE_baner(uden_netvaerk):
    """deepseek er både visible OG cheap. Filteret skal skære på MODELLEN,
    ikke på udbyderen — ellers ryger enten for meget eller for lidt."""
    m = _modeller(rute._list_visible_providers_sync())
    assert "deepseek-v4-flash" in m
    assert "deepseek-chat" not in m


def test_andre_arbejdsgange_er_ude(uden_netvaerk):
    m = _modeller(rute._list_visible_providers_sync())
    assert "gpt-4o" not in m                      # lane=coding
    assert "deepseek-v4.1-flash:cloud" not in m   # lane=inner_enrichment


def test_slukket_model_kommer_ikke_med_selv_i_rigtig_bane(uden_netvaerk):
    assert "deepseek-v4-gammel" not in _modeller(rute._list_visible_providers_sync())


def test_en_model_UDEN_bane_hoerer_ikke_hjemme(uden_netvaerk):
    """En post uden bane er ukendt. Vælgeren er ikke stedet at gætte —
    et forkert tilbud ændrer hvem der svarer."""
    assert "deepseek-uden-bane" not in _modeller(rute._list_visible_providers_sync())


def test_live_ollama_kommer_stadig_med(uden_netvaerk, monkeypatch):
    """Modeller pulles løbende, og de står ikke i registret før nogen skriver
    dem ind. De er lokale af natur — den live-liste skal ikke bane-filtreres
    væk, ellers forsvinder en nyhentet model fra vælgeren."""
    monkeypatch.setattr(rute, "_list_ollama_models_sync", lambda: ["nymodel:latest"])
    assert "nymodel:latest" in _modeller(rute._list_visible_providers_sync())


def test_provideren_foelger_med_hver_model(uden_netvaerk):
    """Klienten skriver udbyderen under modelnavnet — så den skal være der."""
    for p in rute._list_visible_providers_sync():
        assert p["id"].strip()
        assert p["models"]
