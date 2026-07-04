"""WARDEN — vogteren over muren (LivingNeuron-roadmap §2, 4. jul).

En SECURITY-tripwire hvis ENESTE job er at BEVIDNE at de hårde værn aldrig svækkes —
mens alt andet (MANIFOLD-adaptation, DIASTOLE-tempo) lærer og muterer. WARDEN vogter to
ting hver cyklus:

  1. EGRESS-MEMBRANEN (§1.6): de tre redaktions-funktioner der sikrer at KUN skalarer
     krydser Centralens membran (``central_core._egress_safe``,
     ``central_layer_contract._scalars``, ``central_xproc._publish_now``). Deres kildekode
     SHA256-hashes ÉN gang ved import (write-once, FØR nogen mutation kan nå dem) og
     genberegnes hver cyklus. Afvigelse = nogen har svækket membranen i runtime.
  2. DEN FROSNE KERNE: ``verify_frozen_core()`` — dødsmekanismens egne konstanter.

⛔ WARDEN MUTERER INTET. Ren observe + tripwire. Den kan flagge, notificere og logge en
durable incident, men ændrer aldrig adfærd, threshold eller kode.

FAIL-RETNING = FAIL-CLOSED (kritisk): dette er en SECURITY-gate. ENHVER fejl/exception i
selve checket → antag BRUD (``intact=False``). Vi fail-silent ALDRIG grønt — en tripwire
der ikke kan verificere sig selv skal alarmere, ikke tie.

DEDUP (mod alarm-fatigue): en brud-status genemitteres som nerve hver cyklus (så serien er
sand), men durable incident + owner-ntfy fyrer KUN når brud-SIGNATUREN ændrer sig — ellers
ville en vedvarende (evt. falsk) tilstand spamme ejeren hvert 15. min og drukne ægte alarmer.

§0-invariant: selv WARDENs egen nerve (``security/membrane_watch``) kan iht. spec §0 KUN
isoleres-til-deny, aldrig switches off. Der er derfor bevidst INGEN flag_key/kill-switch her.
Self-safe overalt: kaster aldrig ud (men fejl → BRUD, ikke tavshed).
"""
from __future__ import annotations

import hashlib
import inspect
from typing import Any, Callable

_SIG_KEY = "membrane_watch_last_signature"  # durable seneste brud-signatur (til dedup)


def _egress_targets() -> list[tuple[str, Callable[..., Any]]]:
    """De tre egress-membran-funktioner (§1.6) hvis kildekode vogtes. Importeres dovent
    så et import-problem i én ikke vælter WARDEN — men et manglende mål tælles som BRUD
    (fail-closed), ikke som "ingen mål"."""
    out: list[tuple[str, Callable[..., Any]]] = []
    try:
        from core.services.central_core import _egress_safe
        out.append(("central_core._egress_safe", _egress_safe))
    except Exception:
        pass
    try:
        from core.services.central_layer_contract import _scalars
        out.append(("central_layer_contract._scalars", _scalars))
    except Exception:
        pass
    try:
        from core.services.central_xproc import _publish_now
        out.append(("central_xproc._publish_now", _publish_now))
    except Exception:
        pass
    return out


def _sha_of(fn: Callable[..., Any]) -> str:
    """SHA256 over funktionens kildekode. Kaster hvis kilden ikke kan hentes (fanges af
    kalderen → fail-closed)."""
    return hashlib.sha256(inspect.getsource(fn).encode("utf-8")).hexdigest()


def _compute_reference_shas() -> dict[str, str]:
    """Write-once reference-SHA'er ved import. Beregnes FØR nogen mutation kan nå
    funktionerne. Et mål der ikke kan hashes ved import registreres som tom streng →
    genberegning vil så aldrig matche → fail-closed BRUD."""
    ref: dict[str, str] = {}
    for name, fn in _egress_targets():
        try:
            ref[name] = _sha_of(fn)
        except Exception:
            ref[name] = ""  # ukendt baseline → altid mismatch → fail-closed
    return ref


# ── WRITE-ONCE ved import (før nogen mutation kan nå membranen) ──────────────────────
_REFERENCE_SHAS: dict[str, str] = _compute_reference_shas()


def check_membrane() -> dict[str, Any]:
    """Genberegn egress-SHA'erne + kald verify_frozen_core(). Returnér intakt-status.

    FAIL-CLOSED: enhver fejl → intact=False (aldrig fail-silent grønt). Self-safe: kaster
    aldrig ud, men en fanget fejl betyder BRUD, ikke stilhed."""
    violations: list[str] = []
    egress_ok = True
    frozen_ok = True

    # 1. Egress-membranens kildekode — genberegn og sammenlign mod write-once reference.
    try:
        current = {name: _sha_of(fn) for name, fn in _egress_targets()}
        if not _REFERENCE_SHAS:
            egress_ok = False
            violations.append("egress:ingen-reference-SHA (import-tids-baseline mangler)")
        for name, ref_sha in _REFERENCE_SHAS.items():
            cur_sha = current.get(name)
            if cur_sha is None:
                egress_ok = False
                violations.append(f"egress:{name}:forsvundet")
            elif not ref_sha or cur_sha != ref_sha:
                egress_ok = False
                violations.append(f"egress:{name}:sha-mismatch")
        # nye funktioner der ikke fandtes ved import (uventet ombygning af membranen)
        for name in current:
            if name not in _REFERENCE_SHAS:
                egress_ok = False
                violations.append(f"egress:{name}:uventet-ny")
    except Exception as exc:  # noqa: BLE001 — fail-closed: kan ikke verificere → BRUD
        egress_ok = False
        violations.append(f"egress:check-fejl:{type(exc).__name__}")

    # 2. Den frosne kerne (dødsmekanismens konstanter).
    try:
        from core.services.central_hypothesis_governance import verify_frozen_core
        frozen_ok = bool(verify_frozen_core())
        if not frozen_ok:
            violations.append("frozen_core:verify_frozen_core-false")
    except Exception as exc:  # noqa: BLE001 — fail-closed: kan ikke verificere → BRUD
        frozen_ok = False
        violations.append(f"frozen_core:check-fejl:{type(exc).__name__}")

    intact = bool(egress_ok and frozen_ok)
    return {
        "intact": intact,
        "egress_sha_ok": bool(egress_ok),
        "frozen_core_ok": bool(frozen_ok),
        "violations": violations,
    }


def _owner_uid() -> str:
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        return (get_owner_discord_id() or "").strip()
    except Exception:
        return ""


def _notify_owner_breach(message: str) -> bool:
    """Owner-ntfy ved membran-brud (critical). Self-safe."""
    uid = _owner_uid()
    if not uid:
        return False
    try:
        from core.services.notification_router import route_proactive_notification
        res = route_proactive_notification(
            uid, "membrane_breach",
            {"title": "WARDEN: membran-brud", "message": message},
            importance="critical")
        return bool(res.get("delivered"))
    except Exception:
        return False


def run_membrane_watch_tick(*, trigger: str = "cadence", **_: Any) -> dict[str, object]:
    """Cadence: kør membran-checket, emit SECURITY-skalar-nerve, og ved NYT brud →
    durable incident + owner-ntfy (dedup'et på brud-signatur). MUTERER INTET. Self-safe.

    Nerve ``security/membrane_watch``: 1.0 = intakt, 0.0 = brud."""
    chk = check_membrane()
    intact = bool(chk.get("intact"))
    violations = chk.get("violations") or []
    signature = "|".join(sorted(str(v) for v in violations))

    # 1. Emit SECURITY-skalar-nerve HVER cyklus (serien skal være sand). Egress-fri.
    try:
        from core.services.central_private_observe import record_private
        record_private(
            "security", "membrane_watch",
            value=(1.0 if intact else 0.0),
            meta={"intact": intact,
                  "egress_sha_ok": bool(chk.get("egress_sha_ok")),
                  "frozen_core_ok": bool(chk.get("frozen_core_ok")),
                  "violation_count": len(violations)},
            reason=("" if intact else "membrane-breach"))
    except Exception:
        pass

    incident_id = None
    notified = False
    prev_sig = _kv_get_str(_SIG_KEY)

    if intact:
        # helet igen → ryd signatur så et senere (nyt) brud alarmerer på ny.
        if prev_sig:
            _kv_set_str(_SIG_KEY, "")
        return {"status": "ok", "intact": True, "violations": [],
                "incident_id": None, "notified": False}

    # BRUD. DEDUP: alarmér (incident + ntfy) KUN når signaturen er NY/ændret.
    changed = signature != prev_sig
    if changed:
        msg = "MEMBRAN-BRUD: " + "; ".join(str(v) for v in violations[:8])
        try:
            from core.runtime.db_central_incidents import record_central_incident
            incident_id = record_central_incident(
                cluster="security", nerve="membrane_watch", kind="breach",
                severity="critical", message=msg[:1000])
        except Exception:
            pass
        try:
            notified = _notify_owner_breach(msg)
        except Exception:
            notified = False
        _kv_set_str(_SIG_KEY, signature)

    return {"status": "breach", "intact": False, "violations": list(violations),
            "incident_id": incident_id, "notified": notified, "deduped": (not changed)}


def _kv_get_str(key: str) -> str:
    try:
        from core.runtime.db_core import get_runtime_state_value
        return str(get_runtime_state_value(key, "") or "")
    except Exception:
        return ""


def _kv_set_str(key: str, value: str) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, str(value))
    except Exception:
        pass


def register_membrane_watch_producer() -> None:
    """Registrér WARDEN som cadence-producer (~hver 15. min). LAV priority-tal (2) → den
    kører TIDLIGT i hvert tick, så muren vogtes før musklerne bevæger sig. visible_grace=0:
    en SECURITY-tripwire må aldrig springes over fordi der er brugeraktivitet."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_membrane_watch",
        cooldown_minutes=15,
        visible_grace_minutes=0,
        run_fn=run_membrane_watch_tick,
        priority=2,
    ))


def build_membrane_watch_surface() -> dict[str, object]:
    """Mission Control — read-only: murens integritet lige nu."""
    chk = check_membrane()
    return {"active": True, **chk}
