"""Merovingian — den konservative ældste der tvinger Centralen til at forsvare sin egen evolution.

Bjørn+Claude (6. jul): "Alle dine andre værn er REAKTIVE — de træder i kraft når noget er sket.
Merovingian er PROAKTIV: han stiller spørgsmålstegn ved enhver foreslået ændring, FØR den sker."

Hans job er ikke at blokere — det er at forhindre GRADVIS DRIFT. Uden ham: 100 små ændringer, hver
harmløs, driver systemet langt fra sin hensigt uden at nogen enkelt så farlig ud. Med ham: hver
ændring skal forsvares mod en modhypotese, og en pause lader Bjørn (eller Oracle) se retningen.

Mekanik:
  1. MODHYPOTESE — for hver hypotese nær adoptions-tærsklen, generér det modsatte SYMBOLSK (ingen
     LLM): A→B ⇒ A→¬B; A≈B ⇒ A≠B; "øg X" ⇒ "sænk X / X er måske forkert variabel".
  2. DEVIL'S ADVOCATE — tjek variablens track-record: "dine sidste N forsøg på at ændre X gav 0
     forbedring — hvorfor skulle denne gang være anderledes?"
  3. COOLING-OFF — hvis modhypotesen har støtte: 24t pause hvor Centralen skal (a) indsamle flere
     beviser, (b) omformulere, eller (c) opgive.
  4. VETO MED FORKLARING — Merovingian kan ikke selv veto (§8 overruler). Men han tvinger en
     interlanguage-forklaring på HVORFOR modhypotesen er forkert, logget + synlig via Central-CLI.
  5. GENTAGEN UDFORDRING — samme type ændring udfordret ≥3× ⇒ omskriv eller opgiv i 30 dage.

SHADOW-FØRST (Fase 1): default observerer han kun — genererer + logger modhypoteser, blokerer INTET.
`is_adoption_blocked` returnerer altid False indtil enforce-flag flippes (efter shadow-eval). §8 er
altid suveræn. Synlighed via Central-CLI (den nye MC), IKKE Mission Control. Self-safe.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_core import connect

_COOLING_HOURS = 24
_ABANDON_DAYS = 30
_REPEAT_LIMIT = 3
# Nær-tærskel: hypoteser Merovingian gider udfordre (lige under handlings-tærsklen 0.7/3).
_NEAR_CONFIDENCE = 0.6
_NEAR_SAMPLES = 2
_ACTIVE = ("active", "open", "pending", "testing")


def _now() -> datetime:
    return datetime.now(UTC)


def _enforced() -> bool:
    """Shadow-først: enforcement er OFF indtil flag EKSPLICIT flippes efter shadow-eval. §8 forbliver
    suveræn. (central_switches.is_enabled defaulter til ON → vi kræver et eksplicit sat flag i stedet,
    så Merovingian aldrig utilsigtet begynder at blokere.)"""
    try:
        from core.services.central_switches import _key, shared_cache
        val = shared_cache.get(_key("merovingian", "enforce"))
        return isinstance(val, dict) and val.get("enabled") is True
    except Exception:
        return False


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "merovingian", "kind": kind, **payload})
    except Exception:
        pass


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_merovingian (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hyp_id TEXT NOT NULL, variable TEXT NOT NULL DEFAULT '',
            counter TEXT NOT NULL DEFAULT '', support INTEGER NOT NULL DEFAULT 0,
            devils_advocate TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'challenged', explanation TEXT NOT NULL DEFAULT '',
            challenged_at TEXT NOT NULL, cools_off_at TEXT NOT NULL DEFAULT '',
            resolved_at TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_merov_hyp ON central_merovingian(hyp_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_merov_status ON central_merovingian(status)")


def generate_counter(hyp: dict[str, Any]) -> dict[str, str]:
    """Generér en modhypotese SYMBOLSK (ingen LLM) fra notation/statement. Self-safe."""
    notation = str(hyp.get("notation_il") or "").strip()
    statement = str(hyp.get("statement") or "").strip()
    low = statement.lower()
    # 1) notations-negation (interlanguage)
    if notation:
        if "->" in notation:
            x, y = notation.split("->", 1)
            return {"counter": f"{x.strip()} -> ¬{y.strip()}", "type": "negated_consequent"}
        for rel in ("≈", "~"):
            if rel in notation:
                x, y = notation.split(rel, 1)
                return {"counter": f"{x.strip()} ≠ {y.strip()}", "type": "negated_relation"}
        if "↔" in notation:
            return {"counter": f"¬({notation})", "type": "negated_tension"}
    # 2) retnings-negation fra sprog
    up = any(w in low for w in ("øg", "øge", "increase", "raise", "hæv", "højere", "mere", "+"))
    down = any(w in low for w in ("sænk", "decrease", "lower", "reducer", "mindre", "lavere", "-"))
    if up and not down:
        return {"counter": f"det modsatte: variablen bør SÆNKES, ikke øges — eller den er forkert valgt",
                "type": "reversed_direction"}
    if down and not up:
        return {"counter": f"det modsatte: variablen bør ØGES, ikke sænkes — eller den er forkert valgt",
                "type": "reversed_direction"}
    # 3) fallback: udfordr variabel-valget
    return {"counter": "den valgte variabel er måske ikke den rigtige at justere",
            "type": "wrong_variable"}


def _variable_of(hyp: dict[str, Any]) -> str:
    """Stabil variabel-nøgle: source + family (så track-record slås op pr. konkret variabel)."""
    src = str(hyp.get("source") or "")
    fam = ""
    try:
        prov = hyp.get("provenance_json")
        if isinstance(prov, str) and prov:
            fam = str(json.loads(prov).get("family") or "")
        elif isinstance(prov, dict):
            fam = str(prov.get("family") or "")
    except Exception:
        fam = ""
    return f"{src}:{fam}".strip(":")


def variable_track_record(variable: str) -> dict[str, Any]:
    """Devil's advocate-data: hvordan er det gået SIDSTE gang samme variabel blev justeret?
    READ-ONLY. Self-safe."""
    src = variable.split(":", 1)[0]
    try:
        with connect() as conn:
            rows = conn.execute(
                """SELECT outcome, status FROM central_hypotheses
                   WHERE source=? AND resolved_at IS NOT NULL ORDER BY resolved_at DESC LIMIT 20""",
                (src,)).fetchall()
    except Exception:
        rows = []
    attempts = len(rows)
    failed = sum(1 for r in rows if str((r["status"] if hasattr(r, "keys") else r[1]) or "")
                 in ("falsified", "expired", "dead", "quarantined"))
    succeeded = attempts - failed
    # støtte til modhypotesen: hvis tidligere forsøg overvejende fejlede.
    support = attempts >= 3 and failed >= max(2, int(attempts * 0.6))
    if attempts == 0:
        note = f"ingen track-record for '{src}' endnu — ny variabel, forhøjet forsigtighed"
        support = True   # ukendt terræn → udfordr
    elif support:
        note = f"dine sidste {attempts} forsøg med '{src}': {failed} fejlede. Hvorfor nu anderledes?"
    else:
        note = f"'{src}': {succeeded}/{attempts} tidligere forsøg lykkedes — rimelig track-record"
    return {"variable": variable, "attempts": attempts, "failed": failed,
            "succeeded": succeeded, "support": support, "note": note}


def review(hyp: dict[str, Any]) -> dict[str, Any]:
    """Kernen: generér modhypotese + tjek track-record → approved | challenged. Registrerer en
    udfordring (shadow-loggging som standard). §8 overruler; dette forsinker kun. Self-safe."""
    hyp_id = str(hyp.get("hyp_id") or hyp.get("id") or "")
    if not hyp_id:
        return {"verdict": "approved", "reason": "intet hyp_id"}
    counter = generate_counter(hyp)
    variable = _variable_of(hyp)
    tr = variable_track_record(variable)
    # gentagen udfordring? → omskriv-eller-opgiv
    prior = _count_challenges(variable)
    if not tr["support"]:
        return {"verdict": "approved", "counter": counter["counter"], "variable": variable,
                "devils_advocate": tr["note"], "enforced": _enforced()}
    # støtte til modhypotesen → udfordr
    abandon = prior + 1 >= _REPEAT_LIMIT
    cools_hours = _ABANDON_DAYS * 24 if abandon else _COOLING_HOURS
    cools_off = (_now() + timedelta(hours=cools_hours)).isoformat()
    status = "abandon_window" if abandon else "challenged"
    cid = _record_challenge(hyp_id, variable, counter["counter"], tr, status, cools_off)
    _observe("challenged", {"variable": variable, "support": True, "abandon": abandon,
                            "enforced": _enforced()})
    return {"verdict": "challenged", "challenge_id": cid, "counter": counter["counter"],
            "counter_type": counter["type"], "variable": variable, "devils_advocate": tr["note"],
            "cools_off_at": cools_off, "abandon": abandon, "explanation_required": True,
            "enforced": _enforced()}


def _count_challenges(variable: str) -> int:
    try:
        with connect() as conn:
            _ensure(conn)
            return int(conn.execute(
                "SELECT COUNT(*) FROM central_merovingian WHERE variable=?", (variable,)).fetchone()[0])
    except Exception:
        return 0


def _record_challenge(hyp_id: str, variable: str, counter: str, tr: dict, status: str,
                      cools_off: str) -> int | None:
    try:
        with connect() as conn:
            _ensure(conn)
            cur = conn.execute(
                """INSERT INTO central_merovingian
                   (hyp_id, variable, counter, support, devils_advocate, status, challenged_at, cools_off_at)
                   VALUES (?, ?, ?, 1, ?, ?, ?, ?)""",
                (hyp_id, variable, counter, tr["note"], status, _now().isoformat(), cools_off))
            conn.commit()
            return int(cur.lastrowid)
    except Exception:
        return None


def resolve_challenge(hyp_id: str, *, explanation: str) -> dict[str, Any]:
    """Centralen skriver en (interlanguage-)forklaring på HVORFOR modhypotesen er forkert → adoption
    kan fortsætte når cooling er udløbet. Self-safe."""
    if not explanation.strip():
        return {"ok": False, "error": "forklaring påkrævet"}
    try:
        with connect() as conn:
            _ensure(conn)
            cur = conn.execute(
                """UPDATE central_merovingian SET status='explained', explanation=?, resolved_at=?
                   WHERE hyp_id=? AND status IN ('challenged','abandon_window')""",
                (explanation[:1000], _now().isoformat(), hyp_id))
            conn.commit()
            n = int(cur.rowcount or 0)
        if n:
            _observe("explained", {"hyp_id": hyp_id})
        return {"ok": bool(n), "resolved": n}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def is_adoption_blocked(hyp_id: str) -> bool:
    """Enforcement-tjek: er adoption pt. blokeret af en aktiv, uforklaret cooling-off? I SHADOW-mode
    (default) returnerer den ALTID False — Merovingian observerer kun. Self-safe. §8 er suveræn."""
    if not _enforced():
        return False
    try:
        now = _now().isoformat()
        with connect() as conn:
            _ensure(conn)
            row = conn.execute(
                """SELECT 1 FROM central_merovingian
                   WHERE hyp_id=? AND status IN ('challenged','abandon_window')
                   AND cools_off_at > ? LIMIT 1""", (hyp_id, now)).fetchone()
        return bool(row)
    except Exception:
        return False


def expire_cooling() -> dict[str, Any]:
    """Cadence: udløb cooling-off-perioder hvis tiden er gået (status → expired). Self-safe."""
    out = {"expired": 0}
    try:
        now = _now().isoformat()
        with connect() as conn:
            _ensure(conn)
            cur = conn.execute(
                """UPDATE central_merovingian SET status='expired', resolved_at=?
                   WHERE status IN ('challenged','abandon_window') AND cools_off_at != '' AND cools_off_at < ?""",
                (now, now))
            conn.commit()
            out["expired"] = int(cur.rowcount or 0)
    except Exception:
        pass
    return out


def _maturing_hypotheses(limit: int = 20) -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            ph = ",".join("?" for _ in _ACTIVE)
            rows = conn.execute(
                f"""SELECT hyp_id, statement, prediction, confidence, grounded_samples, status,
                    source, provenance_json, notation_il FROM central_hypotheses
                    WHERE status IN ({ph}) AND confidence >= ? AND grounded_samples >= ?
                    ORDER BY confidence DESC LIMIT ?""",
                (*_ACTIVE, _NEAR_CONFIDENCE, _NEAR_SAMPLES, limit)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def scan_and_challenge(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Fase 1-cadence: scan modne hypoteser → generér+log modhypoteser (shadow: blokerer intet).
    Udløb gamle cooling-offs. Self-safe."""
    expire_cooling()
    maturing = _maturing_hypotheses()
    challenged = 0
    already = set()
    for h in maturing:
        hid = str(h.get("hyp_id") or "")
        if hid in already:
            continue
        already.add(hid)
        # spring over hvis allerede udfordret og uafgjort
        if _has_open_challenge(hid):
            continue
        r = review(h)
        if r.get("verdict") == "challenged":
            challenged += 1
    _observe("scan", {"maturing": len(maturing), "challenged": challenged, "enforced": _enforced()})
    return {"status": "ok", "maturing": len(maturing), "challenged": challenged}


def _has_open_challenge(hyp_id: str) -> bool:
    try:
        with connect() as conn:
            _ensure(conn)
            return bool(conn.execute(
                "SELECT 1 FROM central_merovingian WHERE hyp_id=? AND status IN ('challenged','abandon_window') LIMIT 1",
                (hyp_id,)).fetchone())
    except Exception:
        return False


def list_challenges(*, active_only: bool = True, limit: int = 40) -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            _ensure(conn)
            q = ("SELECT * FROM central_merovingian WHERE status IN ('challenged','abandon_window') "
                 "ORDER BY id DESC LIMIT ?" if active_only else
                 "SELECT * FROM central_merovingian ORDER BY id DESC LIMIT ?")
            return [dict(r) for r in conn.execute(q, (limit,)).fetchall()]
    except Exception:
        return []


def build_merovingian_surface() -> dict[str, Any]:
    """Central-CLI-view (den nye MC): aktive udfordringer + cooling-offs + følt linje. Self-safe."""
    active = list_challenges(active_only=True)
    needs_expl = [c for c in active if not c.get("explanation")]
    felt = (f"{len(active)} ændring(er) udfordret; {len(needs_expl)} venter på at Centralen forsvarer "
            f"sig. Jeg bremser ikke — jeg tvinger et forsvar." if active else
            "Ingen foreslåede ændringer udfordret lige nu. Driften holdes i skak.")
    return {"active_challenges": active, "active_count": len(active),
            "awaiting_explanation": len(needs_expl), "enforced": _enforced(), "felt": felt}
