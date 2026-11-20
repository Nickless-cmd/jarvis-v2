"""Hukommelses-loft-advarsel for QUICK_FACTS.md (20/11-2026)."""
import pytest

from core.services import prompt_contract as pc

HEADER = "Quick Facts (altid gældende — tjek her FØR du leder lokalt eller på nettet):\n"


@pytest.fixture(autouse=True)
def _capture(monkeypatch):
    calls = []
    monkeypatch.setattr(pc, "_report_quick_facts_pressure",
                        lambda msg, sev: calls.append((sev, msg)))
    return calls


def _write(tmp_path, text):
    (tmp_path / "QUICK_FACTS.md").write_text(text, encoding="utf-8")


def _doc(sizes):
    return "".join(f"## Sek{i}\n" + "x" * n + "\n" for i, n in enumerate(sizes))


def test_under_threshold_is_byte_identical(tmp_path, _capture):
    text = _doc([100, 200])
    _write(tmp_path, text)
    out = pc._quick_facts_section(workspace_dir=tmp_path, max_chars=1000)
    assert out == HEADER + text.strip()
    assert _capture == []


def test_over_threshold_warns_with_real_numbers(tmp_path, _capture):
    text = _doc([100, 500, 300])  # ~ 930 af 1000
    _write(tmp_path, text)
    n = len(text.strip())
    assert 900 <= n < 1000
    out = pc._quick_facts_section(workspace_dir=tmp_path, max_chars=1000)
    assert out.startswith(HEADER + text.strip())
    assert f"{n} af 1000 tegn" in out
    assert f"{1000 - n} tegn til loftet" in out
    assert "«Sek1» " in out  # største sektion nævnt
    assert "slet intet uden Bjørns ord" in out
    assert [s for s, _ in _capture] == ["info"]


def test_warning_is_deterministic(tmp_path):
    _write(tmp_path, _doc([100, 500, 300]))
    a = pc._quick_facts_section(workspace_dir=tmp_path, max_chars=1000)
    b = pc._quick_facts_section(workspace_dir=tmp_path, max_chars=1000)
    assert a == b


def test_cut_is_reported_not_silent(tmp_path, _capture):
    text = _doc([400, 400, 400])
    _write(tmp_path, text)
    out = pc._quick_facts_section(workspace_dir=tmp_path, max_chars=1000)
    assert "KLIPPET" in out
    assert f"{len(text.strip()) - 999} tegn" in out
    assert "«Sek2»" in out  # helt/delvist væk
    assert [s for s, _ in _capture] == ["error"]
    assert "…" in out


def test_never_writes_to_file(tmp_path):
    text = _doc([400, 400, 400])
    _write(tmp_path, text)
    pc._quick_facts_section(workspace_dir=tmp_path, max_chars=1000)
    assert (tmp_path / "QUICK_FACTS.md").read_text(encoding="utf-8") == text
