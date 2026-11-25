"""Return-konteksten maa ikke citere en pladsholder som om den var et svar.

`build_return_context` laeser `text_preview` fra den seneste synlige koersel og
lægger den i `last_visible_preview`. Naar raekken tilhoerer et medlem og kalderen
er en daemon uden `user_id`, dekrypterer `recent_visible_runs` med kalderens
noegle og returnerer `PLADSHOLDER_KRYPTERET`. Foer fixet gik pladsholderen
videre som om den var indhold, og «kan ikke bevises» endte i resume-konteksten.

Patch-stedet er `absence_awareness.recent_visible_runs`, fordi modulet binder
navnet med `from core.runtime.db import recent_visible_runs`. At patche
`core.runtime.db.recent_visible_runs` ville ramme en anden reference.
"""

from __future__ import annotations

import core.services.absence_awareness as aa
from core.services.visible_preview_crypto import PLADSHOLDER_KRYPTERET


def _stub_run(monkeypatch, *, text_preview: str, user_message_preview: str = "") -> None:
    """Én synlig koersel med praecis den preview vi vil maale paa."""
    run = {"text_preview": text_preview, "user_message_preview": user_message_preview}
    monkeypatch.setattr(aa, "recent_visible_runs", lambda **_: [run])
    monkeypatch.setattr(aa, "get_latest_cognitive_compass_state", lambda: None)
    monkeypatch.setattr(aa, "list_cognitive_seeds", lambda **_: [])


def test_pladsholder_bliver_ikke_til_et_svar(monkeypatch):
    _stub_run(monkeypatch, text_preview=PLADSHOLDER_KRYPTERET)

    context = aa.build_return_context(idle_hours=6.0)

    assert context["last_visible_preview"] == ""


def test_raa_chiffertekst_bliver_ikke_til_et_svar(monkeypatch):
    _stub_run(monkeypatch, text_preview="enc:v1:AAAABBBBCCCCDDDDEEEEFFFF")

    context = aa.build_return_context(idle_hours=6.0)

    assert context["last_visible_preview"] == ""


def test_klartekst_kommer_stadig_med(monkeypatch):
    _stub_run(monkeypatch, text_preview="Jeg rettede de 175 previews i nat")

    context = aa.build_return_context(idle_hours=6.0)

    assert context["last_visible_preview"] == "Jeg rettede de 175 previews i nat"


def test_kort_fravaer_laeser_slet_ikke_preview(monkeypatch):
    """Under tærsklen er der ingen grund til at hente noget — og ingen chance for at lække."""
    kaldt: list[str] = []

    def _forbudt(**_):
        kaldt.append("kaldt")
        return [{"text_preview": "skulle ikke blive laest"}]

    monkeypatch.setattr(aa, "recent_visible_runs", _forbudt)

    context = aa.build_return_context(idle_hours=1.0)

    assert kaldt == []
    assert context["last_visible_preview"] == ""
