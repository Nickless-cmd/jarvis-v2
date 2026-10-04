"""Provider-routeren — «findes ikke» vs. «kunne ikke spørges».

Målt 4/10-2026: `_ollama_model_exists` svarede `False` når Ollama ikke svarede,
og kalderen afviste derfor et gyldigt target med «main agent target must
exist». Fejlen pegede på MODELLEN i stedet for på forbindelsen — og en
installeret model blev erklæret ikke-eksisterende fordi en server var nede.

Tre tilstande, ikke to. De to første er allerede i kilden; den tredje er den
der manglede.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from core.runtime import provider_router as pr


class _Svar:
    """Det minimale af en HTTP-respons som `_ollama_model_exists` læser."""

    def __init__(self, navne: list[str]) -> None:
        self._p = json.dumps({"models": [{"name": n} for n in navne]}).encode()

    def read(self) -> bytes:
        return self._p

    def __enter__(self) -> "_Svar":
        return self

    def __exit__(self, *a) -> bool:
        return False


def _nede(*_a, **_k):
    raise OSError("connection refused")


def _svarer(navne: list[str]):
    return lambda *_a, **_k: _Svar(navne)


@pytest.fixture
def _isoleret(monkeypatch):
    """Ingen ægte registry-fil, og ingen skrivning til runtime.json.

    `select_main_agent_target` kalder `update_visible_execution_settings`, som
    PERSISTERER. En test der rammer den ægte fil ville ændre Bjørns config som
    sidegevinst af at køre suiten.
    """
    monkeypatch.setattr(pr, "load_provider_router_registry", lambda: {})
    monkeypatch.setattr(
        pr,
        "update_visible_execution_settings",
        lambda **kw: SimpleNamespace(
            visible_model_provider=kw.get("visible_model_provider", ""),
            visible_model_name=kw.get("visible_model_name", ""),
            visible_auth_profile=kw.get("visible_auth_profile", ""),
        ),
    )


# ── Hjælperen: tre tilstande ─────────────────────────────────────────────────

def test_ollama_nede_giver_NONE_ikke_False(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", _nede)
    assert pr._ollama_model_exists(registry={}, model="llama3") is None


def test_ollama_svarer_og_modellen_FINDES(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", _svarer(["llama3"]))
    assert pr._ollama_model_exists(registry={}, model="llama3") is True


def test_ollama_svarer_og_modellen_MANGLER(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", _svarer(["mistral"]))
    assert pr._ollama_model_exists(registry={}, model="llama3") is False


# ── Kalde-vejen: det er her fejlen gjorde skade ──────────────────────────────

def test_ollama_der_ikke_svarer_afviser_IKKE_targetet(_isoleret, monkeypatch):
    """Den ÆGTE vej, ikke kun hjælperen.

    Før rettelsen kastede dette «target must exist» for en model der ER
    installeret. En mock på hjælperen kunne ikke se den fejl — den sad i
    grenen der læste svaret.
    """
    monkeypatch.setattr("urllib.request.urlopen", _nede)
    t = pr.select_main_agent_target(provider="ollama", model="llama3")
    assert t["provider"] == "ollama"
    assert t["model"] == "llama3"


def test_ollama_der_svarer_at_modellen_MANGLER_afviser_stadig(_isoleret, monkeypatch):
    """Modprøven: et ÆGTE nej skal stadig afvise.

    Uden den kunne rettelsen gøre enhver validering virkningsløs — «afvis
    aldrig» ville også give grønne tests.
    """
    monkeypatch.setattr("urllib.request.urlopen", _svarer(["mistral"]))
    with pytest.raises(ValueError):
        pr.select_main_agent_target(provider="ollama", model="llama3")
