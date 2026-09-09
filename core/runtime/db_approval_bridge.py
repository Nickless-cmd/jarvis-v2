"""Godkendelses-broen — én beslutning, bundet til ÉT kald, brugt ÉN gang.

Spec: Fase 3, K4 og K5.

    «approval claim and `dispatching` commit in one transaction before crossing
     the provider boundary»
    «it stores the exact invocation digest and atomically consumes one decision»

## Hvad der var galt

I dag er en godkendelse nøglet på `approval_id` alene:

    pending = _PENDING_APPROVALS.pop(approval_id, None)

To huller følger af det.

**Godkendelsen er ikke bundet til kaldet.** Ændrede argumenterne sig mellem at
kortet blev vist og at der blev klikket ja, ville godkendelsen stadig gælde.
Man sagde ja til «slet /tmp/x» og fik «slet /». Ingen kode ville opdage det,
fordi ingen gemte hvad man sagde ja TIL.

**Beslutningen forbruges ikke atomisk sammen med afsendelsen.** `pop`, så et
tjek, så `execute_tool_force`. Mellem dem er der et vindue. To arbejdere kan
begge nå frem, og et nedbrud imellem efterlader en tilstand ingen kan aflæse:
skete handlingen, eller gjorde den ikke?

## Hvordan broen lukker dem

Digesten over `(tool_name, arguments)` gemmes når godkendelsen BEDES om, og
verificeres når den BRUGES. Argumenterne kan ikke skifte undervejs uden at
kravet falder.

Og overtagelsen er ÉN sætning:

    UPDATE … SET state='dispatching' WHERE state='approved' AND digest=?

Enten rammer den én række, eller også ingen. Der er ikke noget mellem. Vinder
man overtagelsen, ejer man afsendelsen — og tilstanden `dispatching` står i
databasen FØR udbyder-grænsen krydses.

## Hvorfor `dispatching` er en tilstand og ikke et flag

Fordi et nedbrud skal kunne aflæses bagefter. Spec'ens K6 kræver at
`aborted_before_dispatch` kan skelnes fra `outcome_unknown`:

  * står den på `approved` da runnet døde → handlingen skete ALDRIG
  * står den på `dispatching` → vi ved det ikke, og K7 siger at et
    ikke-idempotent kald i den tilstand ALDRIG må prøves igen automatisk

Et flag kan ikke bære den forskel. En tilstand kan.
"""
from __future__ import annotations

import hashlib
import json as _json
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_core import connect

logger = logging.getLogger(__name__)

# ── tilstande ────────────────────────────────────────────────────────────
#: En invokation der er FORBEREDT uden at kraeve godkendelse. Auto-godkendte
#: kald der stadig AENDRER noget — fx en workspace-skrivning — havde ellers
#: ingen post overhovedet, og et nedbrud dér efterlod en aegte ukendt tilstand.
PREPARED = "prepared"
PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"
DISPATCHING = "dispatching"
COMPLETED = "completed"
FAILED = "failed"
EXPIRED = "expired"
#: Runnet døde mens beslutningen stadig ventede — handlingen skete ALDRIG.
ABORTED_BEFORE_DISPATCH = "aborted_before_dispatch"
#: Vi nåede at afsende, men så aldrig udfaldet. Se K7: prøv ALDRIG igen
#: automatisk for et ikke-idempotent kald.
OUTCOME_UNKNOWN = "outcome_unknown"

TERMINALE = (DENIED, COMPLETED, FAILED, EXPIRED, ABORTED_BEFORE_DISPATCH,
             OUTCOME_UNKNOWN)

DEFAULT_TTL_S = 3600


class ApprovalRefused(RuntimeError):
    """Overtagelsen blev nægtet. Beskeden siger hvorfor."""


def invocation_digest(tool_name: str, arguments: dict[str, Any] | None) -> str:
    """Digest over DET KALD der blev sagt ja til.

    Nøgler sorteres, så to ens kald altid giver samme digest. Argumenter der
    starter med `_` udelades: de er runtime-plumbing (`_runtime_session_id`,
    `_runtime_trust_all`) og ikke en del af hvad brugeren så på kortet.
    """
    rene = {k: v for k, v in dict(arguments or {}).items()
            if not str(k).startswith("_")}
    try:
        krop = _json.dumps(rene, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), default=str)
    except Exception:
        krop = repr(sorted(rene.items()))
    raa = f"{str(tool_name or '').strip()}\x00{krop}"
    return "sha256:" + hashlib.sha256(raa.encode("utf-8")).hexdigest()


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_claims (
            approval_id       TEXT PRIMARY KEY,
            -- 'approval' = et menneske skal sige ja. 'auto' = kaldet aendrer
            -- noget, men er auto-godkendt; det registreres for at kunne skelne
            -- «skete aldrig» fra «udfaldet er ukendt» efter et nedbrud.
            kind              TEXT NOT NULL DEFAULT 'approval',
            tool_name         TEXT NOT NULL,
            invocation_digest TEXT NOT NULL,
            state             TEXT NOT NULL,
            run_id            TEXT NOT NULL DEFAULT '',
            session_id        TEXT NOT NULL DEFAULT '',
            created_at        TEXT NOT NULL,
            expires_at        TEXT NOT NULL,
            decided_at        TEXT,
            claimed_at        TEXT,
            settled_at        TEXT,
            detail            TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_approval_claims_state "
                 "ON approval_claims(state)")
    # `CREATE TABLE IF NOT EXISTS` tilfoejer ALDRIG en soejle til en tabel der
    # allerede findes. Set paa CT105: tabellen var uden `kind` efter deploy,
    # og INSERT'en ville have fejlet paa foerste auto-registrering — i en
    # try/except der loeb videre. Migrationen skal staa her, ikke i skemaet.
    try:
        soejler = {r[1] for r in conn.execute("PRAGMA table_info(approval_claims)")}
        if "kind" not in soejler:
            conn.execute("ALTER TABLE approval_claims ADD COLUMN "
                         "kind TEXT NOT NULL DEFAULT 'approval'")
    except sqlite3.Error:
        pass


def _nu() -> str:
    return datetime.now(UTC).isoformat()


def request(approval_id: str, *, tool_name: str, arguments: dict[str, Any] | None,
            run_id: str = "", session_id: str = "",
            ttl_s: int = DEFAULT_TTL_S) -> str:
    """Bed om en godkendelse. Gemmer digesten over kaldet. Returnerer digesten."""
    aid = str(approval_id or "").strip()
    if not aid:
        raise ValueError("approval_id mangler")
    d = invocation_digest(tool_name, arguments)
    nu = datetime.now(UTC)
    with connect() as conn:
        _ensure(conn)
        conn.execute(
            "INSERT INTO approval_claims (approval_id, tool_name, invocation_digest, "
            "state, run_id, session_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(approval_id) DO NOTHING",
            (aid, str(tool_name or ""), d, PENDING, str(run_id or ""),
             str(session_id or ""), nu.isoformat(),
             (nu + timedelta(seconds=max(1, int(ttl_s)))).isoformat()),
        )
    return d


def prepare(invocation_id: str, *, tool_name: str,
            arguments: dict[str, Any] | None, run_id: str = "",
            session_id: str = "", ttl_s: int = DEFAULT_TTL_S) -> str:
    """Registrér en invokation der IKKE kraever godkendelse.

    Samme tilstandsmaskine, samme atomiske overtagelse — kun beslutnings-
    skridtet springes over. Det er dét der giver K3 («prepared commits before
    dispatch») for de kald ingen bliver spurgt om.

    MAALT 9/9-2026: 1.086 vaerktoejskald i doegnet, hvoraf de fleste er
    LAESNINGER. Derfor registreres kun kald der faktisk aendrer noget — en
    skrivning pr. `ls` ville vaere den samme fejl som en traad pr.
    foelelses-signal.
    """
    iid = str(invocation_id or "").strip()
    if not iid:
        raise ValueError("invocation_id mangler")
    d = invocation_digest(tool_name, arguments)
    nu = datetime.now(UTC)
    with connect() as conn:
        _ensure(conn)
        conn.execute(
            "INSERT INTO approval_claims (approval_id, kind, tool_name, "
            "invocation_digest, state, run_id, session_id, created_at, expires_at) "
            "VALUES (?, 'auto', ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(approval_id) DO NOTHING",
            (iid, str(tool_name or ""), d, PREPARED, str(run_id or ""),
             str(session_id or ""), nu.isoformat(),
             (nu + timedelta(seconds=max(1, int(ttl_s)))).isoformat()),
        )
    return d


def decide(approval_id: str, *, approved: bool, detail: str = "") -> bool:
    """Mennesket har klikket. Flytter `pending` → `approved`/`denied`.

    Kun fra `pending`: en beslutning der allerede er truffet, kan ikke gøres om
    ved at klikke igen.
    """
    aid = str(approval_id or "").strip()
    with connect() as conn:
        _ensure(conn)
        cur = conn.execute(
            "UPDATE approval_claims SET state = ?, decided_at = ?, detail = ? "
            "WHERE approval_id = ? AND state = ?",
            (APPROVED if approved else DENIED, _nu(), str(detail or ""), aid, PENDING),
        )
        return cur.rowcount == 1


def claim(approval_id: str, *, tool_name: str,
          arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Overtag godkendelsen OG commit `dispatching` — i ÉN sætning.

    Kaster `ApprovalRefused` hvis der ikke er noget at overtage. Kalderen må
    IKKE krydse udbyder-grænsen uden at dette kald er lykkedes.
    """
    aid = str(approval_id or "").strip()
    d = invocation_digest(tool_name, arguments)
    nu = _nu()
    with connect() as conn:
        _ensure(conn)
        # ÉN sætning. Enten rammer den én række, eller også ingen — der er
        # ikke noget mellem, og derfor kan to arbejdere ikke begge vinde.
        cur = conn.execute(
            "UPDATE approval_claims SET state = ?, claimed_at = ? "
            "WHERE approval_id = ? AND state IN (?, ?) AND invocation_digest = ? "
            "AND expires_at > ?",
            (DISPATCHING, nu, aid, APPROVED, PREPARED, d, nu),
        )
        if cur.rowcount == 1:
            return {"approval_id": aid, "state": DISPATCHING, "digest": d,
                    "claimed_at": nu}
        row = conn.execute(
            "SELECT state, invocation_digest, expires_at FROM approval_claims "
            "WHERE approval_id = ?", (aid,)).fetchone()

    if row is None:
        raise ApprovalRefused(f"ukendt godkendelse: {aid!r}")
    tilstand, gemt, udloeb = str(row[0]), str(row[1]), str(row[2])
    if gemt != d:
        # DET vigtigste afslag. Man sagde ja til noget andet end det der nu
        # forsøges — og uden digesten ville ingen have opdaget det.
        raise ApprovalRefused(
            f"godkendelsen gælder et ANDET kald: der blev sagt ja til "
            f"{gemt[:23]}…, men dette er {d[:23]}…"
        )
    if tilstand == DISPATCHING:
        raise ApprovalRefused("godkendelsen er allerede overtaget — den gælder én gang")
    if tilstand in TERMINALE:
        raise ApprovalRefused(f"godkendelsen er afsluttet som {tilstand!r}")
    if tilstand == PENDING:
        raise ApprovalRefused("ingen har besluttet endnu")
    if udloeb <= _nu():
        raise ApprovalRefused("godkendelsen er udløbet")
    raise ApprovalRefused(f"kunne ikke overtages (tilstand {tilstand!r})")


def settle(approval_id: str, *, ok: bool, detail: str = "") -> bool:
    """Afslut efter afsendelsen. `dispatching` → `completed`/`failed`."""
    aid = str(approval_id or "").strip()
    with connect() as conn:
        _ensure(conn)
        cur = conn.execute(
            "UPDATE approval_claims SET state = ?, settled_at = ?, detail = ? "
            "WHERE approval_id = ? AND state = ?",
            (COMPLETED if ok else FAILED, _nu(), str(detail or ""), aid, DISPATCHING),
        )
        return cur.rowcount == 1


def abandon(approval_id: str, *, detail: str = "") -> str:
    """Runnet døde. Sig HVAD vi ved — ikke hvad vi håber.

    Fra `pending`/`approved`: handlingen skete aldrig → `aborted_before_dispatch`.
    Fra `dispatching`: vi nåede at afsende og så aldrig udfaldet →
    `outcome_unknown`. K7 forbyder et automatisk genforsøg i den tilstand for
    et ikke-idempotent kald.
    """
    aid = str(approval_id or "").strip()
    with connect() as conn:
        _ensure(conn)
        row = conn.execute("SELECT state FROM approval_claims WHERE approval_id = ?",
                           (aid,)).fetchone()
        if row is None:
            return ""
        tilstand = str(row[0])
        if tilstand in TERMINALE:
            return tilstand
        # PREPARED og APPROVED betyder begge at vi ALDRIG naaede at afsende.
        ny = OUTCOME_UNKNOWN if tilstand == DISPATCHING else ABORTED_BEFORE_DISPATCH
        conn.execute(
            "UPDATE approval_claims SET state = ?, settled_at = ?, detail = ? "
            "WHERE approval_id = ? AND state = ?",
            (ny, _nu(), str(detail or ""), aid, tilstand),
        )
        return ny


def state(approval_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure(conn)
        row = conn.execute(
            "SELECT approval_id, tool_name, invocation_digest, state, run_id, "
            "session_id, created_at, expires_at, decided_at, claimed_at, "
            "settled_at, detail FROM approval_claims WHERE approval_id = ?",
            (str(approval_id or "").strip(),)).fetchone()
    if row is None:
        return None
    n = ("approval_id", "tool_name", "invocation_digest", "state", "run_id",
         "session_id", "created_at", "expires_at", "decided_at", "claimed_at",
         "settled_at", "detail")
    return dict(zip(n, row))


def expire_stale(now: datetime | None = None) -> int:
    """Marker udløbne, ikke-besluttede godkendelser. Rører ALDRIG `dispatching`:
    en afsendelse der er i gang, udløber ikke — dens udfald er stadig ukendt."""
    nu = (now or datetime.now(UTC)).isoformat()
    with connect() as conn:
        _ensure(conn)
        cur = conn.execute(
            "UPDATE approval_claims SET state = ?, settled_at = ? "
            "WHERE state IN (?, ?, ?) AND expires_at <= ?",
            (EXPIRED, nu, PENDING, APPROVED, PREPARED, nu))
        return int(cur.rowcount)
