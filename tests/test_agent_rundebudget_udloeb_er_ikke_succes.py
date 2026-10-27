"""Rundebudgettet loeb ud midt i arbejdet — det er ikke en fuldfoert opgave (26/10-2026).

MAALT 26/10-2026 paa `asg-a413aa7ac3704131` (run-3ff74d5e954946f6):

  * 7 vaerktoejskald i 7 runder
  * runde 8 = den SIDSTE tilladte — agenten svarede med en statusnote:
    "Confirmed: Task har 5 properties ... Nu spoergsmaal 2 — database-tabel ..."
  * loekken gav sin nudge, som forbruger den sidste runde, og udloeb derefter paa
    `while rounds < max_rounds`
  * `unanswered` blev beregnet men naaede ALDRIG markeringen, fordi den linje ligger
    EFTER `continue`
  * udfaldet blev `completed` med statusnoten som "svar"

Fejlen er ikke en tekstvurdering: at rundebudgettet loeb ud er et FAKTUM. Testen
maaler at det faktum baeres ud — og at en koersel med plads til nudgen stadig
kan blive faerdig, saa vagten ikke goer systemet blindt.
"""
from __future__ import annotations

from core.services import agent_loop_core as core
from core.services.agent_runtime_base import _loop_result

OPGAVE = (
    "Besvar disse TRE spørgsmål.\n\n"
    "SPØRGSMÅL 1: Hvor mange felter har Task-skemaet?\n"
    "SPØRGSMÅL 2: Hvad hedder mandat-tabellen?\n"
    "SPØRGSMÅL 3: Hvor mange steder kaldes dispatch_agent?\n"
)

# Den faktiske tekst fra den maalte koersel: 1 besvaret, 2 og 3 annonceret som naeste skridt.
STATUSNOTE = ("Confirmed: Task har 5 properties: description, model, prompt, "
              "run_in_background, subagent_type.\n\nNu spørgsmål 2 — database-tabel for "
              "agent-assignment-mandater.")
FULDT_SVAR = "1. Fem felter.\n2. agent_assignment_mandates.\n3. To steder."


class FakeIO:
    def __init__(self, replies):
        self.replies = list(replies)
        self.model_calls = 0

    def model(self, *, messages, tools, requires_tools, provider, model):
        self.model_calls += 1
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def tool(self, tc):
        return "ok"

    def after_tool(self, tc, out):
        pass

    def after_round(self, rounds, tool_calls):
        pass


_LÆSEVÆRKTOEJ = [{"function": {"name": "read_file"}}]
_ET_KALD = {"text": "Filen har 161 linjer.", "input_tokens": 10, "output_tokens": 5,
            "cost_usd": 0.0,
            "tool_calls": [{"id": "c1", "function": {"name": "read_file", "arguments": "{}"}}]}


def _svar(tekst: str) -> dict:
    return {"text": tekst, "input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}


def _kør(*, max_rounds: int, antal_kald: int, slutsvar: str) -> dict:
    io = FakeIO([_ET_KALD] * antal_kald + [_svar(slutsvar)])
    return core.run_tool_loop(
        io, prompt=OPGAVE, tools_payload=_LÆSEVÆRKTOEJ, requires_tools=False,
        provider="p", model="m", scout=False, max_rounds=max_rounds,
        synthesis_directive="SLUT",
    )


def test_udloeb_paa_den_sidste_runde_markeres_som_ufuldstaendig():
    """Praecis den maalte vej: 7 kald + tekst i runde 8 = loftet."""
    out = _kør(max_rounds=8, antal_kald=7, slutsvar=STATUSNOTE)
    assert out.get("incomplete") is True, (
        "loekken loeb ud midt i arbejdet og meldte alligevel succes. "
        f"udfald: {out!r}"
    )
    # 3, ikke 2: agenten svarede paa spoergsmaal 1 i PROSA uden at nummerere det, og
    # optaellingen ser kun nummererede svar. Det er den aarlige overkant — derfor hedder
    # det "spoergsmaal uden nummereret svar" i payloaden, ikke "ubesvarede spoergsmaal".
    assert out.get("unanswered") == 3, (
        f"forventede 3 spoergsmaal uden nummereret svar, fik {out.get('unanswered')!r}"
    )


def test_aarsagen_til_stoppet_staar_i_udfaldet():
    """Bjørns krav: HVORFOR arbejdet stoppede — ikke kun at det gjorde."""
    out = _kør(max_rounds=8, antal_kald=7, slutsvar=STATUSNOTE)
    why = str(out.get("stop_reason") or "")
    assert "rundebudgettet" in why, f"aarsagen mangler, fik {why!r}"
    assert "8" in why, f"antallet af runder skal staa i aarsagen, fik {why!r}"


def test_payloaden_baerer_aarsag_antal_og_tekst():
    """Alle tre ting skal kunne laeses af den der modtager resultatet."""
    res = _loop_result(_kør(max_rounds=8, antal_kald=7, slutsvar=STATUSNOTE),
                       scout=False, provider="p", model="m")
    payload = str(res.get("result") or "")
    assert "UFULDSTÆNDIG" in payload, "markeringen mangler"
    assert "rundebudgettet løb ud" in payload, f"aarsagen mangler i payloaden: {payload[:200]!r}"
    # 27/10-2026: formen er nu ÉT tal med kvalifikationen i parentes. Foer stod
    # det samme tal to gange med to forskellige ord («1 spørgsmål stadig
    # ubesvarede …; 1 spørgsmål uden nummereret svar»), og den anden paastod en
    # fejl der ikke fandtes. Kravet er uaendret: tallet skal staa der, aerligt.
    assert "3 spørgsmål stadig ubesvarede" in payload, (
        f"antallet mangler i payloaden: {payload[:200]!r}"
    )
    assert "5 properties" in payload, (
        "agentens tekst blev kastet vaek — Jarvis skal vide HVAD den naaede"
    )


def test_en_koersel_med_plads_til_nudgen_kan_stadig_blive_faerdig():
    """Kontrol: vagten maa ikke stemple alt som ufuldstaendigt.

    Samme form, men med én runde mere: nudgen faar plads, agenten svarer fuldt,
    og udfaldet skal vaere rent.
    """
    io = FakeIO([_ET_KALD] * 7 + [_svar(STATUSNOTE), _svar(FULDT_SVAR)])
    out = core.run_tool_loop(
        io, prompt=OPGAVE, tools_payload=_LÆSEVÆRKTOEJ, requires_tools=False,
        provider="p", model="m", scout=False, max_rounds=9,
        synthesis_directive="SLUT",
    )
    assert not out.get("incomplete"), (
        f"en fuld besvarelse blev markeret som ufuldstaendig: {out!r}"
    )
    assert not out.get("stop_reason"), "der er ingen grund til at melde et stop her"
    payload = str(_loop_result(out, scout=False, provider="p", model="m").get("result") or "")
    assert "UFULDSTÆNDIG" not in payload
    assert "agent_assignment_mandates" in payload, "det fulde svar skal stadig vaere der"
