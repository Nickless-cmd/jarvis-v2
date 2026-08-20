"""canary_measure: en tvetydig cost-række må aldrig blive til et tal.

Værktøjet blev skrevet for at forhindre den fejl jeg selv lavede — at matche
TTFT-tal til cost-rækker på tidsnærhed og konkludere forkert. Men første to
versioner havde selv fejlen indbygget:

  v1: "UMATCHET" var en løgn — første run tog rækken, resten sprang den over.
  v2: run-centreret klassifikation. Ved én cost-række inde i TO overlappende
      runs blev det FØRSTE run stadig printet som gyldigt interval-match; kun
      det andet blev markeret tvetydigt (Codex). Så en tvetydig række blev
      alligevel rapporteret som et datapunkt.

v3 er cost-centreret: ejerskab afgøres PR. RÆKKE, og har den flere mulige
ejere, afvises de ALLE.
"""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "canary_measure",
    Path(__file__).resolve().parents[1] / "scripts/diagnostics/canary_measure.py",
)
cm = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cm)


class TestTidsparsing:
    def test_bevarer_mikrosekunder_og_tz(self):
        """Trunkering til sekunder gjorde boundary-fejl sandsynlige."""
        a = cm.parse_ts("2026-08-20T18:23:41.574256Z")
        b = cm.parse_ts("2026-08-20T18:23:41.574255+00:00")
        assert a and b and a > b, "mikrosekunder skal skelne"

    def test_haandterer_begge_formater(self):
        """costs skriver 'Z', visible_runs '+00:00' — samme øjeblik."""
        z = cm.parse_ts("2026-08-20T18:00:00.000000Z")
        off = cm.parse_ts("2026-08-20T18:00:00.000000+00:00")
        assert z == off

    def test_ugyldigt_giver_None_ikke_kast(self):
        for bad in ("", "ikke en dato", None):
            assert cm.parse_ts(bad) is None


def _db(tmp_path, runs, costs, with_run_id=True):
    p = tmp_path / "t.db"
    con = sqlite3.connect(str(p))
    con.execute("""CREATE TABLE visible_runs (run_id TEXT, lane TEXT, provider TEXT,
                   model TEXT, status TEXT, started_at TEXT, finished_at TEXT)""")
    cols = """created_at TEXT, lane TEXT, provider TEXT, model TEXT,
              input_tokens INT, output_tokens INT, cache_hit_tokens INT,
              cache_miss_tokens INT"""
    con.execute(f"CREATE TABLE costs ({cols}{', run_id TEXT' if with_run_id else ''})")
    con.executemany("INSERT INTO visible_runs (run_id,provider,model,started_at,"
                    "finished_at,status) VALUES (?,?,?,?,?,?)", runs)
    ph = "?,?,?,?,?,?,?,?" + (",?" if with_run_id else "")
    con.executemany(f"INSERT INTO costs VALUES ({ph})", costs)
    con.commit()
    con.close()
    return p


def _run(tmp_path, monkeypatch, capsys, runs, costs, with_run_id=True):
    db = _db(tmp_path, runs, costs, with_run_id)
    monkeypatch.setattr(cm, "DB", db)
    monkeypatch.setattr(cm.sys, "argv", ["canary", "2026-08-20T00:00"])
    cm.main()
    return capsys.readouterr().out


class TestOverlap:
    """Kernen: to runs der overlapper om én cost-række."""

    def _overlappende(self):
        runs = [
            ("visible-AAAA1111", "deepseek", "deepseek-v4-flash",
             "2026-08-20T18:00:00.000000+00:00", "2026-08-20T18:10:00.000000+00:00", "completed"),
            ("visible-BBBB2222", "deepseek", "deepseek-v4-flash",
             "2026-08-20T18:04:00.000000+00:00", "2026-08-20T18:12:00.000000+00:00", "completed"),
        ]
        # Rækken ligger inde i BEGGE intervaller. Tom run_id → interval-fallback.
        costs = [("2026-08-20T18:05:00.000000Z", "primary", "deepseek",
                  "deepseek-v4-flash", 100000, 500, 90000, 10000, "")]
        return runs, costs

    def test_BEGGE_runs_afvises_ikke_kun_det_ene(self, tmp_path, monkeypatch, capsys):
        runs, costs = self._overlappende()
        out = _run(tmp_path, monkeypatch, capsys, runs, costs)
        assert "AAAA1111" not in out.split("UDEN entydig")[0], \
            "første run blev rapporteret som gyldigt — den run-centrerede fejl er tilbage"
        assert "UDEN entydig kobling" in out
        assert out.count("deler cost-række") >= 2, "begge runs skal nævnes"

    def test_intet_cache_tal_udgives_for_tvetydig_raekke(self, tmp_path, monkeypatch, capsys):
        """Det farlige udfald: at 90% dukker op som et troværdigt datapunkt."""
        runs, costs = self._overlappende()
        out = _run(tmp_path, monkeypatch, capsys, runs, costs)
        tabel = out.split("UDEN entydig")[0]
        assert "90%" not in tabel


class TestEntydigeTilfaelde:
    def test_run_id_binder_selv_ved_overlap(self, tmp_path, monkeypatch, capsys):
        """Med run_id er overlap irrelevant — koblingen er eksakt."""
        runs = [
            ("visible-AAAA1111", "deepseek", "m", "2026-08-20T18:00:00.000000+00:00",
             "2026-08-20T18:10:00.000000+00:00", "completed"),
            ("visible-BBBB2222", "deepseek", "m", "2026-08-20T18:04:00.000000+00:00",
             "2026-08-20T18:12:00.000000+00:00", "completed"),
        ]
        costs = [("2026-08-20T18:05:00.000000Z", "primary", "deepseek", "m",
                  100000, 500, 90000, 10000, "visible-BBBB2222")]
        out = _run(tmp_path, monkeypatch, capsys, runs, costs)
        assert "BBBB2222" in out and "run_id" in out
        assert "UDEN entydig" not in out

    def test_forkert_model_binder_ikke(self, tmp_path, monkeypatch, capsys):
        """En samtidig stor cost fra en ANDEN model må ikke tilskrives runnet."""
        runs = [("visible-AAAA1111", "deepseek", "deepseek-v4-flash",
                 "2026-08-20T18:00:00.000000+00:00",
                 "2026-08-20T18:10:00.000000+00:00", "completed")]
        costs = [("2026-08-20T18:05:00.000000Z", "primary", "ollama",
                  "glm-5.2:cloud", 100000, 500, 0, 100000, "")]
        out = _run(tmp_path, monkeypatch, capsys, runs, costs)
        assert "uden ejer" in out, "rækken skulle stå som forældreløs"
