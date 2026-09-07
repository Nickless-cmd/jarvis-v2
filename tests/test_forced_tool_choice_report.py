"""Rapporten skal kunne læses af nogen der ikke kender forespørgslen.

Uden en kørbar aflæsning er en måling kun tilgængelig for den der byggede den
— og så bliver den ikke brugt. Testene kører scriptet mod en midlertidig
database, så den ikke rører rigtige data.
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "forced_tool_choice_report.py"


def _db(tmp_path: Path, raekker: list[dict]) -> Path:
    hjem = tmp_path / ".jarvis-v2" / "state"
    hjem.mkdir(parents=True)
    db = hjem / "jarvis.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, "
                "payload_json TEXT, created_at TEXT)")
    for i, r in enumerate(raekker):
        con.execute("INSERT INTO events (kind, payload_json, created_at) VALUES (?,?,?)",
                    ("runtime.forced_tool_choice_probe", json.dumps(r),
                     f"2026-09-07T0{i}:00:00+00:00"))
    con.commit()
    con.close()
    return db


def _koer(tmp_path: Path) -> str:
    p = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True,
                       env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"})
    return p.stdout + p.stderr


def test_tom_database_siger_det_pænt(tmp_path):
    _db(tmp_path, [])
    assert "Ingen målinger endnu" in _koer(tmp_path)


def test_manglende_database_vaelter_ikke(tmp_path):
    ud = _koer(tmp_path)
    assert "Ingen database" in ud or "Ingen målinger" in ud


def test_taeller_honorerede_og_ikke_honorerede(tmp_path):
    _db(tmp_path, [
        {"model": "deepseek-v4-flash", "honoreret": True, "finish_reason": "stop",
         "text_chars": 0, "tools_advertised": 70, "thinking_disabled": True},
        {"model": "deepseek-v4-flash", "honoreret": False, "finish_reason": "stop",
         "text_chars": 212, "tools_advertised": 70, "thinking_disabled": True},
    ])
    ud = _koer(tmp_path)
    assert "2 tvungne runder" in ud
    assert "1 af   2" in ud or "1 af  2" in ud


def test_peger_paa_den_rigtige_konklusion_ved_stop(tmp_path):
    _db(tmp_path, [{"model": "m", "honoreret": False, "finish_reason": "stop",
                    "text_chars": 200, "tools_advertised": 70,
                    "thinking_disabled": True}])
    assert "ikke håndhæver" in _koer(tmp_path)


def test_peger_paa_budget_ved_length(tmp_path):
    _db(tmp_path, [{"model": "m", "honoreret": False, "finish_reason": "length",
                    "text_chars": 0, "tools_advertised": 70,
                    "thinking_disabled": True}])
    assert "løb tør" in _koer(tmp_path)


def test_nul_annoncerede_vaerktoejer_kaldes_en_HELT_anden_fejl(tmp_path):
    _db(tmp_path, [{"model": "m", "honoreret": False, "finish_reason": "stop",
                    "text_chars": 10, "tools_advertised": 0,
                    "thinking_disabled": True}])
    assert "kom slet ikke med" in _koer(tmp_path)
