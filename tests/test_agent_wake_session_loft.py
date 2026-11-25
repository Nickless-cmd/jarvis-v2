"""Agent-vækninger må ikke kunne starte en ubegrænset kæde af synlige ture.

Målt 25/11-2026: ni synlige ture på én brugerbesked. `recovery_limit` bandt
kun inden for ÉN post, og hver ny ventekontrakt skrev sin egen post med
`recovery_attempt: 0`. Loftet her er per SAMTALE.
"""
from __future__ import annotations

import pytest

from core.services import agent_wake_intentions as awi
from core.services import in_flight_runs as ifr


@pytest.fixture()
def journal(tmp_path, monkeypatch):
    """Isolér journalen — testen må ikke røre den levende tilstand."""
    fil = tmp_path / "in_flight_runs.json"
    monkeypatch.setattr(ifr, "_PATH", fil, raising=False)
    monkeypatch.setattr(ifr, "_load", lambda: {}, raising=False)
    yield fil


def _stage(session: str, kontrakt: str) -> dict:
    return awi.stage_wake(
        task_id=f"agentwake-{kontrakt}",
        session_id=session,
        owner_user_id="bjorn",
        message="[SYSTEM — agentvækning] test",
    )


def test_kaeden_arves_fra_samtalen(journal, monkeypatch):
    """Post nr. to i samme samtale starter ikke på nul."""
    poster: dict = {}
    monkeypatch.setattr(ifr, "_mutate", lambda fn: fn(poster))
    monkeypatch.setattr(ifr, "_load", lambda: poster)
    monkeypatch.setattr(ifr, "_iso", lambda: "2026-11-25T09:00:00+00:00")

    foerste = _stage("s1", "k1")
    assert foerste["created"] is True
    assert foerste["chain"] == 1

    # Første post er nu claimet (running) — der findes ingen `recovering`-post,
    # så merge-grenen kan ikke redde os. Det er præcis hullet.
    poster["agentwake-k1"]["status"] = "running"

    anden = _stage("s1", "k2")
    assert anden["created"] is True
    assert anden["chain"] == 2, "kæden skal arves, ikke nulstilles"


def test_loftet_afviser_den_fjerde_vaekning(journal, monkeypatch):
    """Ved loftet skrives ingen ny post — vækningen undertrykkes."""
    poster: dict = {}
    monkeypatch.setattr(ifr, "_mutate", lambda fn: fn(poster))
    monkeypatch.setattr(ifr, "_load", lambda: poster)
    monkeypatch.setattr(ifr, "_iso", lambda: "2026-11-25T09:00:00+00:00")

    for i in range(awi.MAKS_VAEKNINGER_PR_SESSION):
        _stage("s2", f"k{i}")
        poster[f"agentwake-k{i}"]["status"] = "running"

    afvist = _stage("s2", "k-sidste")
    assert afvist.get("suppressed") is True
    assert afvist["created"] is False
    assert "agentwake-k-sidste" not in poster, "der må ikke skrives en ny post"


def test_anden_samtale_er_upavirket(journal, monkeypatch):
    """Loftet er per samtale — en anden session starter sin egen kæde."""
    poster: dict = {}
    monkeypatch.setattr(ifr, "_mutate", lambda fn: fn(poster))
    monkeypatch.setattr(ifr, "_load", lambda: poster)
    monkeypatch.setattr(ifr, "_iso", lambda: "2026-11-25T09:00:00+00:00")

    for i in range(awi.MAKS_VAEKNINGER_PR_SESSION):
        _stage("s3", f"a{i}")
        poster[f"agentwake-a{i}"]["status"] = "running"

    anden_samtale = _stage("s4", "b0")
    assert anden_samtale["created"] is True
    assert anden_samtale["chain"] == 1
