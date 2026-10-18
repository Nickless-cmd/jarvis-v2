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


#: Standardvægte for de fire led: dækning, dansk, renhed, overlap.
#:
#: IKKE KALIBRERET — og det kan ikke gøres (målt 18/10-2026).
#:
#: Målt mod 10 queries med objektivt facit (top-1 præcision, dvs. er det
#: FØRSTE resultat det rigtige):
#:
#:   Tavily    2/10 = 20 %
#:   SerpAPI   5/10 = 50 %
#:   Exa       7/10 = 70 %
#:   Dommeren  4/10 = 40 %
#:
#: Dommeren er altså DÅRLIGERE end at vælge Exa blindt. Jeg søgte udtømmende
#: gennem 28.561 vægtkombinationer — ingen nåede over 4/10. Vægtene kan ikke
#: redde den, fordi ingen af de fire led måler om top-1 faktisk besvarer
#: spørgsmålet: dansk-andel, støj, dækning og ord-overlap kan alle beregnes
#: uden at læse hvad resultatet siger. Exa vinder på noget dommeren ikke kigger
#: på — semantisk match — så en dommer bygget af de fire led kan pr. konstruktion
#: ikke se forskellen.
#:
#: Derfor er dommeren IKKE længere vælger i produktionskæden. Se
#: `_fetch_alle_providers` i core/tools/simple_tools_web.py: Exa prøves først,
#: de to andre er fallback når den fejler eller intet giver. Modulet beholdes
#: fordi scoren stadig er brugbar som telemetri (og fordi testene vogter de to
#: fejl der blev målt: ord-overlap uden sjældenhedsvægtning, og dækning der
#: belønner mængde).
VAEGTE_STANDARD: tuple[float, float, float, float] = (0.10, 0.25, 0.20, 0.45)


def score_resultater(
    resultater: Iterable[dict[str, Any]],
    *,
    query: str,
    url_felt: str = "url",
    vaegte: tuple[float, float, float, float] = VAEGTE_STANDARD,
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

    Vægtene er dækning 0,10, dansk 0,25, støj 0,20, overlap 0,45 — men de er
    IKKE kalibreret til at vælge provider (se VAEGTE_STANDARD: dommeren ramte
    4/10 mod Exas 7/10, og ingen af 28.561 kombinationer gjorde det bedre).
    Scoren bruges derfor som telemetri, ikke som vælger.
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
        # OBS: hed tidligere ogsaa `vaegte` og overskrev dermed parameteren
        # med samme navn — den ægte fejl, maalt 18/10-2026 (IndexError).
        ord_vaegte = [1.0 if 0 < d < 1.0 else 0.25 for d in daekning_pr_ord]
        overlap = sum(
            d * v for d, v in zip(daekning_pr_ord, ord_vaegte)
        ) / sum(ord_vaegte)
    else:
        overlap = 0.5  # ingen indholdsord at måle på — neutralt

    return round(
        vaegte[0] * daekning + vaegte[1] * dansk
        + vaegte[2] * renhed + vaegte[3] * overlap,
        4,
    )


def bedste_kandidat(
    kandidater: list[dict[str, Any]],
    *,
    query: str,
    vaegte: tuple[float, float, float, float] = VAEGTE_STANDARD,
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
        s = score_resultater(liste, query=query, vaegte=vaegte)
        if s > bedst_score:
            bedst_score = s
            bedst = {**k, "score": s}
    return bedst
