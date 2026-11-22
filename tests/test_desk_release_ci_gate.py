"""Vagten over release-gaten: en rød `ci` må ikke kunne publicere en release.

MÅLT 22/11-2026 — den konkrete hændelse testen findes for:
Release `jarvis-desktop-v0.6.420` blev publiceret med 11 artefakter, mens
`ci` for SAMME commit (`d624a4075`, run 45019130847) fejlede. To jobs var
røde: «desk (lint + typecheck + test)» og «desk (browser-målinger)».
`desk-release` (run 45019130835) kørte grøn samtidig.

Årsagen var strukturel, ikke en forglemmelse: `desk-release.yml` havde kun
`needs: prepare` (build) og `needs: build` (publish). Der var ingen
afhængighed til `ci`-workflowet, så en rød testkørsel kunne ikke blokere
publiceringen. Releasen ser grøn ud, fordi den eneste der spørger den, er
updateren.

HVAD DENNE TEST VÆRNER — tre ting, i den rækkefølge de kan gå galt:

1. **Kæden.** `publish` skal kræve BÅDE `build` og `gate`. Fjernes `gate`
   fra `needs`, kører publiceringen parallelt med gaten og værnet er væk —
   uden at nogen fil ændrer sig synligt i diffen.

2. **At gaten ikke kan åbne blindt.** En gate der svarer «grøn» når den
   ikke kan se `ci`, er samme fejlklasse som `ci_status_watch` blev skrevet
   for at fange. Derfor testes vurderingen mod syv tilfælde, inkl. «ingen
   kørsler» og «cancelled».

3. **At opslaget bruger FULD SHA.** Målt 22/11-2026: både
   `gh run list --commit 8f3b82a08` og `gh api ...?head_sha=8f3b82a08`
   svarer `[]` — tomt, ikke fejl — fordi API'et kræver 40 tegn. Med kort
   SHA ville gaten vente 40 minutter på en kørsel den aldrig så.

Testen læser workflow-filen som DATA og kører vurderingsfunktionen isoleret.
Den påstår ikke at GitHub kører den — kun at logikken gør det rigtige.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "desk-release.yml"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())


@pytest.fixture(scope="module")
def gate_script(workflow: dict) -> str:
    return workflow["jobs"]["gate"]["steps"][0]["run"]


def _vurder_kode(gate_script: str) -> str:
    """Udtræk python-blokken inde i ``vurder()`` så den kan køres isoleret.

    Vi kører den RIGTIGE kode fra workflowet, ikke en kopi. En test der
    gentager implementeringen beviser kun at testen er skrevet.
    """
    m = re.search(r"vurder\(\) \{\n\s*python3 - \"\$1\" <<'PYEOF'\n(.*?)\nPYEOF", gate_script, re.S)
    assert m, "kunne ikke finde vurder()-funktionens python-blok i gate-scriptet"
    kode = m.group(1)
    # Fjern den indrykning YAML-blokken giver (10 mellemrum i workflowet).
    linjer = [r[10:] if r.startswith(" " * 10) else r for r in kode.split("\n")]
    return "\n".join(linjer)


def _vurder(gate_script: str, runs: list[dict]) -> str:
    kode = _vurder_kode(gate_script)
    r = subprocess.run(
        [sys.executable, "-c", kode, json.dumps({"workflow_runs": runs})],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, f"vurderingen fejlede: {r.stderr}"
    return r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""


def _run(rid: int, *, navn: str = "ci", event: str = "push",
         status: str = "completed", conclusion: str | None = "success") -> dict:
    return {"id": rid, "name": navn, "event": event,
            "status": status, "conclusion": conclusion}


# --- 1. Kæden -------------------------------------------------------------

def test_publish_kraever_bade_build_og_gate(workflow: dict) -> None:
    """Uden `gate` i publish's needs er værnet væk, men diffen ser uskyldig ud."""
    needs = workflow["jobs"]["publish"]["needs"]
    assert isinstance(needs, list), (
        "publish.needs skal være en liste der indeholder BÅDE build og gate — "
        f"den står som {needs!r}"
    )
    assert "build" in needs, f"publish skal stadig afhænge af build, har {needs!r}"
    assert "gate" in needs, (
        "publish afhænger ikke af gate — så kan en rød ci publicere en release. "
        "Det er præcis fejlen bag 0.6.420."
    )


def test_gate_ligger_mellem_build_og_publish(workflow: dict) -> None:
    """Gaten skal vente på build (så den ikke lægger sin ventetid oveni) og
    bygge videre på det samme commit som publish udgiver."""
    jobs = workflow["jobs"]
    assert "gate" in jobs, "der findes intet gate-job i desk-release.yml"
    assert jobs["gate"]["needs"] == "build", (
        f"gate skal afhænge af build, har {jobs['gate']['needs']!r}"
    )


def test_gate_har_et_rigtigt_step(gate_script: str) -> None:
    assert gate_script.strip(), "gate-jobbet har et tomt run-step"
    assert "gh api" in gate_script, "gaten læser ikke GitHub API'et"


# --- 2. Opslaget skal bruge fuld SHA -------------------------------------

def test_opslaget_bruger_fuld_sha(gate_script: str) -> None:
    """Kort SHA giver `[]` fra API'et — målt 22/11-2026. Gaten skal
    normalisere, ellers venter den forgæves i 40 minutter."""
    assert "git rev-parse" in gate_script, (
        "gaten normaliserer ikke SHA — et kort input ville gøre den blind"
    )
    assert "head_sha=$FULL" in gate_script, (
        "opslaget skal bruge den normaliserede fulde SHA ($FULL), ikke $SHA"
    )


def test_gaten_afhaenger_ikke_af_jq(gate_script: str) -> None:
    """jq er ikke installeret i alle miljøer (målt 22/11-2026: mangler i
    runtime-containeren). En gate der fejler på et manglende værktøj er
    blind på samme måde som en der ikke kan læse API'et."""
    uden_kommentarer = "\n".join(
        r for r in gate_script.split("\n") if not r.strip().startswith("#")
    )
    assert "jq " not in uden_kommentarer and "| jq" not in uden_kommentarer, (
        "gaten bruger jq i selve koden — brug python3, som findes på ubuntu-latest"
    )


# --- 3. Vurderingen må ikke åbne blindt ----------------------------------

def test_ingen_ci_koersel_venter_frem_for_at_aabne(gate_script: str) -> None:
    """Kan vi ikke se ci, må vi ikke publicere. `INGEN` får løkken til at
    vente — den er ikke en grøn dom."""
    assert _vurder(gate_script, []) == "INGEN"


def test_kun_desk_release_taeller_ikke_som_ci(gate_script: str) -> None:
    """Gaten må ikke forveksle sin egen søster med ci."""
    runs = [_run(1, navn="desk-release")]
    assert _vurder(gate_script, runs) == "INGEN"


def test_roed_ci_afvises(gate_script: str) -> None:
    """Kernebeviset: den røde 0.6.420-kørsel skal give ROED."""
    assert _vurder(gate_script, [_run(45019130847, conclusion="failure")]) == "ROED"


def test_en_roed_skjules_ikke_af_en_groen_soeskende(gate_script: str) -> None:
    """0.6.420's commit havde TO ci-kørsler, begge røde. Havde gaten spurgt
    «findes der en grøn?», var den sluppet igennem."""
    runs = [_run(1, conclusion="success"), _run(2, conclusion="failure")]
    assert _vurder(gate_script, runs) == "ROED"


def test_igangvaerende_ci_venter(gate_script: str) -> None:
    assert _vurder(gate_script, [_run(1, status="in_progress", conclusion=None)]) == "KOERER 1"


def test_cancelled_er_ikke_groen(gate_script: str) -> None:
    """En afbrudt kørsel har ikke testet noget. Den må ikke tælle som grøn."""
    assert _vurder(gate_script, [_run(1, conclusion="cancelled")]) == "IKKE_GROEN"


def test_groen_ci_aabner(gate_script: str) -> None:
    """Modstykket: 0.6.423's commit (8f3b82a08) var grøn og SKAL igennem.
    Uden denne gren ville en gate der altid afviser også bestå testene."""
    assert _vurder(gate_script, [_run(45028233539)]) == "GROEN"


def test_pull_request_koersel_taeller_ikke(gate_script: str) -> None:
    """En PR-kørsel for samme SHA beviser intet om den commit der udgives."""
    runs = [_run(1, event="pull_request", conclusion="failure")]
    assert _vurder(gate_script, runs) == "INGEN"


def test_gaten_har_lov_at_laese_actions(workflow: dict, gate_script: str) -> None:
    """Gaten læser `actions/runs` — så workflowet skal have `actions: read`.

    MÅLT 22/11-2026: `permissions: contents: write` stod alene. Når blokken
    er angivet eksplicit, sætter GitHub ALLE uspecificerede scopes til
    `none` — så opslaget ville få 403, `for`-løkken ville ramme sin
    «kunne ikke læse»-gren og afvise HVER release. Det er fail-safe, men
    blindt: gaten ville se ud som om den virkede, mens den blokerede alt.

    Testen binder de to sider sammen: scriptet SKAL slå actions op, og
    workflowet SKAL have lov til det. Ændres det ene uden det andet,
    fejler den her.
    """
    assert "actions/runs" in gate_script, (
        "gate-scriptet slår ikke actions/runs op — så er denne test forældet"
    )
    tilladelser = workflow.get("permissions") or {}
    assert tilladelser.get("actions") == "read", (
        f"workflowet må ikke læse actions (permissions={tilladelser}). "
        "Gaten ville få 403 og afvise alle releases."
    )


def test_ingen_daad_git_normalisering(gate_script: str) -> None:
    """Gate-jobbet har ingen checkout — så `git rev-parse` kan ikke virke.

    MÅLT 22/11-2026: scriptet kørte
    `FULL="$(git rev-parse "$SHA" 2>/dev/null || echo "$SHA")"`, men
    jobbet har kun ét step og henter intet repo. Kommandoen fejlede
    derfor HVER gang og faldt tilbage til den rå værdi. Normaliseringen
    var død kode der så ud som et værn — den kunne aldrig gøre noget.

    I stedet kræves formen: 40 hex-tegn. Testen værner begge sider —
    at den døde kode ikke kommer tilbage, og at kravet faktisk findes.
    """
    # Maal KODEN, ikke kommentarerne: scriptet forklarer i en kommentar
    # hvorfor `git rev-parse` blev fjernet, og en vagt der greps i hele
    # teksten ville fejle paa sin egen begrundelse.
    kode = "\n".join(
        r for r in gate_script.split("\n") if not r.lstrip().startswith("#")
    )
    assert "git rev-parse" not in kode, (
        "git rev-parse er tilbage i gate-scriptets kode, men jobbet har ingen "
        "checkout — den kan ikke virke og falder tavst tilbage"
    )
    assert "${#FULL}" in kode and "-ne 40" in kode, (
        "gate-scriptet kræver ikke en fuld 40-tegns SHA — så kan opslaget "
        "ske på en kort SHA og svare tomt"
    )
