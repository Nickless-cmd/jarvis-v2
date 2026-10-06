"""Proactive candidates — the ONE queue for "Jarvis wants to tell a user something".

Replaces the two nudge wells as a decision surface (redesign 2026-09-04):

* `outbound_nudges` (DB): 506 nudges/7 days, 0 ever sent, 89 % "Autonom run ✓
  færdig"; the prompt asked Jarvis to call a tool that did not exist, from
  inside a block that told him never to mention it.
* `nudge_broend.json`: 751 pending, all autonomous-run telemetry, 0 sent.

Now:
* telemetry ("run finished") never becomes a candidate — it is an event;
* real messages land here with a priority and are delivered by
  `proactivity_bridge` (presence-gated, digest, cap) — no tool call needed;
* in conversation, at most ONE relevant pending item is shown as a
  "Siden sidst" line, and it counts as delivered when Jarvis mentions it.

Statuses: pending → surfaced (sent by the bridge) | mentioned (Jarvis said it
in a reply) | dismissed | expired.

Bruger-dimension (bygget 6/10-2026, Bjørn). Køen var GLOBAL: 312 rækker og
ingen `user_id`-kolonne overhovedet. Leverings-vejen matchede på TEKST-overlap,
ikke på ejerskab — så «Alarm: Bjørn skal til møde med Line» var en kandidat for
enhver der skrev ordet «møde». Fem brugere deler runtime'en (bjorn, michelle,
mikkel, lotte, rune), og hver har sit eget workspace.

Nu bærer hver kandidat en `user_id` — tre betydninger:

* ``''`` = INTERN. Vises ALDRIG. Bogholderi uden en ejer-mening, og den SIKRE
  default: kan ejeren ikke afgøres, bliver kandidaten tavs frem for gættet.
* ``<owner_id>`` = OWNER-KUN. Maskinrummets telemetri — wakeups, heartbeat,
  run-status. Den er ikke en besked til en bruger, men den er heller ikke
  spild: den hører til den der ejer maskinen, og til ingen anden. (Bjørn,
  6/10-2026: «telemetrien bør være owner only». Før blev den kastet væk ved
  indgangen, så hans EGEN telemetri var usynlig for alle — også ham.)
* ``<discord_id>`` = vises KUN for den bruger.

Ejeren afgøres ved INDGANGEN (`_bruger_for`): eksplicit argument →
`current_user_id()` → session-ejeren → ``''``. Session-ejer-leddet er ikke
pynt: owner (Bjørn) har ofte tom `current_user_id()` inde i run-generatoren —
samme fælde som `memory_tools._resolve_memory_uid` løser — så uden det ville
hans EGNE kandidater blive mærket «interne» og gjort tavse. Fejlen ville ramme
den ene bruger vi har flest af.

Kilder i `_OWNER_KILDER` tvinger owner-uid uanset kontekst: et autonomt run kan
have en session, men «run efterlod 5 ucommittede filer» er ikke en besked til
den der ejer sessionen — den er til den der ejer maskinen. `_INTERNE_KILDER`
tvinger ``''``.
"""
from __future__ import annotations

import logging
import re
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.db import connect

logger = logging.getLogger(__name__)

PRIORITIES = ("low", "medium", "high", "critical")
_URGENT = frozenset({"high", "critical"})
_DEDUPE_HOURS = 24
_EXPIRE_DAYS = 7
_MAX_PENDING = 100

_TERM_RE = re.compile(r"[0-9A-Za-zÆØÅæøå]+")
_STOP = frozenset({
    "hvad", "hvor", "hvilken", "hvilket", "hvilke", "hvorfor", "hvornår", "hvordan",
    "blev", "var", "har", "havde", "det", "der", "den", "til", "fra", "med", "for", "som",
    "jeg", "mig", "du", "dig", "vores", "mine", "dine", "siger", "sagde", "om", "og", "kan",
    "skal", "ikke", "eller", "the", "what", "when", "where", "why", "how", "did", "does",
    "was", "were", "about", "with", "from", "your", "run", "autonom", "reviewe", "vil",
})

_SHOWN: dict[str, tuple[float, list[str]]] = {}
_SHOWN_TTL_S = 900.0

#: Maskinrummets telemetri. `er_telemetri` holder `outbound_nudges.route_for`
#: og dette modul enige om HVAD der er telemetri; `_OWNER_KILDER` er den
#: bredere flok der skal lande hos owner. Målt 6/10-2026 over 7 døgn:
#: `wakeup_dispatcher` 48 kandidater, `heartbeat` 3, `run_closure_gate` 4,
#: `autonomous_run` og `autonomy_budget` 1 hver.
_TELEMETRI_KILDER = frozenset({"wakeup_dispatcher", "heartbeat"})
_TELEMETRI_KINDS = frozenset({"heartbeat_ping"})

#: Telemetri hører til OWNER og til ingen anden. Før kastede indgangen den væk
#: («skipped»), så Bjørns EGEN telemetri var usynlig for alle — også ham.
_OWNER_KILDER = frozenset({
    "wakeup_dispatcher", "heartbeat", "run_closure_gate", "autonomous_run",
    "autonomy_budget",
})

#: Bogholderi uden en ejer-mening — vises aldrig. Bemærk: `kerne_curator` og
#: `development_ritual` er ikke telemetri; de er forslag TIL owner og hører i
#: «delinger»-fladen, som ikke er bygget endnu. De står her til den beslutning.
_INTERNE_KILDER = frozenset({"kerne_curator", "development_ritual"})

#: Et spørgsmål der ER stillet og ikke besvaret skal ikke hænge for evigt.
#: Målt 3/10-2026: 155 `surfaced` + 118 `mentioned` — den ældste fra 4/9,
#: 29 dage gammel — og `expire_stale` ramte kun `pending`. Et ubesvaret
#: spørgsmål forblev altså «åbent» i al evighed.
_STILLET_EXPIRE_DAYS = 14

#: Loft over hvor mange ÅBNE kandidater der må ligge pr. `kind`. Målt samme dag:
#: 37 åbne `rule_proposal:request` — de samme tre rutiner stillet igen og igen i
#: ny ordlyd. Ord-sammenligning kan ikke fange dansk↔engelsk («Send morning
#: briefing to Michelle» vs «Send dagligt morgenvejr til Mikkel» deler ét ord),
#: så loftet er det deterministiske sikkerhedsnet: ét tal, én regel, ingen
#: semantik.
_MAX_AABNE_PER_KIND = 3

#: Hvor ens to kærner skal være for at være «samme spørgsmål». Ord-Jaccard.
_SAMME_KERNE = 0.5

#: Den underliggende anmodning i et regel-forslag, ikke skabelonen omkring.
_CITERET_RE = re.compile(r"«([^»]{4,300})»")


def er_telemetri(source: str, kind: str = "") -> bool:
    """Er dette intern telemetri frem for en besked Bjørn skal se?"""
    return str(source or "") in _TELEMETRI_KILDER or str(kind or "") in _TELEMETRI_KINDS


def _owner_uid() -> str:
    """Owner'ens discord-id — samme kanoniske vej som `proactivity_bridge._owner_uid`.

    Self-safe: kan den ikke afgøres, gives ``''``, og telemetrien bliver intern
    frem for at blive gættet til en tilfældig bruger.
    """
    try:
        from core.identity.owner_resolver import get_owner_discord_id

        uid = (get_owner_discord_id() or "").strip()
        if uid:
            return uid[:64]
    except Exception as exc:
        logger.debug("proactive_candidates: owner-opslag fejlede: %s", exc)
    return ""


def _bruger_for(user_id: str | None, source: str, session_id: str = "",
                kind: str = "") -> str:
    """Hvilken bruger hører denne kandidat til? ``''`` = intern (vises aldrig).

    Telemetri (`er_telemetri` / `_OWNER_KILDER`) får owner-uid uanset kontekst:
    et autonomt run kan have en session, men «run efterlod 5 ucommittede filer»
    er ikke en besked til den der ejer sessionen — den er til den der ejer
    maskinen.

    Ellers er rækkefølgen den samme som `memory_tools._resolve_memory_uid`:
    eksplicit argument → ``current_user_id()`` → session-ejeren → ``''``.
    Session-ejer-leddet er ikke pynt — se docstringen øverst. Self-safe: enhver
    fejl i opslaget giver ``''``, altså tavs frem for gættet.

    `session_id` tages med fordi prompt-byggeren kender sessionen som PARAMETER,
    hvor contextvar'en ikke altid er sat. Uden den ville en kandidat kunne
    falde tilbage til «intern» midt i en samtale den hører til.
    """
    if user_id is not None:
        return str(user_id).strip()[:64]
    if er_telemetri(source, kind) or str(source or "") in _OWNER_KILDER:
        return _owner_uid()
    if str(source or "") in _INTERNE_KILDER:
        return ""
    try:
        from core.identity.workspace_context import current_session_id, current_user_id

        uid = (current_user_id() or "").strip()
        if uid:
            return uid[:64]
        sid = (current_session_id() or "").strip() or str(session_id or "").strip()
        if sid:
            from core.services.chat_sessions import get_session_owner

            return (get_session_owner(sid) or "").strip()[:64]
    except Exception as exc:
        logger.debug("proactive_candidates: bruger-opslag fejlede: %s", exc)
        return ""
    return ""


def _kerne(text: str) -> str:
    """Anmodningen selv — ikke skabelonen den er pakket ind i.

    Et regel-forslag har formen «Du har bedt om det samme N gange …:
    «<anmodning>». …». Sammenligner man HELE teksten, deler to forskellige
    rutiner skabelonens ord og ligner hinanden; sammenligner man kun den
    citerede anmodning, er de to forskellige.
    """
    m = _CITERET_RE.search(str(text or ""))
    return m.group(1) if m else str(text or "")


def _kerne_similarity(a: str, b: str) -> float:
    """Jaccard mellem to kærners ord (0-1)."""
    ta, tb = _terms(a), _terms(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _terms(text: str) -> set[str]:
    out: set[str] = set()
    for raw in _TERM_RE.findall(str(text or "").replace("-", " ")):
        t = raw.lower()
        if len(t) >= 3 and t not in _STOP:
            out.add(t)
    return out


def lexical_coverage(query: str, text: str) -> float:
    q = _terms(query)
    if not q:
        return 0.0
    return min(1.0, len(q & _terms(text)) / max(1, min(len(q), 5)))


def _norm_text(text: str) -> str:
    return " ".join(str(text or "").lower().split())[:300]


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS proactive_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT '',
            text TEXT NOT NULL,
            norm_text TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            surfaced_at TEXT NOT NULL DEFAULT '',
            mentioned_run_id TEXT NOT NULL DEFAULT '',
            user_id TEXT NOT NULL DEFAULT ''
        )
        """
    )
    # Migrering af DB'er skabt før 6/10-2026. Kolonnen lægges SIDST, så
    # rækkefølgen matcher CREATE'en ovenfor — `_row`s tuple-gren læser efter
    # position, og en forskel mellem ny og migreret DB ville give `user_id`
    # en anden plads i de to.
    kolonner = {str(r[1]) for r in conn.execute("PRAGMA table_xinfo(proactive_candidates)")}
    if "user_id" not in kolonner:
        conn.execute("ALTER TABLE proactive_candidates ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_proactive_candidates_status ON proactive_candidates(status, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_proactive_candidates_user ON proactive_candidates(user_id, status)")


def _row(r: Any) -> dict[str, Any]:
    if isinstance(r, sqlite3.Row):
        return dict(r)
    cols = ["id", "candidate_id", "source", "kind", "text", "norm_text", "priority", "status",
            "created_at", "updated_at", "surfaced_at", "mentioned_run_id", "user_id"]
    return dict(zip(cols, r))


def normalize_priority(importance: str) -> str:
    v = str(importance or "").strip().lower()
    if v in PRIORITIES:
        return v
    if v in {"normal", ""}:
        return "medium"
    return "medium"


def add_candidate(*, source: str, text: str, priority: str = "medium", kind: str = "",
                  user_id: str | None = None, session_id: str = "") -> dict[str, Any]:
    """Queue a message for a user. Deduped on normalized text within 24 h.

    `user_id=None` (default) → ejeren afgøres af `_bruger_for`, som også ser på
    `session_id`. Giv `user_id` eksplicit når kalderen allerede VED hvem
    beskeden er til; giv `session_id` når kalderen har en session men ingen
    kontekst — fx ved run-slut, hvor `current_user_id()` er tom for owner.

    Returns {"status": "added"|"duplicate"|"skipped", "candidate_id": ...}."""
    body = " ".join(str(text or "").split()).strip()
    if len(body) < 8:
        return {"status": "skipped", "reason": "empty"}
    # Telemetri afvises IKKE længere her (6/10-2026). Før returnerede dette
    # sted «skipped», og det var forkert ad to veje: det kastede Bjørns EGEN
    # telemetri væk, så den var usynlig for alle — også ham — og
    # `push_nudge`s telemetri-gren svarede det samme et andet sted. Nu bærer
    # telemetrien owner-uid (`_bruger_for`), så den findes for den ene der ejer
    # maskinen og for ingen anden.
    # Laekage-vaern ved INDGANGEN (8/9-2026). Uden det stod den indre daemons
    # telemetri og generatorens egen output-kontrakt som Jarvis' tanker i den
    # proaktive kanal. Her frem for ved visningen, saa ét vaern daekker alle
    # forbrugere af koeen — ikke kun digesten.
    try:
        from core.services.thought_leak_guard import ligner_ikke_en_tanke
        grund = ligner_ikke_en_tanke(body)
    except Exception:
        grund = ""
    if grund:
        return {"status": "skipped", "reason": grund}
    uid = _bruger_for(user_id, source, session_id, kind)
    norm = _norm_text(body)
    now = _now_iso()
    cutoff = (datetime.now(UTC) - timedelta(hours=_DEDUPE_HOURS)).isoformat()
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        dup = conn.execute(
            "SELECT candidate_id FROM proactive_candidates WHERE norm_text = ? AND created_at > ? "
            "AND status IN ('pending', 'surfaced', 'mentioned') LIMIT 1",
            (norm, cutoff),
        ).fetchone()
        if dup is not None:
            return {"status": "duplicate", "candidate_id": dup[0]}
        # Samme spørgsmål i NY ordlyd? Skabelonen ændrer sig (tal, ordvalg), så
        # `norm_text` alene fanger den ikke — målt 3/10: «natlig sanseregistrering»
        # blev stillet 6 gange og morgenbriefen 5, hver med sit eget norm_text.
        # Her sammenlignes KÆRNEN (den citerede anmodning) i stedet for hele
        # spørgsmålet, og UDEN 24-timers-vinduet: et åbent forslag blokerer indtil
        # det er afsluttet eller udløbet.
        aabne = conn.execute(
            "SELECT candidate_id, text FROM proactive_candidates "
            "WHERE kind = ? AND status IN ('pending', 'surfaced', 'mentioned') "
            "ORDER BY created_at DESC LIMIT 200",
            (str(kind or "")[:50],),
        ).fetchall()
        kerne = _kerne(body)
        for row in aabne:
            if _kerne_similarity(kerne, _kerne(str(row[1] or ""))) >= _SAMME_KERNE:
                return {"status": "duplicate", "candidate_id": row[0]}
        if len(aabne) >= _MAX_AABNE_PER_KIND:
            # Sikkerhedsnettet når ord-sammenligningen ikke rækker: dansk↔engelsk
            # deler næsten ingen ord, så «samme rutine, ny formulering» slipper
            # igennem kærne-tjekket. Tre ubesvarede er nok til at han ikke svarer.
            return {"status": "skipped", "reason": "kind-cap"}
        cid = f"pc-{uuid4().hex[:12]}"
        conn.execute(
            "INSERT INTO proactive_candidates (candidate_id, source, kind, text, norm_text, priority, "
            "user_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (cid, str(source or "unknown")[:80], str(kind or "")[:50], body[:1000], norm,
             normalize_priority(priority), uid, now, now),
        )
        # cap: the oldest pending beyond the limit expire
        rows = conn.execute(
            "SELECT candidate_id FROM proactive_candidates WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
        if len(rows) > _MAX_PENDING:
            old = [r[0] for r in rows[_MAX_PENDING:]]
            conn.execute(
                f"UPDATE proactive_candidates SET status='expired', updated_at=? WHERE candidate_id IN "
                f"({','.join('?' for _ in old)})", [now, *old],
            )
        conn.commit()
    return {"status": "added", "candidate_id": cid}


def list_pending(*, limit: int = 20, priorities: tuple[str, ...] | None = None,
                 user_id: str | None = None) -> list[dict[str, Any]]:
    """Pending kandidater. `user_id` er et FILTER på kolonnen:

    * ``None`` (default) → alle rækker, uanset ejer. Til diagnostik og
      overflader — ikke til levering.
    * ``''`` → kun INTERNE rækker.
    * ``'<discord_id>'`` → kun den brugers egne.
    """
    sql = "SELECT * FROM proactive_candidates WHERE status='pending'"
    params: list[Any] = []
    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(str(user_id))
    if priorities:
        sql += f" AND priority IN ({','.join('?' for _ in priorities)})"
        params.extend(priorities)
    sql += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC LIMIT ?"
    params.append(int(limit))
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        return [_row(r) for r in conn.execute(sql, params).fetchall()]


def mark(candidate_ids: list[str], status: str, *, run_id: str = "") -> int:
    if not candidate_ids:
        return 0
    if status not in {"surfaced", "mentioned", "dismissed", "expired", "pending"}:
        raise ValueError(f"bad status {status}")
    now = _now_iso()
    with connect() as conn:
        ensure_table(conn)
        ph = ",".join("?" for _ in candidate_ids)
        extra = ", surfaced_at=?" if status == "surfaced" else ""
        extra_params = [now] if status == "surfaced" else []
        cur = conn.execute(
            f"UPDATE proactive_candidates SET status=?, updated_at=?{extra}, "
            f"mentioned_run_id=CASE WHEN ? != '' THEN ? ELSE mentioned_run_id END "
            f"WHERE candidate_id IN ({ph}) AND status='pending'",
            [status, now, *extra_params, run_id, run_id, *candidate_ids],
        )
        conn.commit()
        return int(cur.rowcount or 0)


def expire_stale(*, days: int = _EXPIRE_DAYS, aabne_days: int = _STILLET_EXPIRE_DAYS) -> int:
    """Luk forældede kandidater. `pending` efter `days`; `surfaced`/`mentioned`
    efter `aabne_days` — de er allerede VIST, men blev aldrig afsluttet."""
    now = _now_iso()
    with connect() as conn:
        ensure_table(conn)
        cur = conn.execute(
            "UPDATE proactive_candidates SET status='expired', updated_at=? WHERE status='pending' AND created_at < ?",
            (now, (datetime.now(UTC) - timedelta(days=days)).isoformat()),
        )
        n = int(cur.rowcount or 0)
        cur = conn.execute(
            "UPDATE proactive_candidates SET status='expired', updated_at=? "
            "WHERE status IN ('surfaced', 'mentioned') AND created_at < ?",
            (now, (datetime.now(UTC) - timedelta(days=aabne_days)).isoformat()),
        )
        n += int(cur.rowcount or 0)
        conn.commit()
        return n


def counts() -> dict[str, int]:
    with connect() as conn:
        ensure_table(conn)
        return {str(k): int(v) for k, v in conn.execute(
            "SELECT status, count(*) FROM proactive_candidates GROUP BY status").fetchall()}


def counts_per_user() -> dict[str, int]:
    """Åbne kandidater pr. ejer. ``(intern)`` er de kilder der aldrig leveres."""
    with connect() as conn:
        ensure_table(conn)
        return {(str(k) or "(intern)"): int(v) for k, v in conn.execute(
            "SELECT user_id, count(*) FROM proactive_candidates "
            "WHERE status IN ('pending', 'surfaced') GROUP BY user_id").fetchall()}


# ── in-conversation surface ─────────────────────────────────────────────


def relevant_for(user_message: str, *, user_id: str | None = None, session_id: str = "",
                 limit: int = 1, min_coverage: float = 0.34) -> list[dict[str, Any]]:
    """Pending items for THIS user, lexically relevant to what they just wrote.

    `user_id=None` → ejeren afgøres af `_bruger_for` (konteksten, eller
    `session_id`). `''` → ingen bruger, intet vises.

    Uden en bruger returneres intet. Før matchede den på tekst alene, så en
    anden brugers kandidat kunne dukke op i denne samtale — «Alarm: Bjørn skal
    til møde med Line» matchede ordet «møde» i enhver samtale. Kravet om en
    bruger er hele fixet: overlap er ikke ejerskab.
    """
    msg = str(user_message or "").strip()
    if len(msg) < 8:
        return []
    uid = str(user_id).strip() if user_id is not None else _bruger_for(None, "", session_id)
    if not uid:
        return []
    scored = []
    for c in list_pending(limit=60, user_id=uid):
        cov = lexical_coverage(msg, f"{c.get('text', '')}")
        if cov >= min_coverage:
            scored.append((cov, c))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [c for _cov, c in scored[:limit]]


def remember_shown(session_id: str, candidate_ids: list[str]) -> None:
    sid = str(session_id or "").strip()
    if not sid or not candidate_ids:
        return
    now = time.time()
    _SHOWN[sid] = (now, list(candidate_ids))
    for k, (ts, _ids) in list(_SHOWN.items()):
        if now - ts > _SHOWN_TTL_S:
            _SHOWN.pop(k, None)


def build_since_last_line(user_message: str, *, session_id: str = "",
                          user_id: str | None = None) -> str:
    """At most ONE line: 'Siden sidst: …' when a pending item is relevant to the message.

    `user_id=None` → `relevant_for` afgør ejeren (kontekst eller `session_id`).
    """
    try:
        items = relevant_for(user_message, user_id=user_id, session_id=session_id, limit=1)
    except Exception as exc:
        logger.debug("proactive_candidates: relevant_for failed: %s", exc)
        return ""
    if not items:
        return ""
    item = items[0]
    remember_shown(session_id, [str(item.get("candidate_id") or "")])
    text = " ".join(str(item.get("text") or "").split())[:240]
    return f"Siden sidst (relevant for det du skriver — nævn det hvis det passer ind): {text}"


def mark_mentioned_if_overlap(*, session_id: str, answer_text: str, run_id: str = "", min_coverage: float = 0.5) -> int:
    """Auto-deliver: the shown item counts as delivered when Jarvis' answer overlaps it."""
    sid = str(session_id or "").strip()
    item = _SHOWN.get(sid)
    if not item:
        return 0
    ts, ids = item
    if time.time() - ts > _SHOWN_TTL_S or not ids:
        _SHOWN.pop(sid, None)
        return 0
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        ph = ",".join("?" for _ in ids)
        rows = [_row(r) for r in conn.execute(
            f"SELECT * FROM proactive_candidates WHERE candidate_id IN ({ph}) AND status='pending'", ids
        ).fetchall()]
    hit = [str(r["candidate_id"]) for r in rows
           if lexical_coverage(str(r.get("text") or ""), answer_text) >= min_coverage]
    if not hit:
        return 0
    _SHOWN.pop(sid, None)
    return mark(hit, "mentioned", run_id=run_id)


# ── bridge integration ──────────────────────────────────────────────────


def bridge_candidates(user_id: str = "") -> list[dict[str, Any]]:
    """Shape expected by proactivity_bridge.collect_candidates().

    Kun ÉN brugers kandidater. Uden en bruger returneres intet: bridgen
    leverer til en navngiven modtager, og «hvem som helst» er ikke en modtager.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return []
    out = []
    for c in list_pending(limit=30, user_id=uid):
        out.append({
            "kind": str(c.get("kind") or "candidate"),
            "text": str(c.get("text") or ""),
            "priority": str(c.get("priority") or "medium"),
            "source": "proactive_candidates",
            "source_id": str(c.get("candidate_id") or ""),
            "ts": str(c.get("created_at") or ""),
        })
    return out


def build_proactive_candidates_surface() -> dict[str, Any]:
    try:
        c = counts()
    except Exception:
        c = {}
    try:
        per_bruger = counts_per_user()
    except Exception:
        per_bruger = {}
    return {"active": bool(c), "counts": c, "per_user": per_bruger,
            "summary": f"{c.get('pending', 0)} pending proactive candidates"}
