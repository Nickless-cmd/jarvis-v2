"""Vagt: kvalitetsdommeren skal vælge den RIGTIGE søgekilde, ikke den største.

BAGGRUND (målt 18/10-2026). Vi har tre søgekilder og de er ikke lige gode til det
samme. Målt på fire queries: SerpAPI vandt dansk-specifik (danskindustri,
heyfunding, fondsmatch) hvor Tavily gav ukrainske grantsider; Tavily vandt
dansk-lokal (svendborg.dk) hvor SerpAPI gav "åbent hus" i Esbjerg og Aalborg.

Dommeren blev bygget forkert TO gange, og begge fejl er fanget her:

1. Første udgave talte et resultat som træf hvis BLOt ÉT query-ord optrådte i
   titlen. På "hvor ligger Svendborg Rådhus og hvornår har de åbent" gav det
   SerpAPI 1.0 for fem sider hvor ordet "åbent" stod i alle titler — emnet var
   helt fraværende. Den valgte den forkerte kilde med højeste karakter.
2. Anden udgave vægtede dækning 0,25, så SerpAPI's 9 resultater slog Tavilys 5
   på en query hvor alle ni var forkerte. Antal er ikke kvalitet.

Testene her låser begge rettelser: den forkerte liste må ikke kunne vinde, og
dækning må ikke kunne bære en dårlig liste alene.
"""
from __future__ import annotations

from core.services.search_quality import (
    bedste_kandidat,
    score_resultater,
)

# De FAKTISKE resultater fra målingen 18/10-2026 — ikke opdigtede.
TAVILY_DANSK_SPECIFIK = [
    {"title": "IT and AI Grants 2026", "url": "https://getgrant.ua/en/blog/it-and-ai-grants"},
    {"title": "AI Grants and Early-Stage Funding", "url": "https://www.sky9capital.com/blog/ai-grants"},
    {"title": "AI Startup Funding", "url": "https://startuptools.builduplabs.com/founder"},
    {"title": "Lean AI Startup Funding", "url": "https://www.hessian.ai/entrepreneurship"},
    {"title": "Danske Fragtmaend", "url": "https://karrierevejviser.dk/en/virksomheder/32910"},
]
SERPAPI_DANSK_SPECIFIK = [
    {"title": "Funding guide 12 typer startup funding i Danmark", "url": "https://www.danskindustri.dk/vi-radgiver-dig/ivarksatteri"},
    {"title": "Komplette guide til startup funding i Danmark", "url": "https://blog.heyfunding.dk/blog/den-komplette-guide"},
    {"title": "Ny AI-assistent for smaa virksomheder", "url": "https://www.danishlifesciencecluster.dk/nyheder/ny-ai-assistent"},
    {"title": "AI Aktier 2026", "url": "https://npinvestor.dk/aktier-for-begyndere/ai-aktier"},
    {"title": "Funding til startups i Danmark", "url": "https://www.fondsmatch.dk/fonde/startups"},
]
TAVILY_DANSK_LOKAL = [
    {"title": "Svendborg Kommune", "url": "https://www.svendborg.dk/borger/borgerservice/vielse"},
    {"title": "Historien om Svendborg Raadhus", "url": "https://www.svendborghistorie.dk/historier/ejendomshistorier/319"},
    {"title": "Svendborg Raadhus", "url": "https://www.kultunaut.dk/perl/sted/type-nynaut/nr-281327"},
    {"title": "Svendborg Raadhus", "url": "https://arnebirk.dk/project/svendborg-raadhus"},
    {"title": "Svendborg Kommune", "url": "https://www.facebook.com/Svendborg/posts/123"},
]
SERPAPI_DANSK_LOKAL = [
    {"title": "Aabent hus i Esbjerg", "url": "https://www.ucsyd.dk/uddannelse/besoeg-os/aabent-hus-i-esbjerg"},
    {"title": "Aabent Hospital i Aalborg", "url": "https://www.regioner.dk/aabenthospital/arrangementer-2026"},
    {"title": "Kan jeg overvaere aabent samraad", "url": "https://www.ft.dk/da/ofte-stillede-spoergsmaal"},
    {"title": "Aabent Hus Psykomotorisk", "url": "https://www.kp.dk/arrangementer/aabent-hus"},
    {"title": "Aabent Hus kandidatuddannelser", "url": "https://www.cbs.dk/events/aabent-hus-kandidatuddannelser-2027"},
]

Q_SPECIFIK = "hvilke danske virksomheder søger startup grants til AI i 2026"
Q_LOKAL = "hvor ligger Svendborg Rådhus og hvornår har de åbent"


def _kandidater(tavily: list, serpapi: list) -> list[dict]:
    return [
        {"provider": "tavily", "resultat": {"results": tavily, "status": "ok"}},
        {"provider": "serpapi", "resultat": {"results": serpapi, "status": "ok"}},
    ]


class TestDommerenVaelgerRigtigt:
    def test_dansk_specifik_skal_serpapi_vinde(self):
        """SerpAPI gav danske funding-kilder; Tavily gav udenlandske."""
        v = bedste_kandidat(_kandidater(TAVILY_DANSK_SPECIFIK, SERPAPI_DANSK_SPECIFIK),
                            query=Q_SPECIFIK)
        assert v is not None
        assert v["provider"] == "serpapi"

    def test_dansk_lokal_skal_tavily_vinde(self):
        """Den afgørende: SerpAPI gav 'åbent hus' i Esbjerg — emnet var Svendborg."""
        v = bedste_kandidat(_kandidater(TAVILY_DANSK_LOKAL, SERPAPI_DANSK_LOKAL),
                            query=Q_LOKAL)
        assert v is not None
        assert v["provider"] == "tavily"

    def test_et_hyppigt_ord_kan_ikke_baere_en_forkert_liste(self):
        """Fejl #1: 'åbent' stod i alle fem titler og gav listen topkarakter."""
        forkert = score_resultater(SERPAPI_DANSK_LOKAL, query=Q_LOKAL)
        rigtig = score_resultater(TAVILY_DANSK_LOKAL, query=Q_LOKAL)
        assert rigtig > forkert

    def test_flere_resultater_er_ikke_automatisk_bedre(self):
        """Fejl #2: 9 forkerte resultater må ikke slå 5 rigtige."""
        mange_forkerte = SERPAPI_DANSK_LOKAL + [
            {"title": "Aabent hus igen", "url": "https://www.ucsyd.dk/igen"},
            {"title": "Aabent hus atter", "url": "https://www.ucsyd.dk/atter"},
            {"title": "Aabent hus mere", "url": "https://www.ucsyd.dk/mere"},
            {"title": "Aabent hus sidst", "url": "https://www.ucsyd.dk/sidst"},
        ]
        assert score_resultater(TAVILY_DANSK_LOKAL, query=Q_LOKAL) > score_resultater(
            mange_forkerte, query=Q_LOKAL
        )


class TestKandidatValg:
    def test_fejlet_provider_kan_ikke_vinde(self):
        """En fejl der bærer resultater må ikke slå en der svarede rigtigt."""
        v = bedste_kandidat([
            {"provider": "doed", "resultat": {"status": "error",
                                              "results": TAVILY_DANSK_LOKAL}},
            {"provider": "levende", "resultat": {"status": "ok",
                                                 "results": SERPAPI_DANSK_LOKAL}},
        ], query=Q_LOKAL)
        assert v is not None
        assert v["provider"] == "levende"

    def test_ingen_resultater_giver_none(self):
        assert bedste_kandidat([], query=Q_LOKAL) is None
        assert bedste_kandidat(
            [{"provider": "tom", "resultat": {"results": [], "status": "ok"}}],
            query=Q_LOKAL,
        ) is None

    def test_tom_liste_scorer_nul(self):
        assert score_resultater([], query=Q_LOKAL) == 0.0

    def test_score_er_altid_mellem_nul_og_en(self):
        for liste in (TAVILY_DANSK_LOKAL, SERPAPI_DANSK_LOKAL,
                      TAVILY_DANSK_SPECIFIK, SERPAPI_DANSK_SPECIFIK):
            s = score_resultater(liste, query=Q_LOKAL)
            assert 0.0 <= s <= 1.0
