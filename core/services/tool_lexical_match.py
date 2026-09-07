"""Leksikalsk vaerktoejs-opslag: saerkende ord slaar semantisk lighed.

Maalt 7/9-2026, efter at cosinus-varianten blev afvist paa data. Den maaling
staar i ``tool_discovery_nudge._skygge``; det korte er, at embedding-lighed
mellem en besked og en vaerktoejsbeskrivelse ikke kan skelne: afstanden fra
bedste til naestbedste traef var 0,0106 i snit — ét procentpoint — saa
ranglisten var reelt vilkaarlig, og 40 aegte beskeder gav nul brugbare bud.

Det der derimod VIRKEDE i de faa rigtige traef var altid det samme: et sjaeldent
ord fra beskeden stod i vaerktoejets navn.

    «Check lige codex 2 sidste nye branches»      → git_branch
    «resultater claude fik fra interlanguage»     → interlanguage_protocol

Embeddingen tilfoejede intet dér — og hvor den foerte, foerte den vild
(«Kan **slet** ikk faa lov at toppe op med kort» → note_delete).

Saa her rangeres paa ordoverlap vaegtet med IDF over vaerktoejskorpuset: et ord
der optraeder i faa vaerktoejer er saerkende, et der optraeder i mange er ikke.
Det giver tre ting cosinus ikke kunne:

1. **Margin der betyder noget.** Paa cosinus var top1→top2 altid ~0,01. Her
   staar et aegte traef klart over feltet (provider_health_check 13,5 mod 8,3),
   mens et tilfaeldigt ligger LIGE med et dusin andre (publish_file 5,0 mod
   5,0). Afstanden er derfor en brugbar port — se ``GULV`` og ``FAKTOR``.
2. **Den kan sige nej.** Cosinus giver altid en top; 43 af 60 beskeder faar
   her slet intet bud, hvilket er det rigtige svar.
3. **Den kan forklare sig.** Traeffet baerer de ord det byggede paa, saa
   nudgen kan vise «via: providers, lane» i stedet for et tal ingen kan
   efterproeve.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import NamedTuple

# Absolut gulv OG relativ margin.
#
# IDF er NORMALISERET (se ``Korpus.idf``), saa gulvet ikke afhaenger af hvor
# mange vaerktoejer korpuset indeholder. Foerste udgave brugte rå IDF med
# gulv 7,0, kalibreret paa 448 vaerktoejer — med et lille korpus kunne INGEN
# score naa derop, saa porten var i praksis bundet til én korpus-stoerrelse.
# Paa den normaliserede skala er 1,0 «ét saerkende ord i selve navnet».
#
# Begge vaerdier maalt paa 60 aegte beskeder 7/9. Slaekkes faktoren til 1,0
# kommer uafgjorte traef ind (publish_file 5,0 mod 5,0 via «paste»), og de er
# stoej — og stoej er vaerre end ingen nudge, fordi han saa laerer at
# ignorere kanalen.
GULV = 1.35
FAKTOR = 1.4

# Mindste ordlaengde. Under fire tegn er det stort set altid stopord paa
# begge sprog, og de faa der ikke er («api», «ssh») rammer alligevel gennem
# beskrivelsen.
_MIN_ORD = 4

# Stopord. Ud over de saedvanlige staar her de ord der EMPIRISK gav falske
# traef i maalingen — dansk har falske venner mod engelske vaerktoejsnavne:
#   «slet» i «slet ikke» (= slet ikke) ramte note_delete
#   «blev», «gamle», «info», «paste» gav uafgjorte traef uden mening
_STOPORD = frozenset("""
og eller men som der det den de en et er var har havde skal kan kunne vil ville
du jeg han hun vi mig dig sig min din hans hendes vores til fra med om for pa på i af
at ikke ikk nu her der hvor hvad hvem hvorfor hvordan lige bare helt meget mere mest
the and or but a an is are was were be been to from with of in on for it this that you i we
he she they can could will would should do does did have has had not no yes just only
saa så ok okay tak hej ja nej hvis naar når ind ud op ned over under
blev bliver blevet gamle gammel slet info noget nogen uden igen side frem selv sige siger
maskine egen dine deres alle andre samme godt bedre altid aldrig maaske måske
""".split())

_ORD = re.compile(r"[a-zA-Zæøåäöü_]{%d,}" % _MIN_ORD)


class Traef(NamedTuple):
    """Et bud. ``ord`` er de saerkende ord det byggede paa, mest saerkende foerst."""

    navn: str
    score: float
    naest: float
    ord: tuple[str, ...]


def ord_i(tekst: str) -> set[str]:
    """Saerkende ord i en tekst — smaa bogstaver, stopord ude."""
    return {w for w in _ORD.findall((tekst or "").lower()) if w not in _STOPORD}


class Korpus:
    """IDF over vaerktoejskorpuset. Bygges én gang pr. vaerktoejssaet.

    Adskilt fra opslaget, fordi IDF kun aendrer sig naar vaerktoejer kommer
    til eller gaar — ikke pr. besked.
    """

    def __init__(self, tekster: dict[str, str]) -> None:
        self._tekster = {nv: (t or "").lower() for nv, t in tekster.items()}
        self._ord = {nv: ord_i(t) for nv, t in self._tekster.items()}
        df: Counter[str] = Counter()
        for ord_saet in self._ord.values():
            df.update(ord_saet)
        self._df = df
        self._n = max(1, len(self._tekster))

    def idf(self, ord_: str) -> float:
        """Sjaeldne ord vejer tungt, paa en skala der ikke afhaenger af korpus-stoerrelsen.

        Normaliseret med ``log(N+1)``, saa et ord der staar i ét eneste
        vaerktoej giver ~1,0 uanset om korpuset har 9 eller 448 vaerktoejer,
        og et ord der staar i halvdelen giver noget naer 0. Uden den
        normalisering var gulvet bundet til det korpus det blev maalt paa.

        +1 i naevneren, saa ukendte ord ikke deler med nul.
        """
        return math.log((self._n + 1) / (1 + self._df.get(ord_, 0))) / math.log(self._n + 1)

    def slaa_op(
        self,
        besked: str,
        kandidater: list[str] | None = None,
        ekstra_stopord: frozenset[str] = frozenset(),
    ) -> Traef | None:
        """Bedste bud, eller ``None`` naar intet staar klart nok over feltet.

        ``None`` er det normale svar — 43 af 60 aegte beskeder i maalingen.

        ``ekstra_stopord`` er ord der er hyppige i BRUGERENS sprog. Se
        ``hyppige_ord_hos_brugeren`` for hvorfor det er noedvendigt.
        """
        bo = ord_i(besked) - ekstra_stopord
        if not bo:
            return None
        navne = kandidater if kandidater is not None else list(self._tekster)
        scoret: list[tuple[float, str, set[str]]] = []
        for navn in navne:
            faelles = bo & self._ord.get(navn, frozenset())
            if not faelles:
                continue
            # Navnet vejer dobbelt: staar ordet i NAVNET, er det et langt
            # staerkere signal end at det optraeder et sted i beskrivelsen.
            navn_lav = navn.lower()
            score = sum(self.idf(w) * (2.0 if w in navn_lav else 1.0) for w in faelles)
            scoret.append((score, navn, faelles))
        if not scoret:
            return None
        scoret.sort(key=lambda r: (-r[0], r[1]))
        score, navn, faelles = scoret[0]
        naest = scoret[1][0] if len(scoret) > 1 else 0.0
        if score < GULV or score < naest * FAKTOR:
            return None
        return Traef(
            navn=navn,
            score=score,
            naest=naest,
            ord=tuple(sorted(faelles, key=lambda w: -self.idf(w))[:3]),
        )


def byg_korpus_fra_definitioner(definitioner: list[dict]) -> Korpus:
    """Korpus ud fra ``get_tool_definitions()``-formen (baade rå og indpakket)."""
    tekster: dict[str, str] = {}
    for d in definitioner or []:
        fn = d.get("function") or d
        navn = str(fn.get("name") or "").strip()
        if navn:
            tekster[navn] = navn + " " + str(fn.get("description") or "")
    return Korpus(tekster)


def hyppige_ord_hos_brugeren(
    beskeder: list[str], *, graense: float = 0.01,
) -> frozenset[str]:
    """Ord brugeren siger HELE TIDEN — spaerret uanset hvor saerkende de er
    blandt vaerktoejerne.

    IDF ovenfor er **ensidig**: den maaler kun hvor sjaeldent et ord er blandt
    vaerktoejsbeskrivelserne. Den ved intet om hvor hyppigt ordet er i det
    brugeren faktisk skriver. Maalt 7/9-2026 paa 400 aegte beskeder var det den
    stoerste stoejkilde i hele matcheren:

        «claude»  tool-IDF 0,68  men staar i  7,2 % af hans beskeder
                  -> dispatch_to_claude_code vandt 22 af 72 bud (30 %),
                     hver gang paa saetninger som «Claude kigger paa det..»

    Et ord han bruger i hver fjortende besked baerer ingen information om
    hvilket vaerktoej han har brug for — uanset at kun ét vaerktoej naevner det.
    Den haandlavede ``_STOPORD`` ovenfor er det samme princip, fundet i haanden
    ét falsk traef ad gangen («slet», «paste»). Denne udgave udleder listen af
    hans eget sprog og holder sig selv ved lige naar emnerne skifter.

    Ved 1 % spaerres ~110 ord — jarvis, claude, tool, prompt, code, container,
    tools. Det er praecis den slags ord han taler *om* systemet med, ikke dem
    han beder om noget med.
    """
    if not beskeder:
        return frozenset()
    df: Counter[str] = Counter()
    for b in beskeder:
        df.update(ord_i(b))
    n = len(beskeder)
    return frozenset(w for w, antal in df.items() if antal / n > graense)
