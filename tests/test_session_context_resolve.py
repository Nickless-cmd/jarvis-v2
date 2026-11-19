"""Hvilken samtale kører vi i — og findes de kilder der spørges til?

Testen blev skrevet om 19/11-2026, fordi den gamle version var grøn af den
forkerte grund. Den opdigtede to moduler med `monkeypatch.setitem(sys.modules,
…)` — `core.services.visible_run_context` og
`core.services.chat_sessions.current_session_id_ctx` — og beviset dermed en
rækkefølge der aldrig kunne indtræffe i virkeligheden. Begge kilder findes
ikke, så begge import-forsøg faldt i det stille igennem, og resolveren spurgte
reelt kun ét sted.

Målt konsekvens: `staged_edits_tools._current_session_id()` havde sin egen
kopi af opslaget med kun de to døde kilder. Sat til `chat-ABC123` svarede den
stadig `_default`, så alle samtaler delte staging-scope.

Vagten nedenfor er det der manglede: hvert modul og hvert navn resolveren
spørger, skal kunne importeres FOR RIGTIGT. En død kilde kan ikke svare, og
skal derfor ikke stå i listen.
"""
from __future__ import annotations

import importlib

import pytest

from core.identity.workspace_context import reset_context, set_session_id
from core.services.session_context_resolve import aktiv_session_id


@pytest.fixture
def kontekst():
    """Sæt og ryd den levende ContextVar — ikke en efterligning af den."""
    tokens = []

    def saet(sid: str):
        tokens.append(set_session_id(sid))

    yield saet

    for tok in reversed(tokens):
        reset_context(tok)


# ─────────────────────────── den levende kilde ───────────────────────────


def test_den_levende_kontekst_vinder(kontekst):
    kontekst("chat-ABC123")
    assert aktiv_session_id() == "chat-ABC123"


def test_mellemrum_taeller_ikke_som_et_svar(kontekst):
    kontekst("   ")
    assert aktiv_session_id("") == ""


def test_ingen_kontekst_giver_standarden(kontekst):
    kontekst("")
    assert aktiv_session_id() == ""
    assert aktiv_session_id("_default") == "_default"


def test_en_kontekst_der_KASTER_vaelter_ikke_kalderen(monkeypatch):
    """Self-safe: et brud i ContextVar'en må ikke vælte det værktøj der spurgte."""
    mod = importlib.import_module("core.identity.workspace_context")

    def eksploder():
        raise RuntimeError("ingen kontekst")

    monkeypatch.setattr(mod, "current_session_id", eksploder)
    assert aktiv_session_id("_default") == "_default"


# ─────────────────────────── vægten mod døde kilder ───────────────────────────


def test_hver_kilde_resolveren_spoerger_findes_for_rigtigt():
    """Den vagt der manglede.

    En import der fejler i det stille er usynlig: resolveren ser ud som om den
    spørger tre steder, men kun ét af dem kan svare. Derfor læses kilden og
    hvert `from X import Y` efterprøves mod den virkelige verden.

    Uden denne test kunne de to døde kilder stå i månedsvis mens alle andre
    tests var grønne — hvilket er præcis hvad der skete.
    """
    import inspect
    import re

    from core.services import session_context_resolve

    kilde = inspect.getsource(session_context_resolve)
    fund = re.findall(r"from\s+([\w.]+)\s+import\s+([\w]+)", kilde)
    assert fund, "resolveren importerer intet — så måler testen ingenting"

    doede = []
    for modul, navn in fund:
        try:
            m = importlib.import_module(modul)
        except Exception as exc:
            doede.append(f"{modul} (modul findes ikke: {type(exc).__name__})")
            continue
        if not hasattr(m, navn):
            doede.append(f"{modul}.{navn} (modul findes, navnet gør ikke)")

    assert not doede, (
        "resolveren spørger kilder der ikke findes — de kan ikke svare, og "
        "fejlen er usynlig fordi importen falder i det stille:\n  "
        + "\n  ".join(doede)
    )


def test_staged_edits_foelger_samtalen(kontekst):
    """Den konkrete fejl der blev målt: staging-scope stod fast på `_default`.

    Målt 19/11-2026: med `set_session_id('chat-ABC123')` sat returnerede
    `_current_session_id()` stadig `_default`, fordi dens egen kopi af opslaget
    kun kendte to døde kilder. Alle samtaler delte dermed kladder.
    """
    from core.tools.staged_edits_tools import _current_session_id

    kontekst("chat-ABC123")
    assert _current_session_id() == "chat-ABC123"


def test_staged_edits_uden_kontekst_falder_til_default(kontekst):
    from core.tools.staged_edits_tools import _current_session_id

    kontekst("")
    assert _current_session_id() == "_default"
