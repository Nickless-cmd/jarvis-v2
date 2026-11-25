"""FTS5 full-text search over session summaries and chat messages.

Memory repair 2026-09-04 (R5): "hvad sagde du i går om X" was a guess — no
full-text index existed over the 14.845 session summaries or the chat
history. SQLite on CT105 and locally is built with FTS5, so two external-
content FTS tables mirror the base tables through triggers. Base tables stay
the source of truth; the FTS tables can be rebuilt at any time with
``rebuild_fts()``.

Everything here is best-effort: if FTS5 is unavailable the ensure step logs
and the search functions return [].
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
from typing import Any

from core.runtime.db import connect

logger = logging.getLogger(__name__)

_FTS_SPECS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    # (fts table, base table, rowid column, indexed columns)
    ("session_summaries_fts", "session_summaries", "id", ("summary", "key_topics", "decisions_made")),
    ("chat_messages_fts", "chat_messages", "id", ("content",)),
)

# 24/10-2026: ``ensure_fts_tables`` slutter med ``conn.commit()``, så HVER
# søgning åbnede en skrivetransaktion for at committe ingenting. Målt med
# py-spy over 135 spidser: `search_session_summaries` stod 10+ sekunder i
# recall-stien, mens det isolerede kald var 13–117 ms — forskellen var
# ventetid på skrivelåsen (``busy_timeout`` 5 s) delt med 30+ skrivende tråde.
#
# Tabellerne og triggerne forsvinder ikke midt i en kørsel, så resultatet
# caches per proces. Cachen fyldes KUN med det der faktisk blev klar: mangler
# en base-tabel (fx ved første opstart før migrationen), kører den igen næste
# gang i stedet for at huske en ufuldstændig tilstand.
_READY_LOCK = threading.Lock()
_READY: dict[str, set[str]] = {}


def _db_key(conn: sqlite3.Connection) -> str:
    """Identiteten på den database forbindelsen peger på.

    Cachen MÅ ikke være proces-global alene: to forbindelser kan pege på hver
    sin database (tests bruger ``:memory:``), og så ville den ene arve den
    andens «tabellerne findes». Målt 24/10-2026: uden denne nøgle faldt syv
    FTS-tests, fordi cachen huskede tabeller fra en anden in-memory-base.

    Tom streng = ingen fil (in-memory) → cachen bruges ikke, den ægte vej
    kører hver gang. Det er billigt og altid korrekt.
    """
    try:
        for _seq, name, path in conn.execute("PRAGMA database_list").fetchall():
            if name == "main":
                return str(path or "")
    except Exception:  # En forbindelse uden database_list er ikke cache-bar.
        return ""
    return ""


def reset_fts_ready_cache() -> None:
    """Glem den proces-lokale 'tabellerne findes'-cache (til tests / efter rebuild)."""
    with _READY_LOCK:
        _READY.clear()

_TOKEN_RE = re.compile(r"[0-9A-Za-zÆØÅæøå_\-.]{2,}")


def fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE IF EXISTS _fts5_probe")
        return True
    except sqlite3.OperationalError:  # FTS5 is optional; absence is a supported capability state.
        return False


def _base_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def ensure_fts_tables(conn: sqlite3.Connection, *, force: bool = False) -> list[str]:
    """Create the FTS tables + sync triggers for every base table that exists.

    Returns the names of FTS tables that are ready. Safe to call repeatedly.

    24/10-2026: resultatet caches per proces. Uden cachen åbnede hver søgning
    en skrivetransaktion (funktionen slutter med ``conn.commit()``), og i
    recall-stien ventede den op til ``busy_timeout`` på skrivelåsen. Kald med
    ``force=True`` når tilstanden bevidst ændres (fx ``rebuild_fts``).
    """
    key = _db_key(conn)
    if not force and key:
        with _READY_LOCK:
            cached = _READY.get(key)
            # Svar KUN når cachen er komplet. En delvis cache (fx fordi
            # chat_messages endnu ikke fandtes) må ikke blokere den ægte vej —
            # målt 24/10-2026 faldt en vagt på præcis det: cachen huskede
            # «session_summaries_fts findes» og opdagede aldrig den nye tabel.
            if cached and len(cached) == len(_FTS_SPECS):
                return [fts for fts, _b, _r, _c in _FTS_SPECS if fts in cached]
    ready: list[str] = []
    # Read-only probes (scripts/memory_probe.py mod en live DB) må ikke oprette
    # tabeller/triggere: JARVIS_FTS_READONLY=1 → brug kun det der allerede findes.
    if os.environ.get("JARVIS_FTS_READONLY") == "1":
        found = [fts for fts, _b, _r, _c in _FTS_SPECS if _base_table_exists(conn, fts)]
        if key:
            with _READY_LOCK:
                _READY.setdefault(key, set()).update(found)
        return found
    if not fts5_available(conn):
        logger.warning("db_fts: FTS5 not available in this SQLite build")
        return ready
    for fts, base, rowid_col, cols in _FTS_SPECS:
        if not _base_table_exists(conn, base):
            continue
        existed = _base_table_exists(conn, fts)
        col_list = ", ".join(cols)
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {fts} USING fts5("
            f"{col_list}, content='{base}', content_rowid='{rowid_col}', tokenize='unicode61')"
        )
        new_vals = ", ".join(f"new.{c}" for c in cols)
        old_vals = ", ".join(f"old.{c}" for c in cols)
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {base}_fts_ai AFTER INSERT ON {base} BEGIN "
            f"INSERT INTO {fts}(rowid, {col_list}) VALUES (new.{rowid_col}, {new_vals}); END"
        )
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {base}_fts_ad AFTER DELETE ON {base} BEGIN "
            f"INSERT INTO {fts}({fts}, rowid, {col_list}) VALUES ('delete', old.{rowid_col}, {old_vals}); END"
        )
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {base}_fts_au AFTER UPDATE ON {base} BEGIN "
            f"INSERT INTO {fts}({fts}, rowid, {col_list}) VALUES ('delete', old.{rowid_col}, {old_vals}); "
            f"INSERT INTO {fts}(rowid, {col_list}) VALUES (new.{rowid_col}, {new_vals}); END"
        )
        if not existed:
            conn.execute(f"INSERT INTO {fts}({fts}) VALUES ('rebuild')")
        ready.append(fts)
    conn.commit()
    if ready and key:
        with _READY_LOCK:
            _READY.setdefault(key, set()).update(ready)
    return ready


def rebuild_fts() -> dict[str, int]:
    """Rebuild every FTS table from its base table. Returns row counts."""
    out: dict[str, int] = {}
    with connect() as conn:
        # force=True: et rebuild er en bevidst tilstandsændring og må ikke
        # besvares ud fra den proces-lokale cache.
        ready = ensure_fts_tables(conn, force=True)
        for fts in ready:
            conn.execute(f"INSERT INTO {fts}({fts}) VALUES ('rebuild')")
            row = conn.execute(f"SELECT count(*) FROM {fts}").fetchone()
            out[fts] = int(row[0] if row else 0)
        conn.commit()
    return out


def _query_terms(query: str, *, max_terms: int = 8) -> list[str]:
    """De enkelte søgeord bag `to_match_query`, uden FTS-syntaks.

    Bruges når teksten skal matches i hukommelsen i stedet for af FTS5 — se
    `_search_encrypted_for_owner`. Tokeniseringen er den SAMME, så en søgning
    giver samme ord uanset hvilken af de to veje der svarer.
    """
    terms: list[str] = []
    seen: set[str] = set()
    for tok in _TOKEN_RE.findall(str(query or "")):
        t = tok.strip("-._").lower()
        if len(t) < 2 or t in seen:
            continue
        seen.add(t)
        terms.append(t)
        if len(terms) >= max_terms:
            break
    return terms


def to_match_query(query: str, *, max_terms: int = 8) -> str:
    """Turn free text into a tolerant FTS5 MATCH expression.

    Tokens (≥ 2 chars) become quoted prefix terms joined with OR, so
    "pfsense nøgle" → '"pfsense"* OR "nøgle"*'. Returns "" when no usable token.
    """
    return " OR ".join(f'"{t}"*' for t in _query_terms(query, max_terms=max_terms))


def _bm25_to_score(rank: float) -> float:
    """FTS5 bm25() returns lower-is-better negative numbers; map to (0, 1]."""
    try:
        return 1.0 / (1.0 + abs(float(rank)))
    except (TypeError, ValueError):  # Invalid ranks are treated as the lowest score.
        return 0.0


def _equivalent_principals(_conn: sqlite3.Connection, canonical_uid: str) -> tuple[str, ...]:
    """Return stored principals that resolve to the current canonical user.

    Older chat rows may contain an external login subject while the request
    context already contains the canonical account id. Treating those two
    spellings as different users hides the owner's own history. Resolution is
    deliberately fail-closed: an unreadable link is not included.
    """
    try:
        from core.services.routine_migration import canonical_identity_aliases

        aliases = canonical_identity_aliases(canonical_uid)
        return aliases or (canonical_uid,)
    except Exception:
        logger.debug("db_fts: principal alias resolution failed", exc_info=True)
        return (canonical_uid,)


def search_session_summaries(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Keyword search over session_summaries FOR THIS USER.

    Målt 6/10-2026: denne FTS-søgning havde intet bruger-scope, og `recall`
    (recall.py:180, med `session_summary` i DEFAULT_SOURCES) eksponerede den
    direkte. BEVIST AKTIV: et recall efter «aftensmadopskrift med kylling
    tomater mælk pasta kartofler» returnerede Michelles private samtale fra
    29/9 som top-hit (score 1,00).

    Samme retning som `chat_crypto.should_encrypt`: ekskludér KUN sessioner der
    beviseligt tilhører en anden bruger — ustemplede/legacy og egne slipper
    igennem, så ingen mister adgang til sin egen historik. Uden uid
    (daemon/autonomt) er adfærden uændret.
    """
    match = to_match_query(query)
    if not match:
        return []
    try:
        from core.services.scoped_recall_policy import require_private_scope
        uid = require_private_scope()
    except Exception:  # Missing principal must hide all private summary rows.
        return []
    try:
        with connect() as conn:
            if "session_summaries_fts" not in ensure_fts_tables(conn):
                return []
            if _base_table_exists(conn, "recall_ownership_quarantine"):
                quarantine_hashes = {
                    str(row[0]) for row in conn.execute(
                        "SELECT source_id_hash FROM recall_ownership_quarantine "
                        "WHERE source_kind='chat_session'"
                    ).fetchall()
                }
            else:
                quarantine_hashes = set()
            if uid:
                principals = _equivalent_principals(conn, uid)
                marks = ",".join("?" for _ in principals)
                # 24/10-2026: ejer-filteret lå som EXISTS direkte i MATCH-grenen,
                # så det kørte for HVER FTS-træffer før LIMIT kunne bide. Målt på
                # den levende DB: 13.463 træffer, 6.432 med ejer-række → 17.201 ms
                # for at returnere 10 rækker. Det var grunden til at `recall` meldte
                # `partial` i 83 % af alle kald (median 3.692 ms mod en deadline på
                # 3.500): session_summary nåede aldrig frem.
                #
                # Nu tages kandidaterne FØRST (rangeret af bm25), og ejer-filteret
                # kører kun på dem. Samme svar, 37 ms. Kandidatloftet er limit × 20
                # så filtreringen ikke kan tømme resultatet; det er stadig en
                # brøkdel af de 13.463, og en session der ejes af brugeren ligger
                # i toppen af sin egen rangering.
                kandidater = max(int(limit) * 20, 200)
                rows = conn.execute(
                    "WITH hits AS ("
                    "  SELECT s.id, s.session_id, s.run_id, s.summary, s.key_topics, "
                    "         s.decisions_made, s.created_at, "
                    "         bm25(session_summaries_fts) AS rank "
                    "  FROM session_summaries_fts f JOIN session_summaries s ON s.id = f.rowid "
                    "  WHERE session_summaries_fts MATCH ? "
                    "  ORDER BY rank LIMIT ?"
                    ") "
                    "SELECT h.id, h.session_id, h.run_id, h.summary, h.key_topics, "
                    "       h.decisions_made, h.created_at, h.rank FROM hits h "
                    "WHERE EXISTS (SELECT 1 FROM chat_messages own "
                    f"  WHERE own.session_id=h.session_id AND own.user_id IN ({marks})) "
                    "AND NOT EXISTS (SELECT 1 FROM chat_messages foreign_row "
                    "  WHERE foreign_row.session_id=h.session_id "
                    "  AND foreign_row.user_id IS NOT NULL AND foreign_row.user_id<>'' "
                    f"  AND foreign_row.user_id NOT IN ({marks})) "
                    "ORDER BY h.rank LIMIT ?",
                    (match, kandidater, *principals, *principals, int(limit)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT s.id, s.session_id, s.run_id, s.summary, s.key_topics, "
                    "s.decisions_made, s.created_at, bm25(session_summaries_fts) AS rank "
                    "FROM session_summaries_fts f JOIN session_summaries s ON s.id = f.rowid "
                    "WHERE session_summaries_fts MATCH ? ORDER BY rank LIMIT ?",
                    (match, int(limit)),
                ).fetchall()
    except sqlite3.OperationalError as exc:
        logger.debug("db_fts: summaries search failed: %s", exc)
        return []
    import hashlib
    return [
        {
            "id": r[0], "session_id": r[1], "run_id": r[2], "summary": r[3],
            "key_topics": r[4], "decisions_made": r[5], "created_at": r[6],
            "score": _bm25_to_score(r[7]),
        }
        for r in rows
        if hashlib.sha256(str(r[1]).encode("utf-8")).hexdigest() not in quarantine_hashes
    ]


def _search_encrypted_for_owner(
    conn: sqlite3.Connection,
    *,
    query: str,
    limit: int,
    session_id: str | None,
    role: str | None,
    principals: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Søg i den kaldendes EGNE krypterede beskeder ved at dekryptere i hukommelsen.

    Målt 25/11-2026: `chat_messages_fts` er en external-content-tabel over
    `chat_messages.content`, og for et medlem står der ``enc:v1:<base64>`` i den
    kolonne. FTS indekserer altså base64 som om det var ord. Michelles session
    gav **0 hit** på «opskrift», «laks» og «kartoffel», mens alle tre ord stod i
    hendes egne beskeder. Fejlen var usynlig fordi `search_session_summaries`
    ligger i klartekst og derfor svarede rigtigt — det så ud som om søgningen
    virkede, indtil nogen søgte efter noget de selv havde skrevet.

    Dekrypteringen sker KUN for rækker i sessioner den kaldende selv ejer, og
    kun for rækker der beviseligt er krypterede. Klartekst på disk er stadig
    forbudt: teksten findes kun i dette kalds hukommelse og forlader den ikke.

    Loftet på 5000 rækker er en prisgrænse, ikke en sikkerhedsgrænse — målt koster
    dekryptering 0,23 ms pr. række, så 5000 er ~1,2 s i værste fald. En bruger
    med mere end 5000 krypterede beskeder søger derfor i sine nyeste.
    """
    terms = _query_terms(query)
    if not terms or not principals:
        return []
    from core.services import chat_crypto

    marks = ",".join("?" for _ in principals)
    sql = (
        "SELECT m.id, m.message_id, m.session_id, m.role, m.content, m.created_at "
        "FROM chat_messages m "
        "WHERE m.encrypted = 1 "
        "  AND m.session_id IN (SELECT own.session_id FROM chat_messages own "
        f"                      WHERE own.user_id IN ({marks}))"
    )
    params: list[Any] = [*principals]
    if session_id:
        sql += " AND m.session_id = ?"
        params.append(session_id)
    if role:
        sql += " AND m.role = ?"
        params.append(role)
    sql += " ORDER BY m.id DESC LIMIT 5000"
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        logger.debug("db_fts: encrypted chat search failed: %s", exc)
        return []

    hits: list[dict[str, Any]] = []
    medlem_per_session: dict[str, str | None] = {}
    for r in rows:
        sid = str(r[2] or "")
        if sid not in medlem_per_session:
            # Én nøgleopslag pr. session, ikke pr. besked — målt til at være
            # forskellen mellem brugbar og ubrugelig på en lang historik.
            medlem_per_session[sid] = chat_crypto.medlem_for_session(sid, conn=conn)
        medlem = medlem_per_session[sid]
        if not medlem or medlem not in principals:
            # Sessionen tilhører en ANDEN bruger — fx en delt session hvor begge
            # har skrevet. Uden denne spærring ville den kaldendes principal
            # åbne sessionen gennem EXISTS-subqueryen, og `medlem_for_session`
            # derefter levere den ANDENS nøgle: altså dekryptere en andens
            # private beskeder for den forkerte læser. Det er præcis den grænse
            # `chat_crypto` værner, så den håndhæves her og ikke i kalderen.
            continue
        tekst = chat_crypto.dekrypter(r[4] or "", medlem)
        if not tekst or chat_crypto.er_krypteret(tekst):
            continue
        low = tekst.lower()
        matched = sum(1 for t in terms if t in low)
        if not matched:
            continue
        hits.append({
            "id": r[0], "message_id": r[1], "session_id": r[2], "role": r[3],
            "content": tekst, "created_at": r[5],
            "score": matched / len(terms),
        })
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[: max(int(limit), 1)]


def search_chat_messages(
    query: str, *, limit: int = 8, session_id: str | None = None, role: str | None = None,
) -> list[dict[str, Any]]:
    """Keyword search over chat_messages FOR THIS USER. Each hit: id, message_id,
    session_id, role, content, created_at, score.

    Samme bruger-scope som `search_session_summaries` (målt 6/10-2026): `chat` er
    en opt-in recall-kilde (recall.py:194, `_source_chat`), så uden scope kunne et
    recall med `sources=['chat']` læse en anden brugers sessioner. Kilden er ikke i
    DEFAULT_SOURCES, men det er samme dør i samme væg — og et halvt fix på en
    lækage giver falsk tryghed.
    """
    match = to_match_query(query)
    if not match:
        return []
    try:
        from core.services.scoped_recall_policy import require_private_scope
        uid = require_private_scope()
    except Exception:  # Missing principal must hide all private chat rows.
        return []
    sql = (
        "SELECT m.id, m.message_id, m.session_id, m.role, m.content, m.created_at, "
        "bm25(chat_messages_fts) AS rank FROM chat_messages_fts f "
        "JOIN chat_messages m ON m.id = f.rowid WHERE chat_messages_fts MATCH ?"
    )
    params: list[Any] = [match]
    if session_id:
        sql += " AND m.session_id = ?"
        params.append(session_id)
    if role:
        sql += " AND m.role = ?"
        params.append(role)
    principals: tuple[str, ...] = ()
    try:
        with connect() as conn:
            if "chat_messages_fts" not in ensure_fts_tables(conn):
                return []
            if uid:
                principals = _equivalent_principals(conn, uid)
                marks = ",".join("?" for _ in principals)
                # 24/10-2026: samme fejl som i `search_session_summaries` — ejer-
                # filteret lå i MATCH-grenen, så EXISTS kørte for hver træffer før
                # LIMIT. Målt: 31.677 ms for ti rækker. Nu tages kandidaterne først
                # (rangeret af bm25), og filteret kører kun på dem.
                kandidater = max(int(limit) * 20, 200)
                sql = (
                    "WITH hits AS ("
                    "  SELECT m.id, m.message_id, m.session_id, m.role, m.content, "
                    "         m.created_at, bm25(chat_messages_fts) AS rank "
                    "  FROM chat_messages_fts f JOIN chat_messages m ON m.id = f.rowid "
                    "  WHERE chat_messages_fts MATCH ?"
                )
                hit_params: list[Any] = [match]
                if session_id:
                    sql += " AND m.session_id = ?"
                    hit_params.append(session_id)
                if role:
                    sql += " AND m.role = ?"
                    hit_params.append(role)
                sql += (
                    "  ORDER BY rank LIMIT ?"
                    ") "
                    "SELECT h.id, h.message_id, h.session_id, h.role, h.content, "
                    "       h.created_at, h.rank FROM hits h "
                    "WHERE EXISTS (SELECT 1 FROM chat_messages own "
                    f"  WHERE own.session_id=h.session_id AND own.user_id IN ({marks}))"
                    " AND NOT EXISTS (SELECT 1 FROM chat_messages foreign_row "
                    "  WHERE foreign_row.session_id=h.session_id "
                    "  AND foreign_row.user_id IS NOT NULL AND foreign_row.user_id<>'' "
                    f"  AND foreign_row.user_id NOT IN ({marks}))"
                    " ORDER BY h.rank LIMIT ?"
                )
                params = [*hit_params, kandidater, *principals, *principals, int(limit)]
            else:
                sql += " ORDER BY rank LIMIT ?"
                params.append(int(limit))
            if _base_table_exists(conn, "recall_ownership_quarantine"):
                # Quarantine stores only SHA-256 source hashes; SQLite has no
                # portable sha256(), so fetch the bounded FTS set then filter
                # conflicted session hashes below.
                quarantine_hashes = {
                    str(row[0]) for row in conn.execute(
                        "SELECT source_id_hash FROM recall_ownership_quarantine "
                        "WHERE source_kind='chat_session'"
                    ).fetchall()
                }
            else:
                quarantine_hashes = set()
            rows = conn.execute(sql, params).fetchall()
            # FTS kan ikke se gennem `enc:v1:`-ciffertekst. Supplér derfor med en
            # dekrypteret søgning i den kaldendes EGNE rækker, så en medlems egen
            # historik er søgbar — se `_search_encrypted_for_owner`.
            krypterede = (
                _search_encrypted_for_owner(
                    conn, query=query, limit=limit, session_id=session_id,
                    role=role, principals=principals,
                )
                if uid else []
            )
    except sqlite3.OperationalError as exc:
        logger.debug("db_fts: chat search failed: %s", exc)
        return []
    import hashlib
    hits = [
        {
            "id": r[0], "message_id": r[1], "session_id": r[2], "role": r[3],
            "content": r[4], "created_at": r[5], "score": _bm25_to_score(r[6]),
        }
        for r in rows
        if hashlib.sha256(str(r[2]).encode("utf-8")).hexdigest() not in quarantine_hashes
    ]
    if krypterede:
        sete = {h["message_id"] for h in hits}
        hits.extend(h for h in krypterede if h["message_id"] not in sete)
        hits.sort(key=lambda h: h["score"], reverse=True)
        hits = hits[: int(limit)]
    return hits
