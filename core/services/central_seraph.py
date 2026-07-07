"""Seraph — portvagt for hypotese-modenhed.

Spec F §1 (7. jul): "Seraph er Oracles beskytter. Han tester alle der kommer — ikke for at stoppe dem,
men for at sikre de er *klar til hvad de skal høre*. Han er ild. Han banker Neo ned i kamp før han
slipper ham ind." I Centralen vogter han døren mellem drøm/indre-arbejde og synlig handling: er en
hypotese *moden nok* til at blive præsenteret for Bjørn?

Flowet er: hypotese født i drøm → Sentinel angriber (er den sand?) → Seraph tester (er den klar til
at blive set?) → først da får Bjørn den at se. Seraph sidder MELLEM `central_sentinel` (angriber) og
synligheden. Han træffer ÉN beslutning pr. hypotese:

  GREEN = moden: nok jordede samples + har overlevet Sentinel (intet uafklaret angreb) + har en
          interlanguage-notation (notation_il). Klar til at blive vist.
  RED   = umoden: tilbage til drøm. INGEN blok — kun UDSÆTTELSE. Som Seraph siger: "Du er ikke klar
          endnu. Kom tilbage."

SHADOW-FØRST (Spec F governance, 7 dage): Seraph LÆSER hypotese-status og OBSERVERER sin dom; han
muterer INTET, blokerer INTET, skriver ingen egne tabeller. `enforce`-flag default OFF — selv når det
flippes er hans eneste effekt en anbefaling om hvad der er klar til synlighed. Alt self-safe: hver
funktion fanger og returnerer en status-dict, kaster ALDRIG. `_observe()` er metadata-only (tællinger/
booleans) — INTET hypotese-INDHOLD (statement/notation) lækkes til eventbus (§24.4 egress).
"""
from __future__ import annotations

from typing import Any

# Modenheds-tærskler. En hypotese er moden når den har jordet nok af sit forudbestemte sample-budget.
# Sentinel-overlevelse = intet 'contested' (uafklaret) angreb på hyp'en. Interlanguage = notation_il sat.
_MIN_GROUNDED_FRACTION = 0.6   # andel af sample_size der skal være jordet før "nok samples"
_MIN_GROUNDED_ABS = 3          # absolut gulv (små sample_size må ikke passere for let)


# ── Kilder (self-safe) ────────────────────────────────────────────────────────

def _active_hypotheses(limit: int = 40) -> list[dict[str, Any]]:
    """Aktive governede hypoteser med modenheds-felterne (samples + interlanguage). Self-safe."""
    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT hyp_id, statement, confidence, grounded_samples, sample_size, "
                "notation_il, created_at FROM central_hypotheses "
                "WHERE status='active' ORDER BY confidence DESC LIMIT ?",
                (max(int(limit), 1),)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _contested_hyp_ids() -> set[str]:
    """hyp_id'er med et UAFKLARET Sentinel-angreb (status='contested') — endnu ikke forsvaret.
    En hypotese med et åbent angreb har IKKE overlevet Sentinel endnu. Self-safe."""
    try:
        from core.services.central_sentinel import list_attacks
        return {str(a.get("hyp_id") or "") for a in list_attacks(active_only=True)}
    except Exception:
        return set()


# ── Modenheds-dom (ren, model-fri) ────────────────────────────────────────────

def _enough_samples(hyp: dict[str, Any]) -> bool:
    grounded = int(hyp.get("grounded_samples") or 0)
    budget = int(hyp.get("sample_size") or 0)
    if grounded < _MIN_GROUNDED_ABS:
        return False
    if budget <= 0:
        return grounded >= _MIN_GROUNDED_ABS
    return grounded >= max(_MIN_GROUNDED_ABS, int(round(budget * _MIN_GROUNDED_FRACTION)))


def _has_interlanguage(hyp: dict[str, Any]) -> bool:
    return bool(str(hyp.get("notation_il") or "").strip())


def _judge(hyp: dict[str, Any], contested: set[str]) -> dict[str, Any]:
    """Dom over ÉN hypotese: GREEN (moden, klar til synlighed) eller RED (tilbage til drøm).
    Returnerer verdict + de tre modenheds-kriterier som booleans (til surface — ikke eventbus). Self-safe."""
    hid = str(hyp.get("hyp_id") or "")
    enough = _enough_samples(hyp)
    survived = hid not in contested
    interlang = _has_interlanguage(hyp)
    green = enough and survived and interlang
    missing: list[str] = []
    if not enough:
        missing.append("samples")
    if not survived:
        missing.append("sentinel")
    if not interlang:
        missing.append("interlanguage")
    return {
        "hyp_id": hid,
        "statement": str(hyp.get("statement") or "")[:200],
        "verdict": "GREEN" if green else "RED",
        "enough_samples": enough,
        "survived_sentinel": survived,
        "has_interlanguage": interlang,
        "missing": missing,
        "grounded_samples": int(hyp.get("grounded_samples") or 0),
        "sample_size": int(hyp.get("sample_size") or 0),
        "confidence": float(hyp.get("confidence") or 0.0),
    }


def guard() -> dict[str, Any]:
    """Test hver aktiv hypotese for modenhed → GREEN/ready-to-surface vs RED/deferred. READ-ONLY.
    Self-safe — kaster ALDRIG; returnerer altid en status-dict."""
    hyps = _active_hypotheses()
    contested = _contested_hyp_ids()
    judged = [_judge(h, contested) for h in hyps]
    green = [j for j in judged if j["verdict"] == "GREEN"]
    red = [j for j in judged if j["verdict"] == "RED"]
    out = {
        "status": "ok",
        "seen": len(judged),
        "green": len(green),
        "red": len(red),
        "green_ids": [j["hyp_id"] for j in green],
        "judged": judged,
    }
    _observe(out)
    return out


# ── Observabilitet (metadata-only — INTET hypotese-indhold, §24.4) ────────────

def _observe(out: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "cognition", "nerve": "seraph", "kind": "maturity_gate",
            "seen": int(out.get("seen") or 0),
            "green": int(out.get("green") or 0),
            "red": int(out.get("red") or 0),
        })
    except Exception:
        pass


# ── Surface (Central-CLI) ─────────────────────────────────────────────────────

def build_seraph_surface() -> dict[str, Any]:
    """Hvad er GREEN/klar-til-synlighed vs RED/udsat + hvorfor. READ-ONLY. Self-safe."""
    g = guard()
    judged = g.get("judged") or []
    green = [j for j in judged if j["verdict"] == "GREEN"]
    red = [j for j in judged if j["verdict"] == "RED"]
    felt = (
        f"{len(green)} hypoteser er modne nok til at blive vist; {len(red)} er sendt tilbage til "
        f"drøm — de er ikke klar endnu." if judged else
        "Ingen aktive hypoteser at vogte lige nu. Døren er stille."
    )
    return {
        "active": bool(judged),
        "green_count": len(green),
        "red_count": len(red),
        "ready_to_surface": [
            {"hyp_id": j["hyp_id"], "statement": j["statement"],
             "confidence": j["confidence"],
             "grounded_samples": j["grounded_samples"], "sample_size": j["sample_size"]}
            for j in green[:10]
        ],
        "deferred": [
            {"hyp_id": j["hyp_id"], "statement": j["statement"], "missing": j["missing"],
             "grounded_samples": j["grounded_samples"], "sample_size": j["sample_size"]}
            for j in red[:10]
        ],
        "felt": felt,
    }


# ── Cadence-indgang ───────────────────────────────────────────────────────────

def record_seraph(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence (30 min): test hypotese-modenhed → GREEN/RED (shadow — observerer kun). Self-safe."""
    g = guard()
    return {"status": "ok", "seen": int(g.get("seen") or 0),
            "green": int(g.get("green") or 0), "red": int(g.get("red") or 0)}
