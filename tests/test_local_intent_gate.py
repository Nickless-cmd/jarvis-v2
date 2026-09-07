"""Intent-gaten: er dét vaerktoej faktisk bestilt?

Ordmatchen finder HVILKET vaerktoej en besked minder om. Den kan ikke afgøre
OM beskeden er en bestilling, og det var nudgens egentlige fejl: 26 af 32 bud
forkerte, og de forkerte var samme slags hver gang — Bjørn taler om systemet
(«Du køre vision i denne session» → hf_vision_analyze).

Testene her holder på de to ting der gør gaten sikker at have i
prompt-samlingen: den **fejler lukket**, og den **venter aldrig længe**.
"""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

import pytest


class _Svar:
    def __init__(self, indhold: str) -> None:
        self._b = json.dumps({"message": {"content": indhold}}).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _med_svar(indhold: str):
    return patch("urllib.request.urlopen", return_value=_Svar(indhold))


@pytest.fixture(autouse=True)
def _uden_cache():
    """Cachen ville lade ét svar farve en senere prøve."""
    with patch("core.services.shared_cache.get", return_value=None), \
         patch("core.services.shared_cache.set"):
        yield


def test_ja_er_ja():
    from core.services.local_intent_gate import er_bestilt

    with _med_svar("JA"):
        assert er_bestilt("hent billederne fra min telefon", "phone_photo") is True


def test_nej_er_nej():
    from core.services.local_intent_gate import er_bestilt

    with _med_svar("NEJ"):
        assert er_bestilt("Du køre vision i denne session", "hf_vision_analyze") is False


@pytest.mark.parametrize("svar", ["", "måske", "JAVEL DET ER SVÆRT", "?", "NEJ, men"])
def test_alt_der_ikke_er_et_klart_ja_er_et_nej(svar):
    """Modellen svarer med ét ord. Alt andet er tvivl, og tvivl koster buddet."""
    from core.services.local_intent_gate import er_bestilt

    with _med_svar(svar):
        assert er_bestilt("en besked", "et_vaerktoej") is False


# ---------------------------------------------------------------------------
# Fejler LUKKET. Gaten sidder i prompt-samlingen, og ollama-kald koeer 28-91 s
# naar ollama er optaget — det er dokumenteret som selve cut-off-roden. En
# gate der fejlede AABENT ville slippe stoejen igennem praecis naar systemet
# er presset.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exc", [
    urllib.error.URLError("nede"),
    TimeoutError("for langsom"),
    OSError("ingen forbindelse"),
    ValueError("ugyldigt svar"),
])
def test_enhver_fejl_giver_nej(exc):
    from core.services.local_intent_gate import er_bestilt

    with patch("urllib.request.urlopen", side_effect=exc):
        assert er_bestilt("hent billederne fra min telefon", "phone_photo") is False


def test_deadline_er_stram_nok_til_prompt_samlingen():
    """Maalt kald er 0,19 s. Bliver denne vaerdi skruet op, skal nogen have
    taenkt over at prompt-samlingen har et samlet budget."""
    from core.services.local_intent_gate import _TIMEOUT_S

    assert _TIMEOUT_S <= 2.0


def test_timeout_gives_videre_til_urlopen():
    from core.services.local_intent_gate import _TIMEOUT_S, er_bestilt

    with patch("urllib.request.urlopen", return_value=_Svar("JA")) as u:
        er_bestilt("en besked", "et_vaerktoej")
    assert u.call_args.kwargs.get("timeout") == _TIMEOUT_S


def test_tom_besked_koster_ikke_et_kald():
    from core.services.local_intent_gate import er_bestilt

    with patch("urllib.request.urlopen") as u:
        assert er_bestilt("", "phone_photo") is False
        assert er_bestilt("noget", "") is False
    u.assert_not_called()


def test_eksemplerne_i_prompten_roerer_ikke_maalesaettet():
    """Første udgave brugte de faktiske fejl som eksempler og scorede 100 % —
    paa sig selv. Rene eksempler holdt tallet: 5 af 5, 26 af 26 afvist."""
    from core.services.local_intent_gate import _SKABELON

    for lukket in ("vision", "look_around", "listen", "gate", "commit"):
        assert lukket not in _SKABELON.lower(), (
            "%s er baade eksempel og maalt fejl — gaten maaler paa sig selv" % lukket
        )
