"""Narrationen over et værktøjskald — den tekst brugeren FAKTISK ser.

Bjørn 17/9-2026, to fejl i samme linje:

* «liveness indikator over composer … viser køre/kørte kommando: cd … og
  næsten altid på køre kommando: cd indtil kommandoen er kørt». Hintet var
  `cmd.split()[0]`, og næsten hver kommando her begynder med
  `cd /media/projects/jarvis-v2 && …`. Linjen sagde altså hvilken MAPPE han
  stod i, mens den rigtige kommando kørte i to minutter.
* «mange kommandoer har navne remember_this eller operator_bash og det ser sku
  ikke særlig godt ud». Tabellen kendte ikke operator-sættet — som med 16.045
  kald på to uger er det MEST brugte — og heller ikke remember_this.
"""
from __future__ import annotations

import pytest

from core.services.visible_runs import _bash_hint, _tool_label


# ───────────────────────────────────────── kommandoen, ikke dens første ord

@pytest.mark.parametrize("kommando,forventet", [
    # Det konkrete tilfælde han så: mappeskiftet foran spiste linjen.
    ("cd /media/projects/jarvis-v2 && grep -rn 'tool_calls' core", "grep tool_calls"),
    ("cd /r && git log --oneline -25 && git status -sb", "git log"),
    # Præfikser hører til scenen, ikke til handlingen.
    ("sudo -n systemctl restart jarvis-api", "systemctl restart"),
    ("timeout 300 /opt/conda/envs/ai/bin/python -m pytest tests/", "python pytest"),
    ("JARVIS_X=1 npm run build", "npm run"),
    # Omdirigering er ikke kommandoens genstand.
    ("cd /tmp/ocp && cat > fwd.py", "cat fwd.py"),
    # Er der KUN et mappeskift, er det dét der skete.
    ("cd /tmp", "cd /tmp"),
    ("", ""),
])
def test_hintet_siger_hvad_kommandoen_GOER(kommando, forventet):
    assert _bash_hint(kommando) == forventet


def test_hintet_er_kort_nok_til_en_linje():
    assert len(_bash_hint("grep " + "x" * 200)) <= 40


# ───────────────────────────────────────────── navne mennesker kan læse

@pytest.mark.parametrize("navn", ["remember_this", "bash_session_run", "explore",
                                  "scout_agent", "recall", "central_query"])
def test_de_hyppigste_vaerktoejer_har_et_dansk_navn(navn):
    """Uden en etiket stod funktionsnavnet i klartekst på skærmen."""
    etiket = _tool_label(navn)
    assert etiket != navn, f"{navn} står stadig som sit funktionsnavn"
    assert "_" not in etiket


@pytest.mark.parametrize("operator,almindelig", [
    ("operator_bash", "bash"),
    ("operator_read_file", "read_file"),
    ("operator_grep", "grep"),
    ("operator_list_dir", "list_dir"),
])
def test_operator_varianten_laeses_som_sit_almindelige_navn(operator, almindelig):
    """Samme handling for læseren — og operator-sættet er det mest brugte."""
    assert _tool_label(operator) == _tool_label(almindelig)


def test_operator_bash_faar_ogsaa_kommando_hintet():
    """Fejlen han så, hele vejen igennem: navnet OG hintet på samme kald."""
    ud = _tool_label("operator_bash",
                     {"command": "cd /media/projects/jarvis-v2 && grep -rn x core"})
    assert ud == "Kører kommando: grep x"


def test_et_UKENDT_vaerktoej_opfinder_vi_ikke_et_navn_til():
    """Bedre det rå navn end en etiket der påstår noget forkert."""
    assert _tool_label("noget_helt_nyt") == "noget_helt_nyt"
