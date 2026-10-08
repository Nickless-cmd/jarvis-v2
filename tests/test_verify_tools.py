"""Tests for core/tools/verify_tools.py.

Vagt-filen `enforce-test-coverage` kræver en test pr. `core/`-modul. Her er den.

Den vigtigste test er `test_findes_bag_1mb_graensen`: den beskriver den fejl
der blev fundet 8/10-2026. `verify_file_contains` læste fast 1 MB og svarede
«expected_substring not present in file» om alt derefter — også når strengen
FAKTISK stod i filen. MEMORY.md er 1,16 MB, så en sektion skrevet til halen
blev rapporteret som «ikke fundet» af netop det værktøj der skal bevise at en
skrivning landede. Det er et falsk negativ i den farlige retning: man «retter»
noget der var rigtigt.

Testene kalder funktionerne direkte. De er rene — ingen DB, ingen netværk,
ingen subprocess ud over den ene der monkeypatches væk.
"""
from __future__ import annotations

import urllib.error

from core.tools.verify_tools import (
    _exec_verify_endpoint_responds,
    _exec_verify_file_contains,
    _exec_verify_service_active,
)

# --------------------------------------------------------------------------
# verify_file_contains
# --------------------------------------------------------------------------


def test_uden_path_er_en_fejl() -> None:
    r = _exec_verify_file_contains({})
    assert r["status"] == "error"


def test_manglende_fil_og_must_exist_giver_failed(tmp_path) -> None:
    r = _exec_verify_file_contains({"path": str(tmp_path / "findes-ikke.txt")})
    assert r["status"] == "failed"
    assert r["reason"] == "file does not exist"


def test_manglende_fil_med_must_exist_false_er_ok(tmp_path) -> None:
    r = _exec_verify_file_contains(
        {"path": str(tmp_path / "findes-ikke.txt"), "must_exist": False}
    )
    assert r["status"] == "ok"
    assert r["exists"] is False


def test_uden_expected_er_et_rent_eksistens_tjek(tmp_path) -> None:
    p = tmp_path / "a.txt"
    p.write_text("noget", encoding="utf-8")
    r = _exec_verify_file_contains({"path": str(p)})
    assert r["status"] == "ok"
    assert r["exists"] is True
    assert r["bytes"] == len("noget")


def test_fundet_substring(tmp_path) -> None:
    p = tmp_path / "a.txt"
    p.write_text("hej med dig", encoding="utf-8")
    r = _exec_verify_file_contains({"path": str(p), "expected_substring": "med dig"})
    assert r["status"] == "ok"
    assert r["found_substring"] is True


def test_ikke_fundet_er_failed_og_ikke_error(tmp_path) -> None:
    """Et negativt svar er «failed» — tjekket kørte, forventningen holdt ikke."""
    p = tmp_path / "a.txt"
    p.write_text("hej med dig", encoding="utf-8")
    r = _exec_verify_file_contains({"path": str(p), "expected_substring": "ZZZ_FINDES_IKKE"})
    assert r["status"] == "failed"
    assert r["found_substring"] is False
    # Hele filen blev gennemsøgt — ikke kun et prefix.
    assert r["searched_bytes"] == p.stat().st_size


def test_findes_bag_1mb_graensen(tmp_path) -> None:
    """Regression 8/10-2026: et træf i filens hale må ikke meldes som fraværende.

    Før fixet læste værktøjet fast 1 MB. MEMORY.md er 1,16 MB, og en sektion
    der lå efter 1 MB blev rapporteret som «not present» mens den var der.
    """
    p = tmp_path / "stor.md"
    hale = "## Sektion der ligger efter 1 MB\n\nmarkoer_ST_DYB"
    p.write_bytes(b"x" * (1024 * 1024 + 5000) + hale.encode("utf-8"))
    assert p.stat().st_size > 1024 * 1024  # filen er reelt over grænsen

    r = _exec_verify_file_contains({"path": str(p), "expected_substring": "markoer_ST_DYB"})
    assert r["status"] == "ok", "et træf efter 1 MB blev meldt som fraværende"
    assert r["found_substring"] is True


def test_findes_helt_til_slut_i_filen(tmp_path) -> None:
    p = tmp_path / "stor.md"
    p.write_bytes(b"y" * (2 * 1024 * 1024) + b"SIDSTE_LINJE_HER")
    r = _exec_verify_file_contains({"path": str(p), "expected_substring": "SIDSTE_LINJE_HER"})
    assert r["found_substring"] is True


def test_traef_der_krydser_en_chunk_groense(tmp_path) -> None:
    """Søgningen streamer i 256 KB-chunks; overlap skal fange et træf der deler."""
    p = tmp_path / "kryds.bin"
    needle = "GRAENSE_TEST_STRENG"
    chunk = 256 * 1024
    p.write_bytes(b"A" * (chunk - 5) + needle.encode() + b"B" * 100)

    r = _exec_verify_file_contains({"path": str(p), "expected_substring": needle})
    assert r["found_substring"] is True


def test_flerbyte_tegn_findes(tmp_path) -> None:
    """Dansk tekst er UTF-8; opdelingen sker på bytes, ikke på tegn."""
    p = tmp_path / "dansk.md"
    p.write_bytes(b"a" * (256 * 1024 - 3) + "æøå — tankestreg".encode("utf-8"))
    r = _exec_verify_file_contains({"path": str(p), "expected_substring": "æøå — tankestreg"})
    assert r["found_substring"] is True


def test_tom_fil_uden_traef(tmp_path) -> None:
    p = tmp_path / "tom.txt"
    p.write_bytes(b"")
    r = _exec_verify_file_contains({"path": str(p), "expected_substring": "noget"})
    assert r["status"] == "failed"
    assert r["searched_bytes"] == 0


# --------------------------------------------------------------------------
# verify_service_active
# --------------------------------------------------------------------------


def test_service_ugyldigt_navn_afvises() -> None:
    r = _exec_verify_service_active({"name": "foo; rm -rf /"})
    assert r["status"] == "error"


def test_service_uden_navn_afvises() -> None:
    r = _exec_verify_service_active({})
    assert r["status"] == "error"


def test_service_aktiv(monkeypatch) -> None:
    class _R:
        stdout = "active\n"

    monkeypatch.setattr(
        "core.tools.verify_tools.subprocess.run", lambda *a, **k: _R()
    )
    r = _exec_verify_service_active({"name": "jarvis-api"})
    assert r["status"] == "ok"
    assert r["active"] is True


def test_service_ikke_aktiv_er_failed(monkeypatch) -> None:
    class _R:
        stdout = "inactive\n"

    monkeypatch.setattr(
        "core.tools.verify_tools.subprocess.run", lambda *a, **k: _R()
    )
    r = _exec_verify_service_active({"name": "jarvis-api"})
    assert r["status"] == "failed"
    assert r["actual_state"] == "inactive"


# --------------------------------------------------------------------------
# verify_endpoint_responds
# --------------------------------------------------------------------------


def test_endpoint_ugyldig_scheme() -> None:
    r = _exec_verify_endpoint_responds({"url": "ftp://x/y"})
    assert r["status"] == "error"


def test_endpoint_uden_url() -> None:
    r = _exec_verify_endpoint_responds({})
    assert r["status"] == "error"


def test_endpoint_http_fejl_laeses_som_statuskode(monkeypatch) -> None:
    """En 404 er et svar, ikke en nettvaerksfejl — koden skal laeses ud."""

    def _boom(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr("core.tools.verify_tools.urllib.request.urlopen", _boom)
    r = _exec_verify_endpoint_responds({"url": "https://x/y", "expected_status": 404})
    assert r["status"] == "ok"
    assert r["actual_status"] == 404


def test_endpoint_netvaerksfejl_er_failed(monkeypatch) -> None:
    def _boom(req, timeout=None):
        raise OSError("no route to host")

    monkeypatch.setattr("core.tools.verify_tools.urllib.request.urlopen", _boom)
    r = _exec_verify_endpoint_responds({"url": "https://x/y"})
    assert r["status"] == "failed"
    assert r["actual_status"] is None
