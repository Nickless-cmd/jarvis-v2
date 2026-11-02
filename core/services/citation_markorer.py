"""Citation-markører — kontrolsyntaks der aldrig må nå skærmen.

To opgaver, én kontrakt (2/11-2026):

* ``side-991bb8e07b`` — memory-citations: ``【memcite】``
* ``side-335ac89e6f`` — web-citations: ``【cite|ref1|ref2】`` og
  ``【url|ankertekst|ref-eller-kvalificeret-url】``

## Hvorfor her og ikke i `visible_runs.py`

``FirstPassOutputFilter`` er allerede den ENE synlige grænse: den fjerner
capability-markup, runtime-markører, DSML og den halve DSML-form før mennesket
ser teksten. Den har også de to ting en markør-kontrakt kræver — en hale der
holder et delvist token tilbage, og en ``flush`` der afgør hvad en uafsluttet
hale betyder. At bygge en parallel grænse ville være samme problem løst to
steder, og den ene ville drive. Boy Scout-reglen: udskilt, ikke indlejret.

## Reglen der gør den sikker

En markør er kun en markør hvis dens indhold VALIDERER:

* ``cite`` accepterer kun ref-id'er der findes i turens kilder. En opdigtet
  reference bliver ALDRIG et link.
* ``url`` accepterer kun en kendt ref ELLER en kvalificeret HTTP(S)-URL.
  ``javascript:``, ``data:``, ``file:`` og ``vbscript:`` afvises.
* Afvises en markør, falder den tilbage til sin EGEN tekst — aldrig til
  ingenting. Et svar må ikke tabe indhold, fordi en model skrev en reference
  der ikke findes.

## Hvorfor klammer og ikke regex

Samme grund som ``visible_text_scrub``: indholdet kan selv indeholde ``】``
(et anker kan hedde noget med en klamme), og et ikke-grådigt regex ville
stoppe for tidligt og efterlade resten på skærmen. Klammetælling klarer begge.

## Hvad den IKKE gør

Den lærer ikke modellen syntaksen. Den fjerner den kun hvis den optræder.
Syntaksen må først sendes til modellen når hele kæden findes — det er
opgavernes eget krav, og det er den rigtige rækkefølge: en parser uden
leverandør er harmløs, en leverandør uden parser lækker.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urlsplit

#: Åbner og lukker for kontrolsyntaksen. Bevidst valgt så de ikke kolliderer
#: med markdown, JSON eller almindelig dansk tegnsætning.
_AABNER = "【"
_LUKKER = "】"

#: Længste markør vi tror på. En ``【`` der IKKE er en markør må ikke kunne
#: holde ubegrænset tekst tilbage i strømmen — så hellere slippe den igennem
#: end at tie resten af svaret ihjel. Samme ræsonnement som ``MAKS_NOTE``.
MAKS_MARKOR = 400

#: Schemes der aldrig må blive et link. ``http``/``https`` er de eneste
#: tilladte; alt andet afvises fail-closed.
_TILLADTE_SCHEMES = ("http", "https")

#: Et anker må ikke kunne injicere markup i den renderede tekst.
_ANKER_FORBUDT = re.compile(r"[<>{}\[\]`]")


@dataclass(frozen=True)
class Kilder:
    """Turens kilder — det eneste en ``cite``/``url``-ref kan pege på.

    ``web`` mapper et stabilt ref-id (``ref1``, ``ref2`` …) til en URL.
    Tomme kilder betyder at INGEN ref kan validere — og så afvises alle
    ``cite``-markører. Det er fail-closed: hellere ingen citation end en
    opdigtet.
    """

    web: dict[str, str] = field(default_factory=dict)

    #: Sandheden om memory var i den byggede prompt — en CALLABLE, ikke et flag.
    #:
    #: 2/11-2026. `memcite` blev godkendt ubetinget, med en kommentar der
    #: påstod at «runtime afgjorde» det. Runtime afgjorde intet: der fandtes
    #: ingen at spørge. Det her er den nogen.
    #:
    #: Hvorfor callable: `FirstPassOutputFilter` laves ved run-start, FØR
    #: prompten findes. En bool læst ved instansiering ville være `False` for
    #: evigt — præcis den rækkefølge-fælde der gjorde kæden død. Proben
    #: aflæses ved OPSLAGET, så den rammer den rækkefølge der faktisk gælder.
    #:
    #: `None` = ingen viden = ingen godkendelse (fail-closed).
    memory_probe: Callable[[], bool] | None = None

    def url_for(self, ref: str) -> str | None:
        return self.web.get(ref)

    def memory_i_kontekst(self) -> bool:
        """Var der memory i den prompt turen faktisk fik? Fail-closed."""
        if self.memory_probe is None:
            return False
        try:
            return bool(self.memory_probe())
        except Exception:
            # En probe der kaster er ikke et ja. Samme regel som for refs:
            # hellere ingen citation end en der ikke kan dokumenteres.
            return False

    def tilfoej(self, ref: str, url: str) -> None:
        """Registrér én kilde — mens turen kører.

        2/11-2026. Filteret laves ved run-start, FØR nogen søgning er kørt, så
        kilderne kan ikke kendes ved instansiering. De skal derfor kunne fyldes
        bagefter. ``frozen=True`` forhindrer ombinding af attributten, ikke
        mutation af dict'en — så beholderen er bevidst delt og levende.
        """
        if ref and url:
            self.web[ref] = url


@dataclass(frozen=True)
class Fund:
    """Én markør der blev fundet — godkendt eller afvist.

    Bæres videre som struktureret metadata til UI/observability, så en
    citation kan spores uden at den rå syntaks står i teksten.
    """

    slags: str
    refs: tuple[str, ...] = ()
    anker: str = ""
    url: str = ""
    #: De URL'er markøren faktisk pegede på, frosset ved parse-tid.
    #:
    #: 2/11-2026: uden dette kunne `til_metadata()` ikke sige HVAD et `cite`
    #: citerede — kun hvilke ref-id'er der stod i teksten, og et ref-id er
    #: ikke en kilde nogen kan følge. Frosset fordi `Kilder` er levende og
    #: vokser mens turen kører: metadata skal beskrive det der blev skrevet,
    #: ikke det der tilfældigvis er i beholderen bagefter.
    urls: tuple[str, ...] = ()
    godkendt: bool = False
    raa: str = ""

    def til_metadata(self, kilder: "Kilder | None" = None) -> dict[str, object]:
        """JSON-egnet form til UI/observability.

        2/11-2026. `CitationKontrakt.fundet` blev fyldt ved hver ``feed()``,
        men havde NUL læsere — metadata blev ikke «ikke afleveret», de lå i en
        død liste. Det her er den form der kan afleveres: rene typer, og de
        URL'er markøren faktisk pegede på.
        """
        urls = list(self.urls)
        if not urls and kilder is not None:
            # Fallback for et fund dannet før `urls` blev frosset.
            urls = [u for u in (kilder.url_for(r) for r in self.refs) if u]
        if not urls and self.url:
            urls = [self.url]
        return {
            "slags": self.slags,
            "godkendt": self.godkendt,
            "refs": list(self.refs),
            "urls": urls,
            "anker": self.anker,
        }



def _gyldig_url(url: str) -> bool:
    """Kun absolutte HTTP(S)-URL'er med et host. Alt andet afvises."""
    if not url or any(c.isspace() for c in url):
        return False
    try:
        dele = urlsplit(url)
    except ValueError:  # ugyldig URL er et AFslag, ikke en fejl der skal op
        return False
    if dele.scheme.lower() not in _TILLADTE_SCHEMES:
        return False
    return bool(dele.netloc)


def _find_lukker(tekst: str, start: int) -> int:
    """Indeks for den LUKKENDE klamme der hører til åbneren ved ``start``.

    Klammetælling: indholdet kan selv indeholde ``【``/``】``, og et regex
    ville stoppe ved den første og efterlade resten på skærmen.
    """
    dybde = 0
    for i in range(start, len(tekst)):
        tegn = tekst[i]
        if tegn == _AABNER:
            dybde += 1
        elif tegn == _LUKKER:
            dybde -= 1
            if dybde == 0:
                return i
    return -1


def _tyd(raa: str, kilder: Kilder) -> Fund | None:
    """Fortolk én markørs indhold. ``None`` = ikke en markør vi kender."""
    dele = raa.split("|")
    slags = dele[0].strip().lower()

    if slags == "memcite" and len(dele) == 1:
        # Memory-citation: markøren siger «dette bygger på brugerkontekst».
        # Den bærer ingen ref — kilden er hukommelsen selv.
        #
        # 2/11-2026: her stod `godkendt=True` med en kommentar om at «runtime
        # afgjorde at den var i konteksten». Det var en påstand uden dækning:
        # ingen spurgte, og markøren blev derfor godkendt i alle ture — også
        # dem hvor [HUKOMMELSE] var tom. Nu spørges den byggede prompt.
        return Fund(
            slags="memcite", godkendt=kilder.memory_i_kontekst(), raa=raa
        )

    if slags == "cite" and len(dele) >= 2:
        refs = tuple(d.strip() for d in dele[1:] if d.strip())
        if not refs:
            return None
        godkendt = all(kilder.url_for(r) for r in refs)
        # URL'erne fryses HER: et ref-id er ikke en kilde nogen kan følge.
        urls = tuple(u for u in (kilder.url_for(r) for r in refs) if u)
        return Fund(slags="cite", refs=refs, urls=urls, godkendt=godkendt, raa=raa)

    if slags == "url" and len(dele) == 3:
        anker = dele[1].strip()
        maal = dele[2].strip()
        if not anker or _ANKER_FORBUDT.search(anker):
            return Fund(slags="url", anker=anker, raa=raa, godkendt=False)
        # Målet er enten et kendt ref-id eller en kvalificeret URL.
        url = kilder.url_for(maal) or (maal if _gyldig_url(maal) else "")
        return Fund(
            slags="url",
            anker=anker,
            url=url,
            urls=(url,) if url else (),
            godkendt=bool(url),
            raa=raa,
        )

    return None


def _render(fund: Fund) -> str:
    """Markørens tekstfallback — hvad der står hvis den ikke kan blive et link.

    Et godkendt ``url`` bliver et almindeligt markdown-link: det er den form
    alle tre klienter allerede renderer, så overgangen kræver ingen ny
    renderer. Et AFVIST link bliver sit anker i almindelig tekst: læseren
    mister ikke sætningen, men får heller ikke et link til noget der ikke
    findes.
    """
    if fund.slags == "url":
        if fund.godkendt and fund.url:
            return f"[{fund.anker}]({fund.url})"
        return fund.anker
    return ""


def parse_markorer(tekst: str, kilder: Kilder) -> tuple[str, list[Fund]]:
    """Fjern alle markører fra ``tekst`` og returnér (ren tekst, fundne).

    Ukendte refs og skadelige URL'er fjernes OGSÅ — men markeres ``godkendt
    = False`` og efterlader deres tekstfallback. Kontrolsyntaks hører aldrig
    på skærmen, uanset om den validerede.
    """
    if _AABNER not in tekst:
        return tekst, []

    ud: list[str] = []
    fundet: list[Fund] = []
    i = 0
    while i < len(tekst):
        start = tekst.find(_AABNER, i)
        if start < 0:
            ud.append(tekst[i:])
            break
        ud.append(tekst[i:start])
        slut = _find_lukker(tekst, start)
        if slut < 0:
            # Uafsluttet: resten er prosa, ikke en markør.
            ud.append(tekst[start:])
            break
        raa = tekst[start + 1:slut]
        if len(raa) > MAKS_MARKOR:
            ud.append(tekst[start:slut + 1])
            i = slut + 1
            continue
        fund = _tyd(raa, kilder)
        if fund is None:
            # Ikke en markør vi kender — bevar den som den står.
            ud.append(tekst[start:slut + 1])
        else:
            fundet.append(fund)
            ud.append(_render(fund))
        i = slut + 1
    return "".join(ud), fundet


class CitationKontrakt:
    """Strøm-sikker markør-fjerner — samme form som ``StroemSkrubber``.

    Halen holdes tilbage så længe den KUNNE være starten på en markør. Det er
    hvad der forhindrer at et delvist token blinker på skærmen: uden halen
    ville ``【ci`` blive vist, og ``te|ref1】`` komme bagefter.
    """

    def __init__(self, kilder: Kilder | None = None) -> None:
        self._kilder = kilder or Kilder()
        self._hale = ""
        self.fundet: list[Fund] = []

    def feed(self, tekst: str) -> str:
        if not tekst:
            return ""
        buffer = self._hale + tekst
        self._hale = ""

        # Er der en åbner uden lukker i bufferen, er halen muligvis en
        # uafsluttet markør: hold den tilbage til næste bid.
        #
        # Kun fra den SIDSTE åbner. Målt 2/11-2026: med `find` (første åbner)
        # blev `【cite|ref1】 midt 【` holdt tilbage som ÉN hale, fordi den
        # første åbner endnu ikke havde fået sin lukker i dette bid — og da
        # næste bid ankom, slap `midt 【` ud som rå tekst.
        start = buffer.rfind(_AABNER)
        if start >= 0 and _find_lukker(buffer, start) < 0:
            hale = buffer[start:]
            # En hale der er blevet for lang er prosa, ikke en markør.
            if len(hale) <= MAKS_MARKOR:
                self._hale = hale
                buffer = buffer[:start]

        ren, fundet = parse_markorer(buffer, self._kilder)
        self.fundet.extend(fundet)
        return ren

    def flush(self) -> str:
        hale, self._hale = self._hale, ""
        if not hale:
            return ""
        # En uafsluttet markør er prosa: den slippes som den står.
        ren, fundet = parse_markorer(hale, self._kilder)
        self.fundet.extend(fundet)
        return ren


__all__ = [
    "CitationKontrakt",
    "Fund",
    "Kilder",
    "MAKS_MARKOR",
    "parse_markorer",
]
