"""De tre indbakke-værktøjer — Opgave 5.

Et værktøjsnavn bor **fem** steder: skema, eksekutor, dispatch, desk og mobil.
Målt 2/10-2026 ramte jeg tre af de fem i første forsøg, og en AST-sletning
efterlod `{'type': 'function'}` — gyldig Python, så `compileall` tav.

Testene her måler alle fem lag, ikke kun at funktionerne virker.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from core.runtime import db_inbox
from core.tools import inbox_tools

BJORN = "bjorn"
NAVNE = ("inbox", "inbox_done", "inbox_drop")


@pytest.fixture
def inbox_db(monkeypatch, tmp_path, ejeren_er_bjorn):
    sti = tmp_path / "t.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)

    # LUK de oevrige kilder. `_exec_inbox` kalder `byg_indbakke` med de AEGTE
    # adaptere, og foerste udgave af disse tests naaede derfor mine egne
    # vaekninger og jobs fra udviklingsmaskinen — fire poster hvor testen
    # forventede nul. En test der laeser levende tilstand maaler noget andet
    # hver gang den koeres, og paa en anden maskine maaler den noget tredje.
    #
    # `_aegte_poster` beholdes med vilje: det ER vejen fra tabellen til
    # vaerktoejet, og den skal maales. De andre er andre opgavers ansvar.
    from core.services import inbox_view as iv
    monkeypatch.setattr(iv, "_aegte_vaekninger", lambda _b: [])
    monkeypatch.setattr(iv, "_aegte_jobs", lambda _b: [])
    monkeypatch.setattr(iv, "_aegte_godkendelser", lambda _b: [])
    return sti


@contextmanager
def _som_bjorn():
    from core.identity import workspace_context as wc
    with patch.object(wc, "current_user_id", return_value=BJORN):
        yield


# ── Alle fem lag ────────────────────────────────────────────────────────────

def test_alle_tre_staar_i_SKEMAET_med_intakt_indre_dict():
    """Fælden fra 2/10: en AST-sletning ramte den INDRE dict og efterlod
    `{'type': 'function'}`. Det er gyldig Python, så `compileall` tav, og først
    en helt anden test fangede det."""
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    navne = [d["function"]["name"] for d in TOOL_DEFINITIONS
             if isinstance(d.get("function"), dict) and d["function"].get("name")]
    for n in NAVNE:
        assert n in navne, f"{n} mangler i skemaet"
    assert all(isinstance(d.get("function"), dict) and d["function"].get("name")
               for d in TOOL_DEFINITIONS), "et skema har mistet sin indre dict"


def test_alle_tre_staar_i_DISPATCH():
    from core.tools.simple_tools import _TOOL_HANDLERS
    for n in NAVNE:
        assert n in _TOOL_HANDLERS, f"{n} har skema men ingen eksekutor"
        assert callable(_TOOL_HANDLERS[n])


def test_alle_tre_SENDES_altid_til_modellen():
    """`inbox_gate`s nægtelse siger «kald inbox» og «luk med inbox_done».

    Var de ikke i tier 1, skulle han hente dem midt i turen — og en hentning
    midt i turen kostede MÅLT 92 % → 26 % cache-hit, fordi tools står FØR
    beskederne. En blokering man kun kan komme ud af ved at buste sin egen
    cache er en blokering man ikke kan komme ud af.
    """
    from core.tools.copilot_tool_pruning import TIER_1_ALWAYS_ON
    for n in NAVNE:
        assert n in TIER_1_ALWAYS_ON, f"{n} sendes ikke — naegtelsen er uden udvej"


def test_alle_tre_er_i_SCOPE_for_baade_chat_og_code():
    """Og IKKE owner-only: isolationen håndhæves på `bruger_id`, så hver bruger
    ser kun sine egne. Var de owner-only, kunne et husstandsmedlem hverken se
    eller lukke det der venter på dem — og en post de ikke kan lukke står for
    evigt."""
    from core.tools.tool_scoping import (
        CHAT_MODE_TOOLS_BASE, CODE_MODE_TOOLS_BASE, OWNER_ONLY_TOOLS)
    for n in NAVNE:
        assert n in CHAT_MODE_TOOLS_BASE, f"{n} strippes i chat mode"
        assert n in CODE_MODE_TOOLS_BASE, f"{n} strippes i code mode"
        assert n not in OWNER_ONLY_TOOLS, f"{n} er owner-only"


def test_desk_OG_mobil_har_en_etikette_til_hver():
    """`tool_text_two_copies`: tool-linjens tekst findes i desk OG mobil, og
    mobilen stod to dage bagud sidst de blev rørt hver for sig. Uden en etikette
    viser rækken det RÅ værktøjsnavn."""
    desk = pathlib.Path("apps/jarvis-desk/src/lib/toolRegistry.ts").read_text()
    for n in NAVNE:
        assert f"{n}:" in desk, f"desk mangler en etikette til {n}"
    mobil = pathlib.Path("apps/mobile/src/lib/krop.ts").read_text()
    assert "'inbox'" in mobil, "mobilen kender ikke inbox"


# ── Et tomt kald giver en TYPET fejl, ikke en undtagelse ────────────────────

def test_et_TOMT_kald_giver_en_typet_fejl(inbox_db):
    with _som_bjorn():
        assert inbox_tools._exec_inbox_done({})["status"] == "error"
        assert inbox_tools._exec_inbox_done(None)["status"] == "error"
        assert inbox_tools._exec_inbox_drop({"id": "x"})["status"] == "error"
        assert inbox_tools._exec_inbox_drop({"reason": "y"})["status"] == "error"


def test_UDEN_autentificeret_bruger_svares_typet(inbox_db):
    from core.identity import workspace_context as wc
    with patch.object(wc, "current_user_id", return_value=""), \
         patch.object(wc, "current_workspace_name", return_value=""):
        for fn, a in ((inbox_tools._exec_inbox, {}),
                      (inbox_tools._exec_inbox_done, {"id": "x"}),
                      (inbox_tools._exec_inbox_drop, {"id": "x", "reason": "y"})):
            r = fn(a)
            assert r["status"] == "error" and "bruger" in r["error"]


def test_vaerktoejerne_tager_IKKE_et_bruger_id_som_parameter():
    """Kunne modellen vælge bruger, var hele bruger-afgrænsningen et flag
    kalderen styrer — præcis den fejlform `registrer_kilde` er bygget imod."""
    for d in inbox_tools.INBOX_TOOL_DEFINITIONS:
        felter = set((d["function"].get("parameters") or {}).get("properties") or {})
        for forbudt in ("bruger_id", "user_id", "bruger", "user"):
            assert forbudt not in felter, f"{d['function']['name']} tager {forbudt}"


# ── Adfærd ──────────────────────────────────────────────────────────────────

def test_inbox_viser_poster_som_TEKST_uden_payload(inbox_db):
    db_inbox.opret_eller_hent(
        bruger_id=BJORN, kildetype="job", kilde_id="job-bglj7",
        verificeret_ejer=db_inbox.EJER_JARVIS, kraever_handling=True,
        beskrivelse="hele suiten", output_sti="tasks/bglj7.output",
        output_bytes=114_688)
    with _som_bjorn():
        r = inbox_tools._exec_inbox({})
    assert r["status"] == "ok"
    assert "job-bglj7" in r["tekst"]
    assert "112 kB" in r["tekst"]
    assert "VENTER PAA DIG" in r["tekst"]
    assert r["antal_venter_paa_dig"] == 1


def test_beslutnings_poster_faar_deres_EGEN_overskrift(inbox_db):
    """5/10-2026: beslutnings-posterne stod i «VENTER PAA DIG» — den eneste
    overskrift der betyder «noget du skal svare på». De gater ikke, og de
    druknede de poster der faktisk kunne blokere."""
    db_inbox.opret_eller_hent(
        bruger_id=BJORN, kildetype="decision", kilde_id="dec_1",
        verificeret_ejer=db_inbox.EJER_JARVIS, kraever_handling=False,
        beskrivelse="[kritisk 0%] noget jeg selv har lovet")
    with _som_bjorn():
        r = inbox_tools._exec_inbox({})
    assert r["status"] == "ok"
    assert "BESLUTNINGER" in r["tekst"]
    assert "dec_1" in r["tekst"]
    assert "VENTER PAA DIG" not in r["tekst"], \
        "beslutningen stod i den gatede sektion"
    assert r["antal_venter_paa_dig"] == 0


def test_en_TOM_indbakke_siger_det_frem_for_seks_tomme_overskrifter(inbox_db):
    """En overskrift med nul linjer fylder i prompten og siger ingenting."""
    with _som_bjorn():
        r = inbox_tools._exec_inbox({})
    assert r["status"] == "ok"
    assert r["tekst"] == "Indbakken er tom."
    for titel in ("VENTER PAA DIG", "I GANG", "PAA VEJ", "PLANLAGTE"):
        assert titel not in r["tekst"]


def test_inbox_returnerer_TEKST_og_INTET_payload(inbox_db):
    """Lækagen målt 5/10-2026: `_exec_inbox` returnerede HELE den rå struktur
    under nøglen `indbakke` oveni `tekst`.

    Målt mod rigtige data samme dag: 4.441 tegn tekst — og 28.014 tegn rå
    struktur oveni, altså 6,3x, hvoraf 9.601 tegn var posternes FULDE
    beskrivelser. Værktøjets eget løfte er «én linje per post, aldrig
    filindhold», og nøglen havde NUL læsere: desk og mobil henter deres tal fra
    `opmaerksomhed`-endpointet, og `inbox_prompt_section` kalder `byg_indbakke`
    direkte.

    Testen måler BEGGE veje. En gren der bare slettede hele posten ville gå
    igennem den ene halvdel — derfor skal posten stadig være i `tekst`.
    """
    lang = ("noget jeg selv har lovet " * 12).strip()   # ~275 tegn
    db_inbox.opret_eller_hent(
        bruger_id=BJORN, kildetype="decision", kilde_id="dec_lang",
        verificeret_ejer=db_inbox.EJER_JARVIS, kraever_handling=False,
        beskrivelse=lang)
    with _som_bjorn():
        r = inbox_tools._exec_inbox({})
    raa = json.dumps(r, ensure_ascii=False)
    assert "indbakke" not in r, "den rå struktur er tilbage i svaret"
    assert lang not in raa, "den FULDE beskrivelse stod i værktøjssvaret"
    assert "dec_lang" in r["tekst"], "posten forsvandt helt — det er den anden fejl"


#: Tallene skemaet må bruge om sektionerne. Kort med vilje: beskrivelsen er
#: prosa for en model, ikke en oversættelsestabel.
_TALORD = {6: "Seks", 7: "Syv", 8: "Otte", 9: "Ni"}


def test_skemaets_beskrivelse_taeller_de_sektioner_der_FINDES():
    """Skemaet sagde «Seks sektioner» længe efter der var otte, og nævnte «hvad
    der gentager sig» — en sektion der ikke findes i visningen
    (`Kilder.gentagende` er `lambda _b: []` og har aldrig haft en kilde).

    Beskrivelsen er det modellen læser FØR den kalder, så et forkert tal der er
    ikke kosmetik: den fortæller hvad værktøjet kan svare på, og en sektion den
    lover men ikke har, er en dør der ikke findes.
    """
    n = len(inbox_tools._SEKTIONER)
    d = inbox_tools.INBOX_TOOL_DEFINITIONS[0]["function"]["description"]
    assert f"{_TALORD[n]} sektioner" in d, \
        f"skemaet siger ikke «{_TALORD[n]} sektioner» (der er {n})"
    assert "gentager sig" not in d, "beskrivelsen nævner en sektion der ikke findes"


def test_inbox_done_paa_et_UKENDT_id_er_en_FEJL_ikke_et_ok(inbox_db):
    """Et «ok» på et id der ikke findes ville frigive gaten uden at lukke
    noget. Husets hyppigste fejlform, og her er den særlig grim."""
    with _som_bjorn():
        r = inbox_tools._exec_inbox_done({"id": "findes-ikke"})
    assert r["status"] == "error"
    assert "findes-ikke" in r["error"]


def test_inbox_done_lukker_posten_og_inbox_falder(inbox_db):
    db_inbox.opret_eller_hent(bruger_id=BJORN, kildetype="job", kilde_id="job-1",
                              verificeret_ejer=db_inbox.EJER_JARVIS,
                              kraever_handling=True, beskrivelse="noget")
    with _som_bjorn():
        assert inbox_tools._exec_inbox_done({"id": "job-1"})["status"] == "ok"
        r = inbox_tools._exec_inbox({})
    assert r["antal_venter_paa_dig"] == 0
    # Men den kan stadig FINDES: «vaek fra forsiden» er ikke «slettet».
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="job-1")["status"] == \
        db_inbox.STATUS_DONE


def test_inbox_drop_kraever_en_grund_og_gemmer_den(inbox_db):
    db_inbox.opret_eller_hent(bruger_id=BJORN, kildetype="job", kilde_id="job-2",
                              verificeret_ejer=db_inbox.EJER_JARVIS,
                              kraever_handling=True)
    with _som_bjorn():
        assert inbox_tools._exec_inbox_drop({"id": "job-2", "reason": "   "})["status"] \
            == "error"
        assert inbox_tools._exec_inbox_drop(
            {"id": "job-2", "reason": "ikke relevant"})["status"] == "ok"
    assert db_inbox.hent(bruger_id=BJORN,
                         kilde_id="job-2")["afgjort_grund"] == "ikke relevant"


def test_en_ANDEN_brugers_post_kan_ikke_lukkes(inbox_db):
    db_inbox.opret_eller_hent(bruger_id="en-anden", kildetype="job",
                              kilde_id="job-andens",
                              verificeret_ejer=db_inbox.EJER_JARVIS,
                              kraever_handling=True)
    with _som_bjorn():
        assert inbox_tools._exec_inbox_done({"id": "job-andens"})["status"] == "error"
    assert db_inbox.hent(bruger_id="en-anden",
                         kilde_id="job-andens")["status"] == db_inbox.STATUS_AABEN
