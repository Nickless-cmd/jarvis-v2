"""Ufuldstaendig leverance skal baere BAADE markering, antal og agentens tekst (26/10-2026).

Krav (Bjørn 26/10): "Jarvis skal altid vide, hvad den naaede, hvad den ikke naaede,
og hvorfor arbejdet stoppede."

Maalt 26/10-2026 foer denne test: `_loop_result` erstattede agentens tekst med den
faste saetning "Agenten sluttede med et løfte den ikke udførte". Markeringen var
der, men resultatet var ubrugeligt — Jarvis kunne se AT noget manglede, ikke HVAD
agenten naaede. Og `unanswered` blev beregnet i loekken men smidt vaek, saa antallet
af ubesvarede spoergsmaal naaede aldrig kalderen.

Testen er et par: markeringen SKAL vaere der, og teksten SKAL stadig vaere der.

Bemaerk om sprogformen: spoergsmaalene skrives som i VIRKELIGHEDEN — `SPØRGSMÅL N:`
med dansk Ø. En tidligere udgave af denne test skrev `SPOERGSAAL` (uden m), som
hverken er dansk eller den ASCII-form regex'en kender (`spoergsmaal`), og den maalte
derfor ingenting. Brug den form der faktisk forekommer i de rigtige opgaver.
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

# Agenten svarer paa 1 og lader 2 og 3 staa — praecis den maalte fejlform.
DELVIST_SVAR = "1. Fem felter.\n\nNu spørgsmål 2 og 3."
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


def _kør(slutsvar: str) -> dict:
    """To runder mere end svaret: scout-nudgen spiser ét svar og spoerger igen."""
    io = FakeIO([_ET_KALD, _svar(slutsvar), _svar(slutsvar)])
    return core.run_tool_loop(
        io, prompt=OPGAVE, tools_payload=_LÆSEVÆRKTOEJ, requires_tools=False,
        provider="p", model="m", scout=True, max_rounds=8, synthesis_directive="SLUT",
    )


def test_vagten_ser_hullerne_i_den_virkelige_opgaveform():
    """Grundlaget: 1 besvaret, 2 og 3 ikke -> 2. Maales paa den raa funktion."""
    assert core._unanswered_questions(OPGAVE, DELVIST_SVAR) == 2
    assert core._unanswered_questions(OPGAVE, FULDT_SVAR) == 0


def test_antallet_af_ubesvarede_naar_ud_af_loekken():
    """`unanswered` blev beregnet men smidt vaek. Det skal kalderen kunne se."""
    out = _kør(DELVIST_SVAR)
    assert out.get("incomplete") is True
    assert out.get("unanswered") == 2, (
        f"forventede 2 ubesvarede, fik {out.get('unanswered')!r}. "
        "Uden tallet kan Jarvis se AT noget mangler, ikke HVOR MEGET."
    )


def test_teksten_bevares_naar_leverancen_er_ufuldstaendig():
    """Markeringen maa ikke erstatte agentens faktiske fund."""
    res = _loop_result(_kør(DELVIST_SVAR), scout=True, provider="p", model="m")
    payload = str(res.get("result") or "")
    assert "UFULDSTÆNDIG" in payload, (
        "markeringen mangler — saa kan Jarvis ikke se at leverancen er delvis"
    )
    assert "Fem felter" in payload, (
        "agentens tekst blev kastet vaek. Jarvis skal vide HVAD den naaede, "
        "ikke kun at den stoppede."
    )
    assert "2 spørgsmål uden nummereret svar" in payload, (
        f"antallet skal staa i payloaden: {payload[:200]!r}"
    )


def test_en_fuld_besvarelse_markeres_ikke():
    """Kontrol: naar alle tre er besvaret, maa der ikke komme en markering."""
    out = _kør(FULDT_SVAR)
    assert not out.get("incomplete"), "en fuld besvarelse blev markeret som ufuldstaendig"
    payload = str(_loop_result(out, scout=True, provider="p", model="m").get("result") or "")
    assert "UFULDSTÆNDIG" not in payload
    assert "agent_assignment_mandates" in payload, "det fulde svar skal stadig vaere der"


def test_tallet_staar_KUN_eEN_gang_i_markeringen():
    """Markeringen maa ikke naevne det samme tal to gange med to ord.

    MAALT I DRIFT 27/10-2026 paa `run-725174bb21544c40`:

        UFULDSTÆNDIG (1 spørgsmål stadig ubesvarede efter afsluttende svar;
                      1 spørgsmål uden nummereret svar)

    To tal der er ENIGE om 1, formuleret som en modstrid. `why` baerer
    allerede tallet; `n` blev lagt oveni som en ANDEN taelling. En laeser
    der ser to tal og to ord maa foerst afgoere om de er uenige — det er
    arbejde markeringen selv skabte.
    """
    # 27/10-2026: MAALT at den foerste udgave af denne vagt var GROEN PAA DEN
    # FORKERTE GREN. `_kør(DELVIST_SVAR)` rammer fallback'en (why er tom), hvor
    # der kun er ÉT tal — mutationen (dobbelt-taellingen sat tilbage) faldt
    # derfor IKKE. Her saettes `why` og `n` eksplicit, saa why+n-grenen rammes:
    # det er praecis den gren der talte to gange i drift.
    o = _kør(DELVIST_SVAR)
    o["stop_reason"] = "2 spørgsmål uden nummereret svar efter afsluttende svar"
    o["unanswered"] = 2
    payload = str(_loop_result(o, scout=True, provider="p", model="m").get("result") or "")
    assert "UFULDSTÆNDIG" in payload, "markeringen mangler"
    assert payload.count("2 spørgsmål") == 1, (
        f"tallet skal staa praecis én gang, ikke to: {payload[:240]!r}"
    )
