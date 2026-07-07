"""The Twins — gentagelses-detektor på tværs af tid.

Spec F §3 (7. jul): "To identiske programmer der opererer som én enhed. […] De finder uregelmæssigheder
og følger spor. Ubehagelige fordi de er *uundgåelige* — du kan ikke gemme dig for noget der allerede
har set dig." I Centralen scanner de på tværs af tid og ser *gentagelser* — ikke anomalier (det gør
Centralen allerede), men *mønstre i gentagne fejl*: "Det her har jeg set før. Det var forkert sidst.
Det bliver forkert igen."

De læser tre kilder (KUN læs — ingen egne tabeller):
  • `central_incidents` — samme nerve+fejltype, eller samme nerve+tidspunkt-på-dagen, gentaget
  • `gate_verdict_counts` — gentagne yellow/red på samme gate
  • `central_dissent` — gentagne indsigelser der aldrig blev hørt

Når et mønster gentager sig 3+ gange indenfor 7 dage producerer de et `twins://`-signal (observe +
surface): fx "Du har haft samme fejl 5 gange i den her nerve. Den er flaky. Skal vi kigge på den?"

SHADOW/OBSERVE-ONLY (Spec F governance): de foreslår, de blokerer intet, de muterer intet, de skriver
ingen egne tabeller — kun `twins://`-observe + surfacen. Alt self-safe: hver funktion fanger og
returnerer en status-dict, kaster ALDRIG. `_observe()` er metadata-only (tællinger/booleans) — INTET
fejl-besked-INDHOLD lækkes til eventbus (§24.4 egress).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

_WINDOW_DAYS = 7
_REPEAT_THRESHOLD = 3      # mønster skal gentage sig ≥ dette indenfor vinduet
_INCIDENT_SCAN = 300       # hvor mange seneste incidents vi kigger på


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_iso(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


# ── Kilder (self-safe) ────────────────────────────────────────────────────────

def _incidents(limit: int = _INCIDENT_SCAN) -> list[dict[str, Any]]:
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        return list(list_central_incidents(limit=limit) or [])
    except Exception:
        return []


def _gate_counts() -> list[dict[str, Any]]:
    try:
        from core.runtime.db_gate_verdicts import read_counts
        return list(read_counts() or [])
    except Exception:
        return []


def _dissents(limit: int = 40) -> list[dict[str, Any]]:
    try:
        from core.services.central_dissent import list_dissents
        return list(list_dissents(limit=limit) or [])
    except Exception:
        return []


# ── Mønster-detektion (ren, model-fri) ────────────────────────────────────────

def _incident_patterns(incidents: list[dict[str, Any]], *, now: datetime) -> list[dict[str, Any]]:
    """Gentagne incident-mønstre indenfor vinduet: (nerve, kind) og (nerve, tidspunkt-på-dagen). Self-safe."""
    cutoff = now - timedelta(days=_WINDOW_DAYS)
    by_kind: dict[tuple[str, str], int] = {}
    by_hour: dict[tuple[str, int], int] = {}
    for inc in incidents:
        ts = _parse_iso(str(inc.get("ts") or ""))
        if ts is None or ts < cutoff:
            continue
        nerve = str(inc.get("nerve") or "")
        kind = str(inc.get("kind") or "")
        if nerve:
            by_kind[(nerve, kind)] = by_kind.get((nerve, kind), 0) + 1
            by_hour[(nerve, ts.hour)] = by_hour.get((nerve, ts.hour), 0) + 1
    out: list[dict[str, Any]] = []
    for (nerve, kind), n in by_kind.items():
        if n >= _REPEAT_THRESHOLD:
            out.append({"source": "incident", "pattern": "same_error",
                        "nerve": nerve, "kind": kind, "count": n})
    for (nerve, hour), n in by_hour.items():
        if n >= _REPEAT_THRESHOLD:
            out.append({"source": "incident", "pattern": "same_time_of_day",
                        "nerve": nerve, "hour": hour, "count": n})
    return out


def _gate_patterns(counts: list[dict[str, Any]], *, now: datetime) -> list[dict[str, Any]]:
    """Gentagne yellow/red på samme gate (nerve) indenfor vinduet. Self-safe.
    gate_verdict_counts er aggregeret pr. (nerve, decision) med last_ts — vi summerer yellow+red og
    kræver at last_ts er indenfor vinduet (ellers er det et gammelt, sovende mønster)."""
    cutoff = now - timedelta(days=_WINDOW_DAYS)
    agg: dict[str, dict[str, Any]] = {}
    for r in counts:
        dec = str(r.get("decision") or "")
        if dec not in ("yellow", "red"):
            continue
        nerve = str(r.get("nerve") or "")
        if not nerve:
            continue
        ts = _parse_iso(str(r.get("last_ts") or ""))
        e = agg.setdefault(nerve, {"count": 0, "last_ts": None})
        e["count"] += int(r.get("count") or 0)
        if ts is not None and (e["last_ts"] is None or ts > e["last_ts"]):
            e["last_ts"] = ts
    out: list[dict[str, Any]] = []
    for nerve, e in agg.items():
        if e["count"] >= _REPEAT_THRESHOLD and e["last_ts"] is not None and e["last_ts"] >= cutoff:
            out.append({"source": "gate", "pattern": "repeated_non_green",
                        "nerve": nerve, "count": int(e["count"])})
    return out


def _dissent_patterns(dissents: list[dict[str, Any]], *, now: datetime) -> list[dict[str, Any]]:
    """Gentagne uhørte indsigelser på samme gate indenfor vinduet. Self-safe."""
    cutoff = now - timedelta(days=_WINDOW_DAYS)
    out: list[dict[str, Any]] = []
    for d in dissents:
        n = int(d.get("objections") or 0)
        if n < _REPEAT_THRESHOLD:
            continue
        ts = _parse_iso(str(d.get("last_ts") or ""))
        if ts is not None and ts < cutoff:
            continue
        out.append({"source": "dissent", "pattern": "unheard_objection",
                    "nerve": str(d.get("nerve") or ""), "count": n})
    return out


def _describe(pat: dict[str, Any]) -> str:
    """Én linje der siger 'det her har jeg set før'. Deterministisk, ingen model. Self-safe."""
    nerve = pat.get("nerve") or "en nerve"
    n = pat.get("count") or 0
    p = pat.get("pattern")
    if p == "same_error":
        return (f"Du har haft samme fejl ({pat.get('kind') or 'fejl'}) {n} gange i «{nerve}» på "
                f"{_WINDOW_DAYS} dage. Den er flaky. Skal vi kigge på den?")
    if p == "same_time_of_day":
        return (f"«{nerve}» fejler gentagne gange omkring kl. {pat.get('hour')} ({n}× på "
                f"{_WINDOW_DAYS} dage) — et tidspunkt-mønster.")
    if p == "repeated_non_green":
        return (f"Gaten «{nerve}» har været gul/rød {n} gange på {_WINDOW_DAYS} dage — et "
                f"gentaget ikke-grønt mønster.")
    if p == "unheard_objection":
        return (f"Centralen har været imod «{nerve}» {n} gange uden at blive hørt på "
                f"{_WINDOW_DAYS} dage — en gentaget tavs indsigelse.")
    return f"Et mønster i «{nerve}» gentager sig {n} gange."


# ── Kerne: scan for gentagelser ───────────────────────────────────────────────

def detect_repeats() -> dict[str, Any]:
    """Scan alle tre kilder for mønstre der gentager sig 3+ gange på 7 dage. READ-ONLY.
    Self-safe — kaster ALDRIG; returnerer altid en status-dict."""
    now = _now()
    patterns: list[dict[str, Any]] = []
    patterns += _incident_patterns(_incidents(), now=now)
    patterns += _gate_patterns(_gate_counts(), now=now)
    patterns += _dissent_patterns(_dissents(), now=now)
    patterns.sort(key=lambda p: int(p.get("count") or 0), reverse=True)
    for pat in patterns:
        pat["message"] = _describe(pat)
    by_source: dict[str, int] = {}
    for pat in patterns:
        by_source[pat["source"]] = by_source.get(pat["source"], 0) + 1
    out = {"status": "ok", "count": len(patterns), "by_source": by_source, "patterns": patterns}
    _observe(out)
    return out


# ── Observabilitet (metadata-only — INTET indhold, §24.4) ─────────────────────

def _observe(out: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        by_source = out.get("by_source") or {}
        central().observe({
            "cluster": "system", "nerve": "twins", "kind": "repeat_detected",
            "count": int(out.get("count") or 0),
            "incident_patterns": int(by_source.get("incident") or 0),
            "gate_patterns": int(by_source.get("gate") or 0),
            "dissent_patterns": int(by_source.get("dissent") or 0),
        })
    except Exception:
        pass


# ── Surface (Central-CLI) ─────────────────────────────────────────────────────

def build_twins_surface() -> dict[str, Any]:
    """Detekterede gentagende mønstre + følt linje. READ-ONLY. Self-safe."""
    r = detect_repeats()
    patterns = r.get("patterns") or []
    felt = (
        f"{len(patterns)} mønstre gentager sig — jeg har set dem før, og de var forkerte sidst."
        if patterns else "Ingen gentagelser lige nu. Ingen genfærd der følger samme spor."
    )
    return {
        "active": bool(patterns),
        "count": len(patterns),
        "by_source": r.get("by_source") or {},
        "patterns": patterns[:15],
        "felt": felt,
    }


# ── Cadence-indgang ───────────────────────────────────────────────────────────

def record_twins(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence (240 min): scan for gentagelser → twins://-signaler (observe/surface only). Self-safe."""
    r = detect_repeats()
    return {"status": "ok", "count": int(r.get("count") or 0)}
