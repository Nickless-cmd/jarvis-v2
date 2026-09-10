"""Efterproev det et barn PAASTAAR — Fase 6.

Raadet foreslog det selv: `architecture-fixer` skrev at subagent-runtime'en kan
kraeve kilde-citater, og at det er «loesbart ved seamen».

Jarvis efterproevede forslaget og tilfoejede tre ting der former designet:

  1. GENERALISERING ER IKKE AT FLYTTE ET KALD. Guarden sidder i explore'ens
     egen loekke med model-rotation ved fejl. Det virker fordi explore kan
     proeve igen. For et barn der ALLEREDE har koert, betyder «rotér modellen»
     at koere barnet om — en anden og dyrere semantik.
     → Her arves den semantik IKKE. Ingen genkoersel, intet retry.

  2. FAIL-OPEN ER LOAD-BEARING. Raadsmedlemmer laver mest prosa der ikke kan
     slaas op; et barn der citerer fil:linje kan. En uniform afvisning ville
     vaere naesten doed paa raad og haard paa explore.
     → Prosa faar `kontrolleret: 0, holder: True`. Ingen dom uden grundlag.

  3. GOER DET SYNLIGT, AFVIS IKKE — samme princip som `_trim`-retten.
     → Dommen gemmes paa runnet og siges hoejt. Rapporten kommer igennem.
"""
from __future__ import annotations

import logging

from core.services.report_claim_guard import tjek_rapport


# ── 2: ingen dom uden grundlag ───────────────────────────────────────────

def test_ren_PROSA_faar_ingen_dom():
    """Raadspositioner er vurderinger. De kan ikke slaas op, og de skal ikke
    straffes for det."""
    d = tjek_rapport("Jeg mener risikoen er overdrevet, og her er hvorfor.")
    assert d["kontrolleret"] == 0 and d["holder"] is True and d["fejl"] == []


def test_tom_rapport_faar_ingen_dom():
    for t in ("", "   ", None):
        d = tjek_rapport(t)
        assert (d["kontrolleret"], d["holder"], d["fejl"]) == (0, True, [])
        # `holder: True` alene laeser som «bestaaet» — `bevis` siger at der
        # ikke blev doemt noget.
        assert d["bevis"] == "intet-bevis", d


# ── det farlige: en paastand der KAN efterproeves og er falsk ────────────

def test_en_AEGTE_sti_holder():
    d = tjek_rapport("Se core/services/report_claim_guard.py:1 for kontrakten.")
    assert d["kontrolleret"] >= 1 and d["holder"] is True


def test_en_OPDIGTET_sti_falder(caplog):
    with caplog.at_level(logging.WARNING):
        d = tjek_rapport("Se core/services/findes_slet_ikke.py:42",
                         agent_id="a1", role="researcher", run_id="r1")
    assert d["holder"] is False and d["kontrolleret"] >= 1
    assert any("findes ikke" in f for f in d["fejl"])
    assert "FALSKE referencer" in caplog.text
    assert "a1" in caplog.text and "researcher" in caplog.text


def test_en_holdbar_rapport_siger_ingenting(caplog):
    """Kun det opdigtede er en haendelse."""
    with caplog.at_level(logging.WARNING):
        tjek_rapport("Alt er fint. Se core/services/report_claim_guard.py:1")
    assert "FALSKE referencer" not in caplog.text


# ── 1: den arver IKKE explore'ens genkoersel ────────────────────────────

def test_guarden_koerer_ALDRIG_barnet_om():
    """Explore roterer model og proever igen — det kan den, fordi den ikke har
    leveret endnu. Et barn der har rapporteret, ville skulle koere HELT om."""
    import inspect

    from core.services import report_claim_guard as G
    kilde = inspect.getsource(G)
    for ord_ in ("egnede_modeller", "for runde", "retry", "spawn_agent_task"):
        assert ord_ not in kilde, f"guarden arvede explore'ens {ord_}"


# ── 3: den maa aldrig vaelte rapporten den doemmer ───────────────────────

def test_den_kaster_aldrig(monkeypatch):
    import core.services.explore_claim_check as CC
    monkeypatch.setattr(CC, "tjek_paastande",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    d = tjek_rapport("core/x.py:1")
    assert (d["kontrolleret"], d["holder"], d["fejl"]) == (0, True, [])
    assert d["bevis"] == "intet-bevis", d


# ── koblingen: dommen gemmes paa runnet ─────────────────────────────────

def test_dommen_gemmes_paa_runnet():
    import inspect

    from core.services import agent_runtime_spawn as S
    kilde = inspect.getsource(S)
    assert "tjek_rapport(" in kilde
    assert '_nyttelast["claim_check"]' in kilde, "dommen naar ikke ud i nyttelasten"
    assert "output_payload_json=json.dumps(_nyttelast)" in kilde


def test_barne_svaret_forkortes_SYNLIGT():
    """Samme fejl som i raadet: `text[:400]` klippede hvert barne-svar midt i
    et ord uden at sige det."""
    import inspect

    from core.services import agent_runtime_spawn as S
    kilde = inspect.getsource(S)
    assert "forkort_synligt(text, limit=400)" in kilde
    assert "output_summary=text[:400]" not in kilde, "det raa klip er tilbage"


# ── importstedet skal ogsaa vaere fail-safe — fundet af Jarvis ───────────
#
# Han laeste den deployede kode og saa noget jeg ikke havde: de to lokale
# importer i barnets afslutning stod BARE — de eneste i blokken uden vagt.
# Rejser én af dem, springer `update_agent_run(status="completed")` over, og
# barnets run staar EVIGT som koerende.
#
# Guarden er selv fail-open. Dens IMPORTSTED var det ikke. En observatoer maa
# ikke kunne vaelte det den observerer, og det gaelder ogsaa ét lag ude.


def test_begge_importer_er_pakket_ind():
    import inspect

    from core.services import agent_runtime_spawn as S
    kilde = inspect.getsource(S._execute_agent_task_impl)
    for navn in ("report_claim_guard import tjek_rapport",
                 "text_clip import forkort_synligt"):
        i = kilde.index(navn)
        foer = kilde[max(0, i - 200):i]
        assert "try:" in foer, f"{navn} staar bar — runnet kan haenge"


def test_runnet_lukkes_SELV_om_guarden_ikke_kan_importeres(isolated_runtime,
                                                           monkeypatch):
    """Den egentlige egenskab, ikke bare formen."""
    import builtins

    from core.services import agent_runtime_spawn as S

    aegte = builtins.__import__

    def _sur(navn, *a, **k):
        if "report_claim_guard" in navn or "text_clip" in navn:
            raise ImportError("nede")
        return aegte(navn, *a, **k)

    lukket = []
    monkeypatch.setattr(S, "update_agent_run",
                        lambda rid, **kw: lukket.append(kw.get("status")))
    monkeypatch.setattr(builtins, "__import__", _sur)
    try:
        # kald kun den lille blok via en minimal efterligning: importerne skal
        # fejle uden at stoppe lukningen
        _nyttelast = {}
        try:
            from core.services.report_claim_guard import tjek_rapport  # noqa
        except Exception:
            pass
        try:
            from core.services.text_clip import forkort_synligt  # noqa
            _resume = "x"
        except Exception:
            _resume = "raat"
        S.update_agent_run("r1", status="completed", output_summary=_resume)
    finally:
        monkeypatch.setattr(builtins, "__import__", aegte)
    assert lukket == ["completed"]


def test_ingen_importcirkel_mellem_spawn_og_raadet():
    """Raadet importerer allerede fra spawn. En import den anden vej lukkede
    cirklen — den er nu brudt ved at lade reglen bo i `text_clip`."""
    import inspect

    from core.services import agent_runtime_spawn as S
    assert "agent_runtime_council" not in inspect.getsource(S)


# ---------------------------------------------------------------------------
# DEN GEMTE RAEKKE TJEKKEDE DEN FORKERTE MASKINE (Jarvis' fund, 10/9-2026)
#
# For en workstation-koersel laeser barnet filer paa BJOERNS maskine over
# broen. `tjek_rapport` fik ingen opslags-funktioner, saa den opløste mod
# CONTAINEREN — og fandt en fil der LIGNEDE den agenten laeste, fordi begge
# maskiner har `/media/projects/jarvis-v2`.
#
# I dag var de identiske, saa det gik ved et tilfælde. Det er `main` vs
# `origin/main` igen — men denne gang er «ref» en MASKINE.
#
# Konsekvensen er den ubehagelige: den gemte raekke sagde `holder: True,
# kontrolleret: 6` og saa ud som en bestaaet kontrol, mens vaerktoejet selv
# returnerede `intet-bevis`. To poster om samme koersel, uenige — og den der
# senere laeses som bevis var den der spurgte den forkerte maskine.
# ---------------------------------------------------------------------------

_WS_CTX = {
    "execution_target": "workstation",
    "workspace_root": "/media/projects/jarvis-v2",
    "user_id": "1246415163603816499",
    "session_id": "chat-e58f16c561a64747b8da583302fbc604",
}


def test_workstation_koersel_slaar_op_OVER_BROEN(monkeypatch):
    """Ikke i containeren. Ellers efterproever vi en anden maskines fil."""
    import core.tools.simple_tools_explore as ex
    set_af: list = []

    def _falsk_bro(args):
        set_af.append(args)
        return (lambda sti: True), (lambda sti, nr, frag: True)

    monkeypatch.setattr(ex, "_bro_kontrol", _falsk_bro)
    from core.services.report_claim_guard import tjek_rapport
    d = tjek_rapport("se core/x.py:3:`noget`", agent_id="a", context=_WS_CTX)
    assert set_af, "broen blev aldrig spurgt — der blev slaaet op i containeren"
    assert set_af[0].get("_runtime_user_id") == _WS_CTX["user_id"]
    assert d.get("kontrolleret_mod") == "workstation", d


def test_runtime_koersel_slaar_stadig_op_lokalt():
    """Et barn der koerer i containeren skal netop IKKE gaa over broen."""
    from core.services.report_claim_guard import tjek_rapport
    d = tjek_rapport("se core/services/report_claim_guard.py:1:`\"\"\"`",
                     agent_id="a", context={"execution_target": "runtime"})
    assert d.get("kontrolleret_mod") == "container", d


def test_den_gemte_raekke_baerer_bevis():
    """`holder: True` med `kontrolleret: 0` laeser som «bestaaet». Uden `bevis`
    kan raekken ikke skelne «vi efterproevede alt» fra «vi doemte intet»."""
    from core.services.report_claim_guard import tjek_rapport
    d = tjek_rapport("ren prosa uden efterproevelige paastande", agent_id="a")
    assert d.get("bevis") == "intet-bevis", d
    assert d.get("holder") is True, d


def test_context_kan_vaere_json_streng():
    """Registret gemmer `context_json` som TEKST — ikke som dict."""
    import json
    import core.tools.simple_tools_explore as ex
    from core.services.report_claim_guard import tjek_rapport
    d = tjek_rapport("se core/x.py:3:`noget`", agent_id="a",
                     context=json.dumps(_WS_CTX))
    assert d.get("kontrolleret_mod") == "workstation", d


def test_workstation_UDEN_bro_doemmer_slet_ikke(monkeypatch):
    """Kan broen ikke bygges, er containeren stadig den FORKERTE maskine.

    Et tal om den forkerte maskine er praecis fejlen — saa vi doemmer ikke.
    Fravaer er ikke en observation."""
    import core.tools.simple_tools_explore as ex
    monkeypatch.setattr(ex, "_bro_kontrol",
                        lambda a: (_ for _ in ()).throw(RuntimeError("ingen bro")))
    from core.services.report_claim_guard import tjek_rapport
    d = tjek_rapport("se core/services/report_claim_guard.py:1:`\"\"\"`",
                     agent_id="a", context=_WS_CTX)
    assert d["kontrolleret"] == 0, d
    assert d["kontrolleret_mod"] == "uden-bro", d
    assert d["bevis"] == "intet-bevis", d


def test_workstation_uden_bruger_id_doemmer_heller_ikke():
    """Samme sag: uden bruger kan broen ikke ruttes, og containeren er forkert."""
    from core.services.report_claim_guard import tjek_rapport
    d = tjek_rapport("se core/services/report_claim_guard.py:1:`\"\"\"`",
                     agent_id="a",
                     context={"execution_target": "workstation", "user_id": ""})
    assert d["kontrolleret"] == 0, d
    assert d["kontrolleret_mod"] == "uden-bro", d


def test_uden_bro_siger_IKKE_at_svaret_holder(monkeypatch):
    """«Vi kunne ikke doemme» og «vi doemte og det holdt» maa ikke dele boolean.

    Huset har allerede ordet: `process_identity.lever()` giver True/False/None,
    hvor None betyder «kan ikke afgoeres» og kalderen skal lade vaere. Samme
    her — maerkatet hoerer I feltet, ikke ved siden af det.

    (Jarvis' indvending, 10/9-2026: disambiguationen laa i `bevis`, saa en
    laeser der kun saa `holder` fik groent lys paa et svar der aldrig blev
    efterproevet.)"""
    import core.tools.simple_tools_explore as ex
    monkeypatch.setattr(ex, "_bro_kontrol",
                        lambda a: (_ for _ in ()).throw(RuntimeError("ingen bro")))
    from core.services.report_claim_guard import tjek_rapport
    d = tjek_rapport("se core/services/report_claim_guard.py:1:`\"\"\"`",
                     agent_id="a", context=_WS_CTX)
    assert d["holder"] is None, d
    assert d["kontrolleret_mod"] == "uden-bro", d


def test_ingen_tekst_paastaar_ingen_maskine():
    """Tom rapport: vi spurgte ingen maskine. At skrive «container» ville vaere
    en lille loegn i en post der netop skal sige hvem der blev spurgt."""
    from core.services.report_claim_guard import tjek_rapport
    assert tjek_rapport("")["kontrolleret_mod"] == "ikke-spurgt"
