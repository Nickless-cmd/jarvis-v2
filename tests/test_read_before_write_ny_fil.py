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


def test_en_fil_der_ikke_findes_blokeres_ikke(tmp_path):
    """Selve tilfaeldet fra produktionen."""
    maal = tmp_path / "workspaces" / "bjorn" / "MEMORY.md"
    tilladt, grund = check_bash_command_safe(
        f"cd /tmp && cat > {maal}", session_id="prøve")
    assert tilladt is True, f"blokeret paa en fil der ikke findes: {grund}"


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
