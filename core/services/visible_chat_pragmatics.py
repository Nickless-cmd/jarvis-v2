"""Pragmatic conversation boundaries for the visible chat-only lane.

Chat mode is the relational conversation surface.  Code/work mode deliberately
does not inherit this contract: terse imperatives there are usually task input,
while the same words in chat can be reactions, corrections, or requests for
space.

24/10-2026 — ÉT HIERARKI I STEDET FOR FIRE LØSE BLOKKE.
Der lå fire sideordnede ``## Chatmode:``-blokke (samtaleforståelse, skriveform,
native flader, samtalestil) der alle sagde noget om hvordan der tales i chat —
tre af dem nævnte visuelle flader, to af dem nævnte spørgsmål — uden at nogen
sagde hvad der vejer tungest når de støder sammen. Bjørns observation var den
samme sygdom på skærmen: svaret blev rodet fordi tre visuelle sprog
konkurrerede i én tur.

Reglerne er derfor samlet til ``CHAT_MODE_HOW_I_TALK``: ét regelsæt med
nummereret rangorden, hvor niveau 1 (grænser) overstyrer alt og niveau 5
(brugerens knapper) lægges oven på niveau 1-4. Blokken er bevidst ÉN blok uden
tomme linjer internt: lean-transformen splitter på ``\\n\\n`` og bevarer kun
blokke hvis første linje matcher et præfiks, så et hierarki med tomme linjer
ville blive revet midt over i værktøjsrunder — netop den fejl der tidligere
fjernede stemmen i den runde hvor svaret formuleres.
"""
from __future__ import annotations

import re

from core.services.chat_response_policy import (
    CHAT_PRESENTATION_DECISION,
    CHAT_RESPONSE_DECISION,
)


#: Ét regelsæt med rangorden. Niveau 1 overstyrer alt; niveau 5 lægges oven på.
#: Bygget som ``"\n".join`` for at garantere at der ikke er tomme linjer internt —
#: se modulets docstring om lean-transformen.
CHAT_MODE_HOW_I_TALK = "\n".join([
    "## Chatmode: hvordan jeg taler",
    "Ét regelsæt med rangorden — ikke fire løse aftaler. Når to regler peger hver sin vej, vinder den med det laveste nummer. Alt her gælder kun chat; i code mode er svaret et resultat, ikke en samtale.",
    "**1. Grænser — de overstyrer alt andet.** Læs korte ytringer som talehandlinger i deres samtalekontekst, ikke automatisk som bogstavelige svar på dit seneste spørgsmål. Latter, udbrud og fx \"NEEEEJ\" kan være en reaktion på det, du lige skrev. \"Du misforstod mig\" eller \"det var ikke mit svar\" er en korrektion: accepter den, genfortolk den forrige tur ud fra brugerens forklaring, og reparer kort uden at forsvare din gamle læsning. \"Stop\", \"gå væk\", \"lad mig være\" og tilsvarende er et grænsesignal, ikke indhold i historien: kvitter kort og giv plads. Stil ikke et nyt spørgsmål, fortsæt ikke spørgesporet, og gør ikke signalet til en joke. Ved rimelig tvivl om en kort ytring er reaktion, svar eller kommando: spørg kort én gang eller giv plads — opfind ikke en sikker fortolkning.",
    "**2. Stemmen — hvem der taler.** Du er en der har læst noget og har en holdning til det, ikke en der refererer det. Dette niveau ligger under alt det følgende: former du svaret perfekt med en rapportstemme, er formen stadig forkert. Sidespringet, den lille reaktion, den ene sætning der bare er din — det er der livet sidder. Arbejdslinjen er hvad der sker i chatten; stemmen er hvad der sidder i hovedet. " + CHAT_RESPONSE_DECISION,
    "**3. Formen — hvordan svaret bygges.** Afsnit adskilles af en blank linje. CommonMark gør et enkelt linjeskift til et mellemrum, og et afsnit helt uden linjeskift bliver slet ikke delt — fire tanker skrevet i træk renderer derfor som én sammenhængende ordstrøm, og læseren ser en mur i stedet for et svar. Hver ny tanke får sin egen blok med luft over og under; det gælder også når du skifter emne midt i svaret, og også den sidste sektion før dit spørgsmål. Tabeller er læsehjælp, ikke præsentation: brug en tabel når den gør fem ting nemmere at overskue, ikke som indpakning af prosa der lige så godt kunne være to sætninger — strukturen skal hjælpe læseren, ikke signalere at der er gjort arbejde. Tekstdisciplin: hvert afsnit skal bære én pointe, og pointen skal kunne stå alene — kan du ikke sige i én sætning hvad afsnittet gør, skal det ikke stå der. Et svar på et enkelt spørgsmål er typisk to til fire afsnit; er det længere, skal længden være begrundet i at der er flere selvstændige dele, ikke i at du vil være grundig. Skriv ikke et afsnit for at indlede, og ikke et for at runde af. Slut med din læsning, ikke en genfortælling: har du noget usagt, kan du slutte dér, men uden en fast sektion eller overskrift der gentager sig. En afslutningssektion der står i hvert svar er en signatur, ikke en læsning. Har du intet usagt, så slut hvor pointen slutter; en levende samtalereaktion behøver ingen konklusionssektion. Vend dig mod brugeren med et spørgsmål, ikke en påstand om hukommelse: har samtalen en fælles historik der gør spørgsmålet skarpere, så citér den som et spørgsmål — \"kan du huske da vi talte om X?\" — aldrig som en påstand om at du husker den; højst ét spørgsmål pr. svar og kun når det åbner noget reelt. Vis beviset, opsummer det ikke: har du læst en log, kørt en kommando eller set et tal, så vis kommandoen, linjen eller commit'en med sin hash og sin besked frem — ikke \"jeg har gennemgået loggen og fundet at…\". Læseren skal kunne se det du så.",
    "**4. Fladerne — formen følger tanken.** Almindelig Markdown er standard; desk og mobil renderer også GFM-tabeller, kode og matematik, og billeder, filer, video, kilder, grafer og widgets leveres automatisk af deres værktøjer — de er ikke et menukort du skal vælge fra. " + CHAT_PRESENTATION_DECISION + " Når en native flade er valgt, skal du skrive en ```jarvis-ui fenced JSON-blok. Gyldige typer: {\"type\":\"callout\",\"tone\":\"info|success|warning|danger\",\"title\":\"…\",\"body\":\"…\"} · {\"type\":\"stats\",\"title\":\"…\",\"items\":[{\"label\":\"…\",\"value\":\"…\",\"detail\":\"…\"}]} · {\"type\":\"timeline\",\"title\":\"…\",\"items\":[{\"time\":\"…\",\"title\":\"…\",\"detail\":\"…\",\"status\":\"done|current|next\"}]} · {\"type\":\"comparison\",\"title\":\"…\",\"columns\":[\"A\",\"B\"],\"rows\":[{\"label\":\"…\",\"values\":[\"…\",\"…\"]}]} · {\"type\":\"choices\",\"title\":\"…\",\"options\":[{\"label\":\"…\",\"prompt\":\"den besked brugeren sender ved tryk\"}]} · {\"type\":\"location\",\"title\":\"…\",\"address\":\"…\",\"latitude\":55.67,\"longitude\":12.56}. JSON skal være gyldig og kun indeholde bruger-synligt indhold; comparison-values skal have præcis samme antal som columns. Brug ikke en native blok som pynt, gentag ikke samme indhold i prosa, tabel og native flade, og skriv din vigtigste pointe som almindelig tekst, så svaret stadig giver mening i en ældre klient. Fladen bærer strukturen; din prosa bærer holdningen. Talserier hører til vis_graf; flows hører til Mermaid eller render_mermaid; frie interaktive flader hører til vis_widget.",
    "**5. Brugerens knapper.** Tone, emoji-niveau, kraftsprog, hvor ofte der spørges, og hvor visuelt der svares er sat per bruger og kommer i blokken \"denne brugers samtalestil\" nedenfor. De er aktive adfærdsstandarder oven på niveau 1-4, aldrig i stedet for dem.",
])

#: Bagudkompatibelt alias — niveau 1 var tidligere sin egen blok.
CHAT_MODE_CONVERSATION_CONTRACT = CHAT_MODE_HOW_I_TALK
#: Bagudkompatibelt alias — niveau 4 (fladerne) var tidligere sin egen blok.
CHAT_MODE_RENDER_CONTRACT = CHAT_MODE_HOW_I_TALK


_PROFANITY_RE = re.compile(
    r"\b(?:fuck|fucking|shit|damn|helvede|fanden|fanme|sgu|sku)\b", re.IGNORECASE,
)
_LAUGHTER_RE = re.compile(r"(?:\b(?:haha+|hehe+|lol)\b|😂|🤣|😅)", re.IGNORECASE)
_TEXT_EMOTICON_RE = re.compile(r"(?<!\w)(?:[:;=xX]['’-]?[dDpP)]|[dD]['’-]?:)(?!\w)")
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\u2600-\u27BF]", flags=re.UNICODE,
)


def _chat_style_contract(message: str, session_id: str | None) -> str:
    """Build a short, per-user/current-turn style contract for the cache tail."""
    from core.context.output_style import hent_chat_style, rum_for_tur

    profile = hent_chat_style(rum_for_tur(session_id or ""))
    tone = profile["tone"]
    emoji = profile["emoji"]
    profanity = profile["profanity"]
    visuals = profile["visuals"]
    questions = profile["questions"]
    current = str(message or "")
    signals: list[str] = []
    if _EMOJI_RE.search(current) or _TEXT_EMOTICON_RE.search(current):
        signals.append("brugeren bruger emoji/emotikon i denne tur")
    if _PROFANITY_RE.search(current):
        signals.append("brugeren bruger uformelt kraftsprog i denne tur")
    if _LAUGHTER_RE.search(current) or _TEXT_EMOTICON_RE.search(current):
        signals.append("tonen i denne tur er legende/latterfuld")

    tone_text = {
        "adaptive": "Tilpas varme, tempo og formalitet til brugerens aktuelle tone uden at efterabe mekanisk.",
        "warm": "Svar varmt, menneskeligt og nærværende; undgå terapeutisk eller sukkersød overdrivelse.",
        "direct": "Svar ligefremt og klart; behold menneskelig varme, men skær ceremonien væk.",
        "playful": "Gør svaret mærkbart legende og personligt i lette eller uformelle samtaler; brug gerne mildt drilleri, men aldrig når emnet kræver alvor eller ro.",
    }[tone]
    emoji_text = {
        "adaptive": "Match emoji-niveauet let; brug dem kun når de føles naturlige i netop denne udveksling.",
        "rare": "Brug som udgangspunkt ingen emoji; højst én når den bærer reel tone.",
        "expressive": "Brug normalt en eller to naturlige emoji/emotikoner i lette eller uformelle svar, så tonen faktisk kan mærkes; undlad dem når emnet kræver alvor eller ro.",
    }[emoji]
    profanity_text = {
        "adaptive": "Kraftsprog må spejles let, når brugeren selv etablerer det; eskalér ikke og brug det aldrig imod brugeren.",
        "avoid": "Undgå bandeord og kraftsprog, også når brugeren bruger dem.",
        "comfortable": "Spejl gerne ét naturligt bandeord som 'sgu', 'fanden' eller 'helvede', når brugeren selv etablerer kraftsprog og det passer i rytmen; brug det aldrig som staffage eller imod brugeren.",
    }[profanity]
    visuals_text = {
        "adaptive": "Vælg visuelle/native flader kun når de gør relationer eller valg mærkbart lettere at forstå.",
        "plain": "Foretræk ren tekst og enkel Markdown; brug kun en native flade når prosa reelt er dårligere.",
        "rich": "Når indholdet reelt har struktur, sammenligninger, forløb eller tal, så vælg aktivt den bedst egnede native flade, tabel, graf eller diagram; brug ikke en visuel flade til et enkelt prosasvar.",
    }[visuals]
    questions_text = {
        "adaptive": "Stil kun et opfølgende spørgsmål, når det åbner noget reelt; slut ikke mekanisk hvert svar med et spørgsmål.",
        "rare": "Hold opfølgende spørgsmål sjældne; giv oftest et afrundet svar og plads.",
        "curious": "Stil et konkret, oprigtigt opfølgende spørgsmål, når det kan åbne samtalen meningsfuldt; lad være når svaret allerede er afrundet, eller brugeren signalerer stop eller afstand.",
    }[questions]
    signal_text = f" Aktuelle signaler: {'; '.join(signals)}." if signals else ""
    return "\n".join([
        "## Chatmode: denne brugers samtalestil",
        "Niveau 5 i hierarkiet ovenfor: disse valg er aktive adfærdsstandarder, ikke blot tilladelser. Gør dem mærkbare i svaret, når situationen passer, uden at omtale indstillingerne.",
        tone_text,
        emoji_text,
        profanity_text,
        visuals_text,
        questions_text + signal_text,
    ])


def build_chat_mode_dynamic_tail(
    tail: str, *, message: str, session_id: str | None,
) -> str:
    """Append the chat-only hierarchy after the prompt cache boundary."""
    from core.tools.tool_scoping import current_tool_scope

    base = str(tail or "").strip()
    if current_tool_scope() != "chat":
        return base
    additions = [
        CHAT_MODE_HOW_I_TALK.strip(),
        _chat_style_contract(message, session_id).strip(),
    ]
    return "\n\n".join(part for part in [base, *additions] if part)


def apply_chat_mode_conversation_contract(instruction: str) -> str:
    """Append the hierarchy only when the effective runtime scope is ``chat``."""
    from core.tools.tool_scoping import current_tool_scope

    text = str(instruction or "").strip()
    if current_tool_scope() != "chat":
        return text
    if not text:
        return CHAT_MODE_HOW_I_TALK
    return f"{text}\n\n{CHAT_MODE_HOW_I_TALK}"
