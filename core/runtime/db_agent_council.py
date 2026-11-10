"""Raad paa agentmotoren (agent-contract-v1 F5, spec 5.1 + 7.1 om raad).

Et raad er IKKE en egen runtime: det er et moenster over de almindelige assignments. Tabellen her holder kun
sammenhaengen - hvilke medlems-assignments hoerer til raadet, og hvilket syntese-assignment der blev oprettet
da ALLE medlemmer var terminale. Selve arbejdet, udfaldene og beskederne ligger i assignment/outbox-tabellerne.

    provisioning -> raekken er oprettet, men medlemmerne er endnu ikke skrevet ind
    gathering  -> medlemmerne arbejder
    synthesizing -> alle medlemmer er terminale; syntese-assignmentet er oprettet
    done       -> syntesen er terminal
    cancelled  -> raadet kunne ikke samles (intet halvt raad)

``provisioning`` findes fordi ``create()`` indsatte raekken med ``members_json='[]'``
og ``advance()`` derefter kunne se ``([], True)``: nul medlemmer, alle "terminale".
Det gav en syntese over et tomt grundlag. Saa laenge raekken er i ``provisioning``,
er den ikke et raad nogen supervisor maa avancere.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_agent_contract import ContractError, _conn, _now_iso

logger = logging.getLogger(__name__)

PROVISIONING = "provisioning"
GATHERING, SYNTHESIZING, DONE, CANCELLED = "gathering", "synthesizing", "done", "cancelled"

#: Statusser hvor raadet stadig er i live og en supervisor skal kigge paa det.
#: ``open_councils()`` bygger sin IN-liste fra denne maengde — en ny aaben status
#: kan derfor ikke glemmes i en haandskrevet literal.
OPEN_STATUSES: frozenset[str] = frozenset({PROVISIONING, GATHERING, SYNTHESIZING})

#: Hvor laenge en raekke maa staa i ``provisioning`` foer den regnes for forladt.
#: ``convene()`` skriver medlemmerne ind i samme synkrone loekke som den opretter raadet,
#: saa en aktiv samling tager sekunder — ikke minutter. 5 minutter er rigelig luft til
#: seks medlemmer, ogsaa naar dispatch er langsom.
PROVISIONING_GRACE_SECONDS = 300


def ensure_council_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_councils (
            council_id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            parent_agent_id TEXT NOT NULL DEFAULT '',
            parent_run_id TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL,
            facts TEXT NOT NULL DEFAULT '',
            synthesis_role TEXT NOT NULL DEFAULT 'synthesizer',
            members_json TEXT NOT NULL DEFAULT '[]',
            synthesis_assignment_id TEXT NOT NULL DEFAULT '',
            budget_tokens INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_councils_idem ON agent_councils"
                 "(owner_user_id, origin_session_id, idempotency_key) WHERE idempotency_key != ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_councils_status ON agent_councils(status)")
    # Additive kolonner: en eksisterende tabel maa ikke tabe data for at faa dem.
    # Samme moenster som db_agent_deadlines.ensure_deadline_columns().
    have = {r["name"] for r in conn.execute("PRAGMA table_info(agent_councils)")}
    for name in ("stalled_after_at", "synthesis_wake_registered_at"):
        if name not in have:
            conn.execute(f"ALTER TABLE agent_councils ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")


def _view(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    out = dict(r)
    out["members"] = json.loads(out.pop("members_json") or "[]")
    return out


def create(*, owner_user_id: str, origin_session_id: str, parent_run_id: str, parent_agent_id: str, topic: str,
           facts: str, synthesis_role: str, budget_tokens: int, idempotency_key: str,
           council_id: str | None = None) -> dict[str, Any]:
    cid = council_id or f"council-{uuid.uuid4().hex[:16]}"
    now = _now_iso()
    conn = _conn()
    conn.execute(
        "INSERT INTO agent_councils (council_id, owner_user_id, origin_session_id, parent_agent_id, parent_run_id, "
        "topic, facts, synthesis_role, budget_tokens, idempotency_key, status, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (cid, owner_user_id, origin_session_id, parent_agent_id, parent_run_id, topic, facts, synthesis_role,
         int(budget_tokens), idempotency_key, PROVISIONING, now, now))
    conn.commit()
    return get(cid, owner_user_id) or {}


def get(council_id: str, owner_user_id: str) -> dict[str, Any] | None:
    """Ejerfiltreret: et andet raad end ejerens er ``None``."""
    return _view(_conn().execute("SELECT * FROM agent_councils WHERE council_id=? AND owner_user_id=?",
                                 (council_id, owner_user_id)).fetchone())


def find_by_key(owner_user_id: str, origin_session_id: str, key: str) -> dict[str, Any] | None:
    if not key:
        return None
    return _view(_conn().execute(
        "SELECT * FROM agent_councils WHERE owner_user_id=? AND origin_session_id=? AND idempotency_key=?",
        (owner_user_id, origin_session_id, key)).fetchone())


def set_members(council_id: str, members: list[dict[str, Any]]) -> None:
    """Gem medlemmerne og flyt raadet fra ``provisioning`` til ``gathering``.

    Skiftet sker KUN fra ``provisioning``. Er raadet allerede ``gathering`` (en retry)
    eller ``cancelled`` (en afbrudt samling), er der intet at flytte — og det er ikke
    en fejl. Derfor ignoreres ``transition``s returvaerdi her.

    Medlemmerne og statusskiftet skrives i ÉN UPDATE. Blev de skrevet hver for sig, kunne
    en samtidig supervisor se en raekke i ``provisioning`` med en fyldt liste — eller en
    fejlet anden halvdel efterlade raekken fast med medlemmer men uden status.
    """
    conn = _conn()
    now = _now_iso()
    payload = json.dumps(members, ensure_ascii=False)
    if members:
        # En TOM liste er ikke et raad. Den gemmes (saa _abandon kan bevare historikken),
        # men den maa ikke flytte raekken til ``gathering``: et raad i gathering uden
        # medlemmer er praecis den tilstand der gav en syntese over et tomt grundlag.
        conn.execute(
            "UPDATE agent_councils SET members_json=?, "
            "status=CASE WHEN status=? THEN ? ELSE status END, updated_at=? WHERE council_id=?",
            (payload, PROVISIONING, GATHERING, now, council_id))
    else:
        conn.execute("UPDATE agent_councils SET members_json=?, updated_at=? WHERE council_id=?",
                     (payload, now, council_id))
    conn.commit()


def transition(council_id: str, *, frm: str, to: str, synthesis_assignment_id: str = "") -> bool:
    """Atomisk statusskifte; ``False`` hvis en anden supervisor allerede har flyttet raadet."""
    conn = _conn()
    cur = conn.execute("UPDATE agent_councils SET status=?, synthesis_assignment_id=CASE WHEN ?!='' THEN ? "
                       "ELSE synthesis_assignment_id END, updated_at=? WHERE council_id=? AND status=?",
                       (to, synthesis_assignment_id, synthesis_assignment_id, _now_iso(), council_id, frm))
    conn.commit()
    return cur.rowcount == 1


def open_councils() -> list[dict[str, Any]]:
    """Alle raad en supervisor stadig skal kigge paa — bygget fra ``OPEN_STATUSES``.

    En ny aaben status kan derfor ikke glemmes i en haandskrevet literal; den skal
    blot med i maengden.
    """
    statuses = sorted(OPEN_STATUSES)
    placeholders = ",".join("?" for _ in statuses)
    rows = _conn().execute(f"SELECT * FROM agent_councils WHERE status IN ({placeholders}) ORDER BY created_at",
                           statuses).fetchall()
    return [_view(r) for r in rows]  # type: ignore[misc]


def _parse_ts(value: Any) -> datetime | None:
    """ISO-tidsstempel, eller ``None`` hvis det ikke kan laeses."""
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:  # ulaeseligt tidsstempel: behandles som "kan ikke vurderes"
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def touch(council_id: str) -> None:
    """Markér at samlingen stadig arbejder.

    ``convene()`` skriver ikke til raekken mens den dispatcher medlemmer, saa alderen
    alene kan ikke skelne en aktiv samling fra en efterladt. Uden dette kan en langsom
    samling blive lukket under foedderne — og dens medlemmer skrevet ind i en
    ``cancelled``-raekke, hvor de fortsætter uden ejer.
    """
    conn = _conn()
    conn.execute("UPDATE agent_councils SET updated_at=? WHERE council_id=?", (_now_iso(), council_id))
    conn.commit()


def is_stale_provisioning(c: dict[str, Any], *, now: datetime | None = None) -> bool:
    """Er raekken efterladt i ``provisioning`` — oprettet, men aldrig samlet?

    Uden dette kan en raekke der blev oprettet men aldrig fik medlemmer (genstart midt i
    samlingen) hverken blive faerdig eller forsvinde: ``advance()`` springer den over for
    evigt, og dens idempotensnoegle laaser en retry ude med IDEMPOTENCY_CONFLICT.

    Alder maales fra det NYESTE tidsstempel, ikke fra ``created_at``: ``convene()`` rører
    ``updated_at`` gennem ``touch()`` foer hver dispatch, saa en aktiv samling holder sig
    frisk uanset hvor laenge den tager.
    """
    if c.get("status") != PROVISIONING:
        return False
    stamps = [d for d in (_parse_ts(c.get("created_at")), _parse_ts(c.get("updated_at"))) if d]
    if not stamps:
        # Ingen laesbar tid paa en aaben raekke: den kan ikke blive faerdig, og vi kan ikke
        # afgoere om den er aktiv. Den lukkes — ellers genindfoerer "lad staa" praecis den
        # permanente laas aendringen skulle fjerne. ``_now_iso()`` skriver altid et gyldigt
        # tidsstempel, saa dette rammer kun korrupte eller importerede raekker.
        return True
    return ((now or datetime.now(UTC)) - max(stamps)).total_seconds() > PROVISIONING_GRACE_SECONDS


def abandon_stale_provisioning(council_id: str, *, now: datetime | None = None) -> bool:
    """Luk en forladt samling og FRIGIV dens idempotensnoegle.

    Noeglen ryddes, saa et nyt forsoeg kan bruge den — raekken selv bliver som historik.
    Kun raekker uden medlemmer rammes: er listen ikke tom, er samlingen naaet laengere end
    det punkt hvor et retry er det rigtige svar.
    """
    row = _conn().execute("SELECT * FROM agent_councils WHERE council_id=?", (council_id,)).fetchone()
    c = _view(row)
    if c is None or c["members"] or not is_stale_provisioning(c, now=now):
        return False
    conn = _conn()
    cur = conn.execute(
        "UPDATE agent_councils SET status=?, idempotency_key='', updated_at=? "
        "WHERE council_id=? AND status=? AND members_json IN ('[]', '')",
        (CANCELLED, _now_iso(), council_id, PROVISIONING))
    conn.commit()
    return cur.rowcount == 1


def release_key(council_id: str) -> None:
    """Frigiv idempotensnoeglen paa et raad der ikke blev samlet.

    Noeglen sidder i en UNIQUE INDEX. Bliver den ikke ryddet, laaser den en retry ude med
    IDEMPOTENCY_CONFLICT — for evigt, fordi raadet er ``cancelled`` og aldrig bliver
    samlet igen. Raekken selv bliver som historik.
    """
    conn = _conn()
    conn.execute("UPDATE agent_councils SET idempotency_key='' WHERE council_id=?", (council_id,))
    conn.commit()


def require(council_id: str, owner_user_id: str) -> dict[str, Any]:
    c = get(council_id, owner_user_id)
    if c is None:
        raise ContractError("INVALID_SCOPE", "ukendt raad")
    return c
