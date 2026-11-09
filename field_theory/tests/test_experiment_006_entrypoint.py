"""The exp_006 command-line entry exists and delegates to run_investigation()."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

import feltteori_research.experiment_006_order as module

PROJECT = Path(__file__).resolve().parents[1]
RUN_PY = PROJECT / "experiments" / "exp_006_order" / "run.py"
PRESERVED_SOURCE = (
    PROJECT / "artifacts" / "exp_006_order" / "noaa_20261030_v2" / "noaa_co2_mm_mlo.csv"
)


def _load_entry():
    spec = importlib.util.spec_from_file_location("exp006_run_entry", RUN_PY)
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    return entry


def test_entry_exists_and_exposes_main() -> None:
    assert RUN_PY.is_file()
    assert callable(_load_entry().main)


def test_entry_forwards_arguments_to_run_investigation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, Path]] = []
    monkeypatch.setattr(
        module, "run_investigation", lambda source, out: calls.append((source, out))
    )
    entry = _load_entry()  # imports the (patched) name at load time
    out = tmp_path / "run"
    entry.main(["--output", str(out), "--source", "local.csv"])
    assert calls == [("local.csv", out)]


def test_entry_defaults_to_fetch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, Path]] = []
    monkeypatch.setattr(
        module, "run_investigation", lambda source, out: calls.append((source, out))
    )
    _load_entry().main(["--output", str(tmp_path / "r")])
    assert calls[0][0] == "fetch"


def test_entry_requires_output() -> None:
    with pytest.raises(SystemExit):
        _load_entry().main([])


@pytest.mark.skipif(not PRESERVED_SOURCE.exists(), reason="preserved source absent")
def test_entry_reproduces_artifacts_offline_from_preserved_source(
    tmp_path: Path,
) -> None:
    out = tmp_path / "repro"
    _load_entry().main(["--output", str(out), "--source", str(PRESERVED_SOURCE)])
    produced = {p.name for p in out.iterdir()}
    preserved = {p.name for p in PRESERVED_SOURCE.parent.iterdir()}
    assert produced == preserved
