"""Et synligt runs terminale beslutning — og vagten mod en optimistisk standard.

Udskilt fra `visible_runs.py` (7.214 linjer) efter Boy Scout-reglen i
CLAUDE.md. Tilstandsmaskinen lå som tre lokale variable i én funktion på 4.700
linjer, med ti overgange spredt ud over den.

## Hvorfor den er farlig nok til at have sit eget navn

Standarden er `completed`. Det er optimistisk med vilje — de fleste runs
lykkes — men det betyder at et run der bliver AFBRUDT undervejs, arver
«completed» hvis ingen når at sige noget andet.

Og det sker: klienten dropper forbindelsen, `GeneratorExit` rejses, eller en
`BaseException` som `except Exception` ikke fanger, river funktionen op
midtvejs. Uden vagten står der `completed` på en samtale der aldrig fik et
svar — og efterbehandlingen fyrer sin «completed + tom tekst»-overlevelsesstemme
på en halv kørsel.

Derfor to ting, som hører uadskilleligt sammen:

* hver eksplicit terminal beslutning markerer sig som NÅET (`finalized`), og
* når `finally` ser en beslutning der ALDRIG blev nået, men som stadig står på
  standardværdien, nedgraderes den til `interrupted`.

Bjørn sporede den rod 4. juli. Kommentarerne i den gamle kode kalder den
«RUNTIME-CUTOFF-ROD-FIX» og «immun mod finally-downgrade».

## Hvorfor det er en klasse og ikke tre variable

Tre løse variable kan komme ud af trit: man kan sætte status uden at sætte
vagten, og så er nedgraderingen forkert. Som ét objekt kan de ikke det —
`mark()` gør begge dele.
"""
from __future__ import annotations

COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"
INTERRUPTED = "interrupted"

#: Den optimistiske standard. Ændres den, ændres betydningen af vagten nedenfor.
DEFAULT_STATUS = COMPLETED


class RunOutcomeState:
    """Holder beslutningen og beskytter den mod at blive arvet ved et uheld."""

    __slots__ = ("_status", "_error", "_finalized")

    def __init__(self) -> None:
        self._status = DEFAULT_STATUS
        self._error: str | None = None
        self._finalized = False

    # ── aflæsning ────────────────────────────────────────────────────────
    @property
    def status(self) -> str:
        return self._status

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def finalized(self) -> bool:
        """Nåede runnet et eksplicit terminalt punkt?"""
        return self._finalized

    @property
    def is_default(self) -> bool:
        """Står beslutningen stadig på den optimistiske standard?"""
        return self._status == DEFAULT_STATUS

    # ── beslutninger ─────────────────────────────────────────────────────
    def mark(self, status: str, *, error: str | None = None,
             finalized: bool = True) -> None:
        """Træf den terminale beslutning.

        `finalized` er sand som standard, fordi det at træffe beslutningen ER
        at have nået et terminalt punkt. De få steder der sætter en status
        undervejs uden at være færdige, siger det eksplicit.
        """
        self._status = str(status)
        if error is not None:
            self._error = str(error)
        if finalized:
            self._finalized = True

    def reach_finalization(self) -> None:
        """Marker at runnet nåede sit done-yield uden at ændre status."""
        self._finalized = True

    def set_error(self, error: str | None) -> None:
        if error is not None:
            self._error = str(error)

    # ── vagten ───────────────────────────────────────────────────────────
    def downgrade_if_abandoned(self, abort_kind: str = "none-clean-exit") -> bool:
        """Nedgradér en aldrig-nået standard til `interrupted`. Returnerer om
        der blev nedgraderet.

        Kaldes fra `finally`. Betingelsen er BEGGE dele: standarden står
        urørt, OG intet terminalt punkt blev nået. Et run der eksplicit blev
        erklæret `completed`, røres ikke — det NÅEDE sin beslutning.
        """
        if self._finalized or not self.is_default:
            return False
        self._status = INTERRUPTED
        if not self._error:
            self._error = f"run-abandoned-before-finalization:{abort_kind}"
        return True

    def __repr__(self) -> str:
        return (f"RunOutcomeState(status={self._status!r}, "
                f"error={self._error!r}, finalized={self._finalized})")
