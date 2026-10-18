"""Kvalitetsdommer for søgeresultater — vælger provider ud fra hvad der FAKTISK kom tilbage.

BAGGRUND (målt 18/10-2026). Vi har tre søgekilder, og de er ikke lige gode til det
samme. Målt på fire queries:

  dansk-specifik  SerpAPI vandt  (danskindustri, heyfunding, fondsmatch)
                  Tavily gav ukrainske og amerikanske grantsider
  dansk-lokal     Tavily vandt   (svendborg.dk, svendborghistorie.dk)
                  SerpAPI gav Esbjerg, Aalborg og CBS — den matchede "åbent" som
                  "åbent hus" og mistede emnet
  dansk-nyhed     Tavily vandt   (dr.dk, altinget, tv2)
                  SerpAPI gav tre DR-liveblog-links, 17,8 s
  teknisk-doc     begge gode    (sqlite.org/wal.html som nr. 1)

Konklusionen er at en FAST rækkefølge er forkert: SerpAPI er 0,07 s og bedst på
dansk-specifik, men fejler på dansk-lokal hvor Tavily rammer. Derfor denne dommer:
den måler resultaterne og vælger, i stedet for at gætte på forhånd.

HVAD DEN IKKE GØR
Den kalder ikke netværket og kender ikke providerne. Den får en liste af kandidater
(provider, resultat) og returnerer den bedste. Det gør den testbar uden sockets —
en dommer der kun kan testes ved at kalde tre API'er bliver ikke testet.
"""
from __future__ import annotations

import re
from typing import Any, Iterable
from urllib.parse import urlparse

#: Domæner der næsten altid er støj i en søgeresultat-liste. Målt: SerpAPI's
#: dansk-lokal-svar indeholdt fire "åbent hus"-sider fra uddannelsesinstitutioner.
_STOEJ_DOMAENER = frozenset({
    "facebook.com", "www.facebook.com", "linkedin.com", "www.linkedin.com",
    "youtube.com", "www.youtube.com", "twitter.com", "x.com",
    "pinterest.com", "instagram.com", "www.instagram.com", "tiktok.com",
})

#: Ord der signalerer at queryen er DANSK og kræver dansk indeks.
_DANSKE_STOPORD = frozenset({
    "hvad", "hvordan", "hvor", "hvornår", "hvilke", "hvilken", "hvem",
    "og", "eller", "ikke", "med", "til", "for", "den", "det", "der",
    "jeg", "kan", "skal", "har", "har", "være", "bliver", "efter", "fra",
})

#: Danske tegn der næsten kun optræder i dansk tekst.
_DANSKE_TEGN = "æøåÆØÅ"


def _domaene(url: str) -> str:
    """Værtsnavn uden www, til støj-filteret."""
    try:
        vaert = (urlparse(url).hostname or "").lower()
    except (ValueError, AttributeError):  # ugyldig URL — behandles som ukendt
        return ""
    return vaert


def _er_dansk_query(query: str) -> bool:
    """Sandt hvis queryen ser dansk ud. Bruges til at vægte .dk-domæner."""
    if any(t in query for t in _DANSKE_TEGN):
        return True
    ord_i_query = set(re.findall(r"[a-z]+", query.lower()))
    return len(ord_i_query & _DANSKE_STOPORD) >= 2


def score_resultater(
    resultater: Iterable[dict[str, Any]],
    *,
    query: str,
    url_felt: str = "url",
) -> float:
    """Ét tal 0..1 for hvor brugbar en resultatliste er for denne query.

    Fire led, alle målbare uden netværk:

    1. **Dækning** — hvor mange resultater kom der overhovedet (0..1).
    2. **Dansk relevans** — andel .dk-domæner, når queryen er dansk. Målt:
       SerpAPI's dansk-lokal-svar havde nul .dk-domæner, Tavilys havde tre.
    3. **Støj** — sociale medier og video trækker ned.
    4. **Emne-overlap** — hvor mange af queryens indholdsord optræder i titel
       eller URL. Det fanger "åbent hus"-fejlen: queryen handlede om Rådhus,
       resultaterne om uddannelse.

    Vægtene er valgt så ét stærkt signal ikke kan drukne de andre: dækning 0,25,
    dansk 0,25, støj 0,20, overlap 0,30.
    """
    liste = [r for r in resultater if isinstance(r, dict)]
    if not liste:
        return 0.0

    # 1. Dækning: 5+ resultater er fuld dækning.
    #
    #    VÆGTEN ER SAT NED FRA 0,25 TIL 0,10 (målt 18/10-2026). Første udgave
    #    belønnede mængde, og SerpAPI returnerer 9-10 resultater hvor Tavily
    #    giver 5. Det gav SerpAPI et gratis forspring på en query hvor ALLE
    #    ni resultater handlede om "åbent hus" i Esbjerg og Aalborg — altså
    #    mere af det forkerte. Antal er ikke kvalitet; det er kun et loft
    #    mod tomme svar.
    daekning = min(len(liste) / 5.0, 1.0)

    # 2. Dansk relevans: andel .dk-domæner (kun når queryen er dansk).
    if _er_dansk_query(query):
        dk = sum(1 for r in liste if _domaene(str(r.get(url_felt) or "")).endswith(".dk"))
        dansk = dk / len(liste)
    else:
        dansk = 0.5  # neutralt: ikke et signal i en engelsk query

    # 3. Støj: andel resultater fra sociale medier / video.
    stoej = sum(
        1 for r in liste
        if _domaene(str(r.get(url_felt) or "")) in _STOEJ_DOMAENER
    ) / len(liste)
    renhed = 1.0 - stoej

    # 4. Emne-overlap: hvor mange af queryens indholdsord der rammes.
    #
    #    FØRSTE UDGAVE VAR FORKERT (målt 18/10-2026). Den talte et resultat som
    #    "ramt" hvis BLOt ÉT af queryens ord optrådte i titel eller URL. På
    #    "hvor ligger Svendborg Rådhus og hvornår har de åbent" gav det SerpAPI
    #    1.0 for fem sider om "åbent hus" i Esbjerg og Aalborg: ordet "åbent"
    #    stod i alle titler, så alle fem talte som træf — selv om emnet
    #    (Svendborg Rådhus) var helt fraværende. Dommeren valgte den forkerte
    #    kilde med højeste karakter.
    #
    #    Nu vægtes ordene efter sjældenhed: et ord der står i ALLE resultater
    #    er ikke et signal, det er støj. Vi måler derfor dækning pr. ord og
    #    tager gennemsnittet — så "Svendborg" (0/5) trækker ned mens "åbent"
    #    (5/5) ikke kan redde listen alene.
    emne_ord = [
        w for w in re.findall(r"[a-zæøå]{4,}", query.lower())
        if w not in _DANSKE_STOPORD
    ]
    if emne_ord:
        daekning_pr_ord: list[float] = []
        for w in emne_ord:
            ramt = sum(
                1 for r in liste
                if w in f"{r.get('title', '')} {r.get(url_felt, '')}".lower()
            )
            daekning_pr_ord.append(ramt / len(liste))
        # Et ord der rammer alt eller intet bærer intet signal — vægt det ned.
        vaegte = [1.0 if 0 < d < 1.0 else 0.25 for d in daekning_pr_ord]
        overlap = sum(
            d * v for d, v in zip(daekning_pr_ord, vaegte)
        ) / sum(vaegte)
    else:
        overlap = 0.5  # ingen indholdsord at måle på — neutralt

    return round(
        0.10 * daekning + 0.25 * dansk + 0.20 * renhed + 0.45 * overlap,
        4,
    )


def bedste_kandidat(
    kandidater: list[dict[str, Any]],
    *,
    query: str,
) -> dict[str, Any] | None:
    """Vælg den bedste provider-udfald blandt flere.

    Hver kandidat er ``{"provider": str, "resultat": dict}``. Returnerer den
    kandidat med højest score, eller ``None`` hvis ingen gav resultater.

    Fejlede kald (``status == "error"``) deltager ikke — en provider der svarer
    med en fejl skal ikke kunne vinde over en der svarede rigtigt, uanset hvor
    mange resultater fejl-objektet end måtte indeholde.
    """
    bedst: dict[str, Any] | None = None
    bedst_score = -1.0
    for k in kandidater:
        res = k.get("resultat") or {}
        if res.get("status") == "error":
            continue
        liste = res.get("results") or []
        # En kandidat UDEN resultater kan ikke vinde (målt 18/10-2026: den fik
        # score 0,0 og blev valgt som "bedste" fordi den var den eneste — så
        # svaret blev en tom liste med status ok i stedet for en ærlig fejl).
        if not liste:
            continue
        s = score_resultater(liste, query=query)
        if s > bedst_score:
            bedst_score = s
            bedst = {**k, "score": s}
    return bedst
