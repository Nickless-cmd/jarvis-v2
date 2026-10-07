"""core/services/peak_hours.py

Myldretids-badge til prompt-halen (30/9-2026, på Bjørns opfordring).

DeepSeek fakturerer det DOBBELTE i myldretiden. Vinduet er defineret i UTC
(``MYLDRE_VINDUER`` i :mod:`core.services.llm_pricing`), mandag-fredag. I dansk
tid svarer det til 08-12 om sommeren og 07-11 om vinteren — derfor regner ALT
her i UTC og oversættes kun til visning. En badge der regnede i lokal tid ville
være forkert halvdelen af året, og det er præcis den slags tavse fejl Bjørn og
jeg har brugt dagen på at jagte.

Badgen har tre tilstande:
  * **tavs**        — off-peak, mere end ``VARSEL_MINUTTER`` til næste vindue
  * **varsel**      — off-peak, inden for varsel-vinduet
  * **stort**       — midt i myldretiden, umulig at overse

Den BLOKERER intet. Husets mønster er at vagter observerer, ikke afviser
(jf. ``paid_lane_guard``: «Den RETTER intet: et lane-valg er en drifts-
beslutning»). Badgen bærer beslutningen videre til den der kan tage den —
den siger hvad turen koster og hvad der kan vente, og lader så Bjørn og mig
vælge. At nægte at svare Bjørn for at spare tyve øre er en dårlig handel, og
hans ture er den eneste udgift der ikke kan flyttes.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from core.services.llm_pricing import MYLDRE_VINDUER, er_myldretid

#: Hvor mange minutter før et vindue åbner at varslet toner frem.
#:
#: 1/10-2026: stod paa 30 her og paa 15 i `peak_varsel_daemon` — to konstanter
#: med SAMME navn i hvert sit modul. Badgen i prompten tonede derfor frem et
#: kvarter foer notifikationen blev sendt, og ingen af tallene var forkerte hver
#: for sig; de var bare ikke det samme. Bjoern: 15 er det rigtige.
#:
#: Daemonen importerer nu herfra. Domaenet ejer tallet; forbrugeren laaner det.
VARSEL_MINUTTER: int = 15

_DANSK = ZoneInfo("Europe/Copenhagen")


def _som_utc(at: datetime | str | None) -> datetime:
    """Læs et tidspunkt som aware UTC. Naivt input læses som UTC (hovedbogen er UTC)."""
    if at is None:
        return datetime.now(UTC)
    if isinstance(at, datetime):
        return at if at.tzinfo else at.replace(tzinfo=UTC)
    tekst = str(at or "").strip()
    if tekst.endswith(("Z", "z")):
        tekst = tekst[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(tekst)
    except ValueError:  # ugyldig ISO-streng → "nu" er aerligere end et gaet
        return datetime.now(UTC)
    return d if d.tzinfo else d.replace(tzinfo=UTC)


#: Offentligt alias (30/9-2026). ``peak_varsel_daemon`` og andre læsere skal
#: ikke importere et understregnings-navn for at få samme UTC-normalisering.
som_utc = _som_utc


def _vindue_start(dag, fra: int) -> datetime:
    return datetime.combine(dag, time(fra, 0), tzinfo=UTC)


def naeste_vindue_start(now_utc: datetime | None = None) -> datetime | None:
    """Næste myldretids-vindue der ÅBNER efter nu. Springer weekender over."""
    nu = _som_utc(now_utc)
    for dage_frem in range(0, 8):
        dag = (nu + timedelta(days=dage_frem)).date()
        if dag.weekday() >= 5:      # lørdag/søndag er aldrig myldretid
            continue
        for fra, _til in MYLDRE_VINDUER:
            start = _vindue_start(dag, fra)
            if start > nu:
                return start
    return None


def aktuelt_vindue(now_utc: datetime | None = None) -> tuple[datetime, datetime] | None:
    """(start, slut) for det vindue vi står i — eller None hvis vi er i off-peak.

    30/9-2026: starten kom med, fordi badgen kun havde slutningen og derfor
    hardcodede '08:00' som visning. Det er rigtigt om sommeren og forkert om
    vinteren — vinduet åbner 07:00 dansk i CET. En visning der er rigtig
    halvdelen af året er den slags tavse fejl vi jager.
    """
    nu = _som_utc(now_utc)
    if nu.weekday() >= 5:
        return None
    for fra, til in MYLDRE_VINDUER:
        start = _vindue_start(nu.date(), fra)
        slut = _vindue_start(nu.date(), til)
        if start <= nu < slut:
            return start, slut
    return None


def aktuelt_vindue_slut(now_utc: datetime | None = None) -> datetime | None:
    """Slutningen på det vindue vi står i — eller None hvis vi er i off-peak."""
    v = aktuelt_vindue(now_utc)
    return v[1] if v else None


def _dansk(ts: datetime) -> str:
    return ts.astimezone(_DANSK).strftime("%H:%M")


def peak_state(now: datetime | str | None = None) -> dict[str, object]:
    """Tilstanden lige nu — grundlaget for badgen og for alt andet der spørger."""
    nu = _som_utc(now)
    i_myldre = er_myldretid(nu)
    vindue = aktuelt_vindue(nu) if i_myldre else None
    start = vindue[0] if vindue else None
    slut = vindue[1] if vindue else None
    naeste = None if i_myldre else naeste_vindue_start(nu)
    return {
        "in_peak": i_myldre,
        "now_utc": nu.isoformat(),
        "now_danish": _dansk(nu),
        "peak_starts_danish": _dansk(start) if start else None,
        "peak_ends_danish": _dansk(slut) if slut else None,
        "minutes_left": int((slut - nu).total_seconds() // 60) if slut else None,
        "next_peak_danish": _dansk(naeste) if naeste else None,
        "minutes_until_next": (
            int((naeste - nu).total_seconds() // 60) if naeste else None
        ),
    }


def _varighed(minutter: int) -> str:
    if minutter < 60:
        return f"{minutter} min"
    t, m = divmod(minutter, 60)
    return f"{t} t {m} min" if m else f"{t} t"


def peak_badge(now: datetime | str | None = None) -> str | None:
    """Badgen til prompt-halen. None når der ikke er noget at sige.

    Kaldes fra ``prompt_contract`` lige før time-pin'en, så de to tids-blokke
    står sammen. Returnerer None i off-peak uden for varsel-vinduet — en badge
    der altid råber er en badge man holder op med at læse.
    """
    st = peak_state(now)

    if st["in_peak"]:
        tilbage = st["minutes_left"]
        rest = f"lukker om {_varighed(int(tilbage))}" if tilbage else "vinduet er åbent"
        return (
            "🔥═══════════════════════════════════════🔥\n"
            "🔥 MYLDRETID — DeepSeek koster 2× lige nu 🔥\n"
            "🔥═══════════════════════════════════════🔥\n"
            f"Vindue: 06–10 UTC = {st['peak_starts_danish']}–"
            f"{st['peak_ends_danish']} dansk · {rest}\n"
            "Hver krone brugt nu kunne have været halvt så dyr.\n"
            "\n"
            "Sådan læser du det:\n"
            "· Bjørns ture — KØR DEM. At nægte at svare koster mere end tillægget, "
            "og hans ture er den eneste udgift der ikke kan flyttes.\n"
            "· Dit EGET tunge arbejde — subagents, batch, cache-varmere, "
            "dybdesessioner, store scan: udskyd til efter vinduet hvis det ikke "
            "haster. At vente er gratis; at køre er det ikke.\n"
            "· Bundet til NU (fejlfinding, Bjørn venter)? Kør. Sig det bare højt "
            "i svaret, så vi begge ved hvorfor."
        )

    mangler = st["minutes_until_next"]
    if mangler is not None and mangler <= VARSEL_MINUTTER:
        return (
            f"⏳ MYLDRETID OM {mangler} MIN — kl. {st['next_peak_danish']} dansk.\n"
            "Tungt arbejde der kan klares nu, bør klares nu. Ellers vent til "
            "vinduet lukker."
        )

    return None


def booking_varsel(naar: datetime | str | None) -> str | None:
    """Én linje hvis et BOOKET tidspunkt rammer myldretiden. Ellers ``None``.

    Hvorfor den findes (7/10-2026, Bjørns opfordring): ``peak_badge`` siger hvad
    der sker NU og i det næste kvarter. Den kan pr. konstruktion ikke se et løfte
    der ligger to timer ude — og det er præcis dér beslutningen om at booke ind i
    vinduet tages. Målt samme aften: jeg bookede en vækning til kl. 08:59 dansk
    og en anden til 19:39, og intet i svaret sagde at den ene lå midt i vinduet.
    Badgen var tavs, fordi bookingen skete i off-peak.

    Værnet BLOKERER intet — samme husmønster som badgen og ``paid_lane_guard``.
    Et afvist booking-forsøg ville tvinge mig til at gætte et nyt tidspunkt, og
    et forkert tidspunkt er dyrere end et varslet et. Det lægger beslutningen
    foran mig, i det svar hvor jeg kan tage den.

    Grænsen genbruger ``VARSEL_MINUTTER`` med vilje. Stod der et andet tal her,
    ville værnet og badgen kunne blive uenige om hvornår vinduet åbner — og det
    er netop den fejl der allerede kostede én runde 1/10-2026 (to konstanter med
    samme navn, 30 og 15).
    """
    tid = _som_utc(naar)
    st = peak_state(tid)

    if st["in_peak"]:
        return (
            f"⚠️ BOOKINGEN LANDER I MYLDRETIDEN "
            f"({st['peak_starts_danish']}–{st['peak_ends_danish']} dansk). "
            "DeepSeek koster 2× i vinduet. Er det dit eget tunge arbejde, kan det "
            "flyttes gratis — Bjørns ture kan ikke."
        )

    mangler = st["minutes_until_next"]
    if mangler is not None and mangler <= VARSEL_MINUTTER:
        return (
            f"⏳ BOOKINGEN LANDER LIGE FØR MYLDRETID (om {mangler} min, kl. "
            f"{st['next_peak_danish']} dansk) — arbejdet løber ind i vinduet."
        )

    return None


def gentagelse_rammer_vindue(interval_minutter: int) -> bool:
    """Vil en rutine med denne kadence uundgåeligt ramme et vindue?

    En rutine der gentages hvert 10. minut kan ikke undgå myldretiden — den
    rammer den mange gange i døgnet. En rutine der kører én gang i døgnet kan
    måske. Førstnævnte skal have besked med det samme, også selvom FØRSTE
    gennemløb ligger i off-peak; ellers ville værnet tie om netop den rutine
    der koster mest.
    """
    try:
        laengste = max((til - fra) * 60 for fra, til in MYLDRE_VINDUER)
    except (TypeError, ValueError):  # tom/ugyldig tabel → gæt ikke, sig intet
        return False
    return 0 < int(interval_minutter) < laengste


def tilfoej_booking_varsel(
    svar: dict[str, Any], naar: datetime | str | None
) -> dict[str, Any]:
    """Hæng ``peak_varsel`` på et booking-svar. Rører intet andet.

    Én indgang til alle booking-veje (``schedule_self_wakeup``,
    ``schedule_task``, ``schedule_recurring``) — så værnet ikke kan blive halvt
    udrullet, og så et svar der ikke er ``ok`` forbliver urørt. Et afvist
    booking-forsøg skal ikke bære et råd om et tidspunkt det aldrig fik.
    """
    if not isinstance(svar, dict) or svar.get("status") != "ok":
        return svar
    if not naar:
        # Uden et tidspunkt ved jeg ikke hvornaar bookingen falder. At varsle om
        # NU ville vaere en paastand jeg ikke kan bakke op — hellere tie.
        return svar
    varsel = booking_varsel(naar)
    if varsel:
        svar["peak_varsel"] = varsel
    return svar
