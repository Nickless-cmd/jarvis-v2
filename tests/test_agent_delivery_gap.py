"""En LÆSE-agent der stopper midt i maa ikke meldes ``completed`` (10/11-2026).

MAALT i drift paa raad `council-92089f9dc9a842f2` (`team-6096a3fb53c51a2c`): to
medlemmer blev meldt ``completed`` med **28 og 56 tegn** efter 3-4 vaerktoejskald:

  * "Nu linjerne omkring 187-320."
  * "Nu skal jeg se linjer omkring 670-720 for fuld kontekst."

Begge havde `max_turns: 8`, brugte 3-4 kald, sluttede 30 minutter FOER deres
deadline, og hvert kald var `ok`. Ingen budgetgraense, ingen fejl — modellen
stoppede selv midt i laesningen.

Stop-grenen havde praecis tre indgange: ``scout`` (research-rollen), ``must_write``
(agenten KAN skrive) og ``unanswered`` (tal i opgaven). Et laese-medlem i et raad
ramte nul af dem, og `_promises_action` kender kun verber — "Nu skal jeg se" har
futurum uden et af dem.

Kilden er derfor ikke en ny ordliste men KONTRAKTEN: `expected_result` er allerede
skrevet ned for hver assignment, men blev hidtil kun sendt TIL agenten som tekst i
prompten — aldrig laest som et vilkaar TIL agenten.

Testen er et PAR, som de andre leverance-tests: den tomme leverance skal afvises,
og den FAKTISKE leverance skal gaa igennem. En vagt der goer alt til "fejlet" er
lige saa blind som den der goer alt til "faerdigt".
"""
from __future__ import annotations

import pytest

from core.services import agent_loop_core as core

#: Kontrakten som den faktisk stod paa det raad hvis medlemmer stoppede midt i.
KONTRAKT = "Præcis forskel mellem worktree-write på worker-ruten og CLI-ruten"

#: De to svar, ord for ord, som systemet meldte ``completed``.
TOM_1 = "Nu linjerne omkring 187-320."
TOM_2 = "Nu skal jeg se linjer omkring 670-720 for fuld kontekst."

#: Et svar der FAKTISK leverer det kontrakten bestiller.
RIGTIGT = (
    "Forskellen ligger i værktøjsskemaet, ikke i agenten. På worker-ruten bygges "
    "skemaet af `tools_for_policy(\"worktree-write\")` i core/services/"
    "agent_runtime_base.py:697, som giver læseværktøjer plus `wt_bash` og "
    "`wt_write_file`. På CLI-ruten bygges det i core/services/agent_cli_backend.py:187 "
    "og indeholder kun Read, Glob, Grep, Edit og Write — ingen shell. Begge ruter "
    "skriver altså i worktreen, men kun worker-ruten kan VERIFICERE sit arbejde."
)


class FakeIO:
    def __init__(self, replies, tool_out="ok"):
        self.replies = list(replies)
        self.tool_out = tool_out
        self.model_calls, self.tool_calls, self.rounds = [], [], []

    def model(self, *, messages, tools, requires_tools, provider, model):
        self.model_calls.append({"tools": tools, "requires_tools": requires_tools,
                                 "messages": [dict(m) for m in messages]})
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def tool(self, tc):
        self.tool_calls.append(tc["id"])
        return self.tool_out

    def after_tool(self, tc, out):
        pass

    def after_round(self, rounds, tool_calls):
        self.rounds.append(rounds)


def _tc(i):
    return {"id": f"c{i}", "function": {"name": "read_file", "arguments": "{}"}}


def _text(t):
    return {"text": t, "tool_calls": []}


def _run(io, **kw):
    base = dict(prompt="Undersøg forskellen.", tools_payload=[{"function": {"name": "read_file"}}],
                requires_tools=True, provider="p", model="m", scout=False, max_rounds=8,
                synthesis_directive="SLUT")
    base.update(kw)
    return core.run_tool_loop(io, **base)


# ── Den maalte fejlform ────────────────────────────────────────────────────

@pytest.mark.parametrize("tomt_svar", [TOM_1, TOM_2])
def test_a_reading_agent_that_stops_mid_reading_is_not_completed(tomt_svar):
    """Ordret de to svar der slap igennem: 28 og 56 tegn efter tre kald."""
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        {"text": "", "tool_calls": [_tc(2)]},
        {"text": "", "tool_calls": [_tc(3)]},
        _text(tomt_svar),
        _text(tomt_svar),
    ])
    out = _run(io, expected_result=KONTRAKT)

    assert out.get("incomplete") is True, "en undersøgelse der stoppede midt i er ikke en leverance"
    assert "tegn" in out["stop_reason"], out["stop_reason"]
    assert "3 værktøjskald" in out["stop_reason"]
    # Teksten bevares — Jarvis skal kunne se HVAD agenten naaede, ikke kun at noget manglede.
    assert out["final_text"] == tomt_svar


def test_the_agent_gets_one_order_naming_the_gap_not_a_verdict():
    """Nudgen skal navngive hullet, saa agenten kan rette det — ikke doemme den."""
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(TOM_1),
        _text(RIGTIGT),
    ])
    out = _run(io, expected_result=KONTRAKT)

    # Foerste kald + nudge + det rigtige svar.
    assert len(io.model_calls) == 3
    # Nudgen ligger i det TREDJE kald: det andet er kaldet hvor det tomme svar kom,
    # og dets sidste besked er stadig værktøjs-resultatet.
    nudge = io.model_calls[2]["messages"][-1]["content"]
    assert "kan ikke accepteres" in nudge
    assert "tegn" in nudge
    # Den rettede sig → leverancen accepteres.
    assert not out.get("incomplete")
    assert out["final_text"] == RIGTIGT


# ── Den faktiske leverance skal gaa igennem ────────────────────────────────

def test_a_real_investigation_passes_without_a_nudge():
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(RIGTIGT),
    ])
    out = _run(io, expected_result=KONTRAKT)

    assert len(io.model_calls) == 2, "et fuldt svar skal ikke have en ekstra runde"
    assert not out.get("incomplete")
    assert out["final_text"] == RIGTIGT


# ── Ingen kontrakt = ingen ny adfaerd ─────────────────────────────────────

def test_without_a_contract_the_loop_behaves_exactly_as_before():
    """Uden `expected_result` findes der intet at maale imod, og grenen er tavs.

    Det er det vaern der holder en gammel, korrekt koersel ude af fejl — samme
    regel som daeknings-erklæringen foelger: kontrakten kan kun goere maalingen
    bedre, aldrig efterlade noget der virkede som fejl.
    """
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(TOM_1),
    ])
    out = _run(io)                       # ingen expected_result

    assert len(io.model_calls) == 2
    assert not out.get("incomplete")


def test_a_contract_without_any_tool_call_is_left_to_the_other_gates():
    """En agent der slet ikke undersøgte ejes af scout-/loefte-grenene, ikke af denne."""
    io = FakeIO([_text(TOM_1), _text(TOM_1)])
    out = _run(io, expected_result=KONTRAKT)

    assert not out.get("incomplete")
    assert out["total_tool_calls"] == 0


# ── Det bestilte bevis ────────────────────────────────────────────────────

def test_a_contract_that_orders_file_names_rejects_a_long_answer_without_them():
    """Et langt svar er ikke det samme som det BESTILTE svar."""
    kontrakt = KONTRAKT + ". Svar med præcise filnavne og linjenumre."
    langt_uden_bevis = (
        "Der er en vigtig forskel på de to ruter. Den ene har shell-adgang gennem "
        "sit worktree-værktøj, den anden har ikke. Det betyder at den ene kan køre "
        "tests selv, mens den anden må beskrive hvad den ville have gjort. Det er "
        "en strukturel forskel i hvad agenten kan verificere, ikke bare i hvilke "
        "navne der står i skemaet."
    )
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(langt_uden_bevis),
        _text(langt_uden_bevis),
    ])
    out = _run(io, expected_result=kontrakt)

    assert out.get("incomplete") is True
    assert "filnavne" in out["stop_reason"]


def test_a_contract_that_orders_file_names_accepts_an_answer_that_carries_them():
    kontrakt = KONTRAKT + ". Svar med præcise filnavne og linjenumre."
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(RIGTIGT),
    ])
    out = _run(io, expected_result=kontrakt)

    assert not out.get("incomplete")


# ── Enheden selv ──────────────────────────────────────────────────────────

def test_the_gap_measure_returns_empty_only_when_the_delivery_can_be_accepted():
    assert core._delivery_gap("", TOM_1, 3) == ""
    assert core._delivery_gap(KONTRAKT, TOM_1, 0) == ""
    assert core._delivery_gap(KONTRAKT, TOM_1, 3) != ""
    assert core._delivery_gap(KONTRAKT, RIGTIGT, 3) == ""


def test_a_writing_agent_is_left_to_the_must_write_gate():
    """En agent der KAN skrive maales paa sin AENDRING, ikke paa sin tekst.

    Maalt 10/11-2026: uden denne afgraensning fik en skrivende agent
    ``_delivery_nudge`` i stedet for ``_ACTION_NUDGE``, fordi dens korte svar blev
    laest som en undersoegelse der ikke var afleveret. Spoergsmaalet om en skrivende
    agent der IKKE skrev ejes af ``must_write``-grenen, og en der skrev har bevist
    sit arbejde i worktree'en.
    """
    assert core._delivery_gap(KONTRAKT, TOM_1, 3, "", 0, True) == ""
    # Den samme maaling for en LAESE-agent er stadig et hul — reglen er ikke en lempelse.
    assert core._delivery_gap(KONTRAKT, TOM_1, 3, "", 0, False) != ""


def test_a_short_answer_that_covers_every_numbered_question_is_a_delivery():
    """Et kort svar er ikke et tomt svar, naar det besvarer det hele.

    Maalt 10/11-2026: "1. Fem felter. 2. agent_assignment_mandates. 3. To steder."
    er 58 tegn og en FULD besvarelse. Laengdetaersklen afviste den — praecis den
    falske positiv taersklen selv advarer om. Daekningen vinder over laengden.
    """
    opgave = ("Undersøg tre ting:\n1) Hvor mange felter har Task?\n"
              "2) Hvilken tabel bærer mandaterne?\n3) Hvor sættes grenen?\n")
    kort_men_fuldt = "1. Fem felter.\n2. agent_assignment_mandates.\n3. To steder."
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(kort_men_fuldt),
        # Reserve-svar: fyrer vagten alligevel, ses det paa antallet af modelkald i
        # stedet for som en IndexError der maskerer fejlen. Maalt 10/11-2026: uden
        # denne reserve var testen groen af den FORKERTE grund — den fangede ikke en
        # mutation der fjernede daeknings-check'en.
        _text(kort_men_fuldt),
    ])
    out = _run(io, prompt=opgave, expected_result=KONTRAKT)

    assert len(io.model_calls) == 2, "et fuldt daekket svar skal ikke have en ekstra runde"
    assert not out.get("incomplete"), out.get("stop_reason")
    assert out["final_text"] == kort_men_fuldt


def test_the_form_request_is_read_from_the_prompt_when_the_contract_is_short():
    """Kravene kan staa i PROMPTEN selv om kontrakten er kort.

    Maalt 10/11-2026 paa 139 assignments: ``Task`` saetter ``expected_result`` til
    den korte description, og **1 af 139** bestilte en form — 89 var under 60 tegn.
    Form-kravet var dermed doedt for alle praktiske formaal, ogsaa naar opgaven selv
    skrev "citer linjenumre, gæt ikke". Kilden er derfor baade kontrakten OG prompten.
    """
    opgave = "Undersøg forskellen. Citér linjenumre — gæt ikke."
    langt_uden_bevis = (
        "Der er en vigtig forskel på de to ruter. Den ene har shell-adgang gennem "
        "sit worktree-værktøj, den anden har ikke. Det betyder at den ene kan køre "
        "tests selv, mens den anden må beskrive hvad den ville have gjort."
    )
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(langt_uden_bevis),
        _text(langt_uden_bevis),
    ])
    out = _run(io, prompt=opgave, expected_result=KONTRAKT)   # kort kontrakt, krav i prompten

    assert out.get("incomplete") is True
    assert "filnavne" in out["stop_reason"]
