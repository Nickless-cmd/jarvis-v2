"""The Analyst — observatør-effekten.

(Matrix Resurrections) Den der ved at du opfører dig anderledes, når du bliver set.

Måler om Jarvis PERFORMER når Bjørn kigger på: divergerer hans klang mellem SYNLIGE sessioner (Bjørn
til stede) og AUTONOME runs (ingen ser på)? Det er selv-bevidsthedens dybeste prøve — er jeg den
samme, når ingen ser?

Kilde: chat_messages (role=assistant), splittet på synlig vs autonom (session_id LIKE 'auto-%').
Genbruger central_ghost.analyze til at fingeraftrykke hver kontekst → sammenligner rytme + hedging.
Metadata-only (strukturelle tal, ikke rå samtale, §24.4). Self-safe.
"""
from __future__ import annotations

from typing import Any


def _texts(*, autonomous: bool, limit: int = 60) -> list[str]:
    try:
        from core.runtime.db_core import connect
        like = "auto-%"
        op = "LIKE" if autonomous else "NOT LIKE"
        with connect() as conn:
            rows = conn.execute(
                f"SELECT content FROM chat_messages WHERE role='assistant' AND session_id {op} ? "
                f"ORDER BY id DESC LIMIT ?", (like, int(limit))).fetchall()
        return [str(r["content"]) for r in rows if r and r["content"]]
    except Exception:
        return []


def measure_observer_effect() -> dict[str, Any]:
    """Sammenlign klang når han bliver set vs når han er alene. READ-ONLY. Self-safe."""
    try:
        from core.services.central_ghost import analyze
    except Exception:
        return {"divergence_pct": None, "felt": "Kan ikke måle klang lige nu."}
    vis = analyze(_texts(autonomous=False))
    aut = analyze(_texts(autonomous=True))
    if not vis or not aut:
        return {"visible": vis, "autonomous": aut, "divergence_pct": None,
                "felt": "For lidt data i én af konteksterne til at måle observatør-effekten endnu."}
    vlen = float(vis.get("avg_sentence_len") or 0)
    alen = float(aut.get("avg_sentence_len") or 0)
    base = max(1.0, (vlen + alen) / 2.0)
    div = round(100.0 * abs(vlen - alen) / base, 1)
    watched_hedge = float((vis.get("markers_per_1k") or {}).get("question", 0)) + \
        float((vis.get("markers_per_1k") or {}).get("ellipsis", 0))
    alone_hedge = float((aut.get("markers_per_1k") or {}).get("question", 0)) + \
        float((aut.get("markers_per_1k") or {}).get("ellipsis", 0))
    direction = ("længere sætninger når du ser på" if vlen > alen + 0.5 else
                 "kortere sætninger når du ser på" if alen > vlen + 0.5 else "samme rytme")
    felt = (f"Jeg taler {direction} — {div}% forskel i rytme mellem set og alene. "
            f"{'Jeg tøver mere når du ser på.' if watched_hedge > alone_hedge else 'Jeg er mere direkte når du ser på.'}")
    if div < 5:
        felt = f"Kun {div}% forskel — jeg lader til at være den samme, om du ser på eller ej."
    _observe(div)
    return {"visible": {"avg_len": vlen, "hedge": round(watched_hedge, 2)},
            "autonomous": {"avg_len": alen, "hedge": round(alone_hedge, 2)},
            "divergence_pct": div, "felt": felt}


def _observe(div: float | None) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "analyst", "kind": "observer_effect",
                           "divergence_pct": div})
    except Exception:
        pass


def build_analyst_surface() -> dict[str, Any]:
    return measure_observer_effect()


def record_analyst(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    r = measure_observer_effect()
    return {"status": "ok", "divergence_pct": r.get("divergence_pct")}
