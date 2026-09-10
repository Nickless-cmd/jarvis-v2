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
    # TANKESTREG (sjette form, 10/9-2026): «`sti:19` — "citat"». Markdown-listens
    # naturlige form, og den claude-sonnet-5 brugte over broen. Separator-klassen
    # kendte kolon og parentes, saa TRE citater blev til ren eksistens-kontrol.
    #
    # Citationstegnet er PAAKRAEVET her. Uden det ville «`sti:19` — se ovenfor»
    # blive slaaet op som linjens indhold, og et rigtigt svar doemt `uenig`.
    # Det er samme regel som for det loese anker: en henvisning er ikke et citat.
    # BLOKCITAT UDEN KOLON (syvende form): «`sti:19`» og citatet paa linjen
    # under som `> ...`. Den sjette form havde et kolon efter linjenummeret,
    # og DET aabnede indholdet; her er `>` det eneste signal — men et staerkt
    # et, for blokcitat BETYDER citat.
    #
    # Hoejst ÉT linjeskift: ellers ville et blokcitat et helt afsnit laengere
    # nede blive laest som indholdet af linje 19.
    r"[`'\"\s]*(?:[—–-]\s*[\"'`«]\s*(.{0,160})|:\s*(.*)|\(\s*[\"'`]?(.{0,120})"
    r"|\n?[ \t]*>[ \t`'\"«]*(.{0,160}))?")
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
    # `[^\S\n]` = mellemrum MEN IKKE linjeskift. Foer matchede `\s` hen over
    # linjer, saa en sti i «Summary» blev parret med en henvisning laengere
    # nede — og agentens prosa derfra blev laest som citatet.
    r"[^\S\n]*(?:,|-|—)?[^\S\n]*"                          # valgfri adskiller
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
# ANKERET ER LOEST — henvisningen behoever ikke starte linjen. Den femte form
# er «- Jarvis: linje 19: ...» og «**Etableringsdato:** Linje 8: ...»: der
# staar altid et LABEL foran, saa `(?:^|\n)` matchede 0 af 5. Det er den mest
# naturlige form for en fil-laesnings-rapport, og igen var det den model der
# LAESER som skrev anderledes end den der gaetter.
_BAR_LINJE = re.compile(
    # Separatoren maa IKKE spise backticken: den er selve markoeren for at
    # det foelgende er et citat. Foerste udgave havde `` i klassen, saa
    # `linje 19: `Jarvis <...>`` kom ud som tekst med kun en AFSLUTTENDE
    # backtick — og citatet blev usynligt.
    r"(?:^|[\s*\-#>(\[])(?:line|linje|l\.)[\s]*(\d{1,6})[\s:*-]+(.{0,160})",
    re.IGNORECASE,
)

# HVAD ER ET CITAT, OG HVAD ER PROSA?
#
# Et loest anker alene giver en FALSK ANKLAGE. Agenten skrev «linje 64
# bekraefter moensteret: `Co-Authored-By: Claude` markerer Claude-arbejde» —
# og tog vi «resten af linjen», ville vi slaa hele saetningen op som citat,
# inklusive agentens egen kommentar, og doemme et RIGTIGT svar `uenig`.
#
# Derfor: vi efterproever kun det der praesenteres SOM et citat — backticks
# eller anfoerselstegn. Er der ingen, er paastanden en henvisning uden citat,
# og saa er «filen findes» alt vi kan sige. Det er ikke en svaekkelse: det er
# forskellen paa at efterproeve en paastand og at efterproeve en formulering.
# (Jarvis' syvende koersel — han afviste selv det loese anker som svar.)
# BLOKCITAT PAA NAESTE LINJE (Jarvis' ottende koersel, 10/9-2026). Den mest
# normale rapportform overhovedet:
#
#     - `docs/x.md:4`:
#       > `ground_truth: "Verified: ..."`
#
# Separatoren mellem linjenummer og indhold spiste linjeskiftet, saa `> ` kom
# med ind i det PAASTAAEDE citat — og dommen blev «linjen indeholder ikke
# \'> `ground_truth:\'» paa et svar hvor hvert linjenummer var rigtigt.
# Markoeren er formatering, ikke paastand.
_LEDENDE = re.compile(r"^[\s>*+#|-]+")

# «(gentaget linje 34 og 39)» er en OPREGNING af hvor det samme staar — ikke et
# citat af linje 34. «og 39)» blev slaaet op som linjens indhold og gav en
# falsk anklage. Den bare form («Linje 3: 2026-05-17») skal stadig doemmes, saa
# vi afviser kun det der ABNER med et bindeord.
_OPREGNING = re.compile(r"^(?:og|and|eller|or|samt|&|,|;)\b", re.IGNORECASE)

_CITAT = re.compile(r"`([^`]{2,120})`|\"([^\"]{2,120})\"|«([^»]{2,120})»")


_AFFLUGT = re.compile(r"\\([`*_\[\]()#+.!\\-])")


def _rens_hale(tekst: str) -> str:
    """Fjern citationstegn i halen — men aldrig en parentes der HOERER til.

    `const foo(bar)` skal ikke ende som `const foo(bar`.
    """
    t = str(tekst or "").strip()
    while t:
        # SKIFTEVIS: parentes-formen `("Etableret ...")` efterlader BEGGE
        # slags i halen. To loekker efter hinanden stopper efter den foerste
        # slags og lader den anden staa.
        if t[-1] in "\"'`":
            t = t[:-1].rstrip()
        elif t.endswith(")") and t.count("(") < t.count(")"):
            t = t[:-1].rstrip()
        else:
            break
    return t


def _laesninger(indhold: str) -> list[str]:
    """Hver rimelig laesning af en paastand, STAERKESTE foerst.

    Vaernet har hele dagen valgt ÉN laesning og anklaget naar den fejlede. Men
    en model der citerer rigtigt kan stadig skrive noget vi laeser forkert:
    indlejrede anfoerselstegn goer «laengste citat» tvetydigt, og i sonnets
    rapport valgte vi hans egen KOMMENTAR som citat og doemte et rigtigt svar
    `uenig`.

    Reglen er derfor ikke «find det rigtige citat» — den er: bekraeft paa den
    staerkeste laesning der HOLDER, og anklag foerst naar ingen af dem goer.
    """
    raa = str(indhold or "").strip()
    # `_citat_i` skal se den OPRINDELIGE tekst: renser vi halen foerst, fjerner
    # vi det afsluttende citationstegn den parrer paa, og «det laengste citat»
    # bliver til «hele teksten».
    citat = _rens_hale(_citat_i(raa))
    noegen = _rens_hale(_LEDENDE.sub("", raa).strip("`"))
    ud: list[str] = []
    for k in (citat, noegen, _kort(citat), _kort(noegen)):
        for v in (k, _AFFLUGT.sub(r"\1", k or "")):
            # MARKDOWN-FLUGT: citerer modellen en linje der selv indeholder en
            # backtick, skriver den \` — som markdown kraever. Citatet er
            # ordret rigtigt; kun en omvendt skraastreg skiller. To saadanne
            # blev doemt opdigt i en live-koersel.
            v = (v or "").strip()
            if len(v) >= 3 and v not in ud:
                ud.append(v)
    return ud


def _kort(kerne: str) -> str:
    """Den svageste rimelige laesning af et citat.

    Modellen klipper: gemini afsluttede sit citat midt i «(72». Kraever vi hele
    strengen, anklager vi et RIGTIGT svar for at have opdigtet den. Derfor
    doemmes en paastand foerst paa hele citatet — og kun hvis DEN OGSAA fejler
    paa dette forkortede, bliver det til en anklage.
    """
    k = str(kerne or "").split("(")[0].strip()
    return k if len(k) >= 8 else str(kerne or "")[:24].strip()


def _citat_i(tekst: str) -> str:
    """Citatet hvis der ER et — ellers hele teksten.

    Reglen er ikke «kun citater»; den er ER DER ET CITAT, GAELDER KUN DET.
    Foerste udgave krævede citationstegn og mistede dermed de aeldre former,
    hvor modellen skriver indholdet nogent: «sub/x.md line 3: Etableret
    2026-05-17». Dér ER teksten paastanden.

    Men skriver den «linje 64 bekraefter moensteret: `X` markerer Y», er `X`
    paastanden og resten kommentar. Tages hele saetningen, doemmes et RIGTIGT
    svar `uenig` — en falsk anklage i stedet for et overset svar.
    """
    t = _LEDENDE.sub("", str(tekst or "").strip())
    # DET LAENGSTE citat, ikke det foerste. En tabelraekke citeres som
    #   > `| `docs/x.md` | faerdig | Verified: ...`
    # hvor det FOERSTE backtick-par er `| ` — to tegn uden indhold. Tog vi det,
    # blev en meningsloes streng "bekraeftet" og talt som belaeg.
    kandidater = [g.strip() for m in _CITAT.finditer(t)
                  for g in m.groups() if g and len(g.strip()) >= 4]
    if kandidater:
        return max(kandidater, key=len)
    return t

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


# Opslagene ligger paa AFSLUTNINGS-stien — `tjek_rapport` koeres synkront foer
# `update_agent_run(status="completed")` — og hvert bro-kald har sin egen
# timeout (grep op til 65 s). Tolv paastande mod en blackhole-bro kunne holde
# barnets run i kvarterer, paa netop det sted hvor kommentaren advarer mod at
# lade runnet staa evigt som koerende.
#
# Svarer de foerste opslag ikke, svarer resten heller ikke. Saa holder vi op.
_UAFGJORT_LOFT = 2


def _bro_tavs(ud: dict[str, object]) -> bool:
    """Har broen tiet saa mange gange i traek at det ikke nytter at spoerge?"""
    return (int(ud.get("uafgjort") or 0) >= _UAFGJORT_LOFT
            and int(ud.get("kontrolleret") or 0) == 0)


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
    # `uafgjort`: broen svarede ikke. FOER blev det kastet vaek med et bart
    # `continue`, saa en DOED bro og en REN rapport gav byte-identiske svar —
    # begge `kontrolleret: 0`. Informationen fandtes paa fejlstedet og forsvandt
    # foer nogen kunne se den. (Jarvis' fund, 10/9-2026.)
    ud: dict[str, object] = {"kontrolleret": 0, "fejl": [], "holder": True,
                             "uafgjort": 0}
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
             # RAA FOER: hver nyere gren adopterede `_citat_i`, den
             # oprindelige aldrig. Samme fejl som bro-grenen nedenfor — «hvad
             # er paastanden» var skrevet TRE steder og drev fra hinanden.
             # gr. 3 = efter tankestreg, 4 = efter kolon, 5 = i parentes
             # RAAT VIDERE: reduktionen sker ÉT sted, ved tjekket. Skete den
             # her, saa `_laesninger` aldrig den oprindelige tekst og kunne
             # ikke falde tilbage naar citat-valget var forkert.
             # gr. 3 tankestreg, 4 kolon, 5 parentes, 6 blokcitat
             (m.group(3) or m.group(4) or m.group(5) or m.group(6) or "").strip())
            for m in _STI_LINJE.finditer(t)
        ]
        # DEDUP PAA (sti, linje) BEHOLDT DEN FOERSTE LAESNING — og `_STI_LINJE`
        # koeres foerst, saa en bar kildehenvisning («Kilde: `x.md:19`») slog
        # citatet ihjel («- Linje 19: `| Jarvis | ... |`»). I en live-koersel
        # blev alle SEKS citater kasseret saadan: `kun-eksistens` paa et svar
        # der citerede hver eneste linje.
        #
        # Samme figur som `_laesninger`: vaelg den RIGESTE laesning, ikke den
        # foerste vi stoedte paa.
        _paastande = [list(x) for x in _paastande]
        _idx: dict[tuple[str, int], int] = {}
        for _i, (_a, _b, _) in enumerate(_paastande):
            _idx.setdefault((_a, int(_b)), _i)

        def _tilfoej(sti_: str, nr_: int, indhold_: str = "") -> None:
            _n = (sti_, int(nr_))
            _i = _idx.get(_n)
            if _i is None:
                _idx[_n] = len(_paastande)
                _paastande.append([sti_, int(nr_), indhold_])
            elif len(indhold_ or "") > len(_paastande[_i][2] or ""):
                _paastande[_i][2] = indhold_
        for m in _STI_LINJE_PROSA.finditer(t):
            _tilfoej(m.group(1), int(m.group(2)), (m.group(3) or "").strip())
        for m in _LINJE_SO_STI.finditer(t):
            # I DENNE FORM STAAR INDHOLDET FOERAN:
            #   «Etableret 2026-05-17 (linje 11, fil docs/x.md)»
            # Uden det ville vi kun tjekke at filen findes — og praecis
            # DET var mistrals fejl: indholdet var rigtigt, linjenummeret
            # opdigtet (11 hvor der staar 8). Et vaern der kun ser filen,
            # ser ikke den fejl.
            _foran = t[max(0, m.start() - 90):m.start()]
            _foran = _foran.rsplit("\n", 1)[-1].strip(" \t-*•`\"'(")
            _tilfoej(m.group(2), int(m.group(1)), _foran[-80:])

        for m in _LINJE_I_STI.finditer(t):
            _tilfoej(m.group(2), int(m.group(1)), "")

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
            # KUN citatet — ikke resten af linjen. Se `_CITAT`.
            _kerne = (m.group(2) or "").strip()
            if _OPREGNING.match(_kerne):
                _kerne = ""       # henvisning til andre linjer, ikke indhold
            _tilfoej(sti, int(m.group(1)), _kerne)

        for sti, nr, indhold in _paastande:
            if sti.rsplit(".", 1)[-1].lower() not in _KENDTE:
                continue
            set_stier.add(sti)
            if _bro_tavs(ud):
                break          # broen svarer ikke — hold op med at spoerge
            _findes_den = _slaa_op(sti)
            if _findes_den is None:
                # Uafgjort: hverken fund eller fejl — men IKKE ingenting.
                ud["uafgjort"] = int(ud["uafgjort"]) + 1
                continue
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
                # FOER: `.strip("`").split("(")[0]` — en TREDJE udgave af
                # «hvad er paastanden», som ingen af dagens lektier naaede.
                # Den gav bl.a. \'> `ground_truth: "Verified:\' som anklage, og
                # den afkortede ethvert citat ved foerste parentes.
                _kand = _laesninger(indhold)
                if not _kand:
                    continue
                passer, kerne = None, _kand[0]
                for k in _kand:
                    try:
                        svar_k = linje_fn(sti, nr, k)
                    except Exception:
                        svar_k = None
                    if svar_k is True:
                        passer, kerne = True, k
                        break
                    if svar_k is False and passer is None:
                        passer, kerne = False, k
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
            # FOER stod optaellingen HER — foer sammenligningen. En paastand
            # der FEJLEDE blev derfor talt baade som belaeg og som fejl, og
            # `indhold_bekraeftet` laeste som bekraeftelse uden at vaere det.
            #
            # Og udtraekningen var en FJERDE udgave af «hvad er paastanden».
            # Fire steder, fire regler; kun de to nyeste kendte dagens lektier.
            _kand = _laesninger(indhold)
            if not _kand:
                continue
            _linje = linjer[nr - 1]
            _holdt = next((k for k in _kand if k in _linje), None)
            if _holdt is None:
                fejl.append(f"{sti}:{nr}: linjen indeholder ikke {_kand[0]!r}")
            else:
                ud["indhold_bekraeftet"] = int(ud.get("indhold_bekraeftet") or 0) + 1

        for m in _STI.finditer(t):
            sti = m.group(1)
            if sti in set_stier or sti.rsplit(".", 1)[-1].lower() not in _KENDTE:
                continue
            set_stier.add(sti)
            if _bro_tavs(ud):
                break
            _findes_den = _slaa_op(sti)
            if _findes_den is None:
                ud["uafgjort"] = int(ud["uafgjort"]) + 1
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
