"""Central Copenhagen timezone utilities — én sandhedskilde for dansk tid.

Bygget 2026-06-10 efter Bjørns påpegning af at Jarvis konsekvent
regner forkert i hovedet, når han ser både UTC og dansk tid i time pin.
Al kode der skal bruge lokal dansk tid importerer herfra i stedet for
at kalde .astimezone() eller ZoneInfo direkte.

Bruger zoneinfo.ZoneInfo("Europe/Copenhagen") — korrekt for både
CEST (UTC+2, sommer) og CET (UTC+1, vinter).
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

__all__ = [
    "DK_ZONE",
    "dk_now",
    "dk_timestamp",
    "dk_hour",
    "dk_date_str",
    "dk_time_str",
    "dk_weekday_da",
    "dk_weekday_en",
    "is_dk_quiet_hours",
    "from_utc_iso",
    "time_label_dk",
]

DK_ZONE = ZoneInfo("Europe/Copenhagen")

_WEEKDAY_DA = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
_WEEKDAY_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def dk_now() -> datetime:
    """Return current datetime i Danmark (CEST/CET)."""
    return datetime.now(UTC).astimezone(DK_ZONE)


def dk_timestamp() -> str:
    """ISO timestamp i dansk tid, f.eks. '2026-06-10 15:31:45 CEST'."""
    now = dk_now()
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")


def dk_hour() -> int:
    """Nuværende time i Danmark (0-23)."""
    return dk_now().hour


def dk_date_str() -> str:
    """Dansk dato, f.eks. '10. juni 2026'."""
    now = dk_now()
    return now.strftime("%d. %B %Y")


def dk_time_str() -> str:
    """Klokkeslæt, f.eks. '15:31'."""
    return dk_now().strftime("%H:%M")


def dk_weekday_da() -> str:
    """Dansk ugedag, f.eks. 'onsdag'."""
    return _WEEKDAY_DA[dk_now().weekday()]


def dk_weekday_en() -> str:
    return _WEEKDAY_EN[dk_now().weekday()]


def is_dk_quiet_hours(quiet_start: int = 22, quiet_end: int = 7) -> bool:
    """Er vi indenfor stille-tid (default 22:00-07:00 dansk tid)?

    Hvis quiet_start == quiet_end, betragtes det som 'ingen stille-tid'.
    Hvis quiet_start < quiet_end: normalt interval (f.eks. 22→07).
    Hvis quiet_start > quiet_end: midnatsoverskridende (f.eks. 22→06).
    """
    if quiet_start == quiet_end:
        return False
    hour = dk_hour()
    if quiet_start < quiet_end:
        return quiet_start <= hour < quiet_end
    return hour >= quiet_start or hour < quiet_end


def from_utc_iso(iso_str: str) -> datetime:
    """Parse en UTC ISO-streng og konvertér til dansk tid.

    Håndterer både 'Z', '+00:00' og naive strenge.
    Returnerer en timezone-aware datetime i DK_ZONE.
    """
    if not iso_str:
        return dk_now()
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(DK_ZONE)
    except (ValueError, TypeError):
        return dk_now()


def time_label_dk(iso_str: str) -> str:
    """Konvertér en ISO-streng til dansk tidslabel, f.eks. '15:31'.

    Falder tilbage til rå strengen hvis parsing fejler.
    """
    try:
        dt = from_utc_iso(iso_str)
        return dt.strftime("%H:%M")
    except (ValueError, TypeError):
        return iso_str
