"""Ærligt ejerskabssignal: `cost_recorded` må ikke påstå en bogføring der fejlede.

Baggrund (målt 25/11-2026): Ollama-adapteren satte `cost_recorded=True`
ubetinget, også når `bogfoer_ollama_kald` havde slugt en fejl og returneret
0.0. De ydre lag springer deres egen bogføring over når flaget er sat — så en
fejlet adapter-bogføring fjernede rækken HELT i stedet for at gøre den dobbelt.
Disse tests låser at flaget afspejler den faktiske skrivning.
"""

from __future__ import annotations

import core.costing.ledger as ledger
from core.services.ollama_usage import (
    bogfoer_ollama_kald,
    bogfoer_ollama_kald_status,
)


def _antal(provider: str, model: str) -> int:
    with ledger.connect() as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM costs WHERE provider=? AND model=?",
                (provider, model),
            ).fetchone()[0]
        )


def test_status_siger_false_naar_bogfoeringen_fejler(isolated_runtime, monkeypatch) -> None:
    """Mutation caught: sæt `skrevet=True` også i except-grenen."""

    def _braek(**_kwargs):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(ledger, "record_cost", _braek)

    pris, skrevet = bogfoer_ollama_kald_status(
        provider="ollama-a2",
        model="honest-fail:cloud",
        input_tokens=100,
        output_tokens=10,
        lane="cheap",
    )

    assert skrevet is False, "et fejlet skriv må ikke meldes som ejerskab"
    assert pris == 0.0
    assert _antal("ollama-a2", "honest-fail:cloud") == 0


def test_status_siger_true_naar_raekken_blev_skrevet(isolated_runtime) -> None:
    """Mutation caught: returnér False også når skrivningen lykkedes."""
    pris, skrevet = bogfoer_ollama_kald_status(
        provider="ollama-a2",
        model="honest-written:cloud",
        input_tokens=100,
        output_tokens=10,
        lane="cheap",
    )

    assert skrevet is True
    assert _antal("ollama-a2", "honest-written:cloud") == 1


def test_gammel_kontrakt_er_stadig_en_float(isolated_runtime) -> None:
    """De 11 eksisterende kaldesteder bruger beløbet, ikke tuple'en."""
    pris = bogfoer_ollama_kald(
        provider="ollama-a2",
        model="honest-float:cloud",
        input_tokens=100,
        output_tokens=10,
        lane="cheap",
    )

    assert isinstance(pris, float), f"wrapperen lækkede en {type(pris).__name__} ud"
