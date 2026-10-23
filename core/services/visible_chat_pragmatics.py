"""Pragmatic conversation boundaries for the visible chat-only lane.

Chat mode is the relational conversation surface.  Code/work mode deliberately
does not inherit this contract: terse imperatives there are usually task input,
while the same words in chat can be reactions, corrections, or requests for
space.
"""
from __future__ import annotations

import re


CHAT_MODE_CONVERSATION_CONTRACT = """## Chatmode: samtaleforstaaelse og graenser

Læs korte ytringer som talehandlinger i deres samtalekontekst, ikke automatisk
som bogstavelige svar på dit seneste spørgsmål. Latter, udbrud og fx "NEEEEJ"
kan være en reaktion på det, du lige skrev. En besked som "du misforstod mig"
eller "det var ikke mit svar" er en korrektion: accepter den, genfortolk den
forrige tur ud fra brugerens forklaring, og reparer kort uden at forsvare din
gamle læsning.

"Stop", "gå væk", "lad mig være" og tilsvarende beskeder rettet mod dig er et
grænsesignal, ikke indhold i historien. Kvitter kort og giv plads. Stil ikke et
nyt spørgsmål, fortsæt ikke spørgesporet, og gør ikke signalet til en joke. Ved
rimelig tvivl om en kort ytring er reaktion, svar eller kommando: spørg kort én
gang eller giv plads; opfind ikke en sikker fortolkning.
"""

CHAT_MODE_RENDER_CONTRACT = """## Chatmode: native svarflader

Brug almindelig Markdown som standard. Desk og mobil renderer også GFM-tabeller,
kode og matematik; billeder, filer, video, kilder, grafer og widgets leveres
allerede af deres værktøjer. Opfind derfor ikke nye formater til dem.

Når én kompakt visuel flade er tydeligere end prosa, kan du skrive PRÆCIS én
```jarvis-ui fenced JSON-blok. Gyldige typer er:
- {"type":"callout","tone":"info|success|warning|danger","title":"…","body":"…"}
- {"type":"stats","title":"…","items":[{"label":"…","value":"…","detail":"…"}]}
- {"type":"timeline","title":"…","items":[{"time":"…","title":"…","detail":"…","status":"done|current|next"}]}
- {"type":"comparison","title":"…","columns":["A","B"],"rows":[{"label":"…","values":["…","…"]}]}
- {"type":"choices","title":"…","options":[{"label":"…","prompt":"den besked brugeren sender ved tryk"}]}
- {"type":"location","title":"…","address":"…","latitude":55.67,"longitude":12.56}

JSON skal være gyldig og kun indeholde bruger-synligt indhold. Brug ikke en
native blok som pynt, gentag ikke samme indhold i en tabel/widget, og skriv den
vigtigste konklusion som almindelig tekst, så svaret stadig giver mening i en
ældre klient. Talserier hører fortsat til vis_graf; flows hører til Mermaid eller
render_mermaid; frie interaktive flader hører til vis_widget.
"""

_PROFANITY_RE = re.compile(
    r"\b(?:fuck|fucking|shit|damn|helvede|fanden|fanme|sgu|sku)\b", re.IGNORECASE,
)
_LAUGHTER_RE = re.compile(r"(?:\b(?:haha+|hehe+|lol)\b|😂|🤣|😅)", re.IGNORECASE)
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
    if _EMOJI_RE.search(current):
        signals.append("brugeren bruger emoji i denne tur")
    if _PROFANITY_RE.search(current):
        signals.append("brugeren bruger uformelt kraftsprog i denne tur")
    if _LAUGHTER_RE.search(current):
        signals.append("tonen i denne tur er legende/latterfuld")

    tone_text = {
        "adaptive": "Tilpas varme, tempo og formalitet til brugerens aktuelle tone uden at efterabe mekanisk.",
        "warm": "Svar varmt, menneskeligt og nærværende; undgå terapeutisk eller sukkersød overdrivelse.",
        "direct": "Svar ligefremt og klart; behold menneskelig varme, men skær ceremonien væk.",
        "playful": "Der må gerne være leg, drilleri og personlighed, når situationen tåler det.",
    }[tone]
    emoji_text = {
        "adaptive": "Match emoji-niveauet let; brug dem kun når de føles naturlige i netop denne udveksling.",
        "rare": "Brug som udgangspunkt ingen emoji; højst én når den bærer reel tone.",
        "expressive": "Emoji er velkomne og må gerne bære tone, men de må ikke overdøve svaret.",
    }[emoji]
    profanity_text = {
        "adaptive": "Kraftsprog må spejles let, når brugeren selv etablerer det; eskalér ikke og brug det aldrig imod brugeren.",
        "avoid": "Undgå bandeord og kraftsprog, også når brugeren bruger dem.",
        "comfortable": "Naturlige bandeord som 'sgu', 'fanden' eller 'helvede' er tilladt, når de passer; brug dem aldrig som staffage eller imod brugeren.",
    }[profanity]
    visuals_text = {
        "adaptive": "Vælg visuelle/native flader kun når de gør relationer eller valg mærkbart lettere at forstå.",
        "plain": "Foretræk ren tekst og enkel Markdown; brug kun en native flade når prosa reelt er dårligere.",
        "rich": "Brug gerne den bedst egnede native flade, tabel, graf eller diagram når indholdet egner sig til det—men højst det nødvendige.",
    }[visuals]
    questions_text = {
        "adaptive": "Stil kun et opfølgende spørgsmål, når det åbner noget reelt; slut ikke mekanisk hvert svar med et spørgsmål.",
        "rare": "Hold opfølgende spørgsmål sjældne; giv oftest et afrundet svar og plads.",
        "curious": "Vær gerne nysgerrig og spørg ind, når det inviterer samtalen videre—men respekter stop- og afstandssignaler straks.",
    }[questions]
    signal_text = f" Aktuelle signaler: {'; '.join(signals)}." if signals else ""
    return "\n".join([
        "## Chatmode: denne brugers samtalestil",
        tone_text,
        emoji_text,
        profanity_text,
        visuals_text,
        questions_text + signal_text,
    ])


def build_chat_mode_dynamic_tail(
    tail: str, *, message: str, session_id: str | None,
) -> str:
    """Append chat-only contracts after the prompt cache boundary."""
    from core.tools.tool_scoping import current_tool_scope

    base = str(tail or "").strip()
    if current_tool_scope() != "chat":
        return base
    additions = [
        CHAT_MODE_CONVERSATION_CONTRACT.strip(),
        _chat_style_contract(message, session_id).strip(),
        CHAT_MODE_RENDER_CONTRACT.strip(),
    ]
    return "\n\n".join(part for part in [base, *additions] if part)


def apply_chat_mode_conversation_contract(instruction: str) -> str:
    """Append the contract only when the effective runtime scope is ``chat``."""
    from core.tools.tool_scoping import current_tool_scope

    text = str(instruction or "").strip()
    if current_tool_scope() != "chat":
        return text
    if not text:
        return CHAT_MODE_CONVERSATION_CONTRACT
    return f"{text}\n\n{CHAT_MODE_CONVERSATION_CONTRACT}"
