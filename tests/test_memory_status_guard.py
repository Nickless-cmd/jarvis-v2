"""Vagt over MEMORY-statusvagten — den skal SE en falsk statuspåstand.

`scripts/verify_memory_status.py` fanger `## `-overskrifter der formulerer sig
som nutid uden et spor. Baggrunden (målt 16/10-2026): MEMORY.md havde 51
sådanne overskrifter, og 16 af dem var blevet falske — «STADIG ÅBEN» om arbejde
der var færdigt for uger siden, «afventer genstart» om en genstart der for
længst var sket. Filen læses ind i prompten hver tur, så en forkert linje
koster Bjørn et træk: han bad mig bygge noget der allerede var bygget.

Vagten kan ikke afgøre SANDHED — den kan kræve et SPOR. Testen her ser den
sige nej, og ser den holde mund når sporet er der.

Ingen af testene rører produktionens MEMORY.md: hjem og grundlinje er
monkeypatchet til tmp_path.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import verify_memory_status as v


@pytest.fixture
def hjem(tmp_path, monkeypatch):
    """Eget JARVIS_HOME og egen grundlinje — hverken produktion eller repo."""
    ws = tmp_path / "workspaces" / "proevemester"
    ws.mkdir(parents=True)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    grund = tmp_path / "baseline.json"
    grund.write_text(json.dumps({"i_alt": 0, "pr_fil": {}}), encoding="utf-8")
    monkeypatch.setattr(v, "GRUNDLINJE", grund)
    return ws / "MEMORY.md"


def test_statuspaastand_uden_spor_afvises(hjem, capsys):
    hjem.write_text("# Jarvis Memory\n\n## Stadig åbent\n\nnoget.\n", encoding="utf-8")
    assert v.main([]) == 1, "vagten accepterede en statuspåstand uden spor"
    assert "NYE statuspaastande" in capsys.readouterr().out


def test_dato_er_et_spor(hjem):
    hjem.write_text("## Stadig åbent (målt 16/10-2026)\n", encoding="utf-8")
    assert v.main([]) == 0


def test_lukke_markoer_er_et_spor(hjem):
    hjem.write_text("## Stadig uvidst (LUKKET 8/10-2026)\n", encoding="utf-8")
    assert v.main([]) == 0


def test_kilde_pegning_er_et_spor(hjem):
    hjem.write_text("## Det der stadig staar aabent (kilde: compaction_log)\n", encoding="utf-8")
    assert v.main([]) == 0


def test_overskrift_uden_nutids_ord_ignoreres(hjem):
    hjem.write_text("## Hvorfor halen findes\n", encoding="utf-8")
    assert v.main([]) == 0


def test_kun_niveau2_overskrifter_scannes(hjem):
    hjem.write_text("### Stadig åbent\n\n**Stadig åbent**\n\n## Stadig åbent\n", encoding="utf-8")
    assert [nr for nr, _ in v.fund_i_fil(hjem)] == [5]


def test_grundlinjen_skrives_kun_med_flaget(hjem):
    hjem.write_text("## Stadig åbent\n", encoding="utf-8")
    assert v.main([]) == 1
    assert v.main(["--skriv-grundlinje"]) == 0
    assert json.loads(Path(v.GRUNDLINJE).read_text(encoding="utf-8"))["i_alt"] == 1
    assert v.main([]) == 0


def test_faerre_end_grundlinjen_er_ikke_en_fejl(hjem, capsys):
    """En oprydning må ikke blokere — kun VÆKST gør."""
    Path(v.GRUNDLINJE).write_text(json.dumps({"i_alt": 5, "pr_fil": {}}), encoding="utf-8")
    hjem.write_text("## Stadig åbent\n", encoding="utf-8")
    assert v.main([]) == 0
    assert "faerre end grundlinjen" in capsys.readouterr().out


def test_ingen_memory_filer_er_ikke_en_fejl(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    assert v.main([]) == 0
