"""core/services/central_sequence.py

Tråd 4 (Intelligent Central-spec §6): CENTRALEN TRÆNER SIG SELV — ægte parametrisk selv-supervision.

Den ENESTE tråd hvor Centralen opdaterer en intern PARAMETER fra data UDEN modellen. central_trace +
event-strømmen er et selv-superviseret datasæt: en lille lokal MARKOV-model (ikke LLM'en) lærer at
forudsige næste event-familie fra den forrige. Så bliver:
  * prediktions-FEJL = overraskelses-signal (surprise = lav forudsagt sandsynlighed for det der SKETE)
  * prediktions-VÆGTE (transition-tællinger) = adaptationen der læres fra erfaring.

Det gør Lag 3 (hypotese) og Lag 4 (adaptation) til ÉT lærende objekt der ikke er sprogmodellen —
matcher paperets tese (intelligens i runtime-strukturen) mere direkte end en regel-motor.

§8: læringen (transition-aggregater) passerer gate_learning_input (kun skalarer). Cursor-baseret
(tæller hver overgang ÉN gang). Egress-fri observe. Alt read/observe, self-safe, kaster ALDRIG.
"""
from __future__ import annotations

from typing import Any

from core.services import central_hypothesis_governance as gov

_CURSOR_KEY = "central_sequence_cursor"      # sidste lærte event-id (cursor, cross-proces via kv)
_WINDOW = 3000
_MIN_FROM_TOTAL = 20         # from-familie skal være set ≥ dette før en overgang kan overraske
_SURPRISE_PROB = 0.05        # observeret overgang med forudsagt P < dette = overraskende
_SCHEMA_READY = False


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def ensure_schema() -> None:
    try:
        from core.runtime.db import connect
        with connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS central_sequence_transitions (
                  from_fam TEXT NOT NULL,
                  to_fam   TEXT NOT NULL,
                  count    INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY (from_fam, to_fam)
                );
                CREATE INDEX IF NOT EXISTS idx_seq_from ON central_sequence_transitions(from_fam);
                """
            )
            c.commit()
    except Exception:
        pass


def _fam(kind: str) -> str:
    return str(kind or "").split(".", 1)[0]


def learn_from_stream(*, window: int = _WINDOW) -> dict[str, int]:
    """Lær transition-tællinger fra NYE events siden cursor (tæller hver overgang ÉN gang). Aggregatet
    passerer gate_learning_input (§8.2: kun skalarer krydser lærings-membranen). Self-safe."""
    ensure_schema()
    try:
        from core.eventbus.bus import event_bus
        rows = event_bus.recent(limit=int(window))
    except Exception:
        return {"learned": 0, "cursor": 0}
    evs = sorted(({"id": int(e.get("id") or 0), "fam": _fam(e.get("kind"))} for e in rows),
                 key=lambda z: z["id"])
    try:
        cursor = int(_kv_get(_CURSOR_KEY, 0) or 0)
    except Exception:
        cursor = 0
    # kun overgange hvor BARN-eventet er nyt (id > cursor) tælles → ingen dobbelt-tælling
    pairs: dict[tuple[str, str], int] = {}
    max_id = cursor
    for i in range(1, len(evs)):
        a, b = evs[i - 1], evs[i]
        if b["id"] <= cursor or not a["fam"] or not b["fam"]:
            continue
        pairs[(a["fam"], b["fam"])] = pairs.get((a["fam"], b["fam"]), 0) + 1
        max_id = max(max_id, b["id"])
    if not pairs:
        return {"learned": 0, "cursor": cursor}
    # §8.2: læringen passerer membranen (aggregat-skalarer)
    gated = gov.gate_learning_input({"count": sum(pairs.values()), "n": len(pairs)})
    if not gated["ok"]:
        return {"learned": 0, "cursor": cursor, "blocked": True}
    try:
        from core.runtime.db import connect
        with connect() as c:
            for (a, b), n in pairs.items():
                c.execute(
                    "INSERT INTO central_sequence_transitions (from_fam, to_fam, count) VALUES (?,?,?) "
                    "ON CONFLICT(from_fam, to_fam) DO UPDATE SET count = count + ?",
                    (a, b, n, n))
            c.commit()
    except Exception:
        return {"learned": 0, "cursor": cursor}
    _kv_set(_CURSOR_KEY, int(max_id))
    return {"learned": sum(pairs.values()), "cursor": int(max_id), "pairs": len(pairs)}


def _from_total(c, from_fam: str) -> int:
    row = c.execute("SELECT COALESCE(SUM(count),0) FROM central_sequence_transitions WHERE from_fam=?",
                    (from_fam,)).fetchone()
    return int(row[0] or 0)


def transition_prob(from_fam: str, to_fam: str) -> float:
    """P(to | from) fra de lærte tællinger. 0.0 hvis aldrig set. Self-safe."""
    try:
        from core.runtime.db import connect
        with connect() as c:
            total = _from_total(c, from_fam)
            if total <= 0:
                return 0.0
            row = c.execute("SELECT count FROM central_sequence_transitions WHERE from_fam=? AND to_fam=?",
                            (from_fam, to_fam)).fetchone()
            return (int(row[0]) / total) if row else 0.0
    except Exception:
        return 0.0


def predict_next(from_fam: str, *, top: int = 5) -> list[dict[str, Any]]:
    """Hvad forudsiger modellen følger efter from_fam? (top mest sandsynlige). Self-safe."""
    try:
        from core.runtime.db import connect
        with connect() as c:
            total = _from_total(c, from_fam)
            if total <= 0:
                return []
            rows = c.execute("SELECT to_fam, count FROM central_sequence_transitions WHERE from_fam=? "
                             "ORDER BY count DESC LIMIT ?", (from_fam, int(top))).fetchall()
        return [{"to": str(r[0]), "prob": round(int(r[1]) / total, 4)} for r in rows]
    except Exception:
        return []


def detect_surprises(*, window: int = _WINDOW, min_from_total: int = _MIN_FROM_TOTAL,
                     threshold: float = _SURPRISE_PROB) -> list[dict[str, Any]]:
    """Overraskelser: overgange der FAKTISK skete i det seneste vindue, men som modellen forudsagde
    som usandsynlige (P < threshold) — OG hvor modellen har set from-familien nok (≥ min_from_total)
    til at være sikker. Prediktions-fejl = surprise = hypotese-signal. Self-safe."""
    try:
        from core.eventbus.bus import event_bus
        rows = event_bus.recent(limit=int(window))
    except Exception:
        return []
    evs = sorted(({"id": int(e.get("id") or 0), "fam": _fam(e.get("kind"))} for e in rows),
                 key=lambda z: z["id"])
    seen: set[tuple[str, str]] = set()
    out = []
    try:
        from core.runtime.db import connect
        with connect() as c:
            for i in range(1, len(evs)):
                a, b = evs[i - 1]["fam"], evs[i]["fam"]
                if not a or not b or a == b or (a, b) in seen:
                    continue
                seen.add((a, b))
                total = _from_total(c, a)
                if total < int(min_from_total):
                    continue
                row = c.execute("SELECT count FROM central_sequence_transitions WHERE from_fam=? AND to_fam=?",
                                (a, b)).fetchone()
                p = (int(row[0]) / total) if row else 0.0
                if p < float(threshold):
                    out.append({"from_family": a, "to_family": b, "prob": round(p, 4),
                                "from_total": total, "cursor": evs[i]["id"]})
    except Exception:
        return []
    out.sort(key=lambda x: x["prob"])
    return out


def run_sequence_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: lær fra strømmen + detektér overraskelser. Egress-fri observe. Self-safe."""
    learned = learn_from_stream()
    surprises = detect_surprises()
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "sequence_self_train",
                       value=float(learned.get("learned") or 0),
                       meta={"learned": learned.get("learned"), "surprises": len(surprises),
                             "pairs": learned.get("pairs")})
    except Exception:
        pass
    return {"status": "ok", "learned": learned.get("learned"), "surprises": len(surprises)}


def register_sequence_producer() -> None:
    """Registrér selv-træningen som cadence-producer (~hvert 15 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_sequence",
        cooldown_minutes=15,
        visible_grace_minutes=0,
        run_fn=run_sequence_tick,
        priority=6,
    ))


def build_central_sequence_surface() -> dict[str, object]:
    """Mission Control surface — read-only: model-størrelse + aktuelle overraskelser."""
    n = 0
    try:
        from core.runtime.db import connect
        with connect() as c:
            n = int(c.execute("SELECT COUNT(*) FROM central_sequence_transitions").fetchone()[0] or 0)
    except Exception:
        pass
    return {"active": True, "transitions_learned": n, "surprises": detect_surprises()[:8]}
