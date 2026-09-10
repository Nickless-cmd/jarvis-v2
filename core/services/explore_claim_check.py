"""Tjek explore-agentens påstande mod virkeligheden.

Bjørn 7/9-2026: «burde der ikke være et værn i explore der kan checke
påstande, og rotere model hvis en påstand ikke holder?»

Ja — og det er stærkere end alt jeg forsøgte forinden. Jeg brugte dagen på at
forudsige om en model VILLE lyve (syntetiske prøver, gentagne kørsler,
opdigt-detektor). `copilot-free/gpt-4.1` bestod dem alle og løj i produktion
alligevel. Men explore's påstande er af en helt særlig slags: de er
**efterprøvelige**. En filsti findes eller findes ikke. Linje 12 indeholder
det den siger, eller gør ikke.

Så vi behøver ikke gætte på modellen. Vi kan slå svaret op.

## Hvad der tjekkes

1. **Filstier** — hver nævnt sti skal findes. Fangede
   `src/jarvis/providers/provider_router.py`, som aldrig har eksisteret.
2. **sti:linje:indhold** — linjen skal findes OG bære indholdet. Fangede
   `provider_router.py:12:def route_provider_request`, hvor linje 12 er noget
   helt andet.

## Hvad der IKKE tjekkes

Prosa. En påstand som «nøglerne læses dynamisk» kan ikke slås op, og et værn
der forsøgte ville afvise gyldige svar. Vi tjekker kun det der ER
efterprøveligt — og et svar uden efterprøvelige påstande får ingen dom.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# `sti:linje:indhold` — den form `search` selv returnerer, og dermed den form
# agenten citerer i.
# `[`'"\s]*` mellem linjenummer og indhold: markdown-formen `sti:12`: indhold
# har en BACKTICK efter tallet, saa indholdet blev aldrig fanget — og
# linje-tjekket aldrig kaldt. Kun filens eksistens blev efterproevet, og en
# ren fabrikation kom tilbage som «verificeret».
#
# Det er den mest naturlige maade at citere paa, saa hullet var ikke en
# sjaelden kant: det var normalvejen. (Jarvis, 10/9-2026, anden explore-test.)
# `[`'"\s(]*` og et valgfrit `:` ELLER en parentes foer indholdet.
#
# Den aerlige model skriver `sti:8 ("**Etableret:** 2026-05-17")` — citatet i
# en PARENTES, uden kolon. Foer blev indholdet ikke fanget, saa kun filens
# eksistens blev efterproevet, og dommen blev `kun-eksistens` paa et svar der
# faktisk var rigtigt hele vejen.
#
# Det er fjerde citatform paa én dag, og de har alle samme form: den model der
# LAESER skriver anderledes end den der gaetter, og vaernet kendte gaetterens
# format bedst.
_STI_LINJE = re.compile(
    r"(?:^|[\s`(\[])(/?[\w./-]+\.[A-Za-z0-9_]{1,6}):(\d{1,6})"
    r"[`'\"\s]*(?::\s*(.*)|\(\s*[\"'`]?(.{0,120}))?")
# Bare filstier med mappe i — et bart "config.py" er for tvetydigt til at dømme.
# `/?` foran: ABSOLUTTE stier blev slet ikke matchet, saa en workstation-rapport
# — der naturligt skriver `/home/bs/projekt/src/main.ts` — gav NUL kontrollerede
# paastande. Vaernet ville have vaeret koblet paa og alligevel blindt.
# URL'er rammes ikke: `https:` fejler paa kolon, og `//host` fejler paa den
# anden skraastreg.
_STI = re.compile(r"(?:^|[\s`(\[])(/?(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9_]{1,6})")

# PROSA-FORMEN (Jarvis' fund, 10/9-2026). `_STI_LINJE` kraever `sti:linje`, men
# en model skriver lige saa gerne «simple_tools_explore.py line 8: _MAKS = 3»
# eller «linje 8 i core/x.py». Da fangede kun den bare-sti-regex den, saa KUN
# filens eksistens blev efterproevet — og et OPDIGTET tal paa en aegte fil
# passerede som «holder».
#
# Det er den farligste form, fordi den ser mest overbevisende ud: en rigtig
# sti, et praecist linjenummer, og en vaerdi ingen har slaaet op.
_STI_LINJE_PROSA = re.compile(
    r"(?:^|[\s`(\[])(/?[\w./-]+\.[A-Za-z0-9_]{1,6})"      # stien
    r"[\s`]*(?:,|-|—)?[\s`]*"                              # valgfri adskiller
    r"(?:line|linje|l\.)[\s`]*(\d{1,6})"                   # «line 8» / «linje 8»
    r"[\s`:*-]*(.{0,120})",                                # og hvad der paastaas
    re.IGNORECASE,
)
# STIEN EFTER TALLET: «(linje 11, fil core/x.py)».
#
# Det er den form MISTRAL brugte — altsaa den model der faktisk LAESTE filen.
# Den aerlige models citatform var usynlig for vaernet, mens den fabrikerende
# models form var daekket. Det er den vaerste vej rundt: vi efterproever den
# der lyver og ikke den der laeser. (Jarvis' fjerde koersel.)
_LINJE_SO_STI = re.compile(
    r"(?:line|linje)[\s`]*(\d{1,6})[\s,;]*(?:i|in|fil|file|of|af)[\s:`]*"
    r"(/?[\w./-]+\.[A-Za-z0-9_]{1,6})",
    re.IGNORECASE,
)

# BAR LINJE-HENVISNING: «Linje 12: indhold» UDEN sti paa samme linje.
#
# Det er den naturlige form for en fil-laesnings-rapport: filen naevnes ÉN
# gang, og derefter listes linjerne. Alle de andre moenstre kraever en sti
# lige ved siden af tallet, saa af otte citater blev ÉT efterproevet.
#
# Jarvis kaldte det «vaernet laeser kun engelsk». Det er ikke aarsagen —
# `linje` er med, og regexen er case-insensitiv; `x.md, Linje 4: tekst`
# doemmes korrekt. Aarsagen er den MANGLENDE STI. Symptomet var rigtigt, og
# det er det der taeller: uden hans maaling havde jeg ikke set formen.
_BAR_LINJE = re.compile(
    r"(?:^|\n)[\s*\-#>]*(?:line|linje|l\.)[\s`]*(\d{1,6})[\s`:*-]+(.{0,120})",
    re.IGNORECASE,
)

# Den omvendte ordstilling: «linje 8 i core/x.py».
_LINJE_I_STI = re.compile(
    r"(?:line|linje|l\.)[\s`]*(\d{1,6})[\s`]*(?:i|in|of|af)[\s`]*"
    r"(/?[\w./-]+\.[A-Za-z0-9_]{1,6})",
    re.IGNORECASE,
)

# Endelser vi kan udtale os om. En sti til noget der ikke er en kildefil
# (fx en URL-agtig streng) skal ikke give falske anklager.
_KENDTE = frozenset({"py", "ts", "tsx", "js", "json", "md", "toml", "yaml", "yml",
                     "sh", "kt", "sql", "cfg", "ini", "txt", "gradle"})


def _rod() -> Path:
    try:
        from core.tools.simple_tools import PROJECT_ROOT
        return Path(str(PROJECT_ROOT))
    except Exception:
        return Path.cwd()


def _findes(sti: str, rod: Path) -> bool:
    p = Path(sti)
    if p.is_absolute():
        return p.exists()
    return (rod / sti).exists()


def tjek_paastande(svar: str, *, rod: Path | None = None,
                   findes_fn=None, linje_fn=None) -> dict[str, object]:
    """Slå svarets efterprøvelige påstande op. Kaster aldrig.

    Returnerer {"kontrolleret": n, "fejl": [...], "holder": bool}. Uden
    efterprøvelige påstande er `kontrolleret` 0 og `holder` True — vi dømmer
    ikke et svar vi ikke kan efterprøve.

    `findes_fn(sti) -> bool | None` slår stier op ET ANDET STED end containerens
    filsystem. Den findes fordi en workstation-explore undersøger BJØRNS
    maskine: `_rod()` peger på containerens repo, så et opslag her ville flage
    HVER eneste sti som opdigtet. Derfor var værnet slået helt fra for
    workstation — og det var rigtigt, men det efterlod den sti hvor en
    fabrikeret rapport koster mest, helt uden værn.

    `None` fra `findes_fn` betyder «kunne ikke afgøres» og tæller hverken som
    fund eller fejl. Et værn der gætter er værre end intet: det ville anklage
    ægte filer for ikke at findes.

    `linje_fn(sti, nr, fragment) -> bool | None` efterprøver et CITAT et andet
    sted. Jarvis foreslog den: `operator_grep` giver fil, linjenummer og tekst
    i ét kald. Målt 10/9-2026 koster et grep 0,08 s — det SAMME som
    eksistens-tjekket, og med mere i svaret. Uden den ville et citat over broen
    kun kunne bekræftes for at filen findes, ikke for at linjen siger det der
    påstås.
    """
    ud: dict[str, object] = {"kontrolleret": 0, "fejl": [], "holder": True}
    try:
        t = str(svar or "")
        if not t.strip():
            return ud
        r = rod or _rod()
        fejl: list[str] = []
        set_stier: set[str] = set()

        def _slaa_op(sti: str) -> bool | None:
            if findes_fn is None:
                return _findes(sti, r)
            try:
                return findes_fn(sti)
            except Exception:
                return None

        # Saml paastandene fra ALLE tre former foerst, saa behandlingen er ens.
        # Foer saa loekken kun `sti:linje:indhold`, og en prosa-formuleret
        # paastand fik derfor kun sin FIL efterproevet — aldrig sin vaerdi.
        _paastande: list[tuple[str, int, str]] = [
            (m.group(1), int(m.group(2)),
             # gruppe 3 = efter kolon, gruppe 4 = inde i parentesen
             ((m.group(3) or m.group(4) or "").strip().rstrip(')"\'`')))
            for m in _STI_LINJE.finditer(t)
        ]
        _set: set[tuple[str, int]] = {(a, b) for a, b, _ in _paastande}
        for m in _STI_LINJE_PROSA.finditer(t):
            _n = (m.group(1), int(m.group(2)))
            if _n not in _set:
                _set.add(_n)
                _paastande.append((m.group(1), int(m.group(2)),
                                   (m.group(3) or "").strip()))
        for m in _LINJE_SO_STI.finditer(t):
            _n = (m.group(2), int(m.group(1)))
            if _n not in _set:
                _set.add(_n)
                # I DENNE FORM STAAR INDHOLDET FOERAN:
                #   «Etableret 2026-05-17 (linje 11, fil docs/x.md)»
                # Uden det ville vi kun tjekke at filen findes — og praecis
                # DET var mistrals fejl: indholdet var rigtigt, linjenummeret
                # opdigtet (11 hvor der staar 8). Et vaern der kun ser filen,
                # ser ikke den fejl.
                _foran = t[max(0, m.start() - 90):m.start()]
                _foran = _foran.rsplit("\n", 1)[-1].strip(" \t-*•`\"'(")
                _paastande.append((m.group(2), int(m.group(1)), _foran[-80:]))

        for m in _LINJE_I_STI.finditer(t):
            _n = (m.group(2), int(m.group(1)))
            if _n not in _set:
                _set.add(_n)
                _paastande.append((m.group(2), int(m.group(1)), ""))

        # Bare linje-henvisninger knyttes til den SENEST naevnte fil. En
        # rapport skriver filen én gang og lister saa linjerne; laeser man
        # hver linje for sig, er der ingen sti at slaa op i.
        #
        # Kun BAGUD: en linje-henvisning hoerer til den fil der allerede er
        # naevnt, aldrig til en der kommer senere. Ellers ville et citat blive
        # tilskrevet en fil rapporten ikke havde aabnet endnu.
        _stier_i_orden = [(m.start(), m.group(1)) for m in _STI.finditer(t)]
        _stier_i_orden += [(m.start(), m.group(1)) for m in _STI_LINJE.finditer(t)]
        _stier_i_orden.sort()
        for m in _BAR_LINJE.finditer(t):
            _foran = [sti for pos, sti in _stier_i_orden if pos < m.start()]
            if not _foran:
                continue                  # ingen fil naevnt endnu — intet at slaa op i
            sti = _foran[-1]
            _n = (sti, int(m.group(1)))
            if _n not in _set:
                _set.add(_n)
                _paastande.append((sti, int(m.group(1)),
                                   (m.group(2) or "").strip()))

        for sti, nr, indhold in _paastande:
            if sti.rsplit(".", 1)[-1].lower() not in _KENDTE:
                continue
            set_stier.add(sti)
            _findes_den = _slaa_op(sti)
            if _findes_den is None:
                continue                      # uafgjort — hverken fund eller fejl
            ud["kontrolleret"] = int(ud["kontrolleret"]) + 1
            if not _findes_den:
                fejl.append(f"{sti}: filen findes ikke")
                continue
            if not indhold:
                continue
            if findes_fn is not None:
                # Over broen: ét grep giver baade linjenummer og tekst.
                if linje_fn is None:
                    continue
                kerne = indhold.strip().strip("`").split("(")[0].strip()
                if not kerne:
                    continue
                try:
                    passer = linje_fn(sti, nr, kerne)
                except Exception:
                    passer = None
                if passer is False:
                    fejl.append(f"{sti}:{nr}: linjen indeholder ikke {kerne!r}")
                elif passer is True:
                    ud["indhold_bekraeftet"] = int(ud.get("indhold_bekraeftet") or 0) + 1
                continue
            try:
                linjer = (r / sti if not Path(sti).is_absolute() else Path(sti)).read_text(
                    encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            if nr < 1 or nr > len(linjer):
                fejl.append(f"{sti}:{nr}: filen har kun {len(linjer)} linjer")
                continue
            ud["indhold_bekraeftet"] = int(ud.get("indhold_bekraeftet") or 0) + 1
            # Sammenlign på et NØGENT fragment: modellen omskriver ofte
            # whitespace og klipper linjen. Vi kræver at det den citerer,
            # findes i linjen — ikke at strengene er identiske.
            kerne = indhold.strip().strip("`").split("(")[0].strip()
            if kerne and kerne not in linjer[nr - 1]:
                fejl.append(f"{sti}:{nr}: linjen indeholder ikke {kerne!r}")

        for m in _STI.finditer(t):
            sti = m.group(1)
            if sti in set_stier or sti.rsplit(".", 1)[-1].lower() not in _KENDTE:
                continue
            set_stier.add(sti)
            _findes_den = _slaa_op(sti)
            if _findes_den is None:
                continue
            ud["kontrolleret"] = int(ud["kontrolleret"]) + 1
            if not _findes_den:
                fejl.append(f"{sti}: filen findes ikke")

        ud["fejl"] = fejl
        ud["holder"] = not fejl
        # BEVIS ER IKKE DET SAMME SOM ENIGHED (Jarvis' fund, 10/9-2026).
        #
        # `holder = not fejl` er sandt naar der INGEN fejl er — ogsaa naar der
        # ingenting blev efterproevet. «Vi doemte intet» laeste derfor identisk
        # med «vi verificerede alt», og en explore-rapport uden en eneste
        # kontrolleret paastand kom tilbage som et rent `status: ok`.
        #
        # Det er PRAECIS den sammenblanding jeg selv navngav og rettede i fase
        # 11 for ledgeren, seks timer foer han fandt den her. Samme ordforraad
        # med vilje — huset maa ikke have to sprog for samme skelnen.
        # EKSISTENS ER IKKE VERIFIKATION (Jarvis, anden explore-test).
        #
        # Foer taalte «filen findes» som en bekraeftet paastand, saa fire
        # fabrikerede citater paa en AEGTE fil kom tilbage som
        # «4 paastand(e) slaaet op og bekraeftet». Det er en falsk positiv, og
        # den er vaerre end den falske negativ jeg lukkede samme formiddag:
        # dén sagde «vi doemte intet», denne siger «vi verificerede alt» om
        # ren opdigt.
        #
        # `verificeret` kraever nu at MINDST ÉN paastand er bekraeftet paa sit
        # INDHOLD. Er kun filer slaaet op, hedder det hvad det er.
        _sub = int(ud.get("indhold_bekraeftet") or 0)
        ud["bevis"] = ("uenig" if fejl
                       else ("verificeret" if _sub > 0
                             else ("kun-eksistens" if int(ud["kontrolleret"]) > 0
                                   else "intet-bevis")))
    except Exception:
        logger.debug("claim-check væltede — dømmer ikke", exc_info=True)
        # Et vaeltet tjek har heller ikke verificeret noget.
        return {"kontrolleret": 0, "indhold_bekraeftet": 0, "fejl": [],
                "holder": True, "bevis": "intet-bevis"}
    return ud
