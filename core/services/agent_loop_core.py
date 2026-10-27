"""Agentens model-/vaerktoejsloekke som ren logik (agent-contract-v1 C6, spec 12.1).

Loekken ved INGENTING om DB, eventbus, udbydere eller filsystem: al I/O gaar gennem et
``LoopIO``-objekt. I serveren er det en in-process-implementation (``agent_runtime_base``);
i den sandboxede workerproces er det RPC-stubs til serverens broker. Samme funktion begge
steder = samme adfaerd, og workeren behoever hverken credentials eller adgang til runtime-filer.

Modulet maa kun importere standardbiblioteket (en test vogter det), fordi det indlaeses i
en sandbox hvor intet andet er monteret.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Protocol

logger = logging.getLogger(__name__)

#: Et scouts aabningssaetning er ikke et researchresultat; den faar ét afgraenset forsoeg til.
_PROGRESS_PREFIXES = ("jeg starter", "jeg vil", "prøver ", "proever ",
                      "i will", "i'll ", "starting ", "let me ")
_SCOUT_NUDGE = (
    "Du har endnu ikke leveret et research-resultat. Brug et af "
    "dine tilgængelige læseværktøjer nu. Afslut først med "
    "konkrete fund, kilde og hvad du ikke kunne verificere.")

#: Et loefte i tekst er ikke et resultat. Maalt 8/10-2026 paa en rigtig agent: den laeste
#: filen (ét wt_bash-kald), svarede "Filen har 161 linjer. Nu tilfoejer jeg kommentarlinjen"
#: og kaldte ALDRIG skrivevaerktoejet. Loekken laeste den stille runde som et faerdigt svar
#: og meldte ``completed`` med files=[] og diff_bytes=0. Vagten fandtes kun for scouts, og
#: kun naar teksten STARTEDE med et loefte - her stod det i anden saetning.
#:
#: Dansk vender ordstillingen om: "nu tilfoejer JEG" — den maalte saetning havde netop den
#: omvendte form. Baade "jeg <verb>" og "<verb> jeg" taeller derfor.
#:
#: To signaler i stedet for ét: et loefte HVOR som helst i teksten, og - staerkere - at en
#: agent der HAR skrivevaerktoejer slutter uden at have skrevet noget.
_PROMISE_VERBS = ("tilføjer", "tilføje", "retter", "opdaterer", "skriver", "ændrer",
                  "fjerner", "implementerer", "indsætter", "bygger", "laver",
                  # 26/10-2026: LÆSE-løfter. En read-only agent lover at UNDERSØGE, ikke at
                  # skrive — og gik hjem uden at gøre det. Målt på en rigtig researcher:
                  # "Task schema har kun 5 felter … Lad mig verificere required-listen."
                  # Den svarede på 1 af 3 spørgsmål og kaldte intet værktøj bagefter.
                  "verificerer", "verificere", "tjekker", "tjekke")
_PROMISE_EN = ("i'll ", "i will ", "let me ", "now i'll", "now i will")
#: 26/10-2026: `let me ` stod i listen — `lad mig ` gjorde ikke. Præcis den engelske form
#: var dækket og den danske manglede, så en dansk cliffhanger slap gennem vagten og
#: agenten blev meldt ``completed`` midt i en sætning. Samme fejlklasse som MEMORY-
#: påstanden tidligere samme dag: jeg greppede på ét sprog og konkluderede om begge.
#: Fraserne er signalet — ikke verbet der følger, for det skifter med opgaven.
_PROMISE_DA = ("lad mig ", "lad os ")
_ACTION_NUDGE = (
    "Du har ikke kaldt et værktøj i denne runde, og du har ikke udført nogen ændring. "
    "Skal opgaven løses, så udfør den nu med et skriveværktøj. Kan du ikke, så sig det "
    "eksplicit med grunden — afslut ikke med et løfte om noget du ikke gjorde.")


def _answers_directive(unanswered: int) -> str:
    """Ordre om at svare NU ud fra det agenten allerede har fundet (26/10-2026).

    MAALT 26/10-2026 paa `asg-b0e20bf925564962` (researcher, run-2d564e05a1f14ef5):
    agenten kaldte tre laesvaerktoejer, svarede korrekt paa spoergsmaal 1 og stoppede
    med "Nu har jeg bekræftet 5 felter. Lad mig se de resterende properties ...".
    Stoffet var der — den fik aldrig ordre til at svare. Scout-nudgen var brugt
    (``scout_retries < 1``), loekken faldt til ``break``, og leverancen blev afvist
    som UFULDSTÆNDIG med tre ubesvarede spoergsmaal. En agent der HAR svaret skal
    ikke doemmes for et spoergsmaal den aldrig fik lov at besvare.
    """
    return (
        f"Du har stadig {unanswered} ubesvarede spørgsmål. Svar på ALLE spørgsmålene NU, "
        "nummereret præcis som de står i opgaven (1), 2), 3) …), ud fra det du allerede "
        "har fundet. Kald INGEN værktøjer — der er ingen runder tilbage. Kan du ikke "
        "svare på et spørgsmål, så skriv det eksplicit med grunden; afslut ikke med et "
        "løfte om at undersøge det senere. Et spørgsmål du ikke kunne verificere er IKKE "
        "besvaret — tæl det ikke med. Slut af med én linje, "
        "'DÆKNING: <de numre du faktisk besvarede>'.")

#: Skrivevaerktoejerne i kataloget. Bruges til at afgoere om agenten overhovedet KAN udfoere
#: en handling: en agent der ikke kan skrive skal ikke nudges for ikke at have skrevet.
_WRITE_TOOL_NAMES = frozenset({
    "write_file", "edit_file", "wt_write_file", "operator_write_file",
    "multi_edit", "apply_patch", "operator_edit_file", "operator_multi_edit",
})


def _promises_action(text: str) -> bool:
    """True naar teksten lover en handling i stedet for at udfoere den.

    Baade aabningssaetningen (``_PROGRESS_PREFIXES``) og et loefte laengere inde i teksten
    taeller: den maalte agent skrev resultatet foerst og loeftet bagefter."""
    low = (text or "").strip().lower()
    if not low:
        return False
    if low.startswith(_PROGRESS_PREFIXES):
        return True
    if any(f"jeg {v}" in low or f"{v} jeg" in low for v in _PROMISE_VERBS):
        return True
    return any(m in low for m in _PROMISE_EN) or any(m in low for m in _PROMISE_DA)


#: 26/10-2026: en tekstheuristik kan ikke afgoere om et svar er FULDSTAENDIGT — den kan
#: kun se om det LYDER som et loefte. Maalt samme dag paa en rigtig Task-agent: den svarede
#: paa 1 af 3 nummererede spoergsmaal og sluttede med "Nu spoergsmaal 2 og 3." Hverken
#: `_PROGRESS_PREFIXES` eller `_PROMISE_DA` fangede den form, saa agenten blev meldt
#: `completed` med `partial: false` — og Jarvis fik intet signal om at halvdelen manglede.
#:
#: Denne vagt gaar den anden vej: den TAELLER i stedet for at gaette. Antallet af
#: nummererede spoergsmaal i opgaven holdes op mod antallet af nummererede svar i
#: resultatet. Er der faerre svar end spoergsmaal, er leverancen ufuldstaendig — uanset
#: hvordan den afsluttende saetning lyder. Den fyrer kun naar opgaven FAKTISK stiller
#: flere spoergsmaal (maalt: 1 af 60 historiske agent-opgaver), saa den er tavs for
#: enkeltspoergsmaal-opgaver og koster intet der.
#: 26/10-2026 (aften): den foerste form var blind for almindelig nummerering. Maalt paa en
#: rigtig Task-agent: opgaven skrev spoergsmaalene som "1)" "2)" "3)", regex'en kraevede
#: ordet "spoergsmaal" foran tallet, fandt NUL spoergsmaal og returnerede 0 — hvorefter
#: agenten blev meldt `completed` efter at have svaret paa 1 af 3. Vagtens tavshed var
#: ikke "alt besvaret", den var "jeg kunne ikke se opgaven". Formerne daekkes nu begge
#: veje: med ordet foran ("SPØRGSMÅL 2", "Spørgsmål 2:") OG som ren nummerering
#: ("1)", "2.", "- 3)"). Kravet om mindst to fundne spoergsmaal staar uaendret, saa en
#: enkeltspoergsmaal-opgave stadig er tavs.
_QUESTION_RE = re.compile(
    r"(?mi)^\s*(?:[-*]\s*)?(?:"
    r"(?:spørgsmål|spoergsmaal|question)\s*(\d+)\b"   # SPØRGSMÅL 2 / Spørgsmål 2:
    r"|(\d+)\s*[.):]"                                  # 1) / 2. / 3:
    r")"
)
_ANSWER_RE = re.compile(r"(?m)^\s*(\d+)\s*[.):]")
#: 27/10-2026: en feltdeklaration ("goal: str", "`scope_files: tuple[str, ...]`") er
#: INDHOLDET af et svar, ikke et svar paa et nummereret spoergsmaal. Maalt paa
#: `asg-cb17dfab58834177`: agenten svarede kun paa spoergsmaal 1 med en nummereret
#: liste over otte felter, og tallene 1-3 blev laest som svar paa spoergsmaal 1-3.
#: Moensteret er snaevert: et bart navn efterfulgt af en PYTHON-TYPE. Prosa som
#: "Fil: agent_loop_core.py:139" skal stadig taelle som et svar.
_DECLARATION_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*\s*:\s*"
    r"(?:str|int|float|bool|bytes|dict|list|tuple|set|Any|None|Optional|Sequence|Mapping)\b"
)

#: 27/10-2026: agentens EGEN daeknings-erklæring. Kontrakten findes fordi en teksttaelling
#: kun kan se FORM, ikke BETYDNING — og det blev maalt tre gange i traek samme doegn:
#:   1) en feltliste ("1. goal: str") blev laest som svar paa spoergsmaal 1-3,
#:   2) "1) 2) 3)"-formen blev slet ikke fundet (regex'en kraevede ordet "spoergsmaal"),
#:   3) en AFVISNING ("3) Jeg kunne ikke verificere ...") blev laest som et svar.
#: Hver lap paa regex'en saa rigtig ud og fejlede paa den naeste formulering. Den eneste
#: kilde der ikke kan narres af formatering er agenten selv: den ved hvad den naaede.
#:
#: Formatet er en linje, ikke prosa: "DAEKNING: 1,2". Kun de numre agenten erklaerer
#: BESVARET. Mangler linjen, falder vi tilbage til taellingen — saa kontrakten kan kun
#: goere maalingen bedre, aldrig efterlade en tidligere korrekt koersel som fejl.
#: "DAEKNING: ingen" (eller tom liste) betyder at intet er besvaret.
_COVERAGE_RE = re.compile(
    r"(?mi)^[\s>*_-]*(?:dækning|daekning|coverage)[\s*_:-]*"
    r"(?:([0-9][0-9, \t]*)|(ingen|none|intet)\b)"
)


def _declared_coverage(final_text: str) -> set[int] | None:
    """Spoergsmaalsnumrene agenten SELV erklaerer besvaret. ``None`` = ingen erklaering.

    ``None`` og ``set()`` betyder ikke det samme og maa ikke blandes sammen:
    ``None`` = agenten skrev ingen daeknings-linje (vi ved det ikke, brug taellingen),
    ``set()`` = agenten skrev at den ikke besvarede noget.
    """
    m = _COVERAGE_RE.search(final_text or "")
    if m is None:
        return None
    if not m.group(1):
        # "DÆKNING: ingen" — agenten erklaerer at den ikke besvarede NOGET. Det er en
        # erklaering, ikke en manglende erklaering: et tomt saet, ikke ``None``.
        return set()
    return {int(x) for x in re.findall(r"\d+", m.group(1))}


def _question_numbers(prompt: str) -> set[int]:
    """Spoergsmaalsnumrene i opgaven, uanset om de er skrevet med ord eller som ren nummerering."""
    out: set[int] = set()
    for m in _QUESTION_RE.finditer(prompt or ""):
        tal = m.group(1) or m.group(2)
        if tal:
            out.add(int(tal))
    return out


def _answered_numbers(final_text: str, qs: set[int]) -> set[int]:
    """Hvilke af opgavens spoergsmaalsnumre der faktisk er besvaret i resultatet.

    27/10-2026: den foerste form talte ALLE nummererede linjer i resultatet som svar.
    Maalt paa `asg-cb17dfab58834177`: agenten svarede kun paa spoergsmaal 1, men svaret
    var en nummereret liste over otte felter ("1. goal", "2. scope_files", ...). De otte
    tal blev laest som svar paa spoergsmaal 1-8, `qs - answered` blev tom, og en
    HALV leverance blev meldt `completed` med tom `error_code`.

    Reglen er derfor ikke "et tal ved linjestart" men "et tal der hoerer til opgaven":
    kun numre der FINDES i opgaven taelles, og et nummer taeller kun naar linjen baerer
    svar-indhold — ikke en tom nummerering og ikke en ren feltdeklaration.
    """
    out: set[int] = set()
    for m in _ANSWER_RE.finditer(final_text or ""):
        n = int(m.group(1))
        if n not in qs:
            continue
        rest = (final_text[m.end():m.end() + 200].split("\n")[0] or "").strip()
        if not rest:
            continue
        # En feltdeklaration er ikke et svar: "1. `goal: str`" og "1. goal: int" er
        # indholdet AF et svar (en liste), ikke et svar paa et nummereret spoergsmaal.
        # Reglen er snaever med vilje: kun et bart navn efterfulgt af en PYTHON-TYPE.
        # "1. Fil: agent_loop_core.py:139" er prosa og skal stadig taelle — derfor
        # matcher vi typenavnet, ikke bare "navn: noget".
        if _DECLARATION_RE.match(rest.strip("`")):
            continue
        out.add(n)
    return out

def _unanswered_questions(prompt: str, final_text: str) -> int:
    """Antal nummererede spoergsmaal i opgaven uden et NUMMERERET svar i resultatet.

    Mekanisk taelling, ikke en vurdering af teksten: spoergsmaalene identificeres ved deres
    nummer i opgaven, svarene ved deres nummer i resultatet. En agent der svarer paa 1 af 3
    giver 2 — ogsaa naar dens afsluttende saetning lyder faerdig.

    Graensen (maalt 26/10-2026): en agent der svarer i PROSA uden at nummerere — fx
    "Confirmed: Task har 5 properties: ..." — taelles som et hul selv om den svarede.
    Tallet er derfor et OVERKANT-tal, og kalderen skal ikke kalde det "ubesvarede
    spoergsmaal" men "spoergsmaal uden nummereret svar". Det er stadig et brugbart signal:
    det fyrer naar en leverance stopper midt i arbejdet, og teksten foelger altid med."""
    qs = _question_numbers(prompt)
    if len(qs) < 2:
        return 0
    # 27/10-2026: agentens egen erklaering vinder over taellingen. Den er den eneste kilde
    # der ikke kan narres af formatering — maalt tre gange samme doegn (feltliste, usynlig
    # nummerering, afvisning laest som svar). Mangler linjen, er svaret uaendret.
    declared = _declared_coverage(final_text or "")
    if declared is not None:
        return len(qs - declared)
    answered = _answered_numbers(final_text or "", qs)
    return len(qs - answered)


class ApprovalPending(Exception):
    """Et vaerktoejskald kraever en menneskelig godkendelse: loekken PARKERER (checkpoint) i stedet for at
    udfoere det. ``approval_id`` er den varige approval; ``tool_call_id`` det kald der venter."""

    def __init__(self, approval_id: str, tool_call_id: str = "") -> None:
        super().__init__(f"APPROVAL_PENDING:{approval_id}")
        self.approval_id, self.tool_call_id = approval_id, tool_call_id


class LoopIO(Protocol):
    def model(self, *, messages: list[dict], tools: list[dict], requires_tools: bool,
              provider: str, model: str) -> dict[str, Any]: ...

    def tool(self, tc: dict) -> str: ...

    def after_tool(self, tc: dict, tool_out: str) -> None: ...

    def after_round(self, rounds: int, tool_calls: list[dict]) -> None: ...


def run_tool_loop(io: LoopIO, *, prompt: str, tools_payload: list[dict], requires_tools: bool,
                  provider: str, model: str, scout: bool, max_rounds: int,
                  synthesis_directive: str, resume: dict[str, Any] | None = None) -> dict[str, Any]:
    """Koer loekken og returner raa tal + tekst. Kaster aldrig: en fejl bliver ``error_str``.

    Kraever et kald en godkendelse (``ApprovalPending`` fra ``io.tool``), STOPPER loekken og returnerer
    ``parked`` med en checkpoint (beskeder, de kald der staar tilbage, taellere). Gives checkpointen tilbage
    som ``resume``, genoptages praecis dér: de ventende kald koeres foerst (det foerste afgoeres nu af
    brugerens beslutning), derefter fortsaetter runderne."""
    messages: list[dict] = [{"role": "user", "content": prompt}]
    total_input = 0
    total_output = 0
    total_cost = 0.0
    total_tool_calls = 0          # kald faktisk udfoert paa tvaers af runder
    final_text = ""
    rounds = 0
    error_str = ""
    tool_calls: list = []         # sidste runde: sandt <=> opbrugt midt i vaerktoejsbrug
    scout_retries = 0
    action_retries = 0
    #: 26/10-2026: ét afsluttende svar-kald uden vaerktoejer, naar spoergsmaal staar
    #: ubesvarede efter nudgen. Uden den gik loekken hjem med stoffet i haanden.
    forced_answers = False
    write_calls = 0
    incomplete = False
    # 26/10-2026: antallet af ubesvarede nummererede spoergsmaal. Baeres med ud til
    # kalderen, saa Jarvis kan se HVOR MEGET der manglede — ikke bare AT der manglede
    # noget. Kravet (Bjørn 26/10): "Jarvis skal altid vide, hvad den naaede, hvad den
    # ikke naaede, og hvorfor arbejdet stoppede."
    unanswered_total = 0
    # 26/10-2026: HVORFOR arbejdet stoppede. Et maalt faktum (rundebudgettet loeb ud), ikke
    # en vurdering af teksten. Maalt paa `asg-a413aa7ac3704131`: agenten brugte 7
    # vaerktoejskald, fik sin nudge i runde 8 — som ER loftet — og loekken udloeb uden at
    # markere noget som helst. Udfaldet blev `completed` med en statusnote som "svar".
    stop_reason = ""
    parked: dict[str, Any] | None = None
    t0 = time.monotonic()
    # Kan agenten skrive i det hele taget? Det afgoeres af SKEMAET den fik, ikke af dens ord.
    write_capable = bool(
        {str((t.get("function") or {}).get("name") or "") for t in tools_payload if isinstance(t, dict)}
        & _WRITE_TOOL_NAMES)

    def checkpoint(pending: list[dict], pending_round_calls: list[dict]) -> dict[str, Any]:
        return {"messages": messages, "pending_calls": pending, "round_calls": pending_round_calls,
                "rounds": rounds, "total_input": total_input, "total_output": total_output,
                "total_cost": total_cost, "total_tool_calls": total_tool_calls,
                "scout_retries": scout_retries, "action_retries": action_retries,
                "write_calls": write_calls, "final_text": final_text}

    def run_calls(calls: list[dict], round_calls: list[dict]) -> bool:
        """Udfoer kald i raekkefoelge. ``True`` hvis loekken blev parkeret."""
        nonlocal total_tool_calls, parked, write_calls
        for i, tc in enumerate(calls):
            tc_id = str(tc.get("id") or "")
            try:
                tool_out = io.tool(tc)
            except ApprovalPending as ap:
                parked = {"approval_id": ap.approval_id, "tool_call_id": tc_id or ap.tool_call_id,
                          "checkpoint": checkpoint(calls[i:], round_calls)}
                return True
            total_tool_calls += 1
            if str((tc.get("function") or {}).get("name") or "") in _WRITE_TOOL_NAMES:
                write_calls += 1
            io.after_tool(tc, tool_out)
            messages.append({"role": "tool", "tool_call_id": tc_id, "content": tool_out})
        io.after_round(rounds, round_calls)
        return False

    try:
        if resume:
            messages = list(resume["messages"])
            rounds = int(resume.get("rounds") or 0)
            total_input = int(resume.get("total_input") or 0)
            total_output = int(resume.get("total_output") or 0)
            total_cost = float(resume.get("total_cost") or 0.0)
            total_tool_calls = int(resume.get("total_tool_calls") or 0)
            scout_retries = int(resume.get("scout_retries") or 0)
            action_retries = int(resume.get("action_retries") or 0)
            write_calls = int(resume.get("write_calls") or 0)
            final_text = str(resume.get("final_text") or "")
            tool_calls = list(resume.get("round_calls") or [])
            if run_calls(list(resume.get("pending_calls") or []), tool_calls):
                return _outcome(final_text, total_input, total_output, total_cost, total_tool_calls, rounds,
                                error_str, t0, parked)
        while rounds < max_rounds:
            rounds += 1
            result = io.model(messages=messages, tools=tools_payload, requires_tools=requires_tools,
                              provider=provider, model=model)
            total_input += int(result.get("input_tokens") or 0)
            total_output += int(result.get("output_tokens") or 0)
            total_cost += float(result.get("cost_usd") or 0.0)
            final_text = str(result.get("text") or "")
            tool_calls = list(result.get("tool_calls") or [])
            if not tool_calls:
                promised = _promises_action(final_text)
                unanswered = _unanswered_questions(prompt, final_text)
                if scout and scout_retries < 1 and (total_tool_calls == 0 or promised or unanswered):
                    scout_retries += 1
                    messages.append({"role": "assistant", "content": final_text})
                    messages.append({"role": "user", "content": _SCOUT_NUDGE})
                    continue
                # Samme vaern for en SKRIVENDE agent (8/10-2026). Én afgraenset nudge - ikke et
                # krav om succes: naeste runde maa gerne vaere "det kan jeg ikke, fordi ...".
                if not scout and action_retries < 1 and (promised or unanswered or (write_capable and write_calls == 0)):
                    action_retries += 1
                    # 26/10-2026: nudgen maa ikke forbruge den SIDSTE tilladte runde. Goer den
                    # det, udloeb loekken paa `while rounds < max_rounds` uden at naa ned til
                    # markeringen nedenfor — og en afbrudt leverance blev meldt `completed`.
                    # Er der ingen runde tilbage, er STOPPET et faktum og skal meldes som et.
                    if rounds >= max_rounds:
                        incomplete = True
                        unanswered_total = unanswered
                        stop_reason = f"rundebudgettet løb ud efter {rounds} runder"
                        break
                    messages.append({"role": "assistant", "content": final_text})
                    messages.append({"role": "user", "content": _ACTION_NUDGE})
                    continue
                # Nudgen blev givet, og svaret er STADIG et loefte uden en eneste skrivning.
                # Det er ikke en fuldfoert opgave - kalderen skal kunne se forskel.
                if promised and write_capable and write_calls == 0:
                    incomplete = True
                # 26/10-2026: ubesvarede nummererede spoergsmaal er et MAALELIGT faktum, ikke
                # en vurdering af teksten. Staar der stadig huller efter nudgen, er leverancen
                # ufuldstaendig — ogsaa for en laese-agent, og ogsaa naar teksten lyder faerdig.
                if unanswered:
                    incomplete = True
                    unanswered_total = unanswered
                    # 26/10-2026 (nat): nudgen er brugt, men spoergsmaalene staar stadig aabne.
                    # Loekken maa ikke gaa hjem her — den skal give agenten ÉT afsluttende kald
                    # UDEN vaerktoejer, hvor den svarer paa alle spoergsmaal ud fra det den
                    # allerede har fundet. Maalt paa `asg-b0e20bf925564962`: tre vaerktoejskald,
                    # derefter "Lad mig se de resterende properties" — stoffet var der, ordren
                    # manglede. En agent der HAR svaret skal ikke doemmes for et spoergsmaal den
                    # aldrig fik lov at besvare.
                    if not forced_answers and not error_str:
                        forced_answers = True
                        try:
                            messages.append({"role": "assistant", "content": final_text})
                            messages.append({"role": "user", "content": _answers_directive(unanswered)})
                            svar = io.model(messages=messages, tools=[], requires_tools=False,
                                            provider=provider, model=model)
                            total_input += int(svar.get("input_tokens") or 0)
                            total_output += int(svar.get("output_tokens") or 0)
                            total_cost += float(svar.get("cost_usd") or 0.0)
                            svar_text = str(svar.get("text") or "").strip()
                            if svar_text:
                                final_text = svar_text
                                # Svaret er NYT: antallet skal maales paa det, ikke paa runden foer.
                                unanswered_total = _unanswered_questions(prompt, final_text)
                                incomplete = bool(unanswered_total)
                                stop_reason = (
                                    f"{unanswered_total} spørgsmål uden nummereret svar "
                                    "efter afsluttende svar" if unanswered_total else "")
                        except Exception:
                            logger.warning(
                                "afsluttende svar fejlede - beholder teksten fra sidste runde",
                                exc_info=True)
                break
            messages.append({"role": "assistant", "content": final_text, "tool_calls": tool_calls})
            if run_calls(tool_calls, tool_calls):
                return _outcome(final_text, total_input, total_output, total_cost, total_tool_calls, rounds,
                                error_str, t0, parked)
    except Exception as exc:                      # model-/loekkefejl - aldrig en falsk succes
        error_str = str(exc)[:400]

    # Rundebudgettet opbrugt midt i vaerktoejsbrug: ÉT afsluttende kald UDEN vaerktoejer, saa
    # agenten giver et brugbart svar. Afgraenset; en fejl her degraderer til teksten foer.
    if not error_str and rounds >= max_rounds and tool_calls:
        try:
            messages.append({"role": "user", "content": synthesis_directive})
            synth = io.model(messages=messages, tools=[], requires_tools=False,
                             provider=provider, model=model)
            total_input += int(synth.get("input_tokens") or 0)
            total_output += int(synth.get("output_tokens") or 0)
            total_cost += float(synth.get("cost_usd") or 0.0)
            synth_text = str(synth.get("text") or "").strip()
            if synth_text:
                final_text = synth_text
                # Syntesen er et NYT svar: antallet af ubesvarede spoergsmaal skal maales paa
                # det, ikke paa runden foer.
                unanswered_total = _unanswered_questions(prompt, final_text)
            else:
                # Ingen syntese = agenten blev afbrudt midt i arbejdet. Det er et faktum.
                incomplete = True
                stop_reason = stop_reason or f"rundebudgettet løb ud efter {rounds} runder"
        except Exception:
            logger.warning("afsluttende syntese fejlede - beholder teksten fra sidste runde", exc_info=True)
            incomplete = True
            stop_reason = stop_reason or f"rundebudgettet løb ud efter {rounds} runder"

    if unanswered_total:
        incomplete = True

    return _outcome(final_text, total_input, total_output, total_cost, total_tool_calls, rounds, error_str, t0,
                    None, incomplete=incomplete, unanswered=unanswered_total, stop_reason=stop_reason)


def _outcome(final_text: str, total_input: int, total_output: int, total_cost: float, total_tool_calls: int,
             rounds: int, error_str: str, t0: float, parked: dict[str, Any] | None,
             incomplete: bool = False, unanswered: int = 0, stop_reason: str = "") -> dict[str, Any]:
    out = {"final_text": final_text, "total_input": total_input, "total_output": total_output,
           "total_cost": total_cost, "total_tool_calls": total_tool_calls, "rounds": rounds,
           "error_str": error_str, "duration_ms": int((time.monotonic() - t0) * 1000)}
    if parked is not None:
        out["parked"] = parked
    if incomplete:
        out["incomplete"] = True
    if unanswered:
        out["unanswered"] = int(unanswered)
    if stop_reason:
        out["stop_reason"] = str(stop_reason)
    return out
