"""Værn: hver gren der gemmer et svar skal normalisere fladerne FØRST.

Rod-årsag (målt 25/10-2026, verificeret mod den levende DB):

15 ud af 15 ``jarvis-ui``-blokke i ``chat_messages`` stod med JSON på
markørens EGEN linje::

    ```jarvis-ui {"type":"comparison",…}
    ```

I CommonMark bliver hele resten af linjen en del af info-stringen, så
rendereren ser ikke sproget ``jarvis-ui`` — og blokken falder tilbage til rå
kode. Det er ikke en render-fejl: ``jarvis_ui_guard.normalisér`` retter formen
deterministisk (målt: mast → tre linjer, JSON byte-identisk).

Fejlen var RÆKKEVIDDE, ikke evne. Normaliseringen fandtes, men sad kun i
first-pass-grenen. Den agentiske gren — den almindelige, 13 af 17 tilfælde —
gemte ``followup_text`` uden at kalde den. Samme fejlform som
comparison-guarden 24/10: **et værn på én gren er ikke et værn.**

To ting måles her, og de måler ikke det samme:

* ``test_normaliser_retter_den_malte_form`` — at mekanismen virker på den
  præcise tekst der fejlede. En grøn kildetest kan ikke se det.
* ``test_hver_gemme_gren_normaliserer`` — at kaldet findes i HVER gren.
  Uden den kan nogen fjerne det fra én gren og alle tests forblive grønne.
"""

from __future__ import annotations

import ast
import json
import re
import sqlite3
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VISIBLE_RUNS = REPO / "core" / "services" / "visible_runs.py"

#: Den præcise tekst fra besked 222382 (12:49:22) — den Bjørn så som rå kode.
MAST = (
    '```jarvis-ui {"type":"comparison","title":"Tre diagnoser — og hvad '
    'målingen viste","columns":["Min diagnose","Hvad målingen viste"],'
    '"rows":[{"label":"Mappen manglede fixet","values":["Jeg greppede dist/ — '
    'du kører dist-web/","Forkert: fixet var der hele tiden"]}]}```\n\n'
    "Kommer den som to kolonner og tre rækker nu? 🙂"
)


# ── Funktionelt: mekanismen virker på den tekst der faktisk fejlede ──────────

def test_normaliser_retter_den_malte_form() -> None:
    """Den maste form skal blive tre linjer — og JSON'en må ikke ændres."""
    from core.services.jarvis_ui_guard import normalisér

    ud = normalisér(MAST, run_id="")

    # Formen: markør, JSON og lukke-fence på hver sin linje.
    assert "```jarvis-ui\n" in ud, (
        "JSON står stadig på markørens linje — blokken renderes som rå kode"
    )
    linjer = ud.split("\n")
    assert linjer[0] == "```jarvis-ui", f"markøren er ikke alene på linjen: {linjer[0]!r}"
    assert linjer[1].startswith("{"), "JSON'en står ikke på linjen efter markøren"
    assert linjer[2] == "```", f"lukke-fencen er ikke alene på linjen: {linjer[2]!r}"

    # Indholdet må ikke ændres: en form-rettelse er ikke en omskrivning.
    raa_json = re.search(r"jarvis-ui\s*(\{.*?\})\s*```", MAST, re.S).group(1)
    ny_json = linjer[1]
    assert json.loads(raa_json) == json.loads(ny_json), (
        "normaliseringen ændrede JSON-indholdet — den skal kun flytte linjer"
    )


def test_normaliser_roerer_ikke_en_korrekt_fence() -> None:
    """En blok der allerede er korrekt må ikke røres — ellers er rettelsen en risiko."""
    from core.services.jarvis_ui_guard import normalisér

    korrekt = (
        "```jarvis-ui\n"
        '{"type":"comparison","columns":["a","b"],"rows":[{"label":"x","values":["1","2"]}]}\n'
        "```"
    )
    assert normalisér(korrekt, run_id="") == korrekt


# ── Kilderegression: kaldet skal findes i HVER gren ─────────────────────────

def _funktionskilde(navn: str) -> str:
    """Kildeteksten for én top-level-funktion i visible_runs.py."""
    kilde = VISIBLE_RUNS.read_text(encoding="utf-8")
    trae = ast.parse(kilde)
    for node in ast.walk(trae):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == navn:
            return ast.get_source_segment(kilde, node) or ""
    raise AssertionError(f"funktionen {navn!r} findes ikke i visible_runs.py")


#: De tre grene der kan gemme et assistent-svar med indhold, med den variabel
#: der gemmes. Fejl- og cancel-beskeder ("Generation cancelled." osv.) er ikke
#: model-svar og skal ikke normaliseres.
#:
#: Variablen er med VILJE: en test der blot kræver at `_normalisér_flader`
#: optræder i funktionen er falsk-grøn. Målt 25/10-2026 — den agentiske gren og
#: first-pass ligger i SAMME funktion (`_stream_visible_run`), så fjernede man
#: kaldet fra den agentiske gren, bestod testen stadig på first-pass' kald.
#: Mutationen slap igennem. Kravet skal pege på den variabel der gemmes.
GRENE = (
    ("_stream_visible_run", "followup_text"),        # agentisk gren
    ("_stream_visible_run", "visible_output_text"),  # first-pass-gren
    ("_complete_visible_run_from_fallback", "text"),
)


@pytest.mark.parametrize("gren,variabel", GRENE)
def test_hver_gemme_gren_normaliserer(gren: str, variabel: str) -> None:
    """MUTATION: fjern kaldet for ÉN variabel → denne test fælder.

    Uden den kan normaliseringen fjernes fra den agentiske gren og alle
    funktionelle tests forblive grønne — præcis den fejl der blev målt, og
    præcis hvad mutation A viste den 25/10.
    """
    kilde = _funktionskilde(gren)
    assert re.search(
        rf"_normalisér_flader\(\s*{variabel}\b", kilde
    ), (
        f"{gren} gemmer `{variabel}` uden at normalisere den — "
        "en mast ```jarvis-ui-blok når DB og skærm som rå kode"
    )


def test_agentisk_gren_sender_scan_correction() -> None:
    """Normalisering alene er halvt: skærmen har allerede fået den rå tekst.

    Uden `scan_correction` retter DB'en sig mens brugeren ser rå kode — målt
    25/10: begge grene kunne gemme korrekt uden at skærmen nogensinde fik det.
    """
    kilde = _funktionskilde("_stream_visible_run")
    # Der skal være mindst to scan_correction-yields knyttet til flade-arbejdet:
    # claim-scanneren, den eksisterende flade-korrektion, normaliseringen i
    # first-pass og normaliseringen i den agentiske gren.
    antal = kilde.count('_sse("scan_correction"')
    assert antal >= 4, (
        f"kun {antal} scan_correction-yields i _stream_visible_run — "
        "normaliseringen i mindst én gren retter teksten uden at vise den"
    )


def test_den_levede_db_har_ikke_nye_maste_blokke() -> None:
    """Vagten mod den ægte DB — men kun som OBSERVATION, ikke blokering.

    Målingen der startede det hele: 15 af 15 blokke var maste. Efter fixet
    skal nye svar være korrekte. Testen springes over hvis DB'en ikke findes
    (fx i CI), og fejler kun hvis der findes maste blokke NYERE end fixet.
    """
    db = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
    if not db.exists():
        pytest.skip("den levende DB findes ikke her")
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        pytest.skip("DB'en kan ikke åbnes read-only")
    try:
        rows = con.execute(
            "SELECT id, content_json FROM chat_messages "
            "WHERE role='assistant' AND content_json LIKE '%```jarvis-ui {%' "
            "ORDER BY id DESC LIMIT 5"
        ).fetchall()
    except sqlite3.Error:
        pytest.skip("chat_messages kan ikke læses")
    finally:
        con.close()

    # Kun observation: de historiske rækker er ikke ændret af fixet, og det
    # er ikke en fejl at de findes. Testen dokumenterer at formen var maste.
    for mid, cj in rows:
        assert "```jarvis-ui {" in cj, f"besked {mid}: forventet mast form"
