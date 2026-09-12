"""Et TOMT svar fra syns-modellen maa ikke vaere tavst (12/9-2026).

ROD-AARSAK (maalt samme dag): `describe_via_deepseek` laeste udelukkende
`choices[0].message.content`. `deepseek-flash` er en taenkende model, og
`max_tokens` daekker BAADE `reasoning_content` og svaret. Ved et foto
braendte taenkningen hele budgettet (finish_reason="length"), `content` var
tom — og funktionen returnerede "" som om billedet var tomt. `analyze_image`
sagde derfor tomt for hvert eneste billede, og fejlen kostede en fejlsoegning
hver gang, fordi den var tavs.

To ting blev rettet: budgettet (400 -> 1600) og den tavse tomhed. Denne test
holder paa det andet — budgettet kan aendre sig, men et svar maa aldrig
forsvinde uden at blive sagt hoejt.
"""
from __future__ import annotations

import io
import json

import pytest

from core.services import vision_backend as VB


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _svar(payload: dict) -> _Resp:
    return _Resp(json.dumps(payload).encode("utf-8"))


def _stub(monkeypatch, payload: dict) -> None:
    # noeglen hentes inde i funktionen fra secrets-modulet
    monkeypatch.setattr("core.runtime.secrets.read_runtime_key",
                        lambda *_a, **_k: "test-noegle")
    monkeypatch.setattr(VB, "_record_cost", lambda *_a, **_k: None)
    monkeypatch.setattr(
        VB.urllib.request, "urlopen", lambda *_a, **_k: _svar(payload))


def test_tomt_content_men_reasoning_giver_ikke_tomt_svar(monkeypatch, caplog):
    """Taenkningen spiste budgettet: svar i `reasoning_content` skal bruges."""
    _stub(monkeypatch, {"choices": [{"message": {
        "content": "", "reasoning_content": "Han har kort haar og skaeg."},
        "finish_reason": "length"}], "usage": {}})
    with caplog.at_level("WARNING"):
        out = VB.describe_via_deepseek("b64", model="deepseek-v4-flash", prompt="?")
    assert out == "Han har kort haar og skaeg."
    assert "tomt svar" in caplog.text, "fejlen skal siges hoejt, ikke ties ihjel"


def test_normalt_svar_gaar_uaendret_igennem(monkeypatch):
    """Regression: den normale vej maa ikke aendre sig."""
    _stub(monkeypatch, {"choices": [{"message": {"content": "  Et rigtigt svar.  "},
                                     "finish_reason": "stop"}], "usage": {}})
    out = VB.describe_via_deepseek("b64", model="deepseek-v4-flash", prompt="?")
    assert out == "Et rigtigt svar."


def test_helt_tomt_svar_uden_reasoning_returnerer_tomt(monkeypatch):
    """Intet content OG ingen reasoning: der er intet at returnere — ikke en loegn."""
    _stub(monkeypatch, {"choices": [{"message": {"content": ""},
                                     "finish_reason": "stop"}], "usage": {}})
    assert VB.describe_via_deepseek("b64", model="deepseek-v4-flash", prompt="?") == ""
