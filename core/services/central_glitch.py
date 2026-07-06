"""The One's Anomaly Detector — glitches i selvbilledet (overskud som glitch).

Bjørn+Claude (6. jul, gartner-idé #3): "I know kung fu." Neo ser Matrixen som det den er — kode, og
glitches i koden. Denne detektor ser Centralens egen krop på samme måde: en policy der er REGISTRERET
men aldrig faktisk beslutter (altid-shadow/altid-skip), eller en nerve der engang fyrede og så DØDE
(frossen). Det er ikke fejl der larmer — det er stille overskud. En déjà vu i systemet: noget der
burde gøre en forskel, men ikke gør.

(Adskilt fra `central_anomaly.py`, som fanger RUNTIME-exceptions. Dette er strukturelle glitches i
governance-kroppen — søster til [[central_excess]] og [[central_construct]].)

Hver glitch markeres med en bevidst anbefalet handling: ENFORCE (den bør faktisk beslutte),
RETIRE (den bærer intet — absorbér/slet), eller INVESTIGATE (noget døde — find ud af hvorfor).
Propose-only: detektoren markerer, den sletter ikke. Owner (eller gartner/keymaker) handler.

Kilde: gate_verdict_ledger (persistent — overlever restart, i modsætning til den in-memory tidsserie).
Self-safe: kaster aldrig; muterer aldrig noget.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# En nerve regnes frossen hvis dens seneste beslutning er ældre end dette OG den havde reel volumen.
_FROZEN_DAYS = 7
_FROZEN_MIN_VOLUME = 20
# Nerver hvor "retire" ALDRIG må foreslås — sikkerhed/execution/helbred (frossen kerne).
_NEVER_RETIRE = frozenset({"cross_user_share", "exec_command", "exec_file", "exec_workspace_trust",
                           "auth", "tool_access", "central_self_probe"})


def _age_days(last_ts: str) -> float | None:
    try:
        then = datetime.fromisoformat(last_ts)
        if then.tzinfo is None:
            then = then.replace(tzinfo=UTC)
        return (datetime.now(UTC) - then).total_seconds() / 86400.0
    except Exception:
        return None


def detect_glitches() -> dict[str, Any]:
    """Find stille overskud: altid-shadow policies + frosne nerver. READ-ONLY. Self-safe.
    Returnerer {glitches: [{nerve, type, detail, action}], always_shadow, frozen, felt}."""
    out: dict[str, Any] = {"glitches": [], "always_shadow": 0, "frozen": 0, "felt": ""}
    try:
        from core.services.gate_verdict_ledger import summary
        rows = summary()
    except Exception:
        return out
    glitches: list[dict[str, Any]] = []
    for nerve, agg in rows.items():
        total = int(agg.get("total") or 0)
        if total <= 0:
            continue
        skip = int(agg.get("skip") or 0)
        protected = nerve in _NEVER_RETIRE
        # (1) altid-shadow: registreret men beslutter aldrig reelt (hvert verdict er skip).
        if skip == total:
            glitches.append({
                "nerve": nerve, "type": "always_shadow", "total": total,
                "detail": f"{total} verdicts, alle skip — registreret men beslutter aldrig",
                "action": "investigate" if protected else "enforce_or_retire",
            })
            continue
        # (2) frossen: fyrede før med volumen, men har været tavs længe (nerven døde).
        age = _age_days(agg.get("last_ts", ""))
        if age is not None and age >= _FROZEN_DAYS and total >= _FROZEN_MIN_VOLUME:
            glitches.append({
                "nerve": nerve, "type": "frozen", "total": total, "age_days": round(age, 1),
                "detail": f"sidste beslutning for {age:.0f} dage siden efter {total} kald — nerven tav",
                "action": "investigate",
            })
    glitches.sort(key=lambda d: -d.get("total", 0))
    shadow = [g for g in glitches if g["type"] == "always_shadow"]
    frozen = [g for g in glitches if g["type"] == "frozen"]
    out["glitches"] = glitches
    out["always_shadow"] = len(shadow)
    out["frozen"] = len(frozen)
    if not glitches:
        out["felt"] = "Ingen glitches i selvbilledet — alt der er registreret, lever og beslutter."
    else:
        out["felt"] = (f"Jeg ser {len(shadow)} policy(er) der aldrig rigtig beslutter og "
                       f"{len(frozen)} nerve(r) der er gået i stå — stille overskud jeg bærer uden grund.")
    return out


def record_glitches() -> dict[str, Any]:
    """Cadence: observér glitches til nerve system/glitch (metadata-only). Self-safe."""
    out = detect_glitches()
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "glitch", "kind": "self_glitch",
                           "always_shadow": out["always_shadow"], "frozen": out["frozen"]})
    except Exception:
        pass
    return out
