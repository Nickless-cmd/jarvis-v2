# tests/test_docs_drift_check.py
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "docs_drift_check", Path(__file__).resolve().parents[1] / "scripts" / "docs_drift_check.py")
d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d)


def test_broken_links_flags_missing_and_passes_valid(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "real.md").write_text("hello")
    good = docs / "a.md"
    good.write_text("[ok](real.md) and [ext](https://x.y) and [anchor](#top)")
    bad = docs / "b.md"
    bad.write_text("[gone](does_not_exist.md)")
    out = d.broken_links(docs)
    targets = {(o["doc"].split("/")[-1], o["target"]) for o in out}
    assert ("b.md", "does_not_exist.md") in targets
    assert not any(o["doc"].endswith("a.md") for o in out)


def test_norm_collapses_dates():
    assert d._norm("Generated 2026-07-08 x") == d._norm("Generated 2020-01-01 x")
    assert d._norm("Generated 2026-07-08 x") != d._norm("Generated 2026-07-08 y")


def test_real_repo_has_no_hard_drift():
    # Guards the committed tree: generated docs match their generators and no links dangle.
    rep = d.run_check()
    assert rep["counts"]["hard"] == 0, rep["hard"][:20]


# ── Vagten skal kunne ses SIGE NEJ (20/9-2026) ──────────────────────────────
def test_gate_afviser_naar_der_er_haard_drift(monkeypatch, capsys):
    """Testfilen dækkede opdagelsen, men aldrig afvisningen.

    En vagt hvis nej ingen har set, er en vagt man ikke ved virker. Den her
    blokerede fire af mine commits i dag — men det vidste vi kun fordi jeg
    tilfældigvis ramte den.
    """
    import sys

    import scripts.docs_drift_check as d
    monkeypatch.setattr(d, "staged_paths", lambda: ["core/x.py"])
    monkeypatch.setattr(d, "hard_drift", lambda staged: [
        {"generator": "api_docs_gen", "kind": "stale", "path": "docs/reference/api/x.md"}])
    monkeypatch.setattr(sys, "argv", ["docs_drift_check.py", "--check"])
    assert d.main() == 1
    ud = capsys.readouterr().out
    assert "1 HARD drift" in ud
    assert "api_docs_gen" in ud          # den skal sige HVILKEN generator


def test_gate_gaar_igennem_uden_drift(monkeypatch, capsys):
    import sys

    import scripts.docs_drift_check as d
    monkeypatch.setattr(d, "staged_paths", lambda: [])
    monkeypatch.setattr(d, "hard_drift", lambda staged: [])
    monkeypatch.setattr(sys, "argv", ["docs_drift_check.py", "--check"])
    assert d.main() == 0
    assert "clean" in capsys.readouterr().out
