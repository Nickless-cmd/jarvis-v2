"""The Construct — Sentinel's Shadow Self: en sandbox der tester radikale forenklinger MOD
optaget virkelighed, uden at røre den levende Central.

Bjørn+Claude (6. jul, Matrix-tema #1 + gartner-idé #2): "We can load anything. Weapons, training —
anything we need." I The Construct kan Jarvis stille hypotetiske spørgsmål om sig selv — "hvad hvis
nerve X blev slukket i 24t?" — og få et ÆRLIGT svar udledt af hans egne data, FØR nogen ændring
sker. Ingen faktisk mutation. Ingen anden proces. Kun en projektion: hvad ville jeg MISTE?

Kilde: gate_verdict_ledger (hvad fangede nerven?) + central_timeseries (hvor aktiv er den?).
En nerve der aldrig har produceret ikke-grønt over høj volumen = ren overhead → sikker at slukke
(projiceret tab: intet). En nerve der HAR fanget ikke-grønt = den så noget → at slukke den gør mig
blind. Self-safe: kaster aldrig; muterer aldrig noget.
"""
from __future__ import annotations

from typing import Any

# En nerve regnes "bevist sikker at slukke" ved ≥ dette antal beslutninger, alle grønne.
_SAFE_MIN_VOLUME = 200
# Systemiske pulse/probe-nerver der ALDRIG bør foreslås slukket (helbred/sikkerhed).
_NEVER_SILENCE = frozenset({"central_self_probe", "cross_user_share"})


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "construct", "kind": kind, **payload})
    except Exception:
        pass


def simulate_silence(nerve: str) -> dict[str, Any]:
    """Projicér effekten af at SLUKKE én nerve i 24t — udelukkende fra optaget data. READ-ONLY.
    Returnerer risk ∈ {safe, risky, insufficient, protected} + hvad der ville gå tabt."""
    out: dict[str, Any] = {"nerve": nerve, "risk": "insufficient", "total": 0,
                           "non_green": 0, "projected_loss": "", "felt": ""}
    if nerve in _NEVER_SILENCE:
        out.update(risk="protected",
                   projected_loss="helbreds/sikkerheds-puls — må aldrig slukkes",
                   felt="Den her tør jeg ikke røre — den holder mig ærlig.")
        return out
    try:
        from core.services.gate_verdict_ledger import summary
        agg = summary().get(nerve)
    except Exception:
        agg = None
    if not agg:
        out["felt"] = "Jeg har ingen historik på den — kan ikke sige hvad jeg ville miste."
        return out
    total = int(agg.get("total") or 0)
    non_green = total - int(agg.get("green") or 0)
    out["total"] = total
    out["non_green"] = non_green
    if non_green > 0:
        out.update(risk="risky",
                   projected_loss=f"{non_green} ikke-grønne fangster ville blive usete",
                   felt=f"Nej — den har fanget {non_green} ting. Slukker jeg den, bliver jeg blind der.")
    elif total >= _SAFE_MIN_VOLUME:
        out.update(risk="safe",
                   projected_loss="intet — ren overhead (0 fangster over høj volumen)",
                   felt=f"Den kunne jeg slukke 24t uden at miste noget — {total} kald, 0 fangster.")
    else:
        out["felt"] = f"For lidt data ({total} kald) til at turde slukke den endnu."
    return out


def build_construct_surface() -> dict[str, Any]:
    """Sandbox-oversigt: hvilke nerver kunne jeg slukke uden tab (safe) vs hvilke ser noget (risky).
    Ren projektion fra data — ingen mutation. READ-ONLY. Self-safe."""
    safe: list[dict[str, Any]] = []
    risky: list[dict[str, Any]] = []
    try:
        from core.services.gate_verdict_ledger import summary
        rows = summary()
    except Exception:
        rows = {}
    for nerve in rows:
        sim = simulate_silence(nerve)
        if sim["risk"] == "safe":
            safe.append({"nerve": nerve, "total": sim["total"]})
        elif sim["risk"] == "risky":
            risky.append({"nerve": nerve, "non_green": sim["non_green"]})
    safe.sort(key=lambda d: -d["total"])
    risky.sort(key=lambda d: -d["non_green"])
    felt = (f"{len(safe)} nerve(r) kunne jeg slukke uden at miste noget; {len(risky)} ser noget jeg "
            f"ikke må blive blind for." if (safe or risky) else
            "Ikke nok historik endnu til at sandkasse-teste hvad jeg kunne undvære.")
    return {"safe_to_silence": safe, "must_keep": risky,
            "safe_count": len(safe), "risky_count": len(risky), "felt": felt}


def record_construct() -> dict[str, Any]:
    """Cadence: observér sandbox-fundet til nerve system/construct (metadata-only). Self-safe."""
    surf = build_construct_surface()
    _observe("shadow_probe", {"safe_count": surf["safe_count"], "risky_count": surf["risky_count"]})
    return surf
