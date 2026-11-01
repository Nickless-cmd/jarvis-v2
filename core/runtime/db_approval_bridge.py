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


#: Tilstande hvor «godkendt» IKKE betyder «det skete». De skal nå samtalen:
#: ellers står der «Godkendt» på skærmen mens udfaldet var et andet.
DAARLIGT_UDFALD = frozenset({FAILED, OUTCOME_UNKNOWN, ABORTED_BEFORE_DISPATCH})


def _varsl_samtalen(approval_id: str) -> None:
    """Skriv udfaldet ind i samtalens historik — KUN når det ikke gik godt.

    ## Hvorfor (1/11-2026)

    Bjørn: «og hvis godkendelsen ikk gik igennem? det ved kun du = så skal
    det osse fikses». Han havde ret, og beviset lå i basen:
    `approval-c48e924bff23` blev godkendt 28/10 kl. 14:38:07 og erklæret
    `outcome_unknown` kl. 16:43:15. I to timer stod der «Godkendt» i
    samtalen mens ingen vidste om kommandoen havde kørt.

    `approval_claims` HAR udfaldet; `chat_messages` fik det aldrig. To flader
    med hver sin sandhed — og den ene var en løgn.

    ## Hvorfor kun de dårlige udfald

    En hændelse på den gode vej ville gøre tavshed meningsløs: så kan
    «ingen række» ikke længere betyde «gik godt».

    ## Hvorfor den aldrig kaster

    Samtalen er en ANDEN skrivning end tilstands-skiftet. Fejler den, er
    udfaldet stadig sandt i `approval_claims` — og et kast her ville få et
    allerede afsluttet kald til at se ud som om det fejlede.
    """
    try:
        info = state(approval_id)
        if not info:
            return
        tilstand = str(info.get("state") or "")
        if tilstand not in DAARLIGT_UDFALD:
            return
        sid = str(info.get("session_id") or "").strip()
        if not sid:
            return
        from core.services.approval_runtime import persist_approval_message

        persist_approval_message(
            approval_id=str(approval_id),
            kort={
                "session_id": sid,
                "tool_name": str(info.get("tool_name") or ""),
                "run_id": str(info.get("run_id") or ""),
                "created_at": str(info.get("created_at") or ""),
            },
            status=tilstand,
        )
    except Exception:  # samtalen er sekundaer — tilstanden er allerede skrevet
        logger.debug("kunne ikke varsle samtalen om udfaldet af %s",
                     approval_id, exc_info=True)


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
        ramt = cur.rowcount == 1
    # UDEN FOR transaktionen: samtalen er en anden skrivning, og en fejl deri
    # må ikke rulle tilstands-skiftet tilbage.
    if ramt and not ok:
        _varsl_samtalen(aid)
    return ramt


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
    # Samme regel som i `settle`: uden for transaktionen, og kun naar udfaldet
    # ikke er det gode. `aborted_before_dispatch` betyder at handlingen ALDRIG
    # skete — også det skal stå i samtalen, ikke kun i basen.
    _varsl_samtalen(aid)
    return ny


def state(approval_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure(conn)
        row = conn.execute(
            "SELECT approval_id, kind, tool_name, invocation_digest, state, run_id, "
            "session_id, created_at, expires_at, decided_at, claimed_at, "
            "settled_at, detail FROM approval_claims WHERE approval_id = ?",
            (str(approval_id or "").strip(),)).fetchone()
    if row is None:
        return None
    n = ("approval_id", "kind", "tool_name", "invocation_digest", "state", "run_id",
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


#: En afsendelse der har staaet i `dispatching` saa laenge, er ikke i gang.
#: To gange en godkendelses levetid; intet vaerktoej her koerer i naerheden af
#: det (operator_bash har 55 s, bash-sessionen 300 s).
FORAELDRELOES_EFTER_S = 2 * 3600


def abandon_orphaned_dispatching(now: datetime | None = None, *,
                                 older_than_s: int = FORAELDRELOES_EFTER_S) -> int:
    """Afslut `dispatching`-poster hvis afsender er vaek. → `outcome_unknown`.

    ## Hvorfor (15/9-2026)

    `approval-5815853a103c` stod i `dispatching` fra 14/9 kl. 18:22 og for
    evigt. Vaerten crashede to gange paa tre minutter; efter foerste crash
    ryddede boot-reconcileren koerslen op (`interrupted`), og DEREFTER blev
    godkendelsen overtaget og kommandoen sendt — midt i andet crash. Den faldt
    mellem alle tre mekanismer: `abandon_run` var allerede loebet, `expire_stale`
    roerer med vilje aldrig `dispatching`, og ingen `settle` kom.

    ## Hvorfor det er sikkert

    Udfaldet ER ukendt, og `outcome_unknown` siger praecis det. Det er ikke et
    genforsoeg: K7 (`prior_unknown_outcome`) nægter netop et automatisk nyt
    forsoeg paa en digest i den tilstand. Posten holder bare op med at ligne
    noget der stadig er i gang.
    """
    nu = now or datetime.now(UTC)
    graense = (nu - timedelta(seconds=int(older_than_s))).isoformat()
    with connect() as conn:
        _ensure(conn)
        raekker = list(conn.execute(
            "SELECT approval_id FROM approval_claims "
            "WHERE state = ? AND claimed_at IS NOT NULL AND claimed_at < ?",
            (DISPATCHING, graense)))
    antal = 0
    for (aid,) in raekker:
        if abandon(aid, detail="forældreløs: ingen afslutning efter afsendelsen") == OUTCOME_UNKNOWN:
            antal += 1
    return antal


def abandon_run(run_id: str, *, detail: str = "") -> dict[str, int]:
    """Opgiv ALLE uafklarede poster for et doedt run — K6.

    Broen kunne skelne fra dag ét, men ingen kaldte `abandon()`. En skelnen
    der aldrig foretages er ikke en skelnen: posterne blev liggende som
    `dispatching` for evigt, og saa betyder «udfald ukendt» ingenting.

    Returnerer antal pr. udfald, saa kalderen kan sige det hoejt.
    """
    rid = str(run_id or "").strip()
    if not rid:
        return {}
    with connect() as conn:
        _ensure(conn)
        raekker = list(conn.execute(
            "SELECT approval_id FROM approval_claims "
            "WHERE run_id = ? AND state IN (?, ?, ?)",
            (rid, PENDING, APPROVED, PREPARED)))
        raekker += list(conn.execute(
            "SELECT approval_id FROM approval_claims "
            "WHERE run_id = ? AND state = ?", (rid, DISPATCHING)))

    ud: dict[str, int] = {}
    for (aid,) in raekker:
        udfald = abandon(aid, detail=detail)
        if udfald:
            ud[udfald] = ud.get(udfald, 0) + 1
    return ud


def prior_unknown_outcome(tool_name: str,
                          arguments: dict[str, Any] | None) -> list[str]:
    """Har PRAECIS dette kald allerede efterladt et ukendt udfald?

    Broen afviste allerede en gen-overtagelse af den SAMME post. Men et
    genforsoeg kommer sjaeldent under samme id — det kommer som et NYT kald der
    goer det samme. Uden et opslag paa digesten ville det sejle igennem, og
    saa er «vi ved ikke om det skete» blevet til «det skete maaske to gange».

    Returnerer id'erne, saa den der spoerger kan sige HVILKE.
    """
    d = invocation_digest(tool_name, arguments)
    with connect() as conn:
        _ensure(conn)
        return [r[0] for r in conn.execute(
            "SELECT approval_id FROM approval_claims "
            "WHERE invocation_digest = ? AND state = ? "
            "ORDER BY created_at DESC LIMIT 20",
            (d, OUTCOME_UNKNOWN))]
