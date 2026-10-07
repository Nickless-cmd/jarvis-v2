"""Den delte klient til den lille lokale model.

Udskilt da kalder nummer to kom til. Kontrakten er bevidst mager: ét ord ud,
``None`` når der ikke er noget svar — og kalderen bestemmer selv hvad tavshed
betyder. De to nuværende kaldere læser det modsat, og det er med vilje.
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


@pytest.mark.parametrize("rå,ventet", [
    ("JA", "JA"), ("ja", "JA"), ("JA.", "JA"), ("  JA, det ville den ", "JA"),
    ("JAVEL", "JAVEL"), ("ÆGTE", "ÆGTE"), ("STØJ", "STØJ"),
    ("", None), ("42", None), ("...", None),
])
def test_foerste_HELE_ord_med_store_bogstaver(rå, ventet):
    """Første ORD, ikke præfiks: «JAVEL» må ikke kunne læses som «JA» af en
    kalder der sammenligner. Derfor returneres hele ordet, ikke et match."""
    from core.services.local_small_model import spoerg_et_ord

    with patch("urllib.request.urlopen", return_value=_Svar(rå)):
        assert spoerg_et_ord("et system", "en bruger") == ventet


@pytest.mark.parametrize("exc", [
    urllib.error.URLError("nede"), TimeoutError("køer"), OSError("ingen rute"),
    ValueError("ugyldigt json"),
])
def test_enhver_fejl_bliver_til_None(exc):
    from core.services.local_small_model import spoerg_et_ord

    with patch("urllib.request.urlopen", side_effect=exc):
        assert spoerg_et_ord("et system", "en bruger") is None


def test_tomt_ind_koster_ikke_et_kald():
    from core.services.local_small_model import spoerg_et_ord

    with patch("urllib.request.urlopen") as u:
        assert spoerg_et_ord("", "noget") is None
        assert spoerg_et_ord("noget", "") is None
    u.assert_not_called()


def test_deadlinen_er_stram_nok_til_prompt_samlingen():
    """Ollama-kald køer 28-91 s når ollama er optaget — dokumenteret som
    cut-off-roden. Målt kald er 0,19 s. Skrues denne værdi op, skal nogen have
    tænkt over at prompt-samlingen har et samlet budget."""
    from core.services.local_small_model import STANDARD_TIMEOUT_S

    assert STANDARD_TIMEOUT_S <= 2.0


def test_timeout_naar_faktisk_ud_til_kaldet():
    from core.services.local_small_model import spoerg_et_ord

    with patch("urllib.request.urlopen", return_value=_Svar("JA")) as u:
        spoerg_et_ord("et system", "en bruger", timeout_s=0.25)
    assert u.call_args.kwargs.get("timeout") == 0.25


def test_base_url_roerer_IKKE_embed_funktionen(monkeypatch):
    """Regression (2/10-2026): base_url pegede på EMBED-værten.

    Her stod ``semantic_memory._ollama_base_url()``, og den peger med vilje på
    den dedikerede embed-vært (``embed_ollama_base_url``, port 11435), som kun
    har ``nomic-embed-text``. Chat-modellen (``qwen3:4b``) ligger på 11434.

    Følgen var tavs og dyr: hvert kald svarede ``None`` straks, og
    ``local_intent_gate`` fejler LUKKET — så gaten sagde nej til ALT i otte
    døgn. Sidste ``gate=1`` i events var 24/9-2026; ingen opdagede det, fordi
    kanalen var slukket og sektionen returnerede tomt alligevel.

    Samme fejl var rettet i ``model_pair_resolver`` 28/9 — den blev blot ikke
    rettet her, hvor kopien stod. Testen pinner at kalderen ikke må genindføres.
    """
    import core.services.local_small_model as m
    import core.services.semantic_memory as sm

    def _boom():
        raise AssertionError("base_url læste embed-værten — det er chat-værten der skal bruges")

    monkeypatch.setattr(sm, "_ollama_base_url", _boom)
    assert m.base_url().startswith("http")


def test_base_url_kommer_fra_chat_vaerten(monkeypatch):
    """Adressen skal tages fra samme kilde som den der FAKTISK kalder chatten."""
    import core.services.local_small_model as m
    import core.services.model_pair_resolver as mpr

    monkeypatch.setattr(mpr, "_chat_ollama_base_url", lambda: "http://chat-vaert:1234")
    assert m.base_url() == "http://chat-vaert:1234"
