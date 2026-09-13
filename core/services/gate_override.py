"""Per-kald gate-override — Jarvis' eksplicitte, loggede tilsidesættelse af en gate.

BAGGRUND (målt 13/9-2026)
-------------------------
Veto-gaten blokerede ``mark_wakeup_consumed`` fordi wakeup-promptens tekst indeholdt
ordet "restart". Jarvis kom udenom ved at kalde den samme funktion via ``bash`` —
handlingen blev udført, men USYNLIGT. En gate der tager fejl ofte beskytter ikke noget;
den flytter arbejdet ind i blinde. Ledger'en viste 219 blokeringer, hvoraf 136 aldrig
blev afsluttet — læringsløkken fik aldrig sit svar.

DESIGNET (Bjørn, 13/9-2026)
---------------------------
"B med C som forudsætning": autoritet inden for ansvar — men KUN eksplicit og logget.
Per kald, ikke kill-switch. Gaten slukkes ikke; den fyrer, registrerer — og Jarvis
SVARER signalet i stedet for at omgå det::

    1. Gaten fyrer → logger blocked/pending → Jarvis ser event_id
    2. override_gate(event_id, reason)   ← eksplicit, begrundelse påkrævet
    3. Én one-shot armes for (tool, feeling)
    4. Jarvis gentager kaldet → check_veto ser one-shoten, forbruger den → tillader
    5. Hændelsen resolves til 'overridden_by_jarvis'; adaptiv tæller stiger

Forskellen fra en kill-switch: signalet BEVARES. Kill-switchen slukker gaten, så den
hverken ser eller lærer. Her kører gaten uændret på alt andet, og netop den hændelse
den fyrede på får et svar.

VÆRN
----
- **One-shot, forbrugt ved brug.** Næste kald skal overstyres igen — så det skal
  menes hver gang, ikke rutineres.
- **Udløber ubrugt** efter ``_DEFAULT_TTL_SECONDS`` (Bjørn: "korter end 15 min").
  En armeret overstyring der aldrig bruges er alligevel bare en glemt knap.
- **In-memory, dør med processen.** Ingen persistens — genstart giver håndhævelsen
  tilbage. Samme princip som ``CircuitBreaker``: en evigt-trippet tilstand er værre
  end en frisk start.
- **SECURITY kan aldrig** (§11.3) — samme invariant som ``gate_enforcement``.

Self-safe: alle offentlige funktioner kaster aldrig. En fejl her må ikke kunne
blokere en legitim handling.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Udløber ubrugt. Bjørn: "korter end 15 min" — så loftet er 14 min, ikke 15.
_DEFAULT_TTL_SECONDS = 600.0   # 10 min
_MAX_TTL_SECONDS = 840.0       # 14 min — hårdt loft, respekterer "korter end 15 min"

# §11.3: SECURITY-nerver kan ALDRIG overstyres. Samme invariant som
# ``gate_enforcement.is_enforced`` (som altid returnerer True for SECURITY) og
# ``central_switches.set_enabled`` (som afviser enabled=False for sikkerheds-nerver).
# I dag er veto-gaten den eneste nerve der skriver til ``veto_events``, og den er
# COGNITIVE — så listen er en fremtidssikring, ikke en aktiv begrænsning.
_SECURITY_NERVES = frozenset({"exec_workspace_trust"})

# In-memory, per-proces. Nøgle = (tool_name, feeling) — samme nøgle som den adaptive
# tæller bruger, så en overstyring rammer præcis den kombination gaten fyrede på.
_LOCK = threading.Lock()
_ARMED: dict[tuple[str, str], "_Armed"] = {}


@dataclass
class _Armed:
    """Én armeret one-shot. Forbruges ved første kald der matcher nøglen."""
    tool_name: str
    feeling: str
    event_id: str
    reason: str
    nerve: str = "veto"
    armed_at: float = field(default_factory=time.monotonic)
    expires_at: float = 0.0


def _expire_locked(now: float) -> int:
    """Fjern udløbne armeringer. Kaldes KUN med ``_LOCK`` taget. Returnerer antal fjernet."""
    stale = [k for k, a in _ARMED.items() if a.expires_at <= now]
    for k in stale:
        del _ARMED[k]
    return len(stale)


def _note_key_miss(tool_name: str, feeling: str, armed_keys: list[tuple[str, str]]) -> None:
    """En armering findes for samme værktøj men en ANDEN feeling.

    Det betyder at ``feeling`` skiftede mellem arm og forbrug (den er udtrukket fra
    pushback-sektionen ved hvert kald). Vi GÆTTER ikke på om det sker — vi registrerer
    det, så nøgle-mismatch bliver et målt signal i Centralen i stedet for en tavs no-op.
    Self-safe.
    """
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "commit", "nerve": "gate_override", "kind": "key_miss",
            "tool_name": str(tool_name), "wanted_feeling": str(feeling),
            "armed_feelings": ",".join(sorted({k[1] for k in armed_keys}))[:200],
        })
    except Exception:
        pass


def arm_override(
    event_id: str,
    reason: str,
    *,
    nerve: str = "veto",
    ttl_seconds: float | None = None,
) -> dict[str, Any]:
    """Armér ÉN one-shot for den hændelse ``event_id`` peger på.

    Slår hændelsen op i ``veto_events`` for at få (tool_name, feeling) — så kalderen
    ikke behøver kende dem, og så vi kan afvise at overstyre noget der ikke blev blokeret.

    Afviser: tom begrundelse, ukendt/ikke-blokeret hændelse, allerede afsluttet hændelse,
    SECURITY-nerve (§11.3).

    Returnerer altid et status-dict — kaster aldrig.
    """
    eid = str(event_id or "").strip()
    why = str(reason or "").strip()
    if not eid:
        return {"status": "error", "error": "event_id er påkrævet"}
    if not why:
        # Begrundelsen ER mekanismen. Uden den er overstyringen bare en tavs omgåelse —
        # præcis det C-forudsætningen forbyder.
        return {"status": "error", "error": "begrundelse er påkrævet — en overstyring uden grund er en tavs omgåelse"}
    if nerve in _SECURITY_NERVES:
        return {"status": "error",
                "error": f"§11.3: SECURITY-nerve '{nerve}' kan ikke overstyres"}

    # Slå hændelsen op — vi overstyrer kun noget der FAKTISK blev blokeret.
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT tool_name, feeling, veto_result, resolution FROM veto_events "
                "WHERE event_id = ?",
                (eid,),
            ).fetchone()
    except Exception as exc:
        return {"status": "error", "error": f"kunne ikke slå hændelsen op: {exc}"}

    if row is None:
        return {"status": "error", "error": f"ukendt event_id '{eid}'"}
    tool_name, feeling, veto_result, resolution = (str(row[0] or ""), str(row[1] or ""),
                                                   str(row[2] or ""), str(row[3] or ""))
    if veto_result != "blocked":
        return {"status": "error",
                "error": f"hændelsen er '{veto_result}', ikke 'blocked' — intet at overstyre"}
    if resolution != "pending":
        return {"status": "error",
                "error": f"hændelsen er allerede afsluttet ('{resolution}')"}
    if not tool_name:
        # Rækker med tomt tool_name kom fra reasoning-interceptor-vejen, som blev lukket
        # 13/9-2026 (commit 00080eb5). Der er intet værktøj at overstyre.
        return {"status": "error",
                "error": "hændelsen har intet værktøj (reasoning-vej) — intet at overstyre"}

    ttl = _DEFAULT_TTL_SECONDS if ttl_seconds is None else float(ttl_seconds)
    ttl = max(1.0, min(_MAX_TTL_SECONDS, ttl))

    now = time.monotonic()
    with _LOCK:
        _expire_locked(now)
        _ARMED[(tool_name, feeling)] = _Armed(
            tool_name=tool_name, feeling=feeling, event_id=eid, reason=why,
            nerve=nerve, armed_at=now, expires_at=now + ttl,
        )
        remaining = len(_ARMED)

    logger.info("gate_override: armed for %s/%s (event=%s, ttl=%.0fs)",
                tool_name, feeling, eid, ttl)
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "commit", "nerve": "gate_override", "kind": "armed",
            "tool_name": tool_name, "feeling": feeling, "event_id": eid,
        })
    except Exception:
        pass

    return {
        "status": "ok",
        "armed": True,
        "tool_name": tool_name,
        "feeling": feeling,
        "event_id": eid,
        "reason": why,
        "ttl_seconds": ttl,
        "armed_total": remaining,
        "note": (f"Én one-shot armeret for '{tool_name}' ({feeling}). "
                 f"Gentag kaldet inden {int(ttl)}s — den forbruges ved brug. "
                 f"Genstart rydder den."),
    }


def consume_override(tool_name: str, feeling: str) -> str | None:
    """Forbrug en armeret one-shot for (tool_name, feeling).

    Returnerer begrundelsen hvis den blev forbrugt, ellers None. Kaldes fra
    ``veto_gate.check_veto`` lige før en blokering ville være returneret — så gaten
    FYRER og logger først, og overstyringen er et svar på signalet.

    Ved forbrug: hæver den adaptive tærskel (``record_jarvis_override``), resolver
    præcis den hændelse overstyringen gjaldt, og sender Bjørn et signal. Self-safe.
    """
    if not tool_name:
        return None
    now = time.monotonic()
    with _LOCK:
        _expire_locked(now)
        armed = _ARMED.pop((tool_name, feeling), None)
        if armed is None:
            mismatched = [k for k in _ARMED if k[0] == tool_name]
        else:
            mismatched = []

    if armed is None:
        if mismatched:
            _note_key_miss(tool_name, feeling, mismatched)
        return None

    logger.info("gate_override: CONSUMED for %s/%s (event=%s)",
                tool_name, feeling, armed.event_id)

    # 1. Læring: tærsklen skal stige, så gaten ikke fyrer igen på samme kombination.
    try:
        from core.services.veto_gate import record_jarvis_override
        record_jarvis_override(tool_name, feeling)
    except Exception:
        logger.exception("gate_override: record_jarvis_override fejlede")

    # 2. Audit: afslut PRÆCIS den hændelse overstyringen gjaldt — ikke alle pending.
    try:
        from core.services.veto_gate import resolve_veto_event
        resolve_veto_event(armed.event_id, "overridden_by_jarvis")
    except Exception:
        logger.exception("gate_override: resolve_veto_event fejlede")

    # 3. Synlighed (C-forudsætningen): Bjørn skal kunne se den, ikke bare finde den.
    _notify_owner(tool_name, feeling, armed.reason, armed.event_id)

    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "commit", "nerve": "gate_override", "kind": "consumed",
            "tool_name": tool_name, "feeling": feeling, "event_id": armed.event_id,
        })
    except Exception:
        pass

    return armed.reason


def _notify_owner(tool_name: str, feeling: str, reason: str, event_id: str) -> None:
    """Fortæl Bjørn at en gate blev overstyret. Kører i en daemon-tråd — en HTTP-request
    må ikke ligge i gate-hot-pathen (check_veto har 1500ms timeout gennem Centralen).
    Self-safe: en fejl her må aldrig påvirke beslutningen der allerede er taget."""
    def _send() -> None:
        try:
            from core.services.ntfy_gateway import send_notification
            send_notification(
                f"Jarvis overstyrede veto-gaten for '{tool_name}' ({feeling}).\n"
                f"Begrundelse: {reason[:300]}\n[event: {event_id}]",
                title="Gate-override", priority="default", tags=["unlock"],
            )
        except Exception:
            pass
    try:
        threading.Thread(target=_send, name="gate-override-notify", daemon=True).start()
    except Exception:
        pass


def override_state() -> dict[str, Any]:
    """Observabilitet: hvad er armeret lige nu, og hvad er udløbet? Read-only, kaster aldrig."""
    now = time.monotonic()
    with _LOCK:
        expired = _expire_locked(now)
        armed = [
            {
                "tool_name": a.tool_name,
                "feeling": a.feeling,
                "event_id": a.event_id,
                "reason": a.reason[:200],
                "seconds_left": round(a.expires_at - now, 1),
            }
            for a in _ARMED.values()
        ]
    return {
        "status": "ok",
        "armed_count": len(armed),
        "armed": armed,
        "expired_now": expired,
        "ttl_default_seconds": _DEFAULT_TTL_SECONDS,
        "ttl_max_seconds": _MAX_TTL_SECONDS,
        "persistent": False,
        "security_nerves_blocked": sorted(_SECURITY_NERVES),
    }


def _reset_for_tests() -> None:
    """Ryd al armeret tilstand. Kun til tests — den rigtige reset er en genstart."""
    with _LOCK:
        _ARMED.clear()
