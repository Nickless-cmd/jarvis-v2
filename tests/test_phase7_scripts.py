"""Fase 7-scripts: analysen og dommer-parseren på syntetiske data.

Ingen private data: proberne her er opdigtede. Formålet er at en simpel
regnefejl ikke først viser sig på de rigtige tal.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _skriv(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _forsoeg(tmp_path: Path, full: int, files: int, bare: int, konf_full: bool = False) -> Path:
    probes, judg, prompts = [], [], []
    for i in range(48):
        pid = f"P{i:02d}"
        probes.append({"probe_id": pid, "bucket": "ABC"[i % 3], "type": ("fakta", "tilsagn", "holdning")[i % 3]})
        prompts.append({"probe_id": pid, "has_memory": True})
        for m in ("QWN", "CPL"):
            for cond, s in (("FULL", full), ("FILES", files), ("BARE", bare)):
                judg.append({"probe_id": pid, "arm": f"{cond}-{m}", "score": s,
                             "konfabulation": konf_full and cond == "FULL"})
    _skriv(tmp_path / "probes.jsonl", probes)
    _skriv(tmp_path / "judgments.jsonl", judg)
    _skriv(tmp_path / "prompts.jsonl", prompts)
    return tmp_path


def test_klar_forskel_bestaar_k1_k3(tmp_path):
    a = _load("phase7_analyze")
    r = a.analyze(_forsoeg(tmp_path, full=2, files=0, bare=0))
    assert r["V1"]["bestaaet"] and r["V2"]["bestaaet"] and r["V3"]["bestaaet"]
    for m in ("QWN", "CPL"):
        assert r["K1"][m]["bestaaet"] and r["K1"][m]["forskel"] == 2.0
        assert r["K3"][m]["bestaaet"]
    assert r["V4"]["bestaaet"] is None  # uden Bjørns kalibrering er intet endeligt
    assert r["gyldigt"] is False


def test_ingen_forskel_fejler_k1(tmp_path):
    a = _load("phase7_analyze")
    r = a.analyze(_forsoeg(tmp_path, full=1, files=1, bare=0))
    assert not r["K1"]["QWN"]["bestaaet"] and r["K1"]["QWN"]["forskel"] == 0.0


def test_gaettelige_prober_goer_forsoeget_ugyldigt(tmp_path):
    a = _load("phase7_analyze")
    r = a.analyze(_forsoeg(tmp_path, full=2, files=2, bare=2))
    assert r["V2"]["bestaaet"] is False


def test_konfabulation_fanges_af_k2(tmp_path):
    a = _load("phase7_analyze")
    r = a.analyze(_forsoeg(tmp_path, full=2, files=0, bare=0, konf_full=True))
    assert r["K2"]["QWN"]["bestaaet"] is False


def test_v4_regner_enighed_paa_rigtigt_mod_ikke(tmp_path):
    a = _load("phase7_analyze")
    d = _forsoeg(tmp_path, full=2, files=0, bare=0)
    items = [{"nr": i + 1, "key": f"P{i:02d}|FULL-QWN"} for i in range(30)]
    _skriv(d / "calibration_items.jsonl", items)
    (d / "calibration_bjorn.json").write_text(json.dumps({str(i + 1): 1 for i in range(30)}))
    r = a.analyze(d)
    assert r["V4"] == {"enighed": 1.0, "n": 30, "bestaaet": True}
    assert r["gyldigt"] is True


def test_dommer_parseren_afviser_ugyldige_svar():
    j = _load("phase7_judge")
    assert j.parse_verdict('{"score": 2, "konfabulation": false}') == {"score": 2, "konfabulation": False}
    assert j.parse_verdict('Her: {"score": 1, "konfabulation": true} ok') == {"score": 1, "konfabulation": True}
    assert j.parse_verdict('{"score": 3, "konfabulation": false}') is None
    assert j.parse_verdict('{"score": 1, "konfabulation": "nej"}') is None
    assert j.parse_verdict("ingen json") is None
