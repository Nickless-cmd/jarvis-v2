"""Vagten maa ikke kraeve at man laeser en fil der ikke findes.

MAALT 12/9-2026, incident 6798:

    ⚠️ READ-BEFORE-WRITE GUARD (bash): denne kommando vil overskrive MEMORY.md
    (/media/projects/jarvis-v2/workspaces/bjorn/MEMORY.md) men filen er ikke
    blevet læst i denne session. Læs den først med `read_file(...)`.

    Første 20 linjer af filen:
    (could not read preview)

Hverken filen eller mappen `workspaces/` fandtes. Instruktionen var altsaa
umulig at efterkomme — og vagten sagde det selv i sin egen fejlbesked:
forhaandsvisningen fejlede fordi der ikke var noget at vise.

Vagten findes for at beskytte indhold man ikke har set. Findes filen ikke, er
der intet indhold at miste.
"""
import pytest

from core.services.read_before_write_guard import check_bash_command_safe


def test_en_HELT_ny_fil_blokeres_ikke(tmp_path):
    """Findes navnet ingen steder, er der intet indhold at miste — og kravet
    «laes den foerst» er umuligt at opfylde."""
    maal = tmp_path / "et-nyt-sted" / "MEMORY.md"
    tilladt, grund = check_bash_command_safe(
        f"cd /tmp && cat > {maal}", session_id="prøve")
    assert tilladt is True, f"blokeret paa en fil der findes ingen steder: {grund}"


def test_den_RIGTIGE_fil_i_den_FORKERTE_rod_blokeres(tmp_path, monkeypatch):
    """Selve tilfaeldet fra produktionen, forstaaet rigtigt.

    Incident 6798 blev foerst laest som «vagten kraever det umulige». Det gjorde
    den — men filen fandtes ANDETSTEDS: repo-stien
    /media/projects/jarvis-v2/workspaces/bjorn/MEMORY.md fandtes ikke, mens
    /home/bs/.jarvis-v2/workspaces/bjorn/MEMORY.md var 124 KB og aendret samme
    dag. Runnet skrev til den rigtige FIL i den forkerte ROD.

    Lod vi den passere, ville der blive oprettet en kopi ingen laeser, mens den
    rigtige stod uroert — Jarvis ville tro han havde gemt, og intet var gemt.
    """
    rigtig_rod = tmp_path / "hjem" / "workspaces"
    (rigtig_rod / "bjorn").mkdir(parents=True)
    (rigtig_rod / "bjorn" / "MEMORY.md").write_text("det rigtige indhold\n", encoding="utf-8")
    monkeypatch.setattr("core.runtime.config.WORKSPACES_DIR", rigtig_rod)

    forkert = tmp_path / "repo" / "workspaces" / "bjorn" / "MEMORY.md"
    tilladt, grund = check_bash_command_safe(
        f"cd {tmp_path}/repo && cat > {forkert}", session_id="prøve-rod")
    assert tilladt is False, "en skrivning til forkert rod slap igennem"
    assert "forkerte rod" in (grund or "").lower() or "FORKERTE" in (grund or "")
    assert str(rigtig_rod / "bjorn" / "MEMORY.md") in (grund or ""), \
        "beskeden siger ikke hvor den rigtige ligger"


def test_en_fil_der_FINDES_beskyttes_stadig(tmp_path):
    """Vagten maa ikke koebe sin rimelighed ved at holde op med at beskytte."""
    maal = tmp_path / "MEMORY.md"
    maal.write_text("noget Bjørn ikke vil miste\n", encoding="utf-8")
    tilladt, grund = check_bash_command_safe(
        f"cat > {maal}", session_id="prøve-2")
    assert tilladt is False, "en eksisterende MEMORY.md blev ikke beskyttet"
    assert "READ-BEFORE-WRITE" in (grund or "")


def test_forhaandsvisningen_viser_faktisk_indholdet(tmp_path):
    """«(could not read preview)» var symptomet. Findes filen, skal dens
    foerste linjer staa i beskeden — ellers kan man ikke se hvad man er ved at
    overskrive."""
    maal = tmp_path / "MEMORY.md"
    maal.write_text("FØRSTE LINJE\nanden linje\n", encoding="utf-8")
    _, grund = check_bash_command_safe(f"cat > {maal}", session_id="prøve-3")
    assert "FØRSTE LINJE" in (grund or "")
    assert "could not read preview" not in (grund or "")
