"""Tests for maintenance/health cadence-producers.

Fokus: hygiene-produceren der lukker kognitive governance-hændelser (10. sep 2026).
Den blev til fordi 931 uløste `gate_enforce`-incidents hobede sig op og fyldte både
panelet og `root_causes()` med governance-støj. Husets klassiske fejl er netop den:
koden skrives, og ingen kalder den — derfor tjekker disse tests både registreringen
OG at produceren faktisk kalder sweepet.
"""
from __future__ import annotations

import inspect

import core.services.internal_cadence_maintenance as M


def _registered() -> dict:
    """Kør registreringen med en indsamler i stedet for den rigtige registry."""
    seen: dict = {}
    M.register_maintenance_producers(lambda spec: seen.__setitem__(spec.name, spec))
    return seen


def test_incident_retention_er_registreret_som_producer():
    """Uden en kadence-producer vokser governance-hændelserne ubegrænset."""
    assert "central_incident_retention" in _registered()


def test_prompt_warmer_sletter_ikke_gyldig_cognitive_cache():
    src = inspect.getsource(_registered()["prompt_assembly_cache_warmer"].run_fn)
    assert "build_cognitive_state_for_prompt" in src
    assert "invalidate_cognitive_state_cache" not in src


def test_incident_retention_koerer_hver_time():
    assert _registered()["central_incident_retention"].cooldown_minutes == 60


def test_incident_retention_kalder_udloebs_funktionen():
    """Produceren skal kalde ALLE udløbs-funktioner — ellers er de bygget og aldrig kørt.
    `expire_gate_enforce_incidents` (2t) tager governance-øjeblikke; `expire_stale_incidents`
    (48t) tager resten; `expire_run_bound_incidents` lukker run-bundne når runnet er
    TERMINALT (en hændelse, ikke en timer); `expire_orphan_incidents` (6t) tager dem uden
    run-tilknytning, som intet levende run bærer."""
    src = inspect.getsource(_registered()["central_incident_retention"].run_fn)
    assert "expire_gate_enforce_incidents" in src
    assert "older_than_hours=2.0" in src
    assert "expire_stale_incidents" in src
    assert "older_than_hours=48.0" in src
    assert "expire_run_bound_incidents" in src
    assert "expire_orphan_incidents" in src
    assert "older_than_hours=6.0" in src


def test_incident_retention_lukker_gamle_governance_incidents(isolated_runtime):
    """Ende-til-ende: en gammel kognitiv governance-hændelse lukkes af produceren."""
    from datetime import UTC, datetime, timedelta

    from core.runtime.db_central_incidents import (
        list_central_incidents, record_central_incident,
    )
    from core.runtime.db_core import connect

    rid = record_central_incident(cluster="proactivity", nerve="verification",
                                  kind="gate_enforce", severity="info", message="gammel")
    old_ts = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
    with connect() as conn:
        conn.execute("UPDATE central_incidents SET ts = ? WHERE id = ?", (old_ts, rid))

    out = _registered()["central_incident_retention"].run_fn(trigger="test")
    assert out["status"] == "ok" and out["expired"] == 1
    assert all(r["id"] != rid for r in list_central_incidents(unresolved_only=True))


# ---------------------------------------------------------------------------
# tmp_cleanup — /tmp er en tmpfs, og pytest rydder ikke sine egne mapper
# ---------------------------------------------------------------------------
#
# Målt 22/11-2026: 25 `pytest-N/`-mapper havde spist alle 16 GB på tmpfs'en, så
# /tmp var 100 % fuld med 4 KB tilbage. Følgen var ikke en pytest-fejl men en
# systemfejl: sampleren tog 148 s med 3 s CPU-tid (hver DB-skrivning ventede på
# plads), codex-agenten døde med CLI_BACKEND_FAILED fordi den ikke kunne skrive
# sit svar, og 36 tests fejlede med Errno 28. Ingen ryddede op, fordi ingen ejede
# opgaven. Disse tests vogter både at produceren findes OG at den ikke kan slette
# en kørsel der er i gang.


def test_tmp_cleanup_er_registreret_som_producer():
    assert "tmp_cleanup" in _registered()


def test_tmp_cleanup_koerer_hver_time():
    assert _registered()["tmp_cleanup"].cooldown_minutes == 60


def test_tmp_cleanup_sletter_gamle_og_bevarer_nye(tmp_path, monkeypatch):
    """Gamle mapper væk, de to nyeste intakte — en igangværende kørsel må ikke
    miste sit arbejdsområde under sig."""
    import os
    import time

    rod = tmp_path / "pytest-of-bs"
    rod.mkdir()
    gamle = []
    for i in range(5):
        m = rod / f"pytest-{i}"
        m.mkdir()
        (m / "data.bin").write_bytes(b"x" * 1024)
        # Aldersforskydning: alle ældre end 30-minutters-grænsen.
        t = time.time() - (7200 + i * 60)
        os.utime(m, (t, t))
        gamle.append(m)

    # De to nyeste skal overleve uanset alder.
    nyeste = sorted(gamle, key=lambda p: p.stat().st_mtime, reverse=True)[:2]

    monkeypatch.setattr(M, "_TMP_PYTEST_ROD", str(rod))
    out = _registered()["tmp_cleanup"].run_fn(trigger="test")

    assert out["status"] == "ok"
    assert out["slettet"] == 3, out
    for m in nyeste:
        assert m.is_dir(), f"nyeste mappe {m.name} blev slettet"
    slettede = [m for m in gamle if not m.is_dir()]
    assert len(slettede) == 3


def test_tmp_cleanup_bevarer_en_aktiv_koersel(tmp_path, monkeypatch):
    """En mappe rørt inden for 30 min er en kørsel der er i gang — den skal
    overleve selv om den ikke er blandt de to nyeste."""
    import os
    import time

    rod = tmp_path / "pytest-of-bs"
    rod.mkdir()
    aktiv = rod / "pytest-aktiv"
    aktiv.mkdir()
    (aktiv / "data.bin").write_bytes(b"x" * 1024)
    # Nyeste mappe er gammel; den AKTIVE er ældre men netop rørt.
    ny1, ny2 = rod / "pytest-ny1", rod / "pytest-ny2"
    for m in (ny1, ny2):
        m.mkdir()
        t = time.time() - 60
        os.utime(m, (t, t))
    t_aktiv = time.time() - 60  # rørt for et minut siden
    os.utime(aktiv, (t_aktiv, t_aktiv))
    # Gør den aktiv mappe ÆLDRE i rækkefølgen ved at sætte de to andre nyere.
    for m in (ny1, ny2):
        t = time.time() - 10
        os.utime(m, (t, t))

    monkeypatch.setattr(M, "_TMP_PYTEST_ROD", str(rod))
    out = _registered()["tmp_cleanup"].run_fn(trigger="test")

    assert out["status"] == "ok"
    assert aktiv.is_dir(), "en mappe rørt for et minut siden blev slettet"


def test_tmp_cleanup_uden_mapper_er_groen(tmp_path, monkeypatch):
    """Ingen pytest-mapper ⇒ ingen fejl. En oprydning der kaster når der intet
    er at rydde, ville gøre produceren til en ny fejlkilde."""
    monkeypatch.setattr(M, "_TMP_PYTEST_ROD", str(tmp_path / "findes-ikke"))
    out = _registered()["tmp_cleanup"].run_fn(trigger="test")

    assert out["status"] == "ok" and out["slettet"] == 0
