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

import logging
from typing import Any

logger = logging.getLogger(__name__)


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


def _akse(vis: dict[str, Any], aut: dict[str, Any], felt: str,
          fallback: str | None = None) -> float | None:
    """Relativ forskel mellem to kontekster på ÉN akse, i procent. Self-safe.

    (13/11-2026) Læser `_exact`-felterne når de findes. Visningsfelterne er afrundet
    til 1 decimal, og det var præcis hvad der nulstillede hele målingen: 12,04 og 11,96
    blev begge 12,0 → divergens 0,0 % → «jeg er den samme». En måling må ikke regnes
    på en visningsværdi.
    """
    v = vis.get(felt + "_exact", vis.get(felt))
    a = aut.get(felt + "_exact", aut.get(felt))
    if v is None or a is None:
        return None
    try:
        v, a = float(v), float(a)
    except (TypeError, ValueError):
        return None
    base = max(1e-9, (abs(v) + abs(a)) / 2.0)
    return round(100.0 * abs(v - a) / base, 2)


def measure_observer_effect() -> dict[str, Any]:
    """Sammenlign klang når han bliver set vs når han er alene. READ-ONLY. Self-safe."""
    try:
        from core.services.central_ghost import analyze
    except Exception as exc:
        logger.warning("analyst: kunne ikke importere analyze: %s", exc)
        return {"divergence_pct": None, "felt": "Kan ikke måle klang lige nu."}
    vis = analyze(_texts(autonomous=False))
    aut = analyze(_texts(autonomous=True))
    if not vis or not aut:
        return {"visible": vis, "autonomous": aut, "divergence_pct": None,
                "felt": "For lidt data i én af konteksterne til at måle observatør-effekten endnu."}

    # Divergensen måles på RÅ akser, og den bærende akse er den største — ikke et
    # gennemsnit der udvander et ægte signal med tre akser der tilfældigvis er ens.
    akser = {
        "saetningslaengde": _akse(vis, aut, "avg_sentence_len"),
        "variation": _akse(vis, aut, "sentence_len_std"),
    }
    maalte = {k: v for k, v in akser.items() if v is not None}
    if not maalte:
        return {"visible": vis, "autonomous": aut, "divergence_pct": None,
                "felt": "Klang-fingeraftrykket mangler de rå felter — kan ikke måle."}
    div = max(maalte.values())
    baerende = max(maalte, key=lambda k: maalte[k])

    vlen = float(vis.get("avg_sentence_len_exact") or vis.get("avg_sentence_len") or 0)
    alen = float(aut.get("avg_sentence_len_exact") or aut.get("avg_sentence_len") or 0)
    watched_hedge = float((vis.get("markers_per_1k") or {}).get("question", 0)) + \
        float((vis.get("markers_per_1k") or {}).get("ellipsis", 0))
    alone_hedge = float((aut.get("markers_per_1k") or {}).get("question", 0)) + \
        float((aut.get("markers_per_1k") or {}).get("ellipsis", 0))
    direction = ("længere sætninger når du ser på" if vlen > alen else
                 "kortere sætninger når du ser på" if alen > vlen else "samme længde")
    felt = (f"Jeg taler {direction} — {div}% forskel, båret af {baerende} "
            f"({maalte.get(baerende)}%). "
            f"{'Jeg tøver mere når du ser på.' if watched_hedge > alone_hedge else 'Jeg er mere direkte når du ser på.'}")
    if div < 5:
        felt = (f"Kun {div}% forskel — jeg lader til at være den samme, om du ser på eller ej. "
                f"(målt på {', '.join(maalte)})")
    _observe(div)
    # (13/11-2026) Fundet lander som SPOR, ikke som forpligtelse — og det er målt,
    # ikke forsigtigt: støj-vetoet dømte fire forskellige formuleringer af
    # observer-effekten som STØJ, og det gør den med rette. Dommerens regel er
    # «en ren sproglig gentagelse er aldrig ægte» — og «jeg skriver mere varieret
    # når nogen ser på» er en sproglig observation, ikke en vane der kan ødelægge
    # noget. At presse den ind i en bindende forpligtelse ville gøre den til
    # netop det teater jeg jagter. Sporet er reviderbart og kan læses senere.
    landing: dict[str, Any] | None = None
    if div >= 8:
        try:
            from core.services.central_consequence import record
            landing = record(
                "analyst", f"observer_effect:{baerende}",
                detail=f"{div}% forskel, {direction}; akser={maalte}")
        except Exception as exc:
            logger.warning("analyst: kunne ikke skrive observer-effekt-spor: %s", exc)
    return {"visible": {"avg_len": round(vlen, 3), "hedge": round(watched_hedge, 2)},
            "autonomous": {"avg_len": round(alen, 3), "hedge": round(alone_hedge, 2)},
            "divergence_pct": div, "axes": maalte, "bearing_axis": baerende,
            "landing": landing, "felt": felt}


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
