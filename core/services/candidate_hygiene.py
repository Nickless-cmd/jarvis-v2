"""Hygiejne for runtime-contract-kandidater — stabil nøgle + flygtigheds-filter.

## Hvorfor (målt 2/10-2026)

Bjørn spurgte «hvorfor så mange, og hvordan filtrerer vi støj fra så det ikke
sker igen». Målingen gav svaret, og det var ikke det ventede:

    form                     rækker   unikke   overflødige      %
    stable-context:slug       21.460      202        21.258   99,1%
    user-preference:slug       2.657      614         2.043   76,9%
    remembered-fact:sha        2.576    2.501            75    2,9%

`runtime_contract_candidates` havde 26.761 rækker men kun 3.361 unikke
`canonical_key`. To defekter bar det, og de er ikke den samme:

1. **Upserten slog kun op på `proposed`/`approved`.** En `applied` nøgle var
   dermed *usynlig*, så den samme kendsgerning blev indsat igen — og dræbt
   igen med det samme som `superseded`. 21.258 af 21.460 stable-context-rækker
   er præcis det: samme nøgle, gentaget ~106 gange. Fixet ligger i db-laget
   (`upsert_runtime_contract_candidate` + `TERMINAL_CANDIDATE_STATUSES`).

2. **Nøglen blev udledt af fri tekst.** `stable-context:{domæne}`, hvor
   domænet var sidste led af en witness-nøgle bygget af en sætning. 202
   «nøgler» dækkede reelt ~3-5 gentagne opgaver, formuleret en smule
   forskelligt hver gang — eksakt-match kan ikke fange det.

3. **Kilden skelnede ikke varigt fra flygtigt.** En åben opgave («læs adb
   outputtet og bekræft enhedsstatus») blev løftet til MEMORY.md-kandidat,
   selvom den er en handling, ikke viden.

Dette modul ejer de to rene hjælpere defekt 2 og 3 kræver. Det importerer
intet internt og kan derfor bruges fra både service- og db-laget uden at
skabe en cirkel.
"""
from __future__ import annotations

import re

#: Ord der ikke bærer betydning i et domæne-navn. Uden dem bliver
#: «l-s-adb-outputtet-i-den-synlige-k-rsel-og» og «l-s-outputtet-fra-adb-...»
#: til nøgler der ligner hinanden nok til at eksakt-match virker.
_STOPWORDS = frozenset(
    {
        # dansk
        "af", "i", "den", "det", "de", "en", "et", "og", "til", "for", "med",
        "om", "som", "at", "er", "der", "fra", "på", "paa", "være", "bliver",
        "skal", "kan", "vil", "har", "havde", "ikke", "men", "så", "også",
        "ved", "over", "under", "mellem", "efter", "før", "nu", "her", "sin",
        "sine", "hans", "hendes", "vores", "jeg", "vi", "du", "han", "hun",
        # engelsk
        "the", "a", "an", "of", "to", "and", "or", "in", "on", "with", "that",
        "this", "is", "are", "was", "were", "be", "been", "it", "its", "as",
        "by", "from", "so", "there", "where", "when", "should", "would",
        "could", "can", "will", "has", "have", "you", "he", "she", "they",
        "my", "our",
    }
)

_TOKEN_RE = re.compile(r"[^a-z0-9æøå]+")


def candidate_domain_tokens(value: object) -> list[str]:
    """Split en fri-tekst-streng i rene tokens (lowercase, alfanumerisk)."""
    return [token for token in _TOKEN_RE.split(str(value or "").lower()) if token]


def normalize_candidate_domain(value: object, *, max_tokens: int = 12) -> str:
    """Fold et fri-tekst-domæne til en ren, stabil nøgle-del.

    Funktionen er **idempotent**: `normalize(normalize(x)) == normalize(x)`.
    Det er ikke pynt — domænet normaliseres både hvor forslaget fødes og hvor
    kandidatnøglen bygges, så de to steder må ikke kunne forskyde hinanden.

    Hvad den gør: lowercase, ét skilletegn, stopord væk, længde kappet.
    Hvad den **ikke** gør: den slår ikke semantisk ens formuleringer sammen.

    Det sidste er målt, ikke gættet. Jeg prøvede først at sortere tokens, så
    rækkefølgen ikke betød noget — men de faktiske top-varianter
    («l-s-adb-outputtet-i-den-synlige-k-rsel-og» mod
    «l-s-outputtet-fra-adb-enhedslisten-og-bekr-ft-om») har reelt forskellige
    ordmængder. Sortering flyttede ingen af dem, men omdøbte hver eneste
    eksisterende nøgle (`user-name` → `name-user`) og brød fem tests.
    Teoretisk gevinst, reel omkostning — derfor er rækkefølgen bevaret.

    Den ægte sammensmeltning sker i to andre lag: upserten lader ikke en
    afgjort nøgle genopstå, og `is_transient_line` afviser de flygtige
    opgaver før de bliver nøgler i det hele taget.
    """
    tokens = candidate_domain_tokens(value)
    kept = [token for token in tokens if token not in _STOPWORDS]
    if not kept:
        # Kun stopord (eller ingenting) bærer ingen betydning. At give dem
        # tilbage som nøgle ville skabe en nøgle der ser ud af noget, men ikke
        # er det. Ét fælles tomt-domæne er ærligere.
        return "carried-context"
    return "-".join(kept[:max_tokens])


#: Dato-former. En linje med en dato beskriver en hændelse, ikke en varig sandhed.
_DATE_RE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")

#: Faste vendinger der altid er et øjebliksbillede eller en skabelon.
_TRANSIENT_MARKERS = (
    "bounded chronicle proposal",
    "(tidligere ",
    "days ago",
    "dage siden",
    "i morges",
    "i går",
    "i dag",
    "lige nu",
)

#: Titler uden indhold. En varig kendsgerning har et subjekt og en påstand —
#: «Understanding of X» har ingen af delene.
_VAGUE_TITLE_PREFIXES = (
    "status of ",
    "understanding of ",
    "insight into ",
    "overview of ",
    "summary of ",
    "available ",
    "the last ",
    "recursive observation",
)

#: Handlings-verber i datid. De beskriver hvad der BLEV gjort i én kørsel.
#: Bevidst smal: «lukket», «rettet» og «tilføjet» er udeladt, fordi de også
#: optræder i varige fund («lukket glemsels-sløjfe»).
_TRANSIENT_VERB_TOKENS = frozenset(
    {
        "landet", "pushet", "bygget", "fikset", "verificeret", "deployet",
        "merged", "committed", "genstartet", "gennemførte", "lukkede",
        "landede", "pushede", "kørte", "afsluttet", "igangsat",
    }
)


def is_transient_line(value: object) -> bool:
    """True når en linje beskriver en flygtig hændelse frem for varig viden.

    Bevidst konservativ. Prisen for at droppe en ægte kendsgerning er højere
    end prisen for at beholde en støjende linje — og efter at upserten er
    rettet, koster en gentaget linje ikke længere en ny række. Filteret er
    derfor et net, ikke en mur: det fanger datoer, skabeloner, indholdsløse
    titler og handlings-verber, og lader tvivlstilfælde passere.
    """
    text = " ".join(str(value or "").split()).strip().lower()
    if not text:
        return False
    if _DATE_RE.search(text):
        return True
    if any(marker in text for marker in _TRANSIENT_MARKERS):
        return True
    if text.startswith(_VAGUE_TITLE_PREFIXES):
        return True
    return bool(set(candidate_domain_tokens(text)) & _TRANSIENT_VERB_TOKENS)
