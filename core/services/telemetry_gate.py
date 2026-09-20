"""Telemetri er ikke sandhed — Fase 10, kriterium 2.

Kriteriet:

    «telemetry records are classified separately from canonical truth, use
     mandatory export-copy redaction, tolerate loss/duplication honestly, and
     cannot authorize or settle work»

## Hvad målingen viste

**Der findes ingen udgående telemetri-vej.** Ingen posthog, sentry, otlp eller
tilsvarende i repoet. `telemetry_sharing` er erklæret i to profiler og beskrev
altså en vej der ikke er bygget. Eksport-redigeringen er derfor et *løfte om
form*, ikke en aktiv rensning: den gælder den dag nogen bygger vejen, og
`redigér_til_eksport()` står klar så den ikke skal opfindes i farten.

**Adskillelsen fra kanonisk sandhed er allerede der — ved et tilfælde.**
Telemetri lander i `state_store` (JSON), mens kørsler og hændelser ligger i
`visible_runs`, `agent_runs`, `events`. Ingen regel holder dem adskilt; det er
lagringen der gør det. `er_kanonisk()` gør tilfældet til en kontrol.

**Tabet var IKKE ærligt.** Målt på runtime 13/9-2026:

    decision_signal_telemetry.surfaces   500 poster  <-- paa loftet
    decision_signal_telemetry.reactions  500 poster  <-- paa loftet

`_save()` gør `list(...)[-500:]`. Begge ringe står præcis på loftet, hvilket
betyder at de har kastet væk — og der findes ikke ét tal for hvor meget.
Femte gang limit-vindue-fælden dukker op i dette hus, denne gang som en
skrivning der taber i tavshed.

Kriteriet siger «tolerate loss honestly». Ikke «undgå tab» — tab er i orden for
telemetri, det er netop forskellen på telemetri og sandhed. Det der ikke er i
orden, er at tabet er usynligt.

## Telemetri må aldrig afgøre noget

Målt: intet i huset lader telemetri autorisere eller afgøre arbejde i dag. Det
er det rigtige, og `maa_afgoere()` findes udelukkende for at kunne HÅNDHÆVE det
med en test. En invariant uden en vagt er en hensigt.

Grunden er at telemetri per definition er ufuldstændig: den taber (se ovenfor),
den kan komme dobbelt, og den er afledt. En beslutning taget på et ufuldstændigt
grundlag er ikke en beslutning man kan efterprøve bagefter.
"""
from __future__ import annotations

import logging
import re
import threading
from datetime import UTC, datetime, timedelta
from typing import Any, Sequence

logger = logging.getLogger(__name__)

#: Brugeren/niveauet kunne ikke bestemmes. Ikke det samme som «ingen deling».
UBESTEMT = "ubestemt"

#: Tabellerne der bærer kanonisk sandhed. Telemetri hører ikke til i dem.
KANONISKE_TABELLER: frozenset[str] = frozenset({
    "visible_runs", "agent_runs", "events", "event_ledger", "costs",
    "chat_messages", "chat_sessions", "audit", "audit_log",
})

#: Mønstre der renses ud af en EKSPORT-kopi. Aldrig ud af originalen —
#: originalen er husets eget, og en rensning der rammer den ville gøre den
#: lokale telemetri ubrugelig for at beskytte en vej der ikke findes endnu.
_REDIGERES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "<email>"),
    (re.compile(r"\b\d{6}-?\d{4}\b"), "<cpr>"),
    (re.compile(r"\b(?:sk|jvs|ghp|xox[baprs])[-_][A-Za-z0-9_-]{8,}\b"), "<noegle>"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I), "Bearer <token>"),
    # ÉT moenster for lange cifferloeb, og et aerligt navn.
    #
    # Foerste udgave havde `<kortnummer>` (13-19 cifre) og `<discord-id>`
    # (17-20) som to moenstre. De overlapper paa 17-19, og det foerste vandt:
    # Bjoerns discord-id blev maerket «kortnummer». Det var stadig fjernet, men
    # etiketten loej — og en rensnings-log man ikke kan stole paa er vaerre end
    # en grovkornet én, fordi nogen bruger den til at lede efter et laek der
    # ikke findes.
    (re.compile(r"\b(?:\d[ -]?){12,19}\d\b"), "<langt-ciffer-id>"),
)

_laas = threading.Lock()
#: navn -> hvor mange poster der er kastet vaek. Det tal der manglede.
_TABT: dict[str, int] = {}


def gaeldende_niveau() -> str:
    """`full` | `redacted` | `none` | `ubestemt` for den kørsel vi er i nu.

    Navnet er ikke tilfældigt: `profile_enforcement._maal_telemetri()`
    importerer præcis denne funktion for at afgøre om aksen har en håndhæver.
    """
    try:
        from types import SimpleNamespace

        from core.identity.workspace_context import current_user_id
        from core.runtime.profiles import byg
        from core.runtime.run_profile import profil_navn_for
        from core.services.run_autonomy_context import is_autonomous
        uid = str(current_user_id() or "").strip()
        if not uid:
            return UBESTEMT
        run = SimpleNamespace(user_id=uid, autonomous=bool(is_autonomous()),
                              local_tool_exec=False)
        return str(byg(profil_navn_for(run)).felter.get("telemetry_sharing") or UBESTEMT)
    except Exception:
        return UBESTEMT


def maa_afgoere() -> bool:
    """Må telemetri autorisere eller afgøre arbejde? **Nej. Altid nej.**

    Funktionen findes ikke fordi svaret er i tvivl, men fordi en invariant uden
    en vagt er en hensigt. `test_telemetri_kan_ALDRIG_afgoere` læser den her, og
    en kilde-vagt læser at ingen telemetri-modul kalder gate-/godkendelses-veje.

    Telemetri er per definition ufuldstændig: den taber, den kan komme dobbelt,
    og den er afledt. En beslutning på det grundlag kan ikke efterprøves.
    """
    return False


def er_kanonisk(tabel: str) -> bool:
    """Hører `tabel` til den kanoniske sandhed?

    Adskillelsen findes allerede — telemetri ligger i `state_store`, sandheden i
    tabellerne — men den er et tilfælde af lagring, ikke en regel. Det her gør
    tilfældet til en kontrol nogen kan teste.
    """
    return str(tabel or "").strip().lower() in KANONISKE_TABELLER


def beskaer(poster: Sequence[Any], maks: int, *, navn: str) -> list[Any]:
    """Behold de nyeste `maks` — og **tæl** det der ryger.

    Det er hele forskellen på dette og `list(poster)[-maks:]`, som er det der
    stod før. Målt 13/9-2026 stod begge ringe i `decision_signal_telemetry`
    præcis på 500/500, hvilket betyder at de havde kastet væk — og der fandtes
    ikke ét tal for hvor meget.

    Tab er i orden for telemetri; det er netop forskellen på telemetri og
    sandhed. Usynligt tab er ikke.
    """
    alle = list(poster or [])
    if maks <= 0 or len(alle) <= maks:
        return alle
    tabt = len(alle) - maks
    with _laas:
        _TABT[str(navn)] = _TABT.get(str(navn), 0) + tabt
        i_alt = _TABT[str(navn)]
    logger.info("telemetri: %s beskaaret til %d, kastede %d vaek (%d i alt)",
                navn, maks, tabt, i_alt)
    return alle[-maks:]


def beskaer_efter_alder(
    poster: Sequence[Any],
    dage: int,
    *,
    navn: str,
    maks: int = 0,
    nu: datetime | None = None,
) -> list[Any]:
    """Behold poster nyere end `dage` — og tæl **alt** der ryger.

    Hvorfor ikke bare et antal. `beskaer()` løser at tabet er *usynligt*; den
    løser ikke at vinduet er *aktivitets-afhængigt*. Målt 20/9-2026 stod
    `verification_gate_telemetry` præcis på 500/500 poster, hvilket dækkede
    9,7 døgn ved ~52 poster/døgn. Ved 500/døgn ville «7d» reelt være 1 døgn —
    og tallet ville se lige så rigtigt ud. Horisonten skal være en *tid*, ikke
    et *antal*, ellers flytter målevinduet sig når aktiviteten gør.

    To tab, ét regnskab:
      * **alderstab** — poster ældre end vinduet. Det er horisonten der virker.
      * **loftstab** — poster ud over `maks`. Rent sikkerhedsnet mod vækst, så
        en løbsk løkke ikke spiser state-filen. Ikke den effektive horisont.

    Poster uden læsbar tidsstempel **beholdes** — alderen kan ikke afgøres, og
    et gæt ville kaste rigtige poster væk. De er stadig omfattet af loftet.
    """
    alle = list(poster or [])
    if dage <= 0:
        return beskaer(alle, maks, navn=navn) if maks > 0 else alle

    graense = (nu or datetime.now(UTC)) - timedelta(days=dage)
    beholdt: list[Any] = []
    alderstab = 0
    for p in alle:
        ts: datetime | None = None
        if isinstance(p, dict):
            try:
                ts = datetime.fromisoformat(str(p.get("at", "")))
            except (ValueError, TypeError):
                ts = None
        if ts is None:
            beholdt.append(p)          # alder ukendt → behold (konservativt)
            continue
        if ts.tzinfo is None:          # naiv → antag UTC frem for at kaste
            ts = ts.replace(tzinfo=UTC)
        if ts >= graense:
            beholdt.append(p)
        else:
            alderstab += 1

    if alderstab:
        with _laas:
            _TABT[str(navn)] = _TABT.get(str(navn), 0) + alderstab
            i_alt = _TABT[str(navn)]
        logger.info("telemetri: %s aldersbeskaaret til %d dage, kastede %d "
                    "gamle poster (%d i alt)", navn, dage, alderstab, i_alt)

    if maks > 0:
        beholdt = beskaer(beholdt, maks, navn=navn)
    return beholdt


def tabt(navn: str = "") -> int | dict[str, int]:
    """Hvor mange poster er kastet væk? Uden navn: hele regnskabet."""
    with _laas:
        if navn:
            return int(_TABT.get(str(navn), 0))
        return dict(_TABT)


def nulstil_tab() -> None:
    """Kun til tests. Produktionen skal aldrig glemme hvad den tabte."""
    with _laas:
        _TABT.clear()


def redigér_til_eksport(vaerdi: Any) -> Any:
    """Rens en **kopi** til eksport. Originalen røres aldrig.

    Kriteriet siger «mandatory export-copy redaction». Ordet *copy* bærer det:
    en rensning der ramte originalen ville gøre husets egen telemetri ubrugelig
    for at beskytte en udgående vej der ikke findes endnu.

    Rensningen er bevidst grovkornet. En for fin maske der overser ét mønster
    er værre end en der rammer lidt for bredt — det første lækker, det andet
    gør en linje mindre præcis.
    """
    if isinstance(vaerdi, str):
        ud = vaerdi
        for moenster, erstatning in _REDIGERES:
            ud = moenster.sub(erstatning, ud)
        return ud
    if isinstance(vaerdi, dict):
        return {k: redigér_til_eksport(v) for k, v in vaerdi.items()}
    if isinstance(vaerdi, (list, tuple)):
        t = type(vaerdi)
        return t(redigér_til_eksport(v) for v in vaerdi)
    return vaerdi
