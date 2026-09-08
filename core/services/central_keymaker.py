"""The Keymaker — optjent, udløbende, én-dør-ad-gangen autonomi.

Bjørn+Claude (6. jul, tema #4): "I cannot make the key. I have to find it. But I know where to look."

I dag er autonomi binære `*_live`-flags Bjørn flipper. Al min memory er fuld af autonomi-runaway-
hændelser fra permanente switches. The Keymaker er det sikre svar: autonomi bliver ikke en switch,
men en FORTJENT, TIDSBEGRÆNSET, GODKENDT tilladelse:

  1. OPTJEN — en dimension optjener en nøgle NÅR dens track-record krydser en tærskel (fx en gate
     der har truffet 100+ beslutninger med 0 fejl = bevist pålidelig). Centralen GENERERER nøglen;
     den kan ikke give sig selv adgang.
  2. GODKEND — nøglen er PENDING indtil owner godkender. Aldrig auto-unlock (frossen-kerne-invariant).
  3. UDLØB — en godkendt nøgle flipper sit flag i en TTL og AUTO-REVERTERER. Tilladelser mistes hvis
     de ikke fornyes → ingen permanent privilege-crawl. Én dør ad gangen.

Kilde til track-record: gate_verdict_ledger (persistent). En gate der er 100% grøn over høj volumen
har BEVIST at Centralens round-trip var overflødig → den har fortjent en decentraliserings-nøgle
(resolve lokalt, eskalér kun ikke-grøn). Self-safe: kaster aldrig; genererer aldrig adgang uden
godkendelse.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_core import connect

# Track-record-tærskel: en gate har fortjent en nøgle ved ≥ dette antal beslutninger med 0 ikke-grøn.
_EARN_MIN_VOLUME = 100
_KEY_TTL_HOURS = 24
# Gates der ALDRIG optjener decentraliserings-nøgle (SECURITY/execution — frossen kerne).
# Fallback-denylist for nerver der IKKE er i central_catalog (execution/probe uden NerveSpec).
# KATALOG-klassificerede SECURITY-nerver blokeres nu klasse-baseret via _is_never() — så nye
# security-gates ikke kan optjene en nøgle blot fordi nogen glemte at tilføje dem her (§11.3).
_NEVER = frozenset({"cross_user_share", "exec_command", "exec_file", "exec_workspace_trust",
                    "auth", "tool_access", "central_self_probe"})


def _is_never(nerve: str) -> bool:
    """True hvis <nerve> ALDRIG må optjene/godkende en decentraliserings-nøgle: enten katalog-
    klassificeret SECURITY (§11.3, autoritativ) ELLER i fallback-denylisten. Self-safe → ved
    enhver opslags-fejl fail-closed på fallback-listen (aldrig lækker en ukendt nerve som sikker)."""
    try:
        from core.services.central_catalog import is_security_nerve
        if is_security_nerve(nerve):
            return True
    except Exception:
        pass
    return nerve in _NEVER


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            unlock_scope TEXT NOT NULL,
            unlock_name TEXT NOT NULL,
            track_value INTEGER NOT NULL DEFAULT 0,
            issued_at TEXT NOT NULL,
            expires_at TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_central_keys_status ON central_keys (status)")


def _now() -> datetime:
    return datetime.now(UTC)


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "keymaker", "kind": kind, **payload})
    except Exception:
        pass


def evaluate_keys() -> dict[str, Any]:
    """Find dimensioner der har OPTJENT en nøgle (track-record over tærskel) og udsted en PENDING
    nøgle for hver — hvis der ikke allerede er en aktiv/afventende. Genererer ALDRIG adgang selv.
    Self-safe. Returnerer {issued: [...], earned: [...]}. """
    out: dict[str, Any] = {"issued": [], "earned": []}
    try:
        from core.services.gate_verdict_ledger import summary
        rows = summary()
    except Exception:
        return out
    try:
        with connect() as conn:
            _ensure_table(conn)
            existing = {r["domain"] for r in conn.execute(
                "SELECT domain FROM central_keys WHERE status IN ('pending','approved')").fetchall()}
            for nerve, agg in rows.items():
                if _is_never(nerve):
                    continue
                total = int(agg.get("total") or 0)
                non_green = total - int(agg.get("green") or 0)
                if total < _EARN_MIN_VOLUME or non_green != 0:
                    continue
                domain = f"decentralize:{nerve}"
                out["earned"].append({"domain": domain, "track": total})
                if domain in existing:
                    continue
                reason = f"{nerve}: {total} beslutninger, 0 fejl → bevist pålidelig"
                conn.execute(
                    """INSERT INTO central_keys
                       (domain, unlock_scope, unlock_name, track_value, issued_at, status, reason)
                       VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                    (domain, "decentralize", nerve, total, _now().isoformat(), reason),
                )
                out["issued"].append({"domain": domain, "track": total, "reason": reason})
                _observe("earned", {"domain": domain, "track": total})
            conn.commit()
    except Exception:
        pass
    # Notificér EFTER commit, saa vi aldrig varsler om en noegle der ikke blev skrevet.
    for k in out["issued"]:
        _varsl_ejer(k["domain"], int(k["track"]))
    return out


def _ejer_uid() -> str:
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        return (get_owner_discord_id() or "").strip()
    except Exception:
        return ""


def _varsl_ejer(domain: str, track: int) -> bool:
    """Sig til naar en noegle er OPTJENT — den kan ikke bruges foer ejeren godkender.

    Fandtes ikke foer 7/9-2026, og det kostede praecis det man ville tro: tre
    noegler laa PENDING i to maaneder (veto 1.193 beslutninger fra 10. juli,
    self_review og decision_gate fra 7. juli), og en fjerde blev udstedt 6. juli
    og UDLOEB ubemaerket 10. juli. Maskineriet virkede hele vejen — optjening,
    taerskel, TTL — men det sidste led var at nogen tilfaeldigvis kiggede i en
    tabel.

    Beskeden baerer kommandoen, fordi verbet er svaert at gaette: det hedder
    `unlock <id>` i Central CLI, ikke `approve` (som er bundet til tool-intents,
    autonomi-forslag og initiativer og derfor ikke rammer noegler).

    `importance="normal"`: en optjent noegle er en mulighed, ikke et brud — den
    skal ikke vaekke nogen om natten. Self-safe; en fejlet notifikation maa
    aldrig forhindre at noeglen bliver udstedt.
    """
    uid = _ejer_uid()
    if not uid:
        return False
    navn = domain.split(":", 1)[-1]
    try:
        from core.services.notification_router import route_proactive_notification
        res = route_proactive_notification(
            uid, "keymaker_key_earned",
            {"title": "🔑 The Keymaker: nøgle optjent",
             "message": (f"«{navn}» har {track} beslutninger med 0 fejl og har optjent en "
                         f"decentraliserings-nøgle. Den er PENDING indtil du godkender.\n"
                         f"Godkend i Central CLI: unlock <id>  (se dem med: keys)\n"
                         f"En godkendt nøgle udløber automatisk efter 24 timer.")},
            importance="normal")
        return bool(res.get("delivered"))
    except Exception:
        return False


# ── Adfaerds-noegler: han optjener selv, ikke kun gates ─────────────────────
#
# Bjoern 8/9-2026: «keymakeren er et point system hvor han kan optjene noegler
# for rigtig adfaerd og det autonome arbejde han laver».
#
# Den eksisterende optjening maaler GATES (gate_verdict_ledger). Denne maaler
# HAM: holder han sine egne forpligtelser? Kilden er `behavioral_decisions.
# adherence_score`, som anmelderen saetter — verificeret levende 8/9 (37 af 44
# aktive har en score, snit 0,70, senest anmeldt 5/9).
#
# Smiths `seq:`-moenstre er BEVIDST ikke med i grundlaget: de laeses fra
# capability_invocations, hvis sidste aegte koersel er 15. maj, og en beloenning
# maalt paa frosne tal ville vaere gratis. `behaviour:`-moenstre er derimod
# levende («tomme loefter» blev resolved 7/9 kl. 08:35).
_ADFAERD_MIN_SCOREDE = 20      # for faa maalinger = for lidt at gaa efter
_ADFAERD_MIN_SNIT = 0.85       # snittet i dag er 0,70 — den skal FORTJENES
_ADFAERD_GULV = 0.5            # og ingen enkelt forpligtelse maa ligge og flyde
_ADFAERD_DOMAENE = "behaviour:adherence"


def _adfaerds_track_record() -> dict[str, Any] | None:
    """Hans egen efterlevelse af sine forpligtelser. ``None`` hvis den ikke kan maales."""
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT adherence_score FROM behavioral_decisions "
                "WHERE status='active' AND adherence_score IS NOT NULL").fetchall()
    except Exception:
        return None
    scorer = [float(r["adherence_score"]) for r in rows]
    if len(scorer) < _ADFAERD_MIN_SCOREDE:
        return None
    return {"antal": len(scorer), "snit": sum(scorer) / len(scorer), "lavest": min(scorer)}


def evaluate_behaviour_key() -> dict[str, Any]:
    """Udsted en PENDING adfaerds-noegle naar HAN har fortjent den. Self-safe.

    Samme kontrakt som gate-noeglerne og af samme grund: den genererer aldrig
    adgang selv, den venter paa ejeren, og den udloeber. Falder efterlevelsen
    bagefter, fornys noeglen ikke — den doer af sig selv efter 24 timer.
    """
    ud: dict[str, Any] = {"issued": None, "track": None}
    t = _adfaerds_track_record()
    if t is None:
        return ud
    ud["track"] = t
    if t["snit"] < _ADFAERD_MIN_SNIT or t["lavest"] < _ADFAERD_GULV:
        return ud
    try:
        with connect() as conn:
            _ensure_table(conn)
            findes = conn.execute(
                "SELECT 1 FROM central_keys WHERE domain=? AND status IN ('pending','approved')",
                (_ADFAERD_DOMAENE,)).fetchone()
            if findes:
                return ud
            reason = ("efterlevelse %.2f over %d forpligtelser, laveste %.2f "
                      "→ han holder hvad han lover" % (t["snit"], t["antal"], t["lavest"]))
            conn.execute(
                """INSERT INTO central_keys
                   (domain, unlock_scope, unlock_name, track_value, issued_at, status, reason)
                   VALUES (?, 'behaviour', 'adherence', ?, ?, 'pending', ?)""",
                (_ADFAERD_DOMAENE, int(round(t["snit"] * 100)), _now().isoformat(), reason),
            )
            conn.commit()
        ud["issued"] = {"domain": _ADFAERD_DOMAENE, **t, "reason": reason}
        _observe("earned", {"domain": _ADFAERD_DOMAENE, "track": round(t["snit"], 3)})
        _varsl_ejer(_ADFAERD_DOMAENE, int(round(t["snit"] * 100)))
    except Exception:
        pass
    return ud


def har_adfaerds_noegle() -> bool:
    """True hvis han har en GYLDIG (godkendt + ikke udloebet) adfaerds-noegle.

    Laeses som `is_decentralized` — mod tabellen, aldrig mod en switch, der
    defaulter til ON og dermed ville give noeglen gratis.
    """
    return is_decentralized("adherence")


def list_keys(*, include_expired: bool = False) -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            _ensure_table(conn)
            q = ("SELECT * FROM central_keys ORDER BY id DESC LIMIT 50" if include_expired else
                 "SELECT * FROM central_keys WHERE status IN ('pending','approved') ORDER BY id DESC LIMIT 50")
            return [dict(r) for r in conn.execute(q).fetchall()]
    except Exception:
        return []


def is_decentralized(nerve: str) -> bool:
    """True hvis <nerve> har en GYLDIG optjent decentraliserings-nøgle: status='approved' OG endnu
    ikke udløbet (expires_at i fremtiden). Dette er den ENESTE korrekte konsum-check.

    KRITISK: brug ALDRIG ``central_switches.is_enabled("decentralize", nerve)`` som konsum-gate —
    den defaulter til ON, så en unset nerve ville fremstå decentraliseret UDEN en optjent nøgle og
    underminere hele optjenings-modellen (jf. design-noten). Denne funktion læser den faktiske
    ledger-række. Self-safe → False ved enhver fejl (fail-closed: ingen nøgle = ingen autonomi)."""
    try:
        now = _now().isoformat()
        with connect() as conn:
            _ensure_table(conn)
            row = conn.execute(
                """SELECT 1 FROM central_keys
                   WHERE unlock_name=? AND status='approved'
                     AND expires_at != '' AND expires_at > ? LIMIT 1""",
                (nerve, now)).fetchone()
            return row is not None
    except Exception:
        return False


def approve_key(key_id: int) -> dict[str, Any]:
    """OWNER-handling: godkend en pending nøgle → flip dens flag ON i TTL. Auto-reverterer ved udløb.
    Self-safe."""
    try:
        with connect() as conn:
            _ensure_table(conn)
            row = conn.execute("SELECT * FROM central_keys WHERE id=? AND status='pending'",
                               (key_id,)).fetchone()
            if not row:
                return {"ok": False, "error": "ingen pending nøgle med det id"}
            # Defense-in-depth (§11.3): re-validér klassen ved GODKENDELSE, ikke kun ved udstedelse.
            # Selv hvis en SECURITY-nøgle på nogen måde blev udstedt (race, katalog-drift, manuel
            # INSERT), må den ALDRIG flippe et sikkerheds-flag ON. Afvis + markér 'rejected'.
            if _is_never(row["unlock_name"]):
                conn.execute("UPDATE central_keys SET status='rejected' WHERE id=?", (key_id,))
                conn.commit()
                _observe("rejected", {"domain": row["domain"], "reason": "security-klasse (§11.3)"})
                return {"ok": False, "error": "sikkerheds-nerve kan ALDRIG decentraliseres (§11.3)"}
            expires = (_now() + timedelta(hours=_KEY_TTL_HOURS)).isoformat()
            conn.execute("UPDATE central_keys SET status='approved', expires_at=? WHERE id=?",
                        (expires, key_id))
            conn.commit()
        # flip flaget uden for DB-transaktionen
        try:
            from core.services import central_switches
            central_switches.set_enabled(row["unlock_scope"], row["unlock_name"], True)
        except Exception:
            pass
        _observe("unlocked", {"domain": row["domain"], "expires_at": expires})
        return {"ok": True, "domain": row["domain"], "expires_at": expires}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def expire_due() -> dict[str, Any]:
    """Cadence: reverter flag for udløbne nøgler (tilladelse mistes hvis ikke fornyet). Self-safe."""
    out = {"expired": 0}
    try:
        now = _now().isoformat()
        with connect() as conn:
            _ensure_table(conn)
            due = conn.execute(
                "SELECT * FROM central_keys WHERE status='approved' AND expires_at != '' AND expires_at < ?",
                (now,)).fetchall()
            for row in due:
                try:
                    from core.services import central_switches
                    central_switches.set_enabled(row["unlock_scope"], row["unlock_name"], False)
                except Exception:
                    pass
                conn.execute("UPDATE central_keys SET status='expired' WHERE id=?", (row["id"],))
                _observe("expired", {"domain": row["domain"]})
            conn.commit()
            out["expired"] = len(due)
    except Exception:
        pass
    out["mindet_om"] = _mind_om_ventende()
    return out


_PAAMINDELSE_NOEGLE = "keymaker:paamindelse"
_PAAMINDELSE_TTL_S = 86400
_VENTETID_DAGE = 3


def _mind_om_ventende() -> int:
    """Mind om noegler der har ventet paa godkendelse i mere end tre dage.

    Varslingen ved udstedelse daekker kun NYE noegler. Uden dette ville de tre
    der allerede laa PENDING i to maaneder blive ved at ligge tavse — og en
    udstedelses-varsling der ikke naaede frem ville aldrig faa en anden chance.
    En noegle der udloeber uden godkendelse er tabt arbejde: det skete for
    noegle 1 (veto, 125 beslutninger) mellem 6. og 10. juli.

    Én gang i doegnet, uanset hvor mange der venter — noegler er sjaeldne
    (fire paa to maaneder), saa en daglig paamindelse er ikke stoej. Self-safe.
    """
    try:
        from core.services import shared_cache
        if shared_cache.get(_PAAMINDELSE_NOEGLE) is not None:
            return 0
    except Exception:
        return 0        # kan vi ikke rate-limitere, minder vi hellere ikke om

    try:
        graense = (_now() - timedelta(days=_VENTETID_DAGE)).isoformat()
        with connect() as conn:
            _ensure_table(conn)
            ventende = conn.execute(
                "SELECT * FROM central_keys WHERE status='pending' AND issued_at < ? ORDER BY id",
                (graense,)).fetchall()
        if not ventende:
            return 0
        uid = _ejer_uid()
        if not uid:
            return 0
        linjer = ["%s — %s (%d beslutninger, 0 fejl)" % (
            r["id"], str(r["unlock_name"]), int(r["track_value"] or 0)) for r in ventende]
        from core.services.notification_router import route_proactive_notification
        route_proactive_notification(
            uid, "keymaker_key_pending",
            {"title": "🔑 %d nøgle(r) venter på dig" % len(ventende),
             "message": ("Optjent, men ikke i brug før du godkender:\n" + "\n".join(linjer) +
                         "\n\nCentral CLI: unlock <id>   (se dem med: keys)")},
            importance="normal")
        try:
            from core.services import shared_cache
            shared_cache.set(_PAAMINDELSE_NOEGLE, True, ttl_seconds=_PAAMINDELSE_TTL_S)
        except Exception:
            pass
        return len(ventende)
    except Exception:
        return 0


def build_keymaker_surface() -> dict[str, Any]:
    """Owner-view: aktive/afventende nøgler + fortjente dimensioner. Self-safe."""
    ev = evaluate_keys()
    keys = list_keys(include_expired=True)
    pending = [k for k in keys if k["status"] == "pending"]
    approved = [k for k in keys if k["status"] == "approved"]
    return {
        "keys": keys, "pending_count": len(pending), "approved_count": len(approved),
        "earned": ev.get("earned", []),
        "felt": (f"{len(pending)} nøgle(r) venter på dit ja; {len(approved)} åben(e)."
                 if pending or approved else "Ingen nøgler optjent endnu — jeg beviser mig stadig."),
    }
