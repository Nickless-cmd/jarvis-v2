"""Markeringens ORD skal følge den KILDE der gav tallet (27/10-2026).

Målt i drift på `run-18acb0c3120142f2`: agenten fik tre nummererede spørgsmål,
svarede på 1 og 3, afviste 2 ærligt ("Kan ikke besvares") og skrev selv
`DÆKNING: 1,3`. Tallet 1 var altså KORREKT — men markeringen sagde:

    UFULDSTÆNDIG (1 spørgsmål uden nummereret svar efter afsluttende svar)

Og agenten HAVDE et nummereret svar på 2). Ordet påstod en formateringsfejl der
ikke fandtes — præcis den samme løgn som «ubesvarede» gjorde før 26/10, bare i
den anden retning. Det er ikke et kosmetisk problem: en markering der navngiver
den forkerte årsag sender den næste læser efter det forkerte spor.

Kilden er todelt, og ordet skal være det samme:
  * agentens egen `DÆKNING:`-linje  -> «spørgsmål uden dækning»
  * den mekaniske optælling         -> «spørgsmål uden nummereret svar»
    (den optælling er et OVERKANT-tal: en agent der svarer i prosa uden at
     nummerere tælles som et hul, så ordet må ikke påstå mere end det måler)
"""
from __future__ import annotations

from core.services import agent_loop_core as core
from core.services.agent_runtime_base import _loop_result

OPGAVE = (
    "Besvar disse TRE spørgsmål.\n\n"
    "SPØRGSMÅL 1: Hvilken commit-SHA står HEAD på?\n"
    "SPØRGSMÅL 2: Hvor mange aktive rækker er der i behavioral_decisions?\n"
    "SPØRGSMÅL 3: Hvilket linjenummer sætter output_sti?\n"
)

# Den målte tekst fra drift: nummererede svar på 1 og 3, ærlig afvisning på 2,
# og agentens egen erklæring allersidst.
MED_ERKLAERING = (
    "1) HEAD peger på 2b83f27c6.\n\n"
    "2) Kan ikke besvares: jeg har ingen SQL-adgang. Jeg gætter ikke et tal.\n\n"
    "3) Feltet sættes på linje 86.\n\n"
    "DÆKNING: 1,3"
)

# Samme leverance UDEN erklæring, og med spørgsmål 2 helt udeladt: nu er det
# optællingen der giver tallet. (MÅLT 27/10-2026: havde teksten beholdt
# «2) Kan ikke besvares», ville optællingen se 0 huller — den tæller NUMMERET,
# ikke om indholdet er et svar. Det er præcis derfor kontrakten blev indført,
# og hvorfor de to kilder ikke må blandes sammen.)
UDEN_ERKLAERING = (
    "1) HEAD peger på 2b83f27c6.\n\n"
    "3) Feltet sættes på linje 86."
)


# ── 1. Ordet følger kilden ──────────────────────────────────────────────────
def test_erklaeringen_giver_ordet_daekning():
    """Agenten erklærede DÆKNING: 1,3 — så er hullet et hul i DÆKNINGEN."""
    n, ord_ = core._unanswered_detail(OPGAVE, MED_ERKLAERING)
    assert n == 1, f"tallet skal være 3 - {{1,3}} = 1, fik {n}"
    assert ord_ == "spørgsmål uden dækning", (
        f"ordet skal sige dækning når agenten selv erklærede den — fik {ord_!r}. "
        "«uden nummereret svar» påstår en formateringsfejl der ikke findes: "
        "agenten SKREV «2)», den afviste bare indholdet."
    )


def test_uden_erklaering_giver_ordet_nummereret_svar():
    """Ingen DÆKNING-linje — så er optællingen kilden, og dens ord er det ærlige."""
    n, ord_ = core._unanswered_detail(OPGAVE, UDEN_ERKLAERING)
    assert n == 1, f"optællingen skal se 2 besvaret af 3, fik {n}"
    assert ord_ == "spørgsmål uden nummereret svar", (
        f"uden en erklæring er optællingen kilden — fik {ord_!r}"
    )


def test_de_to_ord_er_forskellige():
    """Vagten skal ikke kunne bestås ved at gøre begge ord ens."""
    _, a = core._unanswered_detail(OPGAVE, MED_ERKLAERING)
    _, b = core._unanswered_detail(OPGAVE, UDEN_ERKLAERING)
    assert a != b, (
        "de to kilder giver samme ord — så er der ingen forskel at måle, og "
        "ordet følger ikke længere kilden"
    )


# ── 2. Ordet når hele vejen til markeringen ─────────────────────────────────
def _outcome(**kw):
    o = {
        "final_text": MED_ERKLAERING,
        "error_str": "",
        "total_tool_calls": 3,
        "total_input": 10,
        "total_output": 5,
        "total_cost": 0.0,
        "duration_ms": 100,
        "rounds": 2,
        "incomplete": True,
        "unanswered": 1,
        "unanswered_ord": "spørgsmål uden dækning",
        "stop_reason": "",
    }
    o.update(kw)
    return o


def test_markeringen_baerer_ordet_fra_kilden():
    """`_loop_result` skal bruge ordet — ikke sin egen faste sætning."""
    res = _loop_result(_outcome(), scout=False, provider="p", model="m")
    payload = str(res.get("result") or "")
    assert "UFULDSTÆNDIG (1 spørgsmål uden dækning)" in payload, (
        f"markeringen brugte ikke ordet fra kilden: {payload[:200]!r}"
    )
    assert "uden nummereret svar" not in payload, (
        "den faste sætning overlevede — så følger ordet stadig ikke kilden"
    )


def test_uden_ord_bruges_den_gamle_form():
    """Bagudkompatibelt: et outcome uden `unanswered_ord` må ikke kaste."""
    o = _outcome()
    o.pop("unanswered_ord")
    res = _loop_result(o, scout=False, provider="p", model="m")
    payload = str(res.get("result") or "")
    assert "UFULDSTÆNDIG (1 spørgsmål uden nummereret svar)" in payload, (
        f"faldt ikke tilbage på den gamle form: {payload[:200]!r}"
    )


def test_stop_reason_naevner_tallet_men_ikke_to_gange():
    """`why` bærer selv tallet — det må ikke lægges oveni som en anden tælling."""
    o = _outcome(stop_reason="1 spørgsmål uden dækning efter afsluttende svar")
    res = _loop_result(o, scout=False, provider="p", model="m")
    payload = str(res.get("result") or "")
    assert payload.count("1 spørgsmål") == 1, (
        f"tallet står {payload.count('1 spørgsmål')} gange — dobbelt-tællingen er tilbage: "
        f"{payload[:250]!r}"
    )
