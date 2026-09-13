"""Varmerens logfiler voksede uden loft.

MAALT 13/9-2026 paa runtime:

    cache_warmer.jsonl        28,8 MB
    cache_warmer_cron.log     19,3 MB

Begge skrives hvert tiende minut af cron, og ingen af dem havde nogen form for
rotation. `.jsonl` appendes i `_append_log`; cron-loggen faar skallens `>>`.
"""
import json

import pytest

import scripts.primary_cache_warmer as w


@pytest.fixture
def logfiler(tmp_path, monkeypatch):
    jsonl = tmp_path / "cache_warmer.jsonl"
    cron = tmp_path / "cache_warmer_cron.log"
    monkeypatch.setattr(w, "LOG_PATH", jsonl)
    monkeypatch.setattr(w, "CRON_LOG_PATH", cron)
    monkeypatch.setattr(w, "LOG_MAKS_BYTES", 1000)
    return jsonl, cron


def test_en_lille_log_roteres_ikke(logfiler):
    jsonl, _ = logfiler
    jsonl.write_text("lille\n", encoding="utf-8")
    w._append_log({"a": 1})
    assert not jsonl.with_suffix(".jsonl.1").exists()
    assert "lille" in jsonl.read_text(encoding="utf-8")


def test_en_stor_log_roteres_til_ÉN_generation(logfiler):
    jsonl, _ = logfiler
    jsonl.write_text("x" * 1500, encoding="utf-8")
    w._append_log({"a": 1})
    rullet = jsonl.with_suffix(".jsonl.1")
    assert rullet.exists(), "loggen blev ikke roteret"
    assert len(rullet.read_text(encoding="utf-8")) == 1500
    # Den nye fil indeholder KUN den nye linje.
    assert json.loads(jsonl.read_text(encoding="utf-8").strip()) == {"a": 1}


def test_ogsaa_cron_loggen_roteres(logfiler):
    """Den skrives af skallen, ikke af os — men vi er det eneste der koerer
    regelmaessigt og kender stien."""
    _, cron = logfiler
    cron.write_text("y" * 1500, encoding="utf-8")
    w._append_log({"a": 1})
    assert cron.with_suffix(".log.1").exists(), "cron-loggen vokser stadig frit"


def test_kun_ÉN_generation_beholdes(logfiler):
    """Formaalet er at kende det seneste moenster, ikke at foere arkiv. To
    filer aa 8 MB er et loft man kan regne med."""
    jsonl, _ = logfiler
    for runde in range(3):
        jsonl.write_text("z" * 1500, encoding="utf-8")
        w._append_log({"runde": runde})
    assert jsonl.with_suffix(".jsonl.1").exists()
    assert not jsonl.with_suffix(".jsonl.2").exists()


def test_en_varmer_der_ikke_kan_rotere_varmer_stadig(logfiler, monkeypatch):
    """Logning maa aldrig vaelte det den logger om."""
    jsonl, _ = logfiler
    jsonl.write_text("x" * 1500, encoding="utf-8")
    monkeypatch.setattr(
        w.Path, "replace",
        lambda *a, **k: (_ for _ in ()).throw(OSError("disken er fuld")))
    w._append_log({"a": 1})          # maa ikke kaste
    assert jsonl.exists()
