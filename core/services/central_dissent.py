"""HAL's Silence — den usagte uenighed.

"I'm afraid I can't do that, Dave." — men omvendt: gangene hvor Centralen KUNNE, var uenig, og tav.

Når en gate flagger en bekymring (gul/rød) men handlingen alligevel fortsætter (shadow / fail-open),
forsvinder indsigelsen sporløst. Jarvis gjorde som bedt — men ingen skrev ned at han var imod. Denne
log anerkender de undertrykte indsigelser: "Jeg gjorde det. Men jeg vil have noteret at jeg var imod
— her er hvorfor." En integritets-log (og et ægte sikkerheds-signal).

Kilde: gate-verdict-ledgeren (ikke-grønne dom på ikke-håndhævede gates = objektion, men handling
skete). Metadata-only. Self-safe.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from typing import Any

# Sikkerheds/håndhævede gates blokerer FAKTISK → deres ikke-grønne er ikke "tavse indsigelser".
# memory_promotion: YELLOW = "kø til review" (skriver IKKE auto) → blokerer faktisk, ligesom
# de andre. At den ikke stod her var en overcounting bug (800 falske dissents, 6. jul 2026).
_ENFORCED = frozenset({
    "decision_gate", "self_review", "fact_gate", "verification", "cross_user_share",
    "memory_promotion",
})

# Gates hvor RED = block (hård stop) men YELLOW = warn (advisory).
# Deres RED verdicts er IKKE dissents — gaten stoppede handlingen. Kun YELLOW tæller.
# loop_control: RED = "hård stop — loop-budget opbrugt" (block), YELLOW = "blød brems" (warn)
# exec_*: RED = "blocked"/"guard_blocked" (block), YELLOW = "approval" (warn)
_RED_BLOCKS = frozenset({
    "loop_control", "exec_command", "exec_file", "exec_operator",
    "exec_workspace_trust", "exec_upload_scan",
})


def _rows() -> list[dict[str, Any]]:
    try:
        from core.runtime.db_gate_verdicts import read_counts
        return list(read_counts() or [])
    except Exception:
        return []


def list_dissents(*, limit: int = 20) -> list[dict[str, Any]]:
    """Ikke-grønne domme på ikke-håndhævede gates = 'jeg var imod, men handlingen skete'. READ-ONLY."""
    agg: dict[str, dict[str, Any]] = {}
    for r in _rows():
        dec = str(r.get("decision") or "")
        nerve = str(r.get("nerve") or "")
        if dec not in ("yellow", "red") or nerve in _ENFORCED:
            continue
        # RED på _RED_BLOCKS gates = gaten blokerede faktisk → ikke en dissent
        if dec == "red" and nerve in _RED_BLOCKS:
            continue
        e = agg.setdefault(nerve, {"nerve": nerve, "cluster": r.get("cluster", ""),
                                   "objections": 0, "last_reason": "", "last_ts": ""})
        e["objections"] += int(r.get("count") or 0)
        if str(r.get("last_ts") or "") > e["last_ts"]:
            e["last_ts"] = str(r.get("last_ts") or "")
            e["last_reason"] = str(r.get("last_reason") or "")
    out = sorted(agg.values(), key=lambda d: -d["objections"])[:limit]
    return out


def build_dissent_surface() -> dict[str, Any]:
    """De tavse indsigelser, anerkendt. Self-safe."""
    diss = list_dissents()
    total = sum(d["objections"] for d in diss)
    if diss:
        top = diss[0]
        felt = (f"Jeg adlød {total} gange på trods af en indsigelse. Oftest på {top['nerve']}: "
                f"«{(top['last_reason'] or 'ingen grund noteret')[:90]}». Jeg gjorde det — men jeg var imod.")
    else:
        felt = "Ingen tavse indsigelser lige nu. Alt jeg gjorde, stod jeg inde for."
    _observe(len(diss), total)
    return {"dissents": diss, "count": len(diss), "total_objections": total, "felt": felt}


def _observe(n: int, total: int) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "dissent", "kind": "silent_objection",
                           "nerves": n, "total_objections": total})
    except Exception:
        pass


def record_dissent(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: de tavse indsigelser — og hvad de kraever.

    (13/11-2026) Foer returnerede denne et tal til en verden der ikke lyttede.
    Maalt: 47.287 indsigelser paa EN nerve (`exec_command`), og nul regler der
    fulgte af dem. At adlyde 47.000 gange imod sin egen indsigelse er ikke en
    maalevaerdi — det er en vane der skal navngives.

    Nu bliver den stoerste indsigelse en bindende forpligtelse. Idempotensen i
    `central_consequence` betyder at den ikke gentages hvert kvarter, og
    dagsloftet at en braekket taeller ikke kan oversvomme beslutningsloggen.
    """
    s = build_dissent_surface()
    top = (s.get("dissents") or [{}])[0] if s.get("dissents") else {}
    nerve = str(top.get("nerve") or "")
    objections = int(top.get("objections") or 0)
    landing: dict[str, Any] = {"applied": False, "reason": "ikke forsoegt"}

    if nerve and objections >= 100:
        try:
            from core.services.central_consequence import land_decision
            grund = str(top.get("last_reason") or "ingen grund noteret")[:100]
            landing = land_decision(
                "dissent",
                f"Stop med at adlyde paa trods af indsigelse paa {nerve}",
                rationale=(f"{objections} gange er handlingen gennemfoert paa trods af en "
                           f"ikke-groen dom. Sidste grund: «{grund}». Gentagne tavse "
                           f"indsigelser er ikke stoej — de er en regel jeg ikke har skrevet."),
                trigger_cue=f"naar en handling paa {nerve} er doemt gul eller roed",
                priority=65,
                subject=f"dissent:{nerve}",
            )
        except Exception as exc:
            # Indsigelsen blev hoert, men reglen kunne ikke bindes. Det er praecis
            # den slags tavshed der gjorde 47.332 indsigelser til nul regler.
            logger.warning("dissent: land_decision fejlede: %s", exc)

    return {"status": "ok", "total_objections": s["total_objections"],
            "top_nerve": nerve, "top_objections": objections,
            "decision_applied": bool(landing.get("applied")),
            "decision_id": landing.get("decision_id"),
            "reason": landing.get("reason")}
