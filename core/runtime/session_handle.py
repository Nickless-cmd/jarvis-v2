"""`SessionHandle` — én ejer, én lease, én sekvens.

Spec: Fase 1 — «Implement `SessionHandle`, cross-process write leases with
fencing, immutable `SessionHeader`, guarded format generations … append/flush/
close APIs».

## Hvorfor et håndtag og ikke bare funktioner

Ledgeren har allerede lease, fencing-token og sekvens. Men så længe de er tre
løse argumenter, skal HVER kaldested huske alle tre — og det er den slags der
holder i tests og skrider i drift. Håndtaget gør ejerskabet til noget man
HOLDER: man har det, eller også har man det ikke.

Vigtigere: et håndtag kan LUKKE. Uden det bliver en lease liggende til den
udløber, og næste proces venter fem minutter på en session ingen skriver til.

## Skrivebeskyttet åbning er en førsteklasses ting

`open_readonly()` findes fordi den hyppigste grund til at kigge på en session
er at finde ud af hvad der gik galt i den — og dét må ikke kræve at man tager
retten til at skrive fra den der stadig arbejder. Spec'ens krav er skarpt:
«read-only interrupted-session inspection writes nothing». Håndtaget uden
lease har ingen `append`; det er ikke en advarsel, det er et fravær.

## Formatet er en dom, ikke et flag

Fire udfald, og de skal kunne skelnes:

* `current` — kendt generation, åbnes.
* `historical` — ældre generation vi kan læse. Åbnes skrivebeskyttet, fordi at
  skrive nyt format ind i en gammel session ville lave en blanding ingen af
  delene kan læse.
* `future` — nyere end os. Afvises. At læse den «så godt vi kan» ville betyde
  at felter vi ikke kender, tavst forsvandt.
* `corrupt` — headeren giver ikke mening. Afvises.

Fælles for de tre sidste: de fejler HØJT. En session der åbner sig halvt er
værre end en der ikke åbner sig.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

#: Den generation denne kode skriver. Bump'es kun når hændelsernes betydning
#: ændrer sig — ikke når der kommer et felt til.
CURRENT_GENERATION = 1

#: Generationer vi stadig kan LÆSE. Skrivning sker altid i CURRENT_GENERATION.
READABLE_GENERATIONS = (1,)

FORMAT_CURRENT = "current"
FORMAT_HISTORICAL = "historical"
FORMAT_FUTURE = "future"
FORMAT_CORRUPT = "corrupt"


class SessionFormatError(RuntimeError):
    """Sessionens format kan ikke åbnes. Bærer hvilken slags."""

    def __init__(self, verdict: str, besked: str):
        super().__init__(besked)
        self.verdict = verdict


class NotWritable(RuntimeError):
    """Der blev forsøgt en skrivning gennem et skrivebeskyttet håndtag."""


@dataclass(frozen=True)
class SessionHeader:
    """Uforanderlig. Skrives ÉN gang ved oprettelsen og ændres aldrig.

    Uforanderligheden er hele pointen: kan generationen ændres bagefter, kan en
    session komme til at påstå den er skrevet efter regler den ikke er skrevet
    efter — og så betyder formatet ingenting.
    """
    session_id: str
    generation: int
    created_at: str

    def as_json(self) -> str:
        return json.dumps({"session_id": self.session_id,
                           "generation": self.generation,
                           "created_at": self.created_at}, sort_keys=True)


def _ensure_header_column(conn) -> None:
    try:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN ledger_header TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass  # kolonnen findes allerede


def write_header(session_id: str, *, generation: int = CURRENT_GENERATION) -> SessionHeader:
    """Skriv headeren én gang. Et andet forsøg er en fejl, ikke en opdatering."""
    from core.runtime.db import connect
    sid = str(session_id or "").strip()
    h = SessionHeader(sid, int(generation), datetime.now(UTC).isoformat())
    with connect() as conn:
        _ensure_header_column(conn)
        row = conn.execute(
            "SELECT ledger_header FROM chat_sessions WHERE session_id = ?", (sid,)
        ).fetchone()
        if row is None:
            raise ValueError(f"ukendt session: {sid!r}")
        if str(row[0] or "").strip():
            raise ValueError(f"session {sid!r} har allerede en header — den er uforanderlig")
        conn.execute("UPDATE chat_sessions SET ledger_header = ? WHERE session_id = ?",
                     (h.as_json(), sid))
    return h


def read_header(session_id: str) -> SessionHeader | None:
    from core.runtime.db import connect
    sid = str(session_id or "").strip()
    with connect() as conn:
        _ensure_header_column(conn)
        row = conn.execute(
            "SELECT ledger_header FROM chat_sessions WHERE session_id = ?", (sid,)
        ).fetchone()
    raa = str(row[0] or "").strip() if row is not None else ""
    if not raa:
        return None
    try:
        d = json.loads(raa)
        return SessionHeader(str(d["session_id"]), int(d["generation"]),
                             str(d["created_at"]))
    except Exception:
        # Bevidst IKKE None: «findes ikke» og «kan ikke læses» er to forskellige
        # ting, og at slå dem sammen ville lade en ødelagt header se ud som en
        # ny session.
        raise SessionFormatError(FORMAT_CORRUPT,
                                 f"session {sid!r} har en header der ikke kan læses")


def classify_format(session_id: str) -> str:
    """Fire udfald der kan skelnes. En session uden header er `current`:
    den er ikke skrevet af ledgeren endnu, og det er ikke en fejl."""
    try:
        h = read_header(session_id)
    except SessionFormatError as e:
        return e.verdict
    if h is None:
        return FORMAT_CURRENT
    if h.generation > CURRENT_GENERATION:
        return FORMAT_FUTURE
    if h.generation in READABLE_GENERATIONS:
        return (FORMAT_CURRENT if h.generation == CURRENT_GENERATION
                else FORMAT_HISTORICAL)
    return FORMAT_CORRUPT


class SessionHandle:
    """Ejerskabet gjort til noget man holder. Brug som context manager."""

    def __init__(self, session_id: str, *, owner: str, token: int | None,
                 header: SessionHeader | None, format_verdict: str):
        self.session_id = str(session_id)
        self.owner = str(owner)
        self._token = token
        self.header = header
        self.format = format_verdict
        self._pending: list[dict[str, Any]] = []
        self._closed = False

    # ── egenskaber ───────────────────────────────────────────────────────
    @property
    def writable(self) -> bool:
        return self._token is not None and not self._closed

    @property
    def token(self) -> int | None:
        return self._token

    def seq(self) -> int:
        from core.runtime.db_session_ledger import current_seq
        return current_seq(self.session_id)

    # ── skrivning ────────────────────────────────────────────────────────
    def append(self, event: dict[str, Any]) -> None:
        """Læg i kø. Intet rører databasen før `flush()` eller `close()`.

        Køen findes fordi ledgerens append er ATOMISK pr. batch: en tur der
        skrev én hændelse ad gangen kunne efterlade en halv tur hvis processen
        døde midtvejs.
        """
        if self._closed:
            raise NotWritable("håndtaget er lukket")
        if self._token is None:
            raise NotWritable(
                f"session {self.session_id!r} er åbnet skrivebeskyttet"
                + (f" ({self.format})" if self.format != FORMAT_CURRENT else "")
            )
        self._pending.append(dict(event))

    def flush(self) -> int:
        """Skriv køen som ÉN batch. Returnerer antal skrevne hændelser."""
        if not self._pending:
            return 0
        if self._token is None:
            raise NotWritable("skrivebeskyttet håndtag kan ikke flushe")
        from core.runtime.db_session_ledger import append_session_events
        batch, self._pending = self._pending, []
        try:
            append_session_events(self.session_id, owner=self.owner,
                                  token=self._token, events=batch)
        except Exception:
            # Køen lægges TILBAGE. Mister vi lease'n, er hændelserne stadig i
            # hukommelsen og kan skrives af den der overtager — frem for at
            # være væk fordi en skrivning fejlede.
            self._pending = batch + self._pending
            raise
        self._projicer()
        return len(batch)

    def _projicer(self) -> None:
        """Kør projektionerne EFTER commit — kun for en kanonisk session.

        Her, og ikke i kaldestederne, fordi handlet er den eneste sanktionerede
        vej til at skrive i en `ledger`-session. Så gælder «hver append følges
        af en projektion» for enhver skriver der bruger den rigtige vej.

        For `shadow` og `legacy` gøres intet: dér er `chat_messages` sandheden
        og skrives direkte, og en projektion oveni ville skrive de samme rækker
        én gang til.

        En fejl her må ikke boble op: hændelsen ER committet, og en fejlet
        projektion er en projektion der er BAGUD — ikke en tabt skrivning.
        Næste flush eller et `rebuild()` henter den ind, fordi foldningen
        fortsætter fra sit checkpoint.
        """
        try:
            from core.runtime.db_session_ledger import storage_mode
            if storage_mode(self.session_id) != "ledger":
                return
            from core.services.projection_chat_messages import register
            from core.services.projection_runtime import registered, run_for_session
            if "chat_messages" not in registered():
                register()
            run_for_session(self.session_id)
        except Exception:
            logger.warning("session_handle: projektion fejlede efter append for %s",
                           self.session_id, exc_info=True)

    def close(self) -> None:
        """Flush og GIV LEASE'N FRA DIG. Uden det venter næste proces på
        udløbet af en lease ingen bruger."""
        if self._closed:
            return
        try:
            if self._token is not None:
                self.flush()
        finally:
            self._closed = True
            if self._token is not None:
                from core.runtime.db_session_ledger import release_write_lease
                try:
                    release_write_lease(self.session_id, owner=self.owner,
                                        token=self._token)
                except Exception:
                    logger.warning("session_handle: kunne ikke frigive lease", exc_info=True)
                self._token = None

    def __enter__(self) -> "SessionHandle":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _bedoem(session_id: str) -> tuple[str, SessionHeader | None]:
    dom = classify_format(session_id)
    if dom in (FORMAT_FUTURE, FORMAT_CORRUPT):
        # Fejler HØJT. En session der åbner sig halvt er værre end en der ikke
        # åbner sig: felter vi ikke kender ville forsvinde i stilhed.
        raise SessionFormatError(dom, f"session {session_id!r} har format {dom!r}")
    try:
        return dom, read_header(session_id)
    except SessionFormatError:
        raise


def open_readonly(session_id: str) -> SessionHandle:
    """Kig uden at tage noget. Skriver intet — heller ikke en lease-række."""
    dom, h = _bedoem(session_id)
    return SessionHandle(session_id, owner="", token=None, header=h,
                         format_verdict=dom)


def open_for_write(session_id: str, *, owner: str,
                   ttl_s: int | None = None) -> SessionHandle:
    """Tag skriveretten. Returnerer et skrivebeskyttet håndtag hvis en anden
    har den — aldrig et der lader som om det kan skrive."""
    from core.runtime.db_session_ledger import DEFAULT_LEASE_TTL_S, acquire_write_lease
    dom, h = _bedoem(session_id)
    if dom == FORMAT_HISTORICAL:
        # At skrive nyt format ind i en gammel session ville lave en blanding
        # ingen af delene kan læse.
        return SessionHandle(session_id, owner=owner, token=None, header=h,
                             format_verdict=dom)
    token = acquire_write_lease(session_id, owner=owner,
                                ttl_s=ttl_s or DEFAULT_LEASE_TTL_S)
    return SessionHandle(session_id, owner=owner, token=token, header=h,
                         format_verdict=dom)
