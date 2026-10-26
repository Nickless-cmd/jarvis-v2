"""En agent der svarer paa 1 af 3 spoergsmaal maa ikke meldes som en fuld leverance (26/10/2026).

Maalt 26/10-2026 paa en rigtig Task-agent (asg-2e4c9a37b5fc40ad, researcher):

  Spoergsmaal 1: besvaret — men FORKERT (den sagde 6 felter; Task har 5 i den fil,
                 for `idempotency_key` paa linje 74 hoerer til `followup_agent`).
  Spoergsmaal 2: ikke besvaret.
  Spoergsmaal 3: ikke besvaret.
  Afsluttende saetning: "Nu spoergsmaal 2 og 3."

Systemet meldte `completed` med `partial: false`. Jarvis fik INTET signal om at halvdelen
manglede — praecis det modsaatte af hvad en varig leverancekontrakt skal give.

Aarsagen var ikke en manglende gate: `agent_runtime_base.py:459` HAR en scout-gren der
saetter BLOCKED. Men dens trigger er `_promises_action`, som er en tekstheuristik — og
hverken `_PROGRESS_PREFIXES` eller `_PROMISE_DA` indeholder formen "Nu spoergsmaal 2 og 3."

Rettelsen er ikke endnu et moenster. Det er at TAELLE: antal nummererede spoergsmaal i
opgaven holdes op mod antal nummererede svar i resultatet.

Disse tests er et PAR — ligesom shell-guarden: en vagt der fanger alt er lige saa
ubrugelig som en der intet fanger, fordi den ville markere hver eneste agent som
ufuldstaendig.
"""
from __future__ import annotations

from core.services.agent_loop_core import _promises_action, _unanswered_questions

# Den faktiske opgave, ordret som den blev sendt (med æ/ø/å).
OPGAVE_3 = """Besvar disse TRE spørgsmål om kodebasen i /media/projects/jarvis-v2.

SPØRGSMÅL 1: Hvor mange felter har Task-værktøjets skema?
SPØRGSMÅL 2: Hvad hedder tabellen der gemmer agent-mandater?
SPØRGSMÅL 3: Hvor mange steder sammenlignes der med semikolon?
"""

# Det faktiske svar: 1 besvaret (og forkert), 2 og 3 ikke. Uden nummerering.
SVAR_FAKTISK = (
    "Fundet fuldstændig Task-skema: 6 felter (description, prompt, subagent_type, model, "
    "run_in_background, idempotency_key) — linje 59-74.\n\nNu spørgsmål 2 og 3."
)

# Samme leverance, men med nummerering — så tællingen kan se hvilke der er besvaret.
SVAR_NUMMERERET_1_AF_3 = "1. Fem felter (agent_contract_tools.py:59-67).\n"

SVAR_3_AF_3 = """1. Task-skemaet har 5 felter (agent_contract_tools.py:59-67).
2. Tabellen hedder agent_assignment_mandates, kolonnen allowed_tools_json (db_agent_mandate.py:29).
3. Tre steder i classify_command (simple_tools.py).
"""

OPGAVE_1 = "Mål i kodebasen: hvor mange steder kalder koden dispatch_agent("

SVAR_PAA_1 = "22 rene kald i hele repoet, 5 i produktionskode (agent_council.py:95,179,257)."


# ── Acceptkriterium 1: den maalte koersel skal FANGES ────────────────────────────────
def test_den_faktiske_koersel_markerer_alle_tre_ubesvarede():
    """Agenten nummererede ikke sit svar. Så kan taellingen ikke se HVILKE der er besvaret —
    og maa derfor melde alle tre som ubesvarede. Det er konservativt med vilje: hellere
    'jeg ved ikke hvor meget der mangler' end 'alt er fint'."""
    assert _unanswered_questions(OPGAVE_3, SVAR_FAKTISK) == 3


def test_den_afsluttende_saetning_lyder_faerdig_men_er_det_ikke():
    """Kernen i fejlen: teksten LOVER intet — den ANNOUNCERER. Derfor misser
    `_promises_action` den, og derfor maa vagten taelle i stedet."""
    assert _promises_action(SVAR_FAKTISK) is False, (
        "hvis _promises_action fangede formen, var den tællende vagt overflødig — "
        "men den fanger den ikke, og det er hele grunden til at den findes"
    )
    assert _unanswered_questions(OPGAVE_3, SVAR_FAKTISK) > 0


# ── Acceptkriterium 2: nummereret delvis leverance giver det praecise tal ───────────
def test_nummereret_svar_paa_1_af_3_giver_to():
    assert _unanswered_questions(OPGAVE_3, SVAR_NUMMERERET_1_AF_3) == 2


# ── Acceptkriterium 3: en fuld leverance maa IKKE markeres ──────────────────────────
def test_svar_paa_alle_tre_giver_nul():
    assert _unanswered_questions(OPGAVE_3, SVAR_3_AF_3) == 0


# ── Acceptkriterium 4: vagten er tavs naar opgaven kun stiller ét spoergsmaal ───────
def test_enkeltspoergsmaal_opgave_rammes_aldrig():
    """Maalt: 1 af 60 historiske agent-opgaver har flere nummererede spoergsmaal.
    For de 59 andre skal vagten vaere helt tavs — ellers er den stoj, ikke et vaern."""
    assert _unanswered_questions(OPGAVE_1, SVAR_PAA_1) == 0
    assert _unanswered_questions(OPGAVE_1, "") == 0


def test_tom_opgave_og_tomt_svar_er_nul():
    assert _unanswered_questions("", "") == 0
    assert _unanswered_questions("", SVAR_FAKTISK) == 0


# ── Acceptkriterium 5: engelsk form taeller lige saa meget som dansk ─────────────────
def test_engelsk_opgave_taeller_ogsaa():
    opgave = "QUESTION 1: how many fields?\nQUESTION 2: what is the table name?\n"
    assert _unanswered_questions(opgave, "1. Five fields.\n") == 1


# ── Acceptkriterium 6: hul midt i listen fanges ─────────────────────────────────────
def test_hul_midt_i_listen_fanges():
    """Det er ikke nok at tjekke det sidste spoergsmaal: en agent kan svare paa 1 og 3
    og springe 2 over. Taellingen skal se HULLET, ikke bare antallet."""
    svar = "1. Fem felter.\n3. Tre steder.\n"
    assert _unanswered_questions(OPGAVE_3, svar) == 1
