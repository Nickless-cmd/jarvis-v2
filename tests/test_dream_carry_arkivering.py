"""Drømme-carry: arkivering på disk skal vinde over en forældet proces.

Målt 24/10-2026. Fejlen var ikke at drømme blev arkiveret forkert — det var
at `_save()` kun FLETTEDE IND fra disken og aldrig fjernede noget. En proces
der havde indlæst `active=['HC-98']` før arkiveringen skrev derfor drømmen
tilbage som aktiv OG overskrev arkiv-posten:

    før  : active=[]            archive=[HC-98]
    efter: active=['HC-98']     archive=[]        ← arkivet forsvandt

Tre ting skal holde, og de trækker i hver sin retning:

1. En arkiveret drøm må ikke genopstå (det er fejlen).
2. En drøm der IKKE er arkiveret må ikke fjernes (det ville være et for
   aggressivt fix — det ville slette levende drømme).
3. En ulæselig fil må ikke blive til en tavs tom liste (det var den anden
   halvdel: `_load()` havde `except Exception: pass`, så en korrupt fil gav
   en tom aktiv-liste der derefter blev skrevet over den rigtige fil).
"""

from __future__ import annotations

import json

import pytest


def _dream(dream_id: str, confidence: float = 0.8) -> dict:
    return {"dream_id": dream_id, "confidence": confidence, "presented": False}


@pytest.fixture()
def carry(tmp_path, monkeypatch):
    """Isolerer modulet mod en midlertidig fil i stedet for den levende."""
    from core.services import dream_carry_over as dco

    pf = tmp_path / "DREAM_CARRY.json"
    monkeypatch.setattr(dco, "_persist_file", lambda: pf)
    monkeypatch.setattr(dco, "_LOADED", True, raising=False)
    monkeypatch.setattr(dco, "_ACTIVE_DREAMS", [], raising=False)
    monkeypatch.setattr(dco, "_DREAM_ARCHIVE", [], raising=False)
    return dco, pf


def _skriv_disk(pf, *, active=(), archive=()) -> None:
    pf.write_text(
        json.dumps({"active_dreams": list(active), "archive": list(archive)}),
        encoding="utf-8",
    )


def test_arkiveret_droem_genopstaar_ikke(carry) -> None:
    """Kernesagen: en forældet proces må ikke skrive en arkiveret drøm tilbage."""
    dco, pf = carry
    # Processen har indlæst HC-98 som aktiv (før arkiveringen skete).
    dco._ACTIVE_DREAMS[:] = [_dream("HC-98")]
    dco._DREAM_ARCHIVE[:] = []
    # Disken er den NYERE sandhed: HC-98 er arkiveret.
    _skriv_disk(pf, active=[], archive=[_dream("HC-98")])

    dco._save()

    ids = [x.get("dream_id") for x in dco._ACTIVE_DREAMS]
    assert "HC-98" not in ids, (
        "arkiveret drøm blev genoplivet som aktiv — det er præcis fejlen "
        "målt 24/10-2026 (active=[] archive=[HC-98] -> active=['HC-98'] archive=[])"
    )
    skrevet = json.loads(pf.read_text(encoding="utf-8"))
    assert [x.get("dream_id") for x in skrevet["archive"]] == ["HC-98"], (
        "arkiv-posten forsvandt fra disken — den skal bevares, ikke overskrives"
    )
    assert skrevet["active_dreams"] == [], "disken skal ikke indeholde den arkiverede drøm"


def test_ikke_arkiveret_droem_fjernes_ikke(carry) -> None:
    """Et for aggressivt fix ville slette levende drømme. Det skal det ikke."""
    dco, pf = carry
    dco._ACTIVE_DREAMS[:] = [_dream("HC-98"), _dream("HC-C")]
    dco._DREAM_ARCHIVE[:] = []
    # Kun HC-98 er arkiveret på disken.
    _skriv_disk(pf, active=[], archive=[_dream("HC-98")])

    dco._save()

    ids = [x.get("dream_id") for x in dco._ACTIVE_DREAMS]
    assert ids == ["HC-C"], f"kun den arkiverede må fjernes, fik {ids}"


def test_tomt_arkiv_rorer_ingenting(carry) -> None:
    """Uden arkiv på disken er der intet at fjerne — ingen drømme må forsvinde."""
    dco, pf = carry
    dco._ACTIVE_DREAMS[:] = [_dream("HC-A"), _dream("HC-B")]
    dco._DREAM_ARCHIVE[:] = []
    _skriv_disk(pf, active=[], archive=[])

    dco._save()

    ids = [x.get("dream_id") for x in dco._ACTIVE_DREAMS]
    assert ids == ["HC-A", "HC-B"], f"tomt arkiv må ikke fjerne noget, fik {ids}"


def test_ulaeselig_fil_giver_advarsel_ikke_tavshed(carry, caplog) -> None:
    """`_load()` må ikke gøre en korrupt fil til en tavs tom liste."""
    dco, pf = carry
    pf.write_text("{ dette er ikke json", encoding="utf-8")
    dco._ACTIVE_DREAMS[:] = []
    dco._DREAM_ARCHIVE[:] = []

    with caplog.at_level("WARNING"):
        dco._load()

    assert any(
        "dream_carry_over" in r.message and "_load" in r.message for r in caplog.records
    ), "en ulæselig fil skal meldes, ikke sluges — ellers overskrives den rigtige fil"
