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


# ── Scout/spaerringen: kontrakten gaelder OGSAA read-only-researchers ──────

#: Det svar en rigtig researcher gav 11/11-2026 efter fire `find_files`-kald, mod en
#: kontrakt paa 48 tegn. Ordret. Den blev meldt ``completed``.
SCOUT_STOPPEDE = ("No playwright config exists in desk — confirms no e2e. "
                  "Now check reconnect logic, approval flow, and autoUpdate.ts")


def test_a_researcher_that_stops_mid_reading_is_not_completed():
    """`scout` er sat for ENHVER researcher med laesepolitik, saa vagten sprang dem alle over.

    Maalt 11/11-2026 i drift: ``agent_runtime_base.py:342`` saetter ``scout=True`` for
    rollen `researcher` med politik ``read-only-runtime``/``read-only-workstation``, og
    loopet beregnede ``gap = "" if scout else ...``. Vagten var altsaa bygget til praecis
    den fejlform den ikke kunne se. Scout-grenen daekkede kun nul vaerktoejskald; denne
    agent havde fire.
    """
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        {"text": "", "tool_calls": [_tc(2)]},
        {"text": "", "tool_calls": [_tc(3)]},
        {"text": "", "tool_calls": [_tc(4)]},
        _text(SCOUT_STOPPEDE),
        _text(SCOUT_STOPPEDE),
    ])
    out = _run(io, scout=True, expected_result="Verificér Desk-P0-påstande mod koden")

    assert out.get("incomplete") is True, "en researcher der stoppede midt i er ikke en leverance"
    # 11/11-2026: den målte tekst slutter med "Now check reconnect logic …". Den nye
    # slutnings-regel fyrer derfor FOER laengdetaersklen, og grunden er praecisere end
    # "tegn": den navngiver modaliteten. Taersklen alene fangede kun 3 af de 9 maalte
    # arbejdsintentioner, fordi de seks andre var laengere end 160 tegn.
    assert "arbejdsintention" in out["stop_reason"], out["stop_reason"]
    # Nudgen er leverance-ordren, ikke `_ACTION_NUDGE` — en read-only agent kan ikke skrive.
    nudge = io.model_calls[5]["messages"][-1]["content"]
    assert "kan ikke accepteres" in nudge
    assert "skriveværktøj" not in nudge


def test_a_researcher_that_delivers_is_not_nudged():
    """En researcher der FAKTISK leverer skal ikke straffes med en ekstra runde."""
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(RIGTIGT),
    ])
    out = _run(io, scout=True, expected_result=KONTRAKT)

    assert len(io.model_calls) == 2, "et fuldt svar skal ikke have en ekstra runde"
    assert not out.get("incomplete"), out.get("stop_reason")
    assert out["final_text"] == RIGTIGT


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


def test_a_long_answer_that_ends_with_a_plan_is_not_a_delivery():
    """Længde er det forkerte mål: 500 tegn kan være en plan, 89 kan være et svar.

    Målt 11/11-2026 i råd `council-ae9a075e13514694`: 89-tegns-svaret blev fældet af
    længdetærsklen, mens arbejdsintentioner på 214, 233 og 500 tegn gik lige igennem —
    de var alle længere end 160. Over 111 completed-kørsler sluttede 9 fremadrettet, og
    alle 9 var arbejdsintentioner. Tærsklen fangede 3 af dem; modaliteten fanger alle.
    """
    lang_plan = (
        "Jeg har gennemgået de tre workflows og fundet at build-jobbet kun kører "
        "npm ci og npm run build. Der er ingen test-kørsel og ingen lint. "
        "Release-flowet publicerer til tre platforme via electron-builder, og "
        "artefakterne uploades til GitHub-releasen for det tag der pushes. "
        "Version-bumpet i package.json sker manuelt, og der er ingen kontrol "
        "af at versionen matcher tag-navnet. Det betyder at en fejl i "
        "versionsnummeret først opdages når electron-updater ikke finder "
        "latest.yml ude hos brugerne. Now check the PWA build step and gate."
    )
    assert len(lang_plan) > 400
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(lang_plan),
        _text(lang_plan),
    ])
    out = _run(io, expected_result=KONTRAKT)

    assert out.get("incomplete") is True, "en plan i 500 tegn er ikke en leverance"
    assert "arbejdsintention" in out["stop_reason"], out["stop_reason"]


def test_a_long_answer_that_ends_with_a_conclusion_is_a_delivery():
    """Den negative halvdel: en lang konklusion må IKKE rammes af slutnings-reglen.

    En vagt der fanger gode svar er værre end hullet den lukker. Derfor er "næste
    skridt"/"next step" bevidst ikke i mønstret: det kan stå i en gyldig anbefaling.
    """
    konklusion = (
        "Jeg har gennemgået de tre workflows og fundet at build-jobbet kun kører "
        "npm ci og npm run build. Der er ingen test-kørsel og ingen lint. "
        "Release-flowet publicerer til tre platforme via electron-builder, og "
        "artefakterne uploades til GitHub-releasen for det tag der pushes. "
        "Version-bumpet i package.json sker manuelt, og der er ingen kontrol "
        "af at versionen matcher tag-navnet. Konklusion: releasesporet er "
        "dækket på build, men ikke på test — det er den ene manglende vagt. "
        "Næste skridt er at tilføje npm test til workflowet."
    )
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(konklusion),
    ])
    out = _run(io, expected_result=KONTRAKT)

    assert not out.get("incomplete"), out.get("stop_reason")


# ── Svaret i PUNKTER er også et svar (11/11-2026) ─────────────────────────

#: Opgaven ORDRET, som den stod i `agent_runs` for `run-5306b1fe6a7845a5`
#: ("Måling 3/4: Node.js LTS med formatkrav"). To nummererede spørgsmål plus en
#: "Krav til svaret"-sektion hvis tredje punkt er et FORMATkrav.
BULLET_OPGAVE = """Måling 3/4: Node.js LTS med formatkrav

Undersøg to ting og svar kort (maks 120 ord).

1. Hvilken Node.js-version er den aktuelle LTS lige nu?
2. Hvornår blev den frigivet som LTS?

Krav til svaret:
1. Nævn versionsnummeret.
2. Nævn frigivelsesdatoen.
3. Skriv «DÆKNING: 1,2» som sidste linje hvis du har besvaret begge dele, ellers «DÆKNING: N/2»."""

#: Punkterne ORDRET fra samme kørsels `**Findings**`-blok. Kørslen svarede nummereret
#: nederst og skrev DÆKNING-linjen, så den slap igennem ad en anden vej; her er kun
#: punkt-blokken, som er den form A handler om.
BULLET_SVAR = """**Summary** — Den nuværende Active LTS-linje er Node.js 24.x, som gik i Active LTS
den 28. oktober 2025 med udgivelsen af 24.11.0 'Krypton'.

**Findings**
- nodejs.org/en/download viser aktuelt v26.13.0 (LTS), v24.22.2 (LTS) og v22.23.4 (LTS).
- Officiel kilde (nodejs.org blog): "2025-10-28, Version 24.11.0 'Krypton' (LTS)".
- Seneste patch i LTS-linjen pr. søgetidspunkt: Node.js 24.12.0 (udgivet 10. december 2025).
- Node 22.x var tidligere Active LTS og skiftede til Maintenance LTS med Node 24's overgang."""


def test_a_bullet_answer_covers_the_numbered_questions():
    """Et svar i punkter er en leverance — detektoren maalte det som et hul.

    MAALT 11/11-2026: daeknings-grenen kraever et NUMMERERET svar, saa en agent der
    svarede i bullets blev maalt som «2 spoergsmaal uden nummereret svar» og slap
    derefter igennem paa tegn-taersklen i stedet. Maalt over 74 gennemfoerte koersler
    siden 4/11 fjerner denne regel dommen i 2 af dem — begge fyldige leverancer uden
    en DAEKNING-linje. Reglen er altsaa snaever, ikke et frit lejde.
    """
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text(BULLET_SVAR),
    ])
    out = _run(io, prompt=BULLET_OPGAVE, expected_result=KONTRAKT)

    assert len(io.model_calls) == 2, "et daekket svar skal ikke have en ekstra runde"
    assert not out.get("incomplete"), out.get("stop_reason")
    assert core._unanswered_detail(BULLET_OPGAVE, BULLET_SVAR)[0] == 0


def test_a_bullet_answer_with_fewer_points_than_questions_is_still_a_gap():
    """Den anden halvdel: punkter er ikke et frit lejde.

    Stiller opgaven to spoergsmaal og svarer agenten med ET punkt, er leverancen ikke
    daekket. Uden denne halvdel ville reglen goere enhver punkliste til en fuld
    leverance, og saa var hullet byttet for et stoerre.
    """
    assert core._unanswered_detail(BULLET_OPGAVE, "- Node.js 24 er LTS.")[0] == 2
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        _text("- Node.js 24 er LTS."),
        _text("- Node.js 24 er LTS."),
    ])
    out = _run(io, prompt=BULLET_OPGAVE, expected_result=KONTRAKT)

    assert out.get("incomplete") is True
    assert "tegn" in out["stop_reason"]


def test_the_agents_own_declaration_still_wins_over_the_bullet_count():
    """A maa IKKE overrule agentens EGEN daeknings-linje.

    Erklaerer agenten «DÆKNING: 1» til en opgave med tre spoergsmaal, er det en aerlig
    delvis leverance — ogsaa naar svaret har ti punkter. Maalt 11/11-2026: de 19
    resterende huller i de 74 koersler er ALLE denne slags, nul er ren taelling. Ville
    punkter vinde over erklaeringen, gjorde reglen praecis den tavshed den skulle fjerne.
    """
    opgave = "Undersøg tre ting:\n1) Hvad er A?\n2) Hvad er B?\n3) Hvad er C?\n"
    svar = ("- A er besvaret\n- B er besvaret\n- C er besvaret\n"
            "- endnu et punkt\n- og et mere\n\nDÆKNING: 1")
    assert core._unanswered_detail(opgave, svar) == (2, "spørgsmål uden dækning")


def test_the_bullet_measure_counts_only_points_that_carry_content():
    """Enheden selv: tomme punkter og markdown-fremhaevning er ikke svar."""
    assert core._bullet_answers(BULLET_SVAR) == 4
    assert core._bullet_answers("- \n- \n* ") == 0
    # "**Opsummering**" er ikke et punkt: moensteret kraever et mellemrum efter markoeren.
    assert core._bullet_answers("**Opsummering**\ntekst") == 0
    assert core._bullet_answers("Indledning.\n- et\n* to\n• tre\n– fire") == 4

