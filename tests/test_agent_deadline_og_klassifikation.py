"""To grænser der begge var teater (11/11-2026).

MAALT FOER AENDRINGEN:

1. ``AGENT_INCOMPLETE``/``delivery`` blev sat for ENHVER tekst med ordet
   ``UFULDSTÆNDIG`` i. Markeringen baerer allerede den aegte grund i parentesen
   (``agent_runtime_base._loop_result`` skriver ``stop_reason`` derind), men den
   blev kastet vaek. Resultat: et kapacitetsstop ("rundebudgettet loeb ud") blev
   rapporteret som en mangelfuld leverance, og den naeste jagt gik efter den
   forkerte aarsag.

2. ``deadline_at`` blev skrevet ind i kontrakten af ``agent_task_facade`` (nu + 45
   min for skrivende, + 30 for laesende), gemt i ``agent_assignments``, projiceret
   til Desk — og **aldrig laest i loopet**. Den var dekoration. Det eneste loft der
   faktisk stoppede en agent var et rundetal paa 60, og maalt paa 133
   completed-koersler er median-rundetiden 3,5 s: 60 runder = ~3,5 minut, mens
   kontrakten gav 45. Rundetallet ramte altsaa foerst og klippede et arbejde der
   stadig havde tid.

Vagterne er PAR: hver aendring skal baade virke og ikke goere noget andet galt.
"""
from __future__ import annotations

import types
from datetime import UTC, datetime, timedelta

import pytest

from core.runtime.db_agent_contract import partial_delivery_error
from core.services import agent_loop_core as core


class FakeIO:
    def __init__(self, replies, tool_out="ok"):
        self.replies = list(replies)
        self.tool_out = tool_out
        self.model_calls = []

    def model(self, *, messages, tools, requires_tools, provider, model):
        self.model_calls.append([dict(m) for m in messages])
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def tool(self, tc):
        return self.tool_out

    def after_tool(self, tc, out):
        pass

    def after_round(self, rounds, tool_calls):
        pass


def _tc(i):
    return {"id": f"c{i}", "function": {"name": "t", "arguments": "{}"}}


def _run(io, **kw):
    base = dict(prompt="P", tools_payload=[{"function": {"name": "t"}}], requires_tools=True,
                provider="p", model="m", scout=False, max_rounds=3, synthesis_directive="SLUT")
    base.update(kw)
    return core.run_tool_loop(io, **base)


#: Et svar der ikke er et loefte og ikke for kort, saa kun den graense vi maaler
#: kan goere det incomplete.
_FAERDIG = ("Undersoegelsen er afsluttet. Feltet hedder description og er en streng. "
            "Feltet prompt er en streng, subagent_type er en streng, og model er en streng. "
            "run_in_background er en boolean. Det er de fem felter, alle verificeret i koden.")


# ── 1. Klassifikationen: grunden i markeringen afgoer koden ──────────────────
@pytest.mark.parametrize("grund,kode,fase", [
    # Kapacitet: agenten blev STOPPET, dens leverance var ikke mangelfuld.
    ("rundebudgettet løb ud efter 60 runder", "AGENT_BUDGET_EXHAUSTED", "capacity"),
    ("deadline nået efter 12 runder", "AGENT_BUDGET_EXHAUSTED", "capacity"),
    # Leverance: agenten kunne arbejde men gjorde det ikke.
    ("agenten kunne skrive men skrev intet", "AGENT_NO_WRITE", "delivery"),
    ("3 værktøjskald, men svaret er et løfte om næste skridt — ikke et resultat",
     "AGENT_PROMISED_NOT_DONE", "delivery"),
    ("et løfte den ikke udførte", "AGENT_PROMISED_NOT_DONE", "delivery"),
    # Ukendt grund: den gamle kode bevares, saa eksisterende laesere ikke braekker.
    ("2 ubesvarede spørgsmål", "AGENT_INCOMPLETE", "delivery"),
    ("", "AGENT_INCOMPLETE", "delivery"),
])
def test_markeringens_grund_afgoer_koden(grund, kode, fase):
    tekst = f"UFULDSTÆNDIG ({grund}) — agentens tekst:\n" + _FAERDIG
    assert partial_delivery_error(full=tekst, registry_status="failed") == (kode, fase)


def test_en_aegte_fejl_er_stadig_model_og_ikke_kapacitet():
    """Vagten skal ikke goere alt til kapacitet — saa bliver systemet blindt."""
    assert partial_delivery_error(full="Connection reset by peer",
                                  registry_status="failed") == ("AGENT_FAILED", "model")


def test_tekst_med_parentes_uden_markering_falder_tilbage_paa_status():
    assert partial_delivery_error(
        full="RuntimeError (500) — udbyderen svarede",
        registry_status="failed") == ("AGENT_FAILED", "model")


# ── 2. Deadline: tiden er graensen ─────────────────────────────────────────
def _fast_tid(monkeypatch, nu: datetime) -> None:
    """Erstat `time` KUN inde i loop-kernen, saa den globale ur ikke roeres."""
    monkeypatch.setattr(core, "time", types.SimpleNamespace(
        time=lambda: nu.timestamp(), monotonic=lambda: nu.timestamp(),
        sleep=lambda _s: None))


def test_deadline_i_fortiden_stopper_foer_et_eneste_modelkald(monkeypatch):
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([{"text": _FAERDIG}])
    out = _run(io, deadline_at=(nu - timedelta(seconds=1)).isoformat())
    assert io.model_calls == [], "et modelkald blev brugt efter deadlinen"
    assert out.get("incomplete") is True
    assert "deadline" in str(out.get("stop_reason") or "")


def test_rundetallet_klipper_ikke_naar_der_findes_en_deadline(monkeypatch):
    """Det maalte problem: 60 runder = ~3,5 minut mod en deadline paa 45 minutter.

    Med en deadline langt ude skal et lavt `max_rounds` derfor IKKE klippe forloebet.
    """
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        {"text": "", "tool_calls": [_tc(2)]},
        {"text": "", "tool_calls": [_tc(3)]},
        {"text": _FAERDIG},
    ])
    out = _run(io, max_rounds=2, deadline_at=(nu + timedelta(minutes=40)).isoformat())
    assert out["rounds"] == 4, f"blev klippet ved {out['rounds']} runder"
    assert out["total_tool_calls"] == 3


def test_uden_deadline_gaelder_rundetallet_stadig(monkeypatch):
    """Regression: kaldes loekken uden deadline, er det gamle loft uaendret."""
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        {"text": "", "tool_calls": [_tc(2)]},
        {"text": "", "tool_calls": [_tc(3)]},
        {"text": _FAERDIG},
    ])
    out = _run(io, max_rounds=2)
    assert out["rounds"] == 2, f"loftet bandt ikke: {out['rounds']} runder"


def test_tidsnoten_naevner_den_mindste_taerskel_og_ikke_en_stoerre(monkeypatch):
    """Er der 2 minutter tilbage, er "10 minutter tilbage" en loegn."""
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        {"text": _FAERDIG},
    ])
    _run(io, max_rounds=10, deadline_at=(nu + timedelta(seconds=120)).isoformat())
    noter = [m["content"] for m in io.model_calls[1]
             if m["role"] == "user" and "Tidsgrænse" in str(m.get("content"))]
    assert noter, "tidsnoten blev aldrig injiceret"
    assert "3 minutter" in noter[-1], f"fik {noter[-1]!r}"
    assert "10 minutter" not in noter[-1]


def test_ugyldig_deadline_handhaeves_ikke_men_kaster_ikke(monkeypatch):
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([{"text": "", "tool_calls": [_tc(1)]},
                 {"text": _FAERDIG}])
    out = _run(io, max_rounds=5, deadline_at="ikke-en-dato")
    assert out["rounds"] == 2


# ── Daeknings-detektoren: spoergsmaal fra kontrakten, ikke fra fri tekst (11/11-2026) ──
#
# MAALT I DRIFT: 26 af 31 ``AGENT_INCOMPLETE`` ramte daeknings-detektoren, ikke agentens
# arbejde. To mekanismer, begge maalt paa faktiske assignments i basen:
#
#   1. En nummereret linje under en krav-overskrift er et FORMATKRAV. I
#      ``asg-bfde7917307541aa`` bad opgaven om to ting og nummererede derefter tre krav,
#      hvor det tredje var "skriv DAEKNING-linjen". Agenten svarede korrekt paa begge
#      spoergsmaal og erklaerede ``DAEKNING: 1,2`` — og blev doemt for det tredje.
#   2. Et team-medlem fik HELE raadets tekst. De fire medlemmers roller blev laest som
#      fire ubesvarede spoergsmaal, saa alle fire blev stemplet fejlet for de tre andres
#      opgaver. ``_own_task`` fandtes allerede og blev brugt i ``_unanswered_detail``,
#      men var glemt i ``_delivery_gap``.


def test_formatkrav_taelles_ikke_som_spoergsmaal():
    """En nummereret linje der beskriver svarets FORM er et formatkrav, ikke et spoergsmaal."""
    opgave = (
        "Undersoeg to ting:\n"
        "1. Hvad er den nyeste version?\n"
        "2. Hvornaar blev den udgivet?\n"
        "\n"
        "Krav til svaret:\n"
        "1. Naevn versionen.\n"
        "2. Naevn værktøjerne.\n"
        "3. Skriv DAEKNING-linjen til sidst.\n"
    )
    assert core._question_numbers(opgave) == {1, 2}


def test_indholdskrav_under_en_krav_overskrift_er_stadig_spoergsmaal():
    """Værnet mod den for grove regel: placering afgoer ikke, indholdet goer.

    11/11-2026: den foerste udgave skar ALT efter "Krav til svaret:" — og dermed ogsaa de
    aegte krav. Maalt paa `asg-bfde7917307541aa` blev hele spoergsmaalsmaengden tom, saa
    detektoren holdt op med at maale noget som helst. En detektor der ikke kan se forskel
    skal ikke slaa sig selv fra; den skal se snaevert.
    """
    opgave = (
        "Krav til svaret:\n"
        "1. Naevn versionen og udgivelsesdatoen.\n"
        "2. Naevn hvilke værktøjer du brugte.\n"
        "3. Skriv «DAEKNING: 2/2» som sidste linje.\n"
    )
    assert core._question_numbers(opgave) == {1, 2}


def test_svar_paa_alle_aegte_krav_godkendes_trods_formatkrav():
    """Det maalte driftsforloeb ende-til-ende: korrekt svar, erklaering 1,2, tredje var form."""
    opgave = (
        "Krav til svaret:\n"
        "1. Naevn versionen og udgivelsesdatoen.\n"
        "2. Naevn hvilke værktøjer du brugte.\n"
        "3. Skriv «DAEKNING: 2/2» som sidste linje.\n"
    )
    svar = (
        "**Svar**\n"
        "1) Nyeste stabile Python er 3.15.2, udgivet 25. oktober 2026.\n"
        "2) Jeg brugte web_search og web_fetch.\n"
        "DAEKNING: 1,2\n"
    )
    assert core._unanswered_questions(opgave, svar) == 0


def test_spoergsmaal_uden_krav_overskrift_taelles_stadig():
    """Regression: uden en krav-overskrift er nummereringen stadig spoergsmaal."""
    opgave = "Svar paa:\n1. Foerste\n2. Andet\n3. Tredje\n"
    assert core._question_numbers(opgave) == {1, 2, 3}


def test_team_medlem_maales_paa_sin_egen_akse():
    """De andre medlemmers roller er ikke DENNE agents ubesvarede spoergsmaal."""
    raad = (
        "Raad om fire akser.\n\n"
        "MEDLEMMER:\n"
        "1. rolle: bruger\n   task: Gaa gennem views.\n"
        "2. rolle: release\n   task: Afgoer om release kan leveres.\n"
        "3. rolle: testdaekning\n   task: Afgoer hvad testene daekker.\n"
        "4. rolle: dobbeltleverance\n   task: Afgoer om de to leverancer deles.\n"
        "\n"
        "Din opgave i teamet: Afgoer hvad testene daekker og hvad de ikke goer.\n"
    )
    assert core._question_numbers(raad) == {1, 2, 3, 4}
    assert core._question_numbers(core._own_task(raad)) == set()


def test_team_medlem_med_egne_nummererede_spoergsmaal_taeller_dem():
    """Et medlem der FAKTISK faar nummererede spoergsmaal skal stadig maales paa dem."""
    raad = (
        "1. rolle: a\n   task: noget\n"
        "2. rolle: b\n   task: noget andet\n"
        "\n"
        "Din opgave i teamet: Svar paa:\n1. Hvad er X?\n2. Hvad er Y?\n"
    )
    assert core._question_numbers(core._own_task(raad)) == {1, 2}


def test_korrekt_svar_paa_formatkrav_opgave_doemmes_ikke():
    """Det maalte tilfaelde: to spoergsmaal besvaret, tredje nummer var et formatkrav."""
    opgave = (
        "Undersoeg:\n1. Version?\n2. Udgivelsesdato?\n\n"
        "Krav til svaret:\n1. Naevn versionen.\n2. Naevn værktøjerne.\n"
        "3. Skriv DAEKNING-linjen.\n"
    )
    svar = (
        "1) Version 3.15.2.\n"
        "2) Udgivet 25. oktober 2026.\n"
        "DAEKNING: 1,2\n"
    )
    assert core._unanswered_questions(opgave, svar) == 0
