"""Central consequence — hvor en karakters fund FAKTISK lander.

Målt 13/11-2026, den samme defekt i alle 14 Matrix-karakterer: de **beregner**
en konsekvens og kaster den væk.

* `central_sentinel.attack()` regner `proposed_confidence = conf / 2.0` ud,
  gemmer den i en kolonne der hedder `proposed_`, og skriver ALDRIG tilbage.
  `_enforced()` er en shadow-flag der er slukket, og der findes ingen kode bag
  den — så «håndhævelse» var en gren der ikke eksisterede.
* `central_redpill` tæller blå piller og læser aldrig sit eget tal.
* `central_dissent` returnerer `total_objections` til en verden der ikke lytter.

Det er samme fejlform som Smiths «Trin 2 — bundet» uden en binding, og som
`health_check` der pegede på port 8000: en tilstand der påstår en handling der
ikke findes. Stemmen er nu ægte (se `central_matrix_ensemble`), men en stemme
uden konsekvens er stadig teater — bare med bedre replikker.

## Tre levers, og kun tre

1. **confidence** — en hypotese der er angrebet skal faktisk falde. Går gennem
   `central_hypothesis_governance.apply_outcome` (Popper: falsifikation er et
   hårdt multiplikativt nedtræk), ikke gennem en selvopfundet formel.
2. **decision** — et adfærdsmønster bliver en bindende forpligtelse via
   `behavioral_decisions.create_decision`. Den er den stærkeste: et direktiv
   dukker op i hvert heartbeat, indtil det er revokeret eller opfyldt.
3. **record** — fundet lander i `central_consequences` som en reviderbar række.
   Bruges når de to andre ikke må anvendes (vagt, loft, shadow).

Flere levers er ikke bedre. Hver lever er en mutation af noget levende, og
hver mutation kræver et værn.

## Værnene

* **Støj-vetoet** (`smith_noise_veto`) — det samme der standsede 31 mintede
  direktiver med to med indhold. En n-gram-detektor kan ikke skelne en
  adfærdsvane fra almindeligt dansk, så den kan kun sige nej.
* **Dags-loft** — en brækket detektor må ikke kunne køre hele systemet over.
  Målt behov: `central_hypotheses` har 152.754 rækker; en cadence-producer der
  halverer den højeste confidence hver kørsel ville æde økosystemet på timer.
* **Idempotens** — samme (cid, lever, subject) lander kun én gang pr. døgn.

## Det der gør det målbart

`measure_consequences()` svarer på det ene spørgsmål teatret ikke kan svare på:
**hvor mange fund flyttede faktisk noget?** `applied=1` og `before != after`
er beviset. `applied=0` med en grund er ærligt; `applied=1` uden en flytning
er en løgn, og derfor tælles de to ting hver for sig.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_TABLE = "central_consequences"

# Hvor mange landinger pr. lever pr. døgn. Et loft er ikke en semantisk grænse
# — det er et værn mod en detektor der er gået i stykker. 152.754 hypoteser
# betyder at en utæmmet confidence-lever kan tømme økosystemet på få timer.
_DAGSLoft = {"confidence": 8, "decision": 3, "record": 500}


def _nu() -> str:
    return datetime.now(UTC).isoformat()


def _connect():
    from core.runtime.db import connect
    return connect()


def _ensure(conn) -> None:
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cid TEXT NOT NULL,
            lever TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            before_value TEXT NOT NULL DEFAULT '',
            after_value TEXT NOT NULL DEFAULT '',
            applied INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_cid ON {_TABLE}(cid, created_at)"
    )


def _landinger_sidste_doegn(conn, lever: str) -> int:
    cutoff = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    r = conn.execute(
        f"SELECT COUNT(*) FROM {_TABLE} WHERE lever=? AND applied=1 AND created_at>=?",
        (lever, cutoff),
    ).fetchone()
    return int((r or [0])[0] or 0)


def _allerede_landet(conn, cid: str, lever: str, subject: str) -> bool:
    """Idempotens: samme fund lander ikke to gange i samme døgn.

    Uden dette ville en cadence-producer der kører hvert tredje kvarter skrive
    den samme konklusion 96 gange i døgnet — og hver skrivning ville se ud som
    en ny konsekvens i målingen.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    r = conn.execute(
        f"SELECT 1 FROM {_TABLE} WHERE cid=? AND lever=? AND subject=? AND applied=1 AND created_at>=? LIMIT 1",
        (cid, lever, subject, cutoff),
    ).fetchone()
    return r is not None


def _skriv(
    conn,
    *,
    cid: str,
    lever: str,
    subject: str,
    before: str = "",
    after: str = "",
    applied: bool = False,
    reason: str = "",
) -> None:
    conn.execute(
        f"""INSERT INTO {_TABLE} (cid, lever, subject, before_value, after_value, applied, reason, created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
        (cid, lever, subject[:200], str(before)[:200], str(after)[:200], 1 if applied else 0, reason[:300], _nu()),
    )


def _loft_ramt(conn, lever: str) -> str | None:
    loft = int(_DAGSLoft.get(lever, 0))
    n = _landinger_sidste_doegn(conn, lever)
    if loft and n >= loft:
        return f"dagsloft ramt ({n}/{loft})"
    return None


def _gate_taend(scope: str, name: str) -> bool:
    """Er leverens switch taendt?

    UKENDT betyder TAENDT. Det er et bevidst valg, og det er den modsatte
    standard af `central_sentinel._enforced()`, som returnerede False naar
    flaget ikke var sat — med det resultat at «haandhaevelse» var en gren der
    aldrig kunne koere. En shadow-standard der ikke skriver er ikke et vaern;
    det er en undskyldning der ser ud som forsigtighed.

    Det der FAKTISK vaerner mod en braekket detektor er dagsloftet og
    stoej-vetoet, ikke en tavs standard. Switchen er derfor en kill-switch:
    saet den eksplicit til enabled=False, og leveren standser.
    """
    try:
        from core.services.central_switches import _key, shared_cache
        val = shared_cache.get(_key(scope, name))
        if val is None:
            return True
        return isinstance(val, dict) and val.get("enabled") is True
    except Exception as exc:
        # Kan switchen ikke laeses, antages SLUKKET: en mutation maa ikke ske paa
        # et grundlag der ikke kunne verificeres. Modsat UKENDT-flaget, som
        # betyder taendt — her fejlede laesningen selv.
        logger.debug("central_consequence: switch-laesning fejlede: %s", exc)
        return False


def land_confidence(
    cid: str,
    hyp_id: str,
    *,
    falsified: bool = True,
    reason: str = "",
    gate: tuple[str, str] = ("sentinel", "enforce"),
) -> dict[str, Any]:
    """Lad et angreb FAKTISK flytte hypotesens confidence.

    Formlen er `apply_outcome` — den sanktionerede Popper-regel, ikke en
    selvopfundet halvering. `falsified=True` giver et haardt multiplikativt
    nedtraek; en modsigelse dominerer mange bekræftelser, og det er hele
    pointen med at have en Sentinel.

    `applied=False` med en grund er et aerligt svar — en shadow-tilstand der
    ikke skriver, men som heller ikke paastaar at den gjorde noget.
    """
    out: dict[str, Any] = {"applied": False, "before": None, "after": None, "reason": ""}
    try:
        from core.services.central_hypothesis_governance import apply_outcome
    except Exception as exc:
        out["reason"] = f"governance utilgaengelig: {exc}"
        return out

    try:
        with _connect() as conn:
            _ensure(conn)
            row = conn.execute(
                "SELECT confidence FROM central_hypotheses WHERE hyp_id=?", (hyp_id,)
            ).fetchone()
            if row is None:
                out["reason"] = "hypotese findes ikke"
                return out
            before = float((row["confidence"] if isinstance(row, dict) else row[0]) or 0.0)
            out["before"] = before

            def _afvis(why: str) -> dict[str, Any]:
                out["reason"] = why
                _skriv(conn, cid=cid, lever="confidence", subject=hyp_id,
                       before=str(before), after=str(before), applied=False, reason=why)
                conn.commit()
                return out

            if _allerede_landet(conn, cid, "confidence", hyp_id):
                return _afvis("allerede landet i doegnet")
            if not _gate_taend(*gate):
                return _afvis(f"switch slukket: {gate[0]}/{gate[1]}")
            if (loft := _loft_ramt(conn, "confidence")) is not None:
                return _afvis(loft)

            after = float(apply_outcome(before, falsified=bool(falsified)))
            # Et loft er ét vaern; dette er det andet: et enkelt angreb maa ikke
            # kunne nulstille en hypotese. Den skal kunne forsvare sig.
            after = max(0.01, min(1.0, after))
            if abs(after - before) < 1e-9:
                return _afvis("ingen flytning")

            conn.execute("UPDATE central_hypotheses SET confidence=? WHERE hyp_id=?", (after, hyp_id))
            _skriv(conn, cid=cid, lever="confidence", subject=hyp_id,
                   before=str(before), after=str(after), applied=True, reason=reason or "falsified")
            conn.commit()
            out.update({"applied": True, "after": after, "reason": reason or "falsified"})
            return out
    except Exception as exc:
        logger.debug("central_consequence: land_confidence fejlede: %s", exc)
        out["reason"] = f"fejl: {str(exc)[:120]}"
        return out


def land_decision(
    cid: str,
    directive: str,
    *,
    rationale: str = "",
    trigger_cue: str = "",
    priority: int = 55,
    subject: str = "",
    gate: tuple[str, str] = ("consequence", "bind_decisions"),
) -> dict[str, Any]:
    """Lad et fund blive en BINDENDE forpligtelse.

    Gaar gennem stoej-vetoet foerst. Det er ikke forsigtighed: det er maalt.
    Uden vetoet har Smith mintet 31 direktiver hvoraf to havde indhold — og
    seks handlede om hans egen replik, der kom retur via prompt-halen.
    """
    out: dict[str, Any] = {"applied": False, "decision_id": None, "reason": ""}
    subject = (subject or directive)[:200]
    try:
        from core.services.smith_noise_veto import maa_minte
        ok, grund = maa_minte(f"{cid}:{subject}", directive)
        if not ok:
            out["reason"] = f"veto: {grund}"
            with _connect() as conn:
                _ensure(conn)
                _skriv(conn, cid=cid, lever="decision", subject=subject,
                       applied=False, reason=out["reason"])
                conn.commit()
            return out
    except Exception as exc:
        out["reason"] = f"veto utilgaengeligt: {str(exc)[:80]}"
        return out

    try:
        with _connect() as conn:
            _ensure(conn)
            if _allerede_landet(conn, cid, "decision", subject):
                out["reason"] = "allerede landet i doegnet"
                _skriv(conn, cid=cid, lever="decision", subject=subject,
                       applied=False, reason=out["reason"])
                conn.commit()
                return out
            if not _gate_taend(*gate):
                out["reason"] = f"switch slukket: {gate[0]}/{gate[1]}"
                _skriv(conn, cid=cid, lever="decision", subject=subject,
                       applied=False, reason=out["reason"])
                conn.commit()
                return out
            if (loft := _loft_ramt(conn, "decision")) is not None:
                out["reason"] = loft
                _skriv(conn, cid=cid, lever="decision", subject=subject,
                       applied=False, reason=out["reason"])
                conn.commit()
                return out
            conn.commit()
    except Exception as exc:
        out["reason"] = f"fejl: {str(exc)[:120]}"
        return out

    try:
        from core.services.behavioral_decisions import create_decision
        dec = create_decision(
            directive=directive,
            rationale=rationale or None,
            trigger_cue=trigger_cue or None,
            priority=int(priority),
            source_type=f"character:{cid}",
            created_by="jarvis",
        )
        did = str(dec.get("decision_id") or "") or None
        deduped = bool(dec.get("deduped"))
        out.update({"applied": not deduped, "decision_id": did,
                    "reason": "deduped" if deduped else "bundet"})
        with _connect() as conn:
            _ensure(conn)
            _skriv(conn, cid=cid, lever="decision", subject=subject,
                   before="", after=str(did or ""), applied=not deduped, reason=out["reason"])
            conn.commit()
        return out
    except Exception as exc:
        out["reason"] = f"create_decision fejlede: {str(exc)[:120]}"
        return out


def record(cid: str, subject: str, *, detail: str = "") -> dict[str, Any]:
    """Fund uden en anvendelig lever: skriv det ned som reviderbart spor.

    Den aerlige tredje mulighed — ikke en undskyldning for at lade vaere, men
    svaret naar der ikke findes et vaern der goer mutationen forsvarlig.
    """
    try:
        with _connect() as conn:
            _ensure(conn)
            _skriv(conn, cid=cid, lever="record", subject=subject, after=detail[:200], applied=False)
            conn.commit()
        return {"applied": False, "reason": "kun registreret"}
    except Exception as exc:
        logger.debug("central_consequence: record fejlede: %s", exc)
        return {"applied": False, "reason": f"fejl: {str(exc)[:120]}"}


def measure_consequences(*, days: int = 7) -> dict[str, Any]:
    """Beviset: hvor mange fund flyttede faktisk noget?

    `applied=1` OG `before != after` er den eneste kombination der taeller som
    en aegte konsekvens. En raekke med `applied=1` uden flytning er en loegn, og
    taelles derfor separat — den slags skal kunne ses, ikke skjules i et snit.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=max(1, int(days)))).isoformat()
    try:
        with _connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                f"""SELECT cid, lever, applied, before_value, after_value
                    FROM {_TABLE} WHERE created_at>=?""",
                (cutoff,),
            ).fetchall()
    except Exception as exc:
        # Maalingen er beviset — fejler den, skal det staa i loggen og ikke kun
        # som et svar der ligner "ingen konsekvenser".
        logger.warning("central_consequence: measure fejlede: %s", exc)
        return {"status": "fejl", "error": str(exc)[:160]}

    per: dict[str, dict[str, int]] = {}
    flyttede = 0
    uden_flytning = 0
    for r in rows:
        cid = str(r[0] if not isinstance(r, dict) else r["cid"])
        applied = int(r[2] if not isinstance(r, dict) else r["applied"] or 0)
        before = str(r[3] if not isinstance(r, dict) else r["before_value"] or "")
        after = str(r[4] if not isinstance(r, dict) else r["after_value"] or "")
        d = per.setdefault(cid, {"landet": 0, "afvist": 0, "flyttede": 0})
        if applied:
            d["landet"] += 1
            if before != after:
                d["flyttede"] += 1
                flyttede += 1
            else:
                uden_flytning += 1
        else:
            d["afvist"] += 1
    return {
        "status": "ok",
        "dage": days,
        "i_alt": len(rows),
        "flyttede": flyttede,
        "landet_uden_flytning": uden_flytning,
        "per_karakter": per,
        "uden_landing": sorted(c for c, d in per.items() if d["landet"] == 0),
    }
