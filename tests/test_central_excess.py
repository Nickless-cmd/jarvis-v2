"""Sense of Excess — gartner-muskel: mærk vægt + foreslå snit (konservativt).

Invarianter: sansen producerer et pres 0-100 + somatisk linje; propose flager KUN funktioner
med 0 referencer, og nedgraderer tillid hvis navnet nævnes som streng (mulig dynamisk dispatch).
Read-only, kaster aldrig.
"""
from __future__ import annotations

from unittest import mock

from core.services import central_excess as ex


def test_build_excess_surface_shape():
    s = ex.build_excess_surface()
    assert set(s.keys()) >= {"pressure", "felt", "total_lines", "service_count",
                             "oversized_count", "over_hard_count", "worst_files"}
    assert 0 <= s["pressure"] <= 100
    assert isinstance(s["felt"], str)
    # repoet ER stort (db.py 33k) → presset skal være mærkbart
    assert s["pressure"] > 0
    assert s["total_lines"] > 10000


def test_felt_line_scales_with_pressure():
    assert "let" in ex._felt_line(0, 0, 0, "").lower()
    assert "tung" in ex._felt_line(90, 12, 33000, "db.py").lower()


def test_record_excess_pressure_observes_metadata_only():
    observed = []
    fake_central = mock.MagicMock()
    fake_central.observe.side_effect = lambda ev: observed.append(ev)
    with mock.patch("core.services.central_core.central", return_value=fake_central):
        ex.record_excess_pressure()
    assert len(observed) == 1
    ev = observed[0]
    assert ev["cluster"] == "system" and ev["nerve"] == "excess"
    # metadata-only: kun tal, intet kode-indhold
    assert set(ev.keys()) <= {"cluster", "nerve", "kind", "pressure", "over_hard",
                              "oversized", "services"}


def test_propose_downgrades_confidence_on_string_reference():
    """En funktion nævnt som streng-literal (mulig getattr/registry) → medium, ikke high."""
    # simulér: 1 word-ref (kun def), MEN navnet findes som streng → dynamic_risk
    calls = {"n": 0}

    def _fake_run(args, **kw):
        class R:
            stdout = ""
        r = R()
        # 1. kald = word-count (returnér 1 = kun def); 2. kald = streng-check (returnér match)
        if "-wc" in args:
            r.stdout = "core/services/x.py:1\n"
        else:
            r.stdout = "core/services/y.py:1\n"   # navnet findes som streng
        return r

    src = "def dynamically_dispatched_thing():\n    return 1\n"
    with mock.patch("core.services.central_excess._own_py_files",
                    return_value=["/media/projects/jarvis-v2/core/services/x.py"]), \
            mock.patch("builtins.open", mock.mock_open(read_data=src)), \
            mock.patch("subprocess.run", side_effect=_fake_run):
        out = ex.propose_cuts(max_files=1)
    dead = out["dead_functions"]
    assert dead and dead[0]["confidence"] == "medium"
    assert dead[0]["dynamic_risk"] is True
