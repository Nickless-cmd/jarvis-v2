"""Koordinering må ikke matche på chiffertekst.

MÅLT 25/11-2026: `_kilde_synlige` læste `visible_runs.text_preview` og
`visible_work_units.user_message_preview` RÅT. For en medlems-kørsel er begge
felter `enc:v1:...`, så koordineringen matchede på base64 — det kunne give et
falsk «samme arbejde» (chiffertekst der deler tokens med et andet anker) eller
skjule et ægte et (fordi det rigtige svar aldrig blev læst).

Værnet: dekryptér med rækkens EGET `user_id` (koordinering er allerede scopet
til brugeren), og kan nøglen ikke bevises, match på tom tekst frem for chiffer.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import chat_crypto
from core.services import work_coordination as wc

EMNE = "Verificér om decision_gate.py håndhæver den nyeste ændring"


def _iso(minutter_siden: float = 0) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutter_siden)).isoformat()


def _synlig_tur(run_id, *, user="u1", spoerg="", svar="", min_siden=2):
    from core.runtime.db import connect

    with connect() as conn:
        conn.execute(
            "INSERT INTO visible_runs (run_id, lane, provider, model, status, started_at,"
            " finished_at, text_preview, user_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, "primary", "p", "m", "completed", _iso(min_siden), _iso(min_siden), svar, user),
        )
        conn.execute(
            "INSERT INTO visible_work_units (work_id, run_id, status, lane, provider, model,"
            " finished_at, user_message_preview) VALUES (?,?,?,?,?,?,?,?)",
            (f"w-{run_id}", run_id, "completed", "primary", "p", "m", _iso(min_siden), spoerg),
        )


def test_chiffertekst_i_preview_giver_ikke_daekning(isolated_runtime):
    """En kørsel hvis svar er chiffertekst må ikke dække et initiativ.

    Uden værnet ville `_samme_arbejde` læse base64 som om det var et svar.
    """
    chiffer = "enc:v1:AAAA" + "Q2hpZmZlcnRla3N0" * 6
    assert chat_crypto.er_krypteret(chiffer)
    _synlig_tur("visible-chiffer", user="u1", spoerg="", svar=chiffer)

    daek = wc.find_covering_work(EMNE, user_id="u1")
    assert daek is None, f"chiffertekst blev læst som arbejde: {daek}"


def test_klartekst_i_preview_giver_stadig_daekning(isolated_runtime):
    """Værnet må ikke svække den ægte funktion: klartekst dækker som før."""
    _synlig_tur(
        "visible-klar",
        user="u1",
        spoerg="Verificér decision_gate.py mod den nyeste ændring",
        svar="Jeg tjekkede decision_gate.py og den håndhæver ændringen.",
    )

    daek = wc.find_covering_work(EMNE, user_id="u1")
    assert daek is not None, "klartekst skulle stadig dække"
    assert daek.get("kind") == "visible_run"


def test_chiffertekst_fra_anden_bruger_laekker_ikke(isolated_runtime):
    """Scoping gælder uanset kryptering: en andens kørsel dækker ikke min."""
    chiffer = "enc:v1:BBBB" + "QW5kZW5icnVnZXI" * 6
    _synlig_tur("visible-anden", user="u2", spoerg="", svar=chiffer)

    assert wc.find_covering_work(EMNE, user_id="u1") is None
