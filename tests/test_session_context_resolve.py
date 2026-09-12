"""Hvilken samtale koerer vi i — og i hvilken raekkefoelge spoerges der?"""
import sys
import types

import pytest

from core.services.session_context_resolve import aktiv_session_id


@pytest.fixture
def falske_kilder(monkeypatch):
    """Erstat de to ContextVar-moduler med noget vi kan styre.

    De rigtige saettes af run-loekken og chat-maskineriet, og ingen af delene
    koerer i en unit-test. Uden den her ville testen kun kunne maale
    fallbacken - altsaa netop ikke raekkefoelgen, som er det der betyder noget.
    """
    def saet(synlig: str | None, chat: str | None):
        for navn, vaerdi, felt in (
            ("core.services.visible_run_context", synlig, "current_session_id"),
            ("core.services.chat_sessions", chat, "current_session_id_ctx"),
        ):
            if vaerdi is None:
                monkeypatch.setitem(sys.modules, navn, types.ModuleType(navn))
                continue
            mod = types.ModuleType(navn)
            setattr(mod, felt, lambda v=vaerdi: v)
            monkeypatch.setitem(sys.modules, navn, mod)
    return saet


def test_den_synlige_loekke_vinder(falske_kilder):
    # Den er taettere paa det brugeren kigger paa.
    falske_kilder("fra-run", "fra-chat")
    assert aktiv_session_id() == "fra-run"


def test_chat_bruges_naar_den_synlige_er_tom(falske_kilder):
    falske_kilder("", "fra-chat")
    assert aktiv_session_id() == "fra-chat"


def test_en_kilde_der_KASTER_springes_over(falske_kilder, monkeypatch):
    # Self-safe: en manglende ContextVar maa aldrig vaelte det vaerktoej der
    # spurgte.
    mod = types.ModuleType("core.services.visible_run_context")
    def eksploder():
        raise RuntimeError("ingen kontekst")
    mod.current_session_id = eksploder
    monkeypatch.setitem(sys.modules, "core.services.visible_run_context", mod)
    chat = types.ModuleType("core.services.chat_sessions")
    chat.current_session_id_ctx = lambda: "fra-chat"
    monkeypatch.setitem(sys.modules, "core.services.chat_sessions", chat)
    assert aktiv_session_id() == "fra-chat"


def test_mellemrum_taeller_ikke_som_et_svar(falske_kilder):
    falske_kilder("   ", "fra-chat")
    assert aktiv_session_id() == "fra-chat"


def test_ingen_kilder_giver_standarden(falske_kilder, monkeypatch):
    falske_kilder(None, None)
    monkeypatch.setitem(sys.modules, "core.identity.workspace_context",
                        types.ModuleType("core.identity.workspace_context"))
    assert aktiv_session_id() == ""
    assert aktiv_session_id("_default") == "_default"
