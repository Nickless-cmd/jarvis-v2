"""En agent med stoffet i hånden skal have ORDRE til at svare, ikke gå hjem (26/10-2026).

Krav (Bjørn 26/10): "sørg for dine agenter virker og gør som de skal.. og de
levere efter de krav du stillere."

MAALT 26/10-2026 paa `asg-b0e20bf925564962` (researcher, run-2d564e05a1f14ef5):

  * tre laesvaerktoejskald — stoffet VAR hentet
  * svarede korrekt paa spoergsmaal 1 ("Nu har jeg bekræftet 5 felter")
  * stoppede med "Lad mig se de resterende properties i agent_contract_tools.py"
  * loekken gik hjem og meldte UFULDSTÆNDIG (3 spoergsmaal uden nummereret svar)

Aarsagen var ikke modellen: scout-nudgen er afgraenset til ÉT forsoeg
(``scout_retries < 1``), og syntese-kaldet fyredes kun naar RUNDEBUDGETTET var
opbrugt. Denne koersel brugte 3 af 8 runder — saa den faldt aldrig ind i den gren.
Agenten blev doemt for et spoergsmaal den aldrig fik lov at besvare.

Rettelsen: naar spoergsmaal staar ubesvarede efter nudgen, gives ÉT afsluttende
kald UDEN vaerktoejer, hvor agenten svarer ud fra det den allerede har fundet.

Testen er et PAR: agenten skal levere alle tre svar — og naar den afsluttende
runde STADIG ikke daekker det hele, skal udfaldet forblive ufuldstaendigt.
En vagt der goer alt til "faerdigt" er lige saa blind som den der goer alt til
"fejlet".
"""
from __future__ import annotations

from core.services import agent_loop_core as core

OPGAVE = (
    "Besvar disse tre spørgsmål om kodebasen.\n\n"
    "1) Hvor mange felter har skemaet for værktøjet Task?\n"
    "2) Hvad hedder tabellen for agent-assignment-mandater?\n"
    "3) Hvor i koden kaldes dispatch_agent?\n"
)

# Praecis den maalte form: svar paa 1, derefter et loefte om mere.
KLADDE = "1) Task har 5 felter: description, model, prompt, run_in_background, subagent_type."
LOEFTE = "Lad mig se de resterende properties i agent_contract_tools.py."
FULDT_SVAR = "1) Fem felter.\n2) agent_assignment_mandates.\n3) I agent_runtime_spawn.py."
HALVT_SVAR = "1) Fem felter.\n2) agent_assignment_mandates."


class FakeIO:
    """Svarer i raekkefoelge; en Exception i listen kastes (model-fejl)."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.model_calls: list[dict] = []

    def model(self, *, messages, tools, requires_tools, provider, model):
        self.model_calls.append({"tools": tools, "requires_tools": requires_tools})
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
_ET_KALD = {
    "text": "Filen har 161 linjer.",
    "input_tokens": 10,
    "output_tokens": 5,
    "cost_usd": 0.0,
    "tool_calls": [{"id": "c1", "function": {"name": "read_file", "arguments": "{}"}}],
}
_TOM = {"text": "", "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "tool_calls": []}


def _kør(replies, *, scout=True, max_rounds=8):
    io = FakeIO(replies)
    out = core.run_tool_loop(
        io,
        prompt=OPGAVE,
        tools_payload=_LÆSEVÆRKTOEJ,
        requires_tools=False,
        provider="test",
        model="test",
        scout=scout,
        max_rounds=max_rounds,
        synthesis_directive="Syntetisér nu.",
    )
    return io, out


def test_agenten_faar_et_afsluttende_svar_naar_spoergsmaal_staar_aabne():
    """Den maalte fejlform: 1 værktøjskald, svar på 1, derefter et løfte — så ORDRE."""
    io, out = _kør([
        _ET_KALD,
        {"text": KLADDE, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
        {"text": LOEFTE, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
        # Det afsluttende kald — her leveres alle tre.
        {"text": FULDT_SVAR, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
    ])
    assert out.get("final_text") == FULDT_SVAR, (
        f"agentens afsluttende svar blev ikke brugt, fik {out.get('final_text')!r}")
    assert (out.get("unanswered") or 0) == 0, (
        f"leverancen skulle daekke alle tre spoergsmaal, fik unanswered={out.get('unanswered')!r}")
    assert not out.get("incomplete"), "et fuldt svar maa ikke markeres ufuldstaendigt"


def test_det_afsluttende_kald_sker_uden_vaerktoejer():
    """Ordren er at SVARE, ikke at undersøge videre — der er ingen runder tilbage."""
    io, _ = _kør([
        _ET_KALD,
        {"text": KLADDE, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
        {"text": LOEFTE, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
        {"text": FULDT_SVAR, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
    ])
    sidste = io.model_calls[-1]
    assert sidste["tools"] == [], f"det afsluttende kald fik værktøjer: {sidste['tools']!r}"
    assert sidste["requires_tools"] is False


def test_et_halvt_afsluttende_svar_er_stadig_ufuldstaendigt():
    """Vagten maa ikke goere systemet blindt: svarer den kun paa 2 af 3, er det ikke færdigt."""
    _, out = _kør([
        _ET_KALD,
        {"text": KLADDE, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
        {"text": LOEFTE, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
        {"text": HALVT_SVAR, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
    ])
    assert out.get("unanswered") == 1, f"forventede 1 ubesvaret, fik {out.get('unanswered')!r}"
    assert out.get("incomplete") is True
    assert out.get("final_text") == HALVT_SVAR, "det halve svar skal stadig leveres, ikke kastes"


def test_en_model_fejl_i_det_afsluttende_kald_bevarer_den_sidste_tekst():
    """Et fejlet afsluttende kald maa ikke efterlade et tomt svar."""
    _, out = _kør([
        _ET_KALD,
        {"text": KLADDE, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
        {"text": LOEFTE, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
        RuntimeError("udbyderen svarede ikke"),
    ])
    assert out.get("final_text") == LOEFTE, (
        f"teksten fra sidste runde gik tabt, fik {out.get('final_text')!r}")
    assert out.get("incomplete") is True


def test_et_fuldt_svar_i_foerste_runde_udloeser_ikke_et_ekstra_kald():
    """Kun naar der ER huller. En komplet leverance skal ikke koste et ekstra modelkald."""
    io, out = _kør([
        _ET_KALD,
        {"text": FULDT_SVAR, "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0, "tool_calls": []},
    ])
    assert len(io.model_calls) == 2, f"uventet ekstra modelkald: {len(io.model_calls)}"
    assert (out.get("unanswered") or 0) == 0
    assert not out.get("incomplete")
