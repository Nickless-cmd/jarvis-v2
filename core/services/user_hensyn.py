"""Bruger-hensyn — handlingsrelevante hensyn med VARIG og SITUATIONEL levetid.

Baggrund (målt 25/10-2026, Bjørn). Tre målinger lå til grund:

* ``USER.md`` er 103.886 tegn. Prompten injicerer ``## Kerne`` (48 linjer) fast;
  ``## Lært`` (477 linjer) læses relevans-udvalgt med 3 linjer / 700 tegn pr. tur
  og kræver 34 % leksikalsk overlap.
* ``user_model_daemon`` kører hvert 10. minut, men måler kun **stil**
  (``terse``/``normal``/``verbose``, spørgelyst). Indhold findes ikke som kategori.
* Resultatet: «jeg er vegetar» er en biografisk note der forsvinder i mængden, i
  stedet for et hensyn der styrer næste svar.

Denne fil dækker hullet — og kun det. Den måler ikke stil (det gør
``user_model_daemon``), og den skriver ikke til ``## Lært`` (det gør
konsolideringen). Den udleder **hensyn** og giver dem en levetid.

Fire regler styrer designet, alle fra Bjørns krav:

1. **Hensyn, ikke fakta.** «vegetar» bliver til «foreslå ikke kød». Formen er en
   handling eller undladelse der kan efterleves — ikke en note om et menneske.
2. **Hver linje bærer sin egen grænse.** «foreslå ikke kød — medmindre han selv
   spørger om madvaner». Et absolut forbud uden udgang er GPT-fejlen
   (brain-note ``brn_01M5J42TEHFNTF6YGG79S9XBMZ``). En kandidat uden grænse
   forkastes, uanset hvor rigtig den ellers er.
3. **To levetider.** VARIGT har intet udløb og kan kun fjernes ved at Bjørn siger
   det. SITUATIONELT har halveringstid og falmer af sig selv, så «ikke nu, jeg er
   træt» ikke bliver en livsregel. Standard er situationel; forfremmelse kræver
   gentagelse eller en eksplicit varig-markør.
4. **Der skal være en udgang.** Et hensyn der er injiceret ``N_TURE_UDEN_EFFEKT``
   gange uden at have ramt et svar er støj og fjernes. Uden den regel vokser
   sektionen til en væg — det er præcis den «samme besked hver gang» Bjørn kalder
   tom.

Falske positiver er dyrere end falske negativer: et hensyn der aldrig skulle have
været der styrer samtalen forkert. Derfor er kandidat-genereringen konservativ
(kræver en handlingsmarkør), og en modelfejl forkaster kandidaten frem for at
gætte.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)

# ── Konstanter ──────────────────────────────────────────────────────────────

KATEGORIER = ("kost", "foelelser", "relationer", "tid", "arbejdsform", "sprog")

VARIG = "varig"
SITUATIONEL = "situationel"

AKTIV = "aktiv"
STOEJ = "stoej"
UDLOEBET = "udloebet"

#: Halveringstid for et situationelt hensyn. 14 dage: en dagsform holder et par
#: uger, en livsregel gør ikke. Forfremmelse — ikke længere levetid — er vejen til
#: at noget bliver varigt.
HALVERINGSTID_DAGE = 14.0

#: Under denne vægt er et situationelt hensyn ikke længere værd at bruge plads på.
VAEGT_FLOOR = 0.25

#: Så mange injektioner uden evidens før hensynet erklæres støj.
N_TURE_UDEN_EFFEKT = 40

#: Et hensyn skal have set mindst så mange forekomster før det bliver varigt.
FORFREMNING_GENTAGELSER = 2

#: Kun kandidatlinjer af en vis længde kan bære et reelt hensyn.
_MIN_KANDIDAT_TEGN = 18

#: Hvor tit baggrunds-udledningen må køre. 60 min — profilen ændrer sig når
#: Bjørn skriver noget nyt, ikke hvert tiende minut. Dedup'en gør kørslen billig,
#: men et modelkald er stadig et modelkald.
CADENCE_MINUTTER = 60

#: Sidste kørsel i denne proces. Ikke persistent: efter en genstart kører den
#: igen, hvilket er harmløst fordi allerede vurderede linjer springes over.
_last_tick_at: datetime | None = None

_STATE_KEY = "user_hensyn"
_BEHANDLET_KEY = "user_hensyn.behandlet"

# Handlingsmarkører: negation eller imperativ. En linje UDEN en af dem er en
# biografisk fakta («Bor i Svendborg»), ikke et hensyn — og bliver ikke kandidat.
_HANDLING_RE = re.compile(
    r"\b(?:ikke|aldrig|undgå|undlad|nævn|skriv|brug|spørg|kør|ring|fortæl"
    r"|forstyr|send|vis|husk|luk|åbn|start|stop|vent|spring)\b",
    re.IGNORECASE,
)

# Eksplicitte varig-markører. Står de i kildelinjen, er hensynet varigt fra start.
_VARIG_RE = re.compile(
    r"\b(?:altid|hele (?:mit|hans) liv|princip|generelt|fremover|for evigt"
    r"|altid været|livsregel)\b",
    re.IGNORECASE,
)

# Kategorisignaler. Bruges til at give kandidaten en kategori — ikke til at
# afgøre om den ER et hensyn (det gør handlingsmarkøren + modellen).
_KATEGORI_SIGNALER: dict[str, re.Pattern[str]] = {
    "kost": re.compile(
        r"\b(?:vegetar|vegan|kød|mad|spiser|allergi|tåler|kost|måltid)\b",
        re.IGNORECASE,
    ),
    "foelelser": re.compile(
        r"\b(?:ked af|sårbar|svært ved|følsom|græder|sorg|angst|skam"
        r"|taler ikke om|rør ikke ved)\b",
        re.IGNORECASE,
    ),
    "relationer": re.compile(
        r"\b(?:flæng|foran|privat|familie|mor|far|bror|søster|datter|ven"
        r"|michelle|mikkel|rune|lotte|saselin|liva)\b",
        re.IGNORECASE,
    ),
    "tid": re.compile(
        r"\b(?:nat|morgen|aften|weekend|ferie|sove|træt|pause|tid|klokken"
        r"|forstyr)\b",
        re.IGNORECASE,
    ),
    "arbejdsform": re.compile(
        r"\b(?:godkend|bekræft|spørg|autorisation|go ahead|kør|commit|plan)\b",
        re.IGNORECASE,
    ),
    "sprog": re.compile(
        r"\b(?:dansk|engelsk|tone|formulering|ordet|fraser|emojis?|form)\b",
        re.IGNORECASE,
    ),
}

#: Ord der afslører at et svar FREMSÆTTER et forbudt emne frem for at omtale det.
#: Både «du kunne» og «kunne du» — dansk bruger begge, og den første er den
#: almindelige (målt 25/10-2026: mønstret dækkede kun den anden, så et reelt brud
#: blev usynligt).
_FORESLAA_RE = re.compile(
    r"\b(?:(?:du|vi|man) (?:kunne|kan|bør|skal)"
    r"|kunne (?:du|vi|man)"
    r"|hvad med|prøv|anbefaler|anbefal|foreslår|foreslå)\b",
    re.IGNORECASE,
)

#: Kategori → de substantiver et brud kan måles på. Kun kost er entydig nok til
#: at en deterministisk detektor giver mening; resten lever på injiceret-tællingen
#: og på en eksplicit markering.
_BRUD_NOEGLEORD: dict[str, tuple[str, ...]] = {
    "kost": ("kød", "flæsk", "bacon", "kylling", "oksekød", "svin", "fisk"),
}


# ── Datamodel ───────────────────────────────────────────────────────────────


@dataclass
class Hensyn:
    """Ét handlingsrelevant hensyn med levetid, grænse og effekt-tælling.

    ``regel`` er undladelsen/handlingen («foreslå ikke kød»); ``graense`` er den
    betingelse hvor den viger («medmindre han selv spørger om madvaner»). Begge
    er påkrævet — en regel uden grænse er et absolut forbud, og dem vil vi ikke
    have.
    """

    hensyn_id: str
    kategori: str
    regel: str
    graense: str
    levetid: str = SITUATIONEL
    kilde: str = ""
    oprettet: str = ""
    sidst_set: str = ""
    forekomster: int = 1
    injiceret: int = 0
    ramte: int = 0
    brud: int = 0
    status: str = AKTIV
    ekstra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Hensyn:
        kendte = {f for f in cls.__dataclass_fields__ if f != "ekstra"}
        felter = {k: v for k, v in (data or {}).items() if k in kendte}
        ekstra = {k: v for k, v in (data or {}).items() if k not in kendte}
        return cls(**felter, ekstra=ekstra)


# ── Persistens ──────────────────────────────────────────────────────────────


def _load() -> list[Hensyn]:
    """Læs de gemte hensyn. Tom liste hvis intet er gemt — aldrig en fejl."""
    try:
        from core.runtime.state_store import load_json

        raw = load_json(_STATE_KEY, {"items": []}) or {}
        items = raw.get("items") if isinstance(raw, dict) else raw
        return [Hensyn.from_dict(row) for row in (items or []) if isinstance(row, dict)]
    except Exception as exc:  # ikke-tavs: en læsefejl må kunne ses i loggen
        logger.debug("user_hensyn: kunne ikke læse state: %s", exc)
        return []


def _save(items: list[Hensyn]) -> None:
    try:
        from core.runtime.state_store import save_json

        save_json(_STATE_KEY, {"items": [h.to_dict() for h in items]})
    except Exception as exc:
        logger.debug("user_hensyn: kunne ikke gemme state: %s", exc)


# ── Kandidat-generering (deterministisk, konservativ) ────────────────────────


def _normaliser(tekst: str) -> str:
    return " ".join(str(tekst or "").split()).strip()


def _nøgle(regel: str) -> str:
    """Sammenligningsnøgle for to formuleringer af samme hensyn."""
    body = _normaliser(regel).lower()
    body = re.sub(r"[^0-9a-zæøå ]+", " ", body)
    return " ".join(body.split())[:120]


def kandidat_kategori(linje: str) -> str | None:
    """Kategori for en kandidatlinje — ``None`` når linjen ikke er en kandidat.

    Konservativ med vilje: kræver en handlingsmarkør OG et kategorisignal. En
    biografisk note som «Bor i Svendborg» har ingen af delene og bliver aldrig
    kandidat.
    """
    tekst = _normaliser(linje)
    if len(tekst) < _MIN_KANDIDAT_TEGN:
        return None
    if not _HANDLING_RE.search(tekst):
        return None
    bedst: tuple[int, str] | None = None
    for kategori, moenster in _KATEGORI_SIGNALER.items():
        hits = len(moenster.findall(tekst))
        if hits and (bedst is None or hits > bedst[0]):
            bedst = (hits, kategori)
    return bedst[1] if bedst else None


def kandidater(linjer: list[str]) -> list[tuple[str, str]]:
    """(kategori, linje) for de linjer der kan bære et hensyn. Rækkefølgen bevares."""
    ud: list[tuple[str, str]] = []
    for linje in linjer:
        kategori = kandidat_kategori(linje)
        if kategori:
            ud.append((kategori, _normaliser(linje)))
    return ud


_FORMULER_PROMPT = """Du udleder HANDLINGSRELEVANTE HENSYN om en bruger.

En linje fra brugerens profil:
\"{linje}\"

Kategori: {kategori}

Svar KUN i dette format, to linjer:
REGEL: <en undladelse eller handling, imperativ, maks 60 tegn>
GRAENSE: <hvornår reglen viger, maks 60 tegn>

Eller svar KUN med ordet INGEN hvis linjen ikke rummer et hensyn — fx fordi den
er en biografisk fakta, en engangshændelse eller en teknisk note.

Regler:
- Hensynet skal kunne efterleves i et svar. «vegetar» → «foreslå ikke kød».
- GRAENSE er obligatorisk. Et forbud uden udgang er ubrugeligt.
- Vær konkret. «vær hensynsfuld» er ikke et hensyn.
"""


def _formuler(
    linje: str,
    kategori: str,
    llm: Callable[[str], str] | None,
) -> tuple[str, str] | None:
    """Formulér (regel, grænse) for én kandidat — ``None`` når den forkastes.

    En modelfejl forkaster kandidaten. Hellere et mistet hensyn end et opdigtet:
    falske positiver styrer samtalen forkert.
    """
    if llm is None:
        try:
            from core.services.daemon_llm import daemon_llm_call

            def llm(prompt: str) -> str:  # noqa: E306 — lokal binding til daemon-kaldet
                return daemon_llm_call(
                    prompt,
                    max_len=200,
                    fallback="",
                    daemon_name="user_hensyn",
                )

        except Exception as exc:
            logger.debug("user_hensyn: daemon_llm utilgængelig: %s", exc)
            return None

    try:
        svar = str(llm(_FORMULER_PROMPT.format(linje=linje, kategori=kategori)) or "")
    except Exception as exc:
        logger.debug("user_hensyn: modelkald fejlede: %s", exc)
        return None

    if not svar.strip() or "INGEN" in svar.upper()[:40]:
        return None

    regel_match = re.search(r"REGEL:\s*(.+)", svar, re.IGNORECASE)
    graense_match = re.search(r"GRAENSE:\s*(.+)", svar, re.IGNORECASE)
    if not regel_match or not graense_match:
        return None

    regel = _normaliser(regel_match.group(1)).strip(" .")
    graense = _normaliser(graense_match.group(1)).strip(" .")
    # Grænsen er ikke valgfri — det er hele pointen med designet.
    if len(regel) < 8 or len(graense) < 8:
        return None
    return regel, graense


# ── Levetid ─────────────────────────────────────────────────────────────────


def _nu() -> datetime:
    return datetime.now(UTC)


def _alder_dage(hensyn: Hensyn, nu: datetime) -> float:
    try:
        start = datetime.fromisoformat(str(hensyn.oprettet).replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
    except Exception:  # ugyldigt tidsstempel → behandl som ny, ikke som udløbet
        return 0.0
    return max(0.0, (nu - start).total_seconds() / 86400.0)


def vaegt(hensyn: Hensyn, nu: datetime | None = None) -> float:
    """Hensynets aktuelle vægt 0-1. Varige er altid 1.0."""
    if hensyn.levetid == VARIG:
        return 1.0
    nu = nu or _nu()
    alder = _alder_dage(hensyn, nu)
    return float(0.5 ** (alder / HALVERINGSTID_DAGE))


def forfrem(hensyn: Hensyn, nu: datetime | None = None) -> Hensyn:
    """Situationel → varig når den er set nok gange eller kilden er eksplicit varig."""
    if hensyn.levetid == VARIG:
        return hensyn
    nu = nu or _nu()
    eksplicit = bool(_VARIG_RE.search(f"{hensyn.regel} {hensyn.graense}"))
    if hensyn.forekomster >= FORFREMNING_GENTAGELSER or eksplicit:
        hensyn.levetid = VARIG
        hensyn.sidst_set = nu.isoformat()
    return hensyn


def opdater(hensyn: Hensyn, nu: datetime | None = None) -> Hensyn:
    """Anvend levetidsreglerne: forfrem, falm, og erklær støj.

    Udgangen er indbygget: et hensyn der er injiceret ``N_TURE_UDEN_EFFEKT`` gange
    uden at have ramt et svar — og uden at et brud har vist at det var relevant —
    er støj og forlader prompten.
    """
    nu = nu or _nu()
    hensyn = forfrem(hensyn, nu)

    if hensyn.levetid == SITUATIONEL and vaegt(hensyn, nu) < VAEGT_FLOOR:
        hensyn.status = UDLOEBET
        return hensyn

    if (
        hensyn.injiceret >= N_TURE_UDEN_EFFEKT
        and hensyn.ramte == 0
        and hensyn.brud == 0
    ):
        hensyn.status = STOEJ
    return hensyn


def aktive(hensyns: list[Hensyn], nu: datetime | None = None) -> list[Hensyn]:
    """De hensyn der må bruge plads i prompten, stærkeste først."""
    nu = nu or _nu()
    levende = [opdater(h, nu) for h in hensyns]
    levende = [h for h in levende if h.status == AKTIV]
    levende.sort(key=lambda h: (h.levetid != VARIG, -vaegt(h, nu), h.kategori))
    return levende


# ── Effekt-måling ───────────────────────────────────────────────────────────


def marker_injiceret(hensyns: list[Hensyn], ids: list[str]) -> list[Hensyn]:
    """Tæl at disse hensyn blev injiceret i en tur. Kaldes af læsesiden."""
    valgte = set(ids)
    for h in hensyns:
        if h.hensyn_id in valgte:
            h.injiceret += 1
    return hensyns


def marker_ramte(hensyns: list[Hensyn], hensyn_id: str) -> list[Hensyn]:
    """Registrér at hensynet faktisk påvirkede et svar. Nulstiller støj-tællingen."""
    for h in hensyns:
        if h.hensyn_id == hensyn_id:
            h.ramte += 1
            h.injiceret = 0
            h.sidst_set = _nu().isoformat()
    return hensyns


def tjek_brud(hensyn: Hensyn, svar: str) -> bool:
    """Deterministisk brud-detektor for de kategorier hvor det er entydigt.

    Kun kost er sikker nok: reglen «foreslå ikke kød» kan måles mod et svar der
    fremsætter kød i en foreslå-kontekst. For de øvrige kategorier ville en
    ord-match give falske brud, og et falsk brud er lige så skadeligt som et
    falsk hensyn — det holder et ubrugeligt hensyn i live.
    """
    ord_liste = _BRUD_NOEGLEORD.get(hensyn.kategori)
    if not ord_liste:
        return False
    tekst = str(svar or "")
    if not tekst:
        return False
    for ord_ in ord_liste:
        if ord_.lower() not in tekst.lower():
            continue
        # Kun et brud hvis ordet står i en sætning der foreslår noget.
        for saetning in re.split(r"(?<=[.!?])\s+", tekst):
            if ord_.lower() in saetning.lower() and _FORESLAA_RE.search(saetning):
                return True
    return False


def registrer_svar(hensyns: list[Hensyn], svar: str) -> list[Hensyn]:
    """Kør brud-detektoren på et færdigt svar. Returnerer den opdaterede liste."""
    for h in hensyns:
        if h.status != AKTIV:
            continue
        if tjek_brud(h, svar):
            h.brud += 1
            h.injiceret = 0
    return hensyns


# ── Udledning ───────────────────────────────────────────────────────────────


def _linje_hash(linje: str) -> str:
    import hashlib

    return hashlib.sha1(_normaliser(linje).encode("utf-8")).hexdigest()[:16]


def _behandlede() -> set[str]:
    """Kildelinjer der allerede er vurderet — så et modelkald ikke gentages.

    Målt 25/10-2026: første kørsel mod Bjørns 477 Lært-linjer gav 60 modelkald.
    Uden denne dedup ville de 60 køre hvert 10. minut for evigt — også de 59 der
    svarede «INGEN». Et forkastet svar er også et svar.
    """
    try:
        from core.runtime.state_store import load_json

        raw = load_json(_BEHANDLET_KEY, {"hashes": []}) or {}
        return {str(h) for h in (raw.get("hashes") or [])}
    except Exception as exc:
        logger.debug("user_hensyn: kunne ikke læse behandlede: %s", exc)
        return set()


def _gem_behandlede(hashes: set[str]) -> None:
    try:
        from core.runtime.state_store import save_json

        # Loft: profilen vokser, men de ældste linjer forsvinder sjældent. 2.000
        # hashes er ~44 KB og dækker rigeligt en profil af denne størrelse.
        save_json(_BEHANDLET_KEY, {"hashes": sorted(hashes)[-2000:]})
    except Exception as exc:
        logger.debug("user_hensyn: kunne ikke gemme behandlede: %s", exc)


def udled(
    linjer: list[str],
    *,
    kilde: str,
    llm: Callable[[str], str] | None = None,
    eksisterende: list[Hensyn] | None = None,
) -> list[Hensyn]:
    """Udled hensyn fra profil-linjer. Eksisterende hensyn genkendes og tælles.

    Gentagne forekomster hæver ``forekomster``, hvilket er det der forfremmer et
    situationelt hensyn til varigt — ikke en længere halveringstid.

    Linjer der allerede er vurderet springes over, så en kørsel uden nye linjer
    koster nul modelkald.
    """
    nu = _nu()
    kendte = list(eksisterende or [])
    indeks = {_nøgle(h.regel): h for h in kendte}
    nye: list[Hensyn] = []
    behandlede = _behandlede()
    nye_hashes: set[str] = set()

    for _kilde_kategori, linje in kandidater(linjer):
        noegle_linje = _linje_hash(linje)
        if noegle_linje in behandlede:
            continue
        formet = _formuler(linje, _kilde_kategori, llm)
        nye_hashes.add(noegle_linje)
        if formet is None:
            continue
        regel, graense = formet
        # Kategorien hører til HENSYNET, ikke til den linje det kom fra. Målt
        # 25/10-2026: en kød-regel blev klassificeret som «sprog», fordi
        # kildelinjen handlede om formulering. Reglen selv er det bedste signal.
        kategori = kandidat_kategori(f"{regel} {graense}") or _kilde_kategori
        noegle = _nøgle(regel)
        if noegle in indeks:
            indeks[noegle].forekomster += 1
            indeks[noegle].sidst_set = nu.isoformat()
            continue
        hensyn = Hensyn(
            hensyn_id=f"h-{uuid4().hex[:12]}",
            kategori=kategori,
            regel=regel,
            graense=graense,
            levetid=SITUATIONEL,
            kilde=kilde,
            oprettet=nu.isoformat(),
            sidst_set=nu.isoformat(),
        )
        # En kilde der selv siger «altid» forfremmes med det samme — ellers skal
        # den bevise sig ved gentagelse.
        if _VARIG_RE.search(linje):
            hensyn.levetid = VARIG
        indeks[noegle] = hensyn
        nye.append(hensyn)

    if nye_hashes:
        _gem_behandlede(behandlede | nye_hashes)

    return kendte + nye


def _profil_linjer(workspace_dir: Path) -> list[tuple[str, str]]:
    """(sektion, linje) fra de dele af USER.md der kan bære hensyn."""
    from core.services.prompt_sections.learned_about_user import (
        core_lines,
        learned_lines,
    )

    ud: list[tuple[str, str]] = []
    for linje in core_lines(workspace_dir):
        ud.append(("USER.md#Kerne", linje))
    for row in learned_lines(workspace_dir):
        ud.append(("USER.md#Lært", str(row.get("text") or "")))
    return [(k, l) for k, l in ud if l.strip()]


# ── Baggrunds-kørsel ────────────────────────────────────────────────────────


def tick_user_hensyn(
    *,
    workspace_dir: Path | None = None,
    llm: Callable[[str], str] | None = None,
    skip_cadence: bool = False,
) -> dict[str, Any]:
    """Baggrunds-udledning: læs profilen, udled hensyn, anvend levetiderne.

    Kører som de øvrige daemoner og skriver til ``state_store``. Idempotent:
    samme profil to gange giver ingen nye rækker, men hæver ``forekomster`` —
    hvilket er hvad der forfremmer et situationelt hensyn.

    Cadence er 60 minutter, ikke 10 som stil-daemonen: profilen ændrer sig når
    Bjørn skriver noget nyt, ikke hvert tiende minut. ``skip_cadence`` bruges af
    tests og af en manuel kørsel.
    """
    global _last_tick_at
    nu = _nu()
    if not skip_cadence and _last_tick_at is not None:
        if (nu - _last_tick_at) < timedelta(minutes=CADENCE_MINUTTER):
            return {"generated": False, "skip_reason": "cadence_gate"}

    if workspace_dir is None:
        # Samme vej som prompt_contract bruger — ikke en egen sti-gætning. Falder
        # den tilbage på WORKSPACES_DIR/bjorn, er det fordi bootstrap ikke kunne
        # svare, og så skal det kunne ses i loggen.
        try:
            from core.identity.workspace_bootstrap import ensure_default_workspace

            workspace_dir = ensure_default_workspace()
        except Exception as exc:
            logger.debug("user_hensyn: ensure_default_workspace fejlede: %s", exc)
            try:
                from core.runtime.config import WORKSPACES_DIR

                workspace_dir = Path(WORKSPACES_DIR) / "bjorn"
            except Exception as exc2:
                logger.debug("user_hensyn: ingen workspace-sti: %s", exc2)
                return {"generated": False, "skip_reason": "no_workspace"}

    try:
        linjer = _profil_linjer(Path(workspace_dir))
    except Exception as exc:
        logger.debug("user_hensyn: kunne ikke læse profilen: %s", exc)
        return {"generated": False, "skip_reason": "read_failed"}

    if not linjer:
        return {"generated": False, "skip_reason": "no_profile_lines"}

    eksisterende = _load()
    foer = len(eksisterende)
    opdaterede = udled(
        [l for _k, l in linjer],
        kilde="USER.md",
        llm=llm,
        eksisterende=eksisterende,
    )
    opdaterede = [opdater(h) for h in opdaterede]
    _save(opdaterede)

    nye = len(opdaterede) - foer
    varige = sum(1 for h in opdaterede if h.levetid == VARIG)
    _last_tick_at = nu
    return {
        "generated": nye > 0,
        "i_alt": len(opdaterede),
        "nye": nye,
        "varige": varige,
        "aktive": len(aktive(opdaterede)),
    }


# ── Læsesiden: prompt-sektionen ─────────────────────────────────────────────


def byg_hensyn_sektion(
    *,
    max_chars: int = 600,
    nu: datetime | None = None,
    taeller_injektion: bool = True,
) -> str:
    """Prompt-sektionen — "" når intet hensyn er aktivt.

    Egen lille kurateret sektion, ikke en del af Lært-puljen: et hensyn der skal
    efterleves hører ikke sammen med en note fra i sidste uge. Ingen modelkald —
    dette er læsesiden og kaldes ved hver prompt-bygning.
    """
    nu = nu or _nu()
    alle_hensyn = _load()
    if not alle_hensyn:
        return ""

    levende = aktive(alle_hensyn, nu)
    if not levende:
        return ""

    linjer: list[str] = []
    brugt = 0
    valgte: list[str] = []
    for h in levende:
        tekst = f"• {h.regel} — {h.graense}"
        if brugt + len(tekst) > max_chars and linjer:
            break
        linjer.append(tekst)
        valgte.append(h.hensyn_id)
        brugt += len(tekst)

    if not linjer:
        return ""

    if taeller_injektion:
        marker_injiceret(alle_hensyn, valgte)
        _save(alle_hensyn)

    return "Hensyn om Bjørn (efterlev dem; grænsen står ved hver linje):\n" + "\n".join(linjer)
