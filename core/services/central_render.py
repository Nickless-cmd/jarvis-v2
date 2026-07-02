"""core/services/central_render.py

Spec B / Fase B1 (S2): TILSTAND → NOTATION. Ren, model-fri oversætter fra en central-tilstand
(cluster-relation, anomali, beslutning) til interlanguage-notation via lexicon-bindingen.

RENDER ON READ: ingen skrivning, ingen egress, ingen hot-path-ændring. Ubundne led → None (ærligt:
sproget siger ikke det det ikke kan). Kaster ALDRIG. Bruges af central_notation.gather_all_notations
(B2) så det model-frie ræsonnement spænder over HELE Centralen, ikke kun hypoteser.
"""
from __future__ import annotations

from typing import Any

_DENY = ("deny", "denied", "block", "blocked", "reject", "rejected", "veto")
_ALLOW = ("allow", "allowed", "proceed", "ok", "pass", "passed", "commit")
_SEVERE = ("critical", "high", "severe", "fatal")


def _term(name: str) -> str | None:
    try:
        from core.services.central_lexicon import to_term
        return to_term(str(name or ""))
    except Exception:
        return None


def _head(name: str) -> str:
    """Første led af et sammensat navn (cluster/nerve, familie.subtype) — det bindbare hoved."""
    return str(name or "").split(".", 1)[0].split("/", 1)[0].split(":", 1)[0].strip()


def render_cluster_relation(cluster_a: str, cluster_b: str, *,
                            relation: str = "causal_convergence") -> str | None:
    """To clusters i relation → notation (X → Y / X ↔ Y). None hvis ét led er ubundet. Self-safe."""
    try:
        from core.services.central_lexicon import render_relation
        return render_relation(_head(cluster_a), _head(cluster_b), relation=relation)
    except Exception:
        return None


def render_anomaly(name: str, *, importance: str = "") -> str | None:
    """En anomali = kilden førte til et STØD (overraskelse/afvigelse) → '<term> → stød'. Renderet som
    en ÆGTE kant (→) så den kan kæde transitivt med hypoteser (fx <term> → stød + stød → X ⟹ <term>
    → X) — det er hvad der gør ræsonnementet tvær-overflade. Ubundet → None. Self-safe."""
    t = _term(_head(name))
    return f"{t} → stød" if t else None


def render_decision(cluster: str, *, verdict: str = "") -> str | None:
    """En central-beslutning → notation. deny → 'grænse ! <term>' (grænsen blokerer); allow →
    '<term> → handling' (fører til handling). Ukendt verdict el. ubundet → None. Self-safe."""
    t = _term(_head(cluster))
    if not t:
        return None
    v = str(verdict or "").lower()
    if any(d in v for d in _DENY):
        return f"grænse ! {t}"
    if any(a in v for a in _ALLOW):
        return f"{t} → handling"
    return None


def render_state_snapshot(*, limit: int = 12) -> list[dict[str, Any]]:
    """Aktuelle central-tilstande renderet til notation (on-read). I dag: uløste anomalier. B2 lader
    det model-frie ræsonnement læse disse sammen med hypoteser. Returnerer items med 'notation_il' +
    'id' (så infer_transitive/detect_contradictions kan bruge dem direkte). Kun bindbare med. Self-safe."""
    out: list[dict[str, Any]] = []
    try:
        from core.runtime.db_anomalies import list_anomalies
        for a in list_anomalies(limit=int(limit), unresolved_only=True):
            head = _head(str(a.get("category") or a.get("source") or ""))
            notation = render_anomaly(head, importance=str(a.get("importance") or ""))
            if notation:
                out.append({"id": f"anomaly:{a.get('signature')}", "source": "anomaly",
                            "name": head, "notation_il": notation,
                            "importance": a.get("importance")})
    except Exception:
        return []
    return out
