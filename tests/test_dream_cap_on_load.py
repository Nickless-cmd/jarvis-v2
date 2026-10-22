"""Loftet skal håndhæves ved LÆSNING, ikke kun ved næste skrivning.

Målt 22/10-2026: `_enforce_active_cap` blev kun kaldt fra `adopt_dream`. En
`DREAM_CARRY.json` med 28 aktive drømme blev derfor indlæst som 28 og forblev
28 indtil producenten tilfældigvis kaldte adopt igen — så loftet beskrev næste
skrivning, ikke tilstanden. Hver ny proces startede med den samme oppustede
liste, uanset hvor mange gange loftet ellers havde virket.

Det er forskellen mellem en regel og en tilstand: en regel der kun gælder ved
skrivning kan ikke rette noget der allerede er skrevet.
"""
from __future__ import annotations

import json

from core.services import dream_carry_over as dco


def _dream(i: int, confidence: float = 0.5) -> dict:
    return {
        "dream_id": f"disk{i}",
        "content": f"Drøm {i}",
        "confidence": confidence,
        "status": "active",
        "presented": True,
        "presented_in_session": "",
        "confirmed": False,
        "session_carry_count": 1,
        "confirmed_sessions": 0,
        "adopted_at": f"2026-10-{10 + (i % 10):02d}T00:00:00Z",
        "updated_at": "2026-10-20T00:00:00Z",
    }


def _isoler(monkeypatch, tmp_path, antal: int):
    """Skriv en DREAM_CARRY.json på disk og nulstil modulets hukommelse."""
    pf = tmp_path / "DREAM_CARRY.json"
    pf.write_text(
        json.dumps(
            {"active_dreams": [_dream(i) for i in range(antal)], "archive": []},
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(dco, "_persist_file", lambda: pf)
    monkeypatch.setattr(dco, "_ACTIVE_DREAMS", [])
    monkeypatch.setattr(dco, "_DREAM_ARCHIVE", [])
    monkeypatch.setattr(dco, "_LOADED", False)
    return pf


def test_indlaesning_haandhaever_loftet(monkeypatch, tmp_path):
    """28 på disk → 12 i hukommelsen. Uden dette er loftet kun en skrive-regel."""
    _isoler(monkeypatch, tmp_path, dco._MAX_ACTIVE_DREAMS + 16)

    dco._ensure_loaded()

    assert len(dco._ACTIVE_DREAMS) == dco._MAX_ACTIVE_DREAMS, (
        "indlæsningen efterlod flere aktive drømme end loftet tillader — så "
        "cappen gælder kun næste adopt, ikke den tilstand der faktisk er"
    )


def test_indlaesning_skriver_resultatet_til_disk(monkeypatch, tmp_path):
    """Cappen skal overleve processen — ellers ser næste opstart de samme 28."""
    pf = _isoler(monkeypatch, tmp_path, dco._MAX_ACTIVE_DREAMS + 16)

    dco._ensure_loaded()

    paa_disk = json.loads(pf.read_text(encoding="utf-8"))
    assert len(paa_disk["active_dreams"]) == dco._MAX_ACTIVE_DREAMS
    assert len(paa_disk["archive"]) == 16, (
        "de cappede drømme skal stå i arkivet på disken, ikke bare forsvinde"
    )


def test_normal_indlaesning_skriver_intet(monkeypatch, tmp_path):
    """Under loftet må load ikke skrive: en processtart skal ikke røre filen."""
    pf = _isoler(monkeypatch, tmp_path, 3)
    foer = pf.stat().st_mtime_ns

    dco._ensure_loaded()

    assert len(dco._ACTIVE_DREAMS) == 3
    assert pf.stat().st_mtime_ns == foer, (
        "load under loftet skrev til filen — så koster hver processtart et "
        "unødigt filskriv og en ændret mtime"
    )


def test_bekraeftet_droem_overlever_indlaesningens_cap(monkeypatch, tmp_path):
    """Bekræftede drømme uddybes — heller ikke ved load må de arkiveres."""
    pf = tmp_path / "DREAM_CARRY.json"
    drømme = [_dream(i) for i in range(dco._MAX_ACTIVE_DREAMS + 10)]
    drømme[0]["confirmed"] = True
    drømme[0]["confidence"] = 0.1  # svagest muligt — skal stadig beskyttes
    pf.write_text(
        json.dumps({"active_dreams": drømme, "archive": []}, indent=2),
        encoding="utf-8",
    )
    monkeypatch.setattr(dco, "_persist_file", lambda: pf)
    monkeypatch.setattr(dco, "_ACTIVE_DREAMS", [])
    monkeypatch.setattr(dco, "_DREAM_ARCHIVE", [])
    monkeypatch.setattr(dco, "_LOADED", False)

    dco._ensure_loaded()

    ids = {d["dream_id"] for d in dco._ACTIVE_DREAMS}
    assert "disk0" in ids, "en bekræftet drøm blev arkiveret af load-cappen"
