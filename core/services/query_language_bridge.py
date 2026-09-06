"""Bro fra Bjoerns dansk til de engelske vektorer — foer et embedding-opslag.

Maalt 6/9-2026 mod den aegte embedding-DB: modellen (``nomic-embed-text``) er
engelsk-centrisk, mens tool-navne og -beskrivelser er engelske og Bjoern skriver
dansk. Det spaerrer ikke porten — ``top_sim`` er median 0,695 paa hans aegte
beskeder, langt over routerens taerskel paa 0,4 — men det korrumperer
**rangordningen**, og rangordningen er hele pointen:

    «kan du laegge et moede ind i min kalender paa fredag»
        0.694 curiosity_read_dreams · 0.678 read_learning_memo · 0.674 note_add
        · 0.665 calendar_list_events            ← stoej oeverst

    samme, med to ord byttet til engelsk
        0.770 calendar_list_events · 0.744 calendar_create_event
        · 0.668 curiosity_search_sessions       ← rigtigt oeverst

Afstanden til stoejen gaar fra 0,03 til 0,10. Det er ren ord-substitution:
ingen model, intet kald, deterministisk og testbar. En oversaetter-model i
prompt-kaeden ville koste praecis det ekstra kald embedding-match blev valgt
for at undgaa — og vaere ikke-deterministisk oveni.

Ordforraadet er grundet i hans FAKTISKE sprog (1.500 beskeder gennemgaaet):
hans fagord er i forvejen engelske (tool, prompt, bash, code, session,
container, image), saa broen behoever kun de ord der er aegte danske.

Skills-matcheren loeste samme problem den anden vej — den indekserer
``use_when`` tosproget. Den vej er bedre naar man ejer indholdet; her ejer vi
det ikke (tool-beskrivelser kommer fra vaerktoejerne selv), saa vi normaliserer
forespoergslen i stedet.
"""

from __future__ import annotations

import re

# Kun ord hvor dansk og engelsk faktisk divergerer. Ord han allerede skriver paa
# engelsk staar IKKE her — de virker i forvejen.
_ORDBOG: dict[str, str] = {
    # tid og aftaler — her var fejlen stoerst
    "kalender": "calendar", "kalenderen": "calendar",
    "møde": "meeting", "møder": "meetings", "mødet": "meeting",
    "aftale": "appointment", "aftaler": "appointments",
    "påmindelse": "reminder", "påmindelser": "reminders",
    "begivenhed": "event", "begivenheder": "events",
    # post og beskeder
    "mail": "email", "mails": "emails", "post": "mail",
    "besked": "message", "beskeder": "messages",
    "send": "send", "sende": "send",
    # filer og steder
    "fil": "file", "filer": "files", "filen": "file",
    "mappe": "folder", "mapper": "folders", "mappen": "folder",
    "sti": "path", "stien": "path",
    "billede": "image", "billeder": "images", "billedet": "image",
    # handlinger
    "skriv": "write", "skrive": "write",
    "læs": "read", "læse": "read",
    "søg": "search", "søge": "search", "find": "find",
    "slet": "delete", "slette": "delete",
    "kør": "run", "køre": "run", "kørsel": "run",
    "tjek": "check", "tjekke": "check",
    "prøv": "try", "prøve": "try",
    "opret": "create", "oprette": "create",
    "ret": "fix", "rette": "fix",
    "husk": "remember", "huske": "remember",
    # ting
    "hukommelse": "memory", "hukommelsen": "memory",
    "maskine": "machine", "maskinen": "machine",
    "netværk": "network", "netværket": "network",
    "skærm": "screen", "skærmen": "screen",
    "note": "note", "noter": "notes",
    "kode": "code", "koden": "code",
    "nøgle": "key", "nøgler": "keys",
    "vejr": "weather", "vejret": "weather",
    "kontakt": "contact", "kontakter": "contacts",
}

_ORD = re.compile(r"[a-zA-ZæøåÆØÅ]+", re.UNICODE)


def normalise_for_embedding(text: str) -> str:
    """Byt danske fagord til engelske foer et embedding-opslag.

    Bevarer alt andet uroert — ogsaa store bogstaver uden for ordbogen, tegn og
    tal — saa resultatet stadig ligner den oprindelige saetning. Er der intet at
    bytte, returneres teksten uaendret (ingen allokering af en ny streng-liste
    er noget vaerd her; laesbarheden er).
    """
    t = str(text or "")
    if not t:
        return ""

    def _byt(m: re.Match[str]) -> str:
        ord_ = m.group(0)
        erstat = _ORDBOG.get(ord_.lower())
        if erstat is None:
            return ord_
        # Bevar begyndelsesbogstav: «Kalender» → «Calendar».
        return erstat.capitalize() if ord_[:1].isupper() else erstat

    return _ORD.sub(_byt, t)


def build_query_language_bridge_surface(text: str = "") -> dict[str, object]:
    """Observationsflade — hvad broen ville goere ved denne besked."""
    ud = normalise_for_embedding(text)
    return {
        "vocabulary_size": len(_ORDBOG),
        "input": text,
        "normalised": ud,
        "changed": ud != str(text or ""),
    }
