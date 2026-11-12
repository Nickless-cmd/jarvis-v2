"""`read_file` må aldrig læse en stor fil ind som én streng (12/11-2026).

Målt på CT105: et autonomt run kaldte read_file på ~/.jarvis-v2/state/jarvis.db
(6,65 GB) med start_line=1, end_line=2. `_ws_read_text` læste HELE filen ind som en
streng (plus UTF-8-dekodning), og `text.split("\\n")` lavede endnu en fuld kopi FØR
linjeintervallet blev skåret ud; `MAX_READ_CHARS` klippede først bagefter.
jarvis-runtime nåede 7 GB RAM og 8,6 GB swap, holdt op med at svare på interne
stream-forespørgsler (klienten fik 503) og blev genstartet.

Testene sætter grænsen lavt og lader `_ws_read_text` KASTE, så de beviser at den store
vej aldrig indlæser hele filen — frem for at gætte ud fra at et resultat ser rigtigt ud.
"""
from __future__ import annotations

import pytest

from core.tools import file_tools_exec as fx


@pytest.fixture
def lille_graense(monkeypatch):
    monkeypatch.setattr(fx, "MAX_FULD_LAESNING_BYTES", 1024)

    def _maa_ikke_kaldes(_p):
        raise AssertionError("hele filen blev læst ind som én streng")

    monkeypatch.setattr(fx, "_ws_read_text", _maa_ikke_kaldes)


def _linjefil(tmp_path, antal=500):
    p = tmp_path / "stor.log"
    p.write_text("".join(f"linje {i}\n" for i in range(1, antal + 1)), encoding="utf-8")
    assert p.stat().st_size > 1024
    return p


def test_et_linjeinterval_i_en_stor_fil_streames_uden_at_laese_hele_filen(tmp_path, lille_graense):
    r = fx._exec_read_file({"path": str(_linjefil(tmp_path)), "start_line": 10, "end_line": 12})

    assert r["status"] == "ok"
    assert r["text"] == "linje 10\nlinje 11\nlinje 12"
    assert (r["start_line"], r["end_line"]) == (10, 12)
    assert r["large_file"] is True and r["total_lines"] is None


def test_en_stor_fil_uden_interval_giver_kun_begyndelsen_og_siger_det(tmp_path, lille_graense, monkeypatch):
    import core.tools.simple_tools as st

    monkeypatch.setattr(st, "MAX_READ_CHARS", 200)
    r = fx._exec_read_file({"path": str(_linjefil(tmp_path))})

    assert r["status"] == "ok"
    assert r["text"].startswith("linje 1\nlinje 2\n")
    assert len(r["text"]) <= 200
    assert r["truncated"] is True
    assert "start_line" in r["note"]


def test_et_interval_der_overstiger_tegnloftet_klippes_og_peger_videre(tmp_path, lille_graense, monkeypatch):
    import core.tools.simple_tools as st

    monkeypatch.setattr(st, "MAX_READ_CHARS", 60)
    r = fx._exec_read_file({"path": str(_linjefil(tmp_path)), "start_line": 1, "end_line": 400})

    assert r["truncated"] is True and len(r["text"]) <= 60
    assert str(r["end_line"] + 1) in r["note"]


@pytest.mark.parametrize("start, slut, fragment", [
    ("x", 5, "start_line must be an integer"),
    (1, "y", "end_line must be an integer"),
    (50, 10, "is after end_line"),
])
def test_ugyldige_intervaller_afvises_ogsaa_for_store_filer(tmp_path, lille_graense, start, slut, fragment):
    r = fx._exec_read_file({"path": str(_linjefil(tmp_path)), "start_line": start, "end_line": slut})

    assert r["status"] == "error" and fragment in r["error"]


def test_en_stor_binaer_fil_afvises_med_en_tydelig_besked(tmp_path, lille_graense):
    """Præcis jarvis.db: SQLite-headeren er `SQLite format 3\\0`."""
    p = tmp_path / "db.sqlite"
    p.write_bytes(b"SQLite format 3\x00" + b"\x00\x01\x02" * 2000)

    r = fx._exec_read_file({"path": str(p), "start_line": 1, "end_line": 2})

    assert r["status"] == "error"
    assert "binary" in r["error"].lower()


def test_en_enkelt_enorm_linje_i_en_stor_fil_bliver_ikke_laest_hel(tmp_path, lille_graense, monkeypatch):
    """6 GB uden et eneste linjeskift må ikke blive til én 6 GB-linje i hukommelsen."""
    import core.tools.simple_tools as st

    monkeypatch.setattr(st, "MAX_READ_CHARS", 100)
    monkeypatch.setattr(fx, "MAX_LINJE_BYTES", 256)
    p = tmp_path / "en_linje.txt"
    p.write_text("a" * 50_000, encoding="utf-8")

    r = fx._exec_read_file({"path": str(p), "start_line": 1, "end_line": 1})

    assert r["status"] == "ok" and len(r["text"]) <= 256


def test_en_lille_fil_opfoerer_sig_som_foer(tmp_path):
    """Under grænsen er adfærden UÆNDRET — fuld læsning, total_lines, ingen large_file."""
    p = tmp_path / "lille.txt"
    p.write_text("a\nb\nc\nd\n", encoding="utf-8")

    r = fx._exec_read_file({"path": str(p), "start_line": 2, "end_line": 3})

    assert r["text"] == "b\nc"
    assert r["total_lines"] == 5
    assert "large_file" not in r


def test_den_store_vej_noterer_stadig_laesningen_til_read_before_write_guarden(tmp_path, lille_graense, monkeypatch):
    set_: list[str] = []
    monkeypatch.setattr("core.services.read_before_write_guard.record_read",
                        lambda path, session_id="": set_.append(path))

    fx._exec_read_file({"path": str(_linjefil(tmp_path)), "start_line": 1, "end_line": 2,
                        "_runtime_session_id": "s1"})

    assert set_ == [str((tmp_path / "stor.log").resolve())]
