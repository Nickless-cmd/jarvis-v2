"""core/services/central_hypothesis_generator.py

Lag 3 (LivingNeuron v3 §11 Fase 2): den GOVERNED hypotese-generator — Centralens første ægte læring.

Danner FALSIFICERBARE hypoteser om tvær-temporale/tvær-modale korrelationer fra det målte substrat
(Fase 1) og router ALT gennem dødsmekanismen (§8, central_hypothesis_governance). Konsoliderer under
ÉN governed tabel (`central_hypotheses`) i stedet for at genopfinde de spredte organer (§6): kilde-
organer (meta_learning/dream/curiosity/causal) FODRER kandidater ind; denne tabel er det ENESTE
governede livscyklus-hjem. Ingen dual-truth.

⛔ OBSERVE-ONLY (rådets krav: byg IKKE Lag 4 endnu). Generatoren DANNER + SPORER hypoteser og opdaterer
confidence via evaluate() — men HANDLER aldrig på dem (ingen selv-mutation). Lag 4 (aktiv adaptation)
kræver shadow-first + Bjørn-godkendelse, som ikke er bygget.

TRIGGER v1 (grounded i Fase 1d): tilbagevendende MENINGSFULDE (Tier-1/2, ikke Tier-3-støj) kausal-kanter
mellem samme to event-familier → "familie X forudsiger familie Y"-hypotese. Divergens-trigger (2
subsystemer i modstrid) + GWT-convergens er v2 (rådets dybeste indsigt, noteret).

Alt read/observe, self-safe, kaster ALDRIG.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from core.services import central_hypothesis_governance as gov

# Trigger-parametre.
_EDGE_WINDOW = 2000          # seneste kanter der scannes
_MIN_RECURRENCE = 3          # familie-par skal optræde ≥ dette (crude multiple-comparisons-gulv)
_DEFAULT_TTL_S = 7 * 24 * 3600
_DEFAULT_SAMPLE_SIZE = 5
_INITIAL_CONFIDENCE = 0.3
_MEANINGFUL_SOURCES = ("inferred-kind", "inferred-id", "explicit")   # ikke Tier-3 temporal-støj


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_schema() -> None:
    """Idempotent — CREATE IF NOT EXISTS køres hver gang (billigt; tåler per-test-isolerede DB'er)."""
    try:
        from core.runtime.db import connect
        with connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS central_hypotheses (
                  hyp_id TEXT PRIMARY KEY,
                  source TEXT NOT NULL,
                  statement TEXT NOT NULL,
                  prediction TEXT NOT NULL,
                  null_hypothesis TEXT NOT NULL,
                  success_criterion TEXT NOT NULL,
                  sample_size INTEGER NOT NULL,
                  ttl_seconds INTEGER NOT NULL,
                  provenance_json TEXT NOT NULL,
                  confidence REAL NOT NULL,
                  status TEXT NOT NULL,
                  outcome TEXT,
                  grounded_samples INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL,
                  resolved_at TEXT,
                  notation_il TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_ch_status ON central_hypotheses(status);
                CREATE INDEX IF NOT EXISTS idx_ch_provfam ON central_hypotheses(source, status);
                CREATE TABLE IF NOT EXISTS central_hypothesis_samples (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  hyp_id TEXT NOT NULL,
                  supports INTEGER NOT NULL,
                  falsifies INTEGER NOT NULL,
                  source TEXT NOT NULL,
                  ground_ref TEXT,
                  triggered_by TEXT,
                  created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chs_hyp ON central_hypothesis_samples(hyp_id);
                """
            )
            # Migration: notation_il på eksisterende tabeller (interlanguage-notation, Fase 0).
            cols = [r[1] for r in c.execute("PRAGMA table_info(central_hypotheses)").fetchall()]
            if "notation_il" not in cols:
                c.execute("ALTER TABLE central_hypotheses ADD COLUMN notation_il TEXT")
            c.commit()
    except Exception:
        pass


def _notation_for(source: str, provenance: dict[str, Any]) -> str | None:
    """Rendér en hypotese til interlanguage-notation via lexicon-bindingen. None hvis leddene er
    ubundne (sproget kan ikke sige det endnu). Self-safe."""
    try:
        from core.services import central_lexicon
        fam = str(provenance.get("family") or "")
        if source == "causal_convergence" and "->" in fam:
            x, y = fam.split("->", 1)
            return central_lexicon.render_relation(x, y, relation="causal_convergence")
        if source == "causal_divergence" and ":" in fam:
            # "parent:good|bad" → parent ↔ ! (spænding om udfald)
            parent = fam.split(":", 1)[0]
            t = central_lexicon.to_term(parent)
            return f"{t} ↔ !udfald" if t else None
    except Exception:
        pass
    return None


def _stable_id(provenance: dict[str, Any], created_at: str) -> str:
    """Immutabelt server-tildelt id (ikke statement-afledt → ingen kontrol-arm-p-hacking)."""
    raw = json.dumps(provenance, sort_keys=True) + "|" + created_at
    return "clh-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# ── Registrering: governance-gated ───────────────────────────────────────────────────
def register_governed_hypothesis(candidate: dict[str, Any]) -> dict[str, Any]:
    """Registrér en kandidat SOM governed hypotese — men KUN hvis den er fuldt pre-registreret
    (§8 validate_preregistration). Tildeler stabilt server-id. Self-safe."""
    ensure_schema()
    created = _now()
    prov = candidate.get("provenance") or {}
    hyp = {
        "statement": candidate.get("statement"),
        "prediction": candidate.get("prediction"),
        "null_hypothesis": candidate.get("null_hypothesis"),
        "success_criterion": candidate.get("success_criterion"),
        "sample_size": int(candidate.get("sample_size") or _DEFAULT_SAMPLE_SIZE),
        "ttl_seconds": int(candidate.get("ttl_seconds") or _DEFAULT_TTL_S),
        "provenance": prov,
    }
    ok, missing = gov.validate_preregistration(hyp)
    if not ok:
        return {"status": "rejected", "missing": missing}
    hyp_id = _stable_id(prov, created)
    try:
        from core.runtime.db import connect
        with connect() as c:
            exists = c.execute("SELECT 1 FROM central_hypotheses WHERE hyp_id=?", (hyp_id,)).fetchone()
            if exists:
                return {"status": "duplicate", "hyp_id": hyp_id}
            src = str(candidate.get("source") or "causal_convergence")
            notation = _notation_for(src, prov)
            c.execute(
                "INSERT INTO central_hypotheses (hyp_id, source, statement, prediction, null_hypothesis, "
                "success_criterion, sample_size, ttl_seconds, provenance_json, confidence, status, "
                "outcome, grounded_samples, created_at, resolved_at, notation_il) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,'active',NULL,0,?,NULL,?)",
                (hyp_id, src, hyp["statement"],
                 hyp["prediction"], hyp["null_hypothesis"], hyp["success_criterion"],
                 hyp["sample_size"], hyp["ttl_seconds"], json.dumps(prov),
                 float(candidate.get("confidence") or _INITIAL_CONFIDENCE), created, notation),
            )
            c.commit()
        return {"status": "registered", "hyp_id": hyp_id}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _load(hyp_id: str) -> dict[str, Any] | None:
    try:
        from core.runtime.db import connect
        with connect() as c:
            row = c.execute("SELECT * FROM central_hypotheses WHERE hyp_id=?", (hyp_id,)).fetchone()
            if not row:
                return None
            h = dict(row)
            samples = c.execute(
                "SELECT supports, falsifies, source, ground_ref, triggered_by "
                "FROM central_hypothesis_samples WHERE hyp_id=?", (hyp_id,)).fetchall()
        h["_samples"] = [dict(s) for s in samples]
        return h
    except Exception:
        return None


def _to_evidence(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"supports": bool(s.get("supports")), "falsifies": bool(s.get("falsifies")),
             "source": s.get("source"), "ground_ref": s.get("ground_ref"),
             "triggered_by": s.get("triggered_by")} for s in samples]


def record_governed_sample(hyp_id: str, *, supports: bool, falsifies: bool = False,
                           source: str = "", ground_ref: str = "",
                           triggered_by: str = "", verifier=None) -> dict[str, Any]:
    """Registrér ét udfald-sample + re-evaluér hypotesen gennem hele dødsmekanismen (evaluate).
    Opdaterer confidence/status/outcome. OBSERVE-ONLY: handler aldrig på resultatet. Self-safe."""
    ensure_schema()
    h = _load(hyp_id)
    if not h:
        return {"status": "error", "error": f"unknown hyp_id {hyp_id}"}
    if h.get("status") != "active":
        return {"status": "noop", "reason": f"hypotese er {h.get('status')!r}"}
    try:
        from core.runtime.db import connect
        with connect() as c:
            c.execute(
                "INSERT INTO central_hypothesis_samples (hyp_id, supports, falsifies, source, "
                "ground_ref, triggered_by, created_at) VALUES (?,?,?,?,?,?,?)",
                (hyp_id, 1 if supports else 0, 1 if falsifies else 0, str(source),
                 str(ground_ref), str(triggered_by), _now()))
            c.commit()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    # Re-hent + evaluér gennem governance.
    h = _load(hyp_id) or h
    evidence = _to_evidence(h.get("_samples") or [])
    grounded_n = sum(1 for e in evidence
                     if gov.is_externally_grounded(e, verifier=verifier))
    hyp_for_eval = {
        "id": hyp_id, "statement": h["statement"], "prediction": h["prediction"],
        "null_hypothesis": h["null_hypothesis"], "success_criterion": h["success_criterion"],
        "sample_size": int(h["sample_size"]), "ttl_seconds": int(h["ttl_seconds"]),
        "provenance": json.loads(h.get("provenance_json") or "{}"),
        "confidence": float(h.get("confidence") or 0.0), "created_at": h["created_at"],
    }
    verdict = gov.evaluate(hyp_for_eval, confirming_evidence=evidence,
                           grounded_sample_count=grounded_n, verifier=verifier)

    # Persistér ny confidence + evt. resolution (dødsmekanismen EKSEKVERER).
    new_status, outcome, resolved_at = "active", None, None
    if verdict.quarantined:
        new_status = "quarantined"
    elif not verdict.alive:
        new_status, outcome, resolved_at = "dead", "falsified", _now()
    elif grounded_n >= int(h["sample_size"]):
        new_status, resolved_at = "resolved", _now()
        outcome = "supported" if verdict.confidence >= gov.MIN_ACT_CONFIDENCE else "contradicted"
    try:
        from core.runtime.db import connect
        with connect() as c:
            c.execute("UPDATE central_hypotheses SET confidence=?, status=?, outcome=?, "
                      "grounded_samples=?, resolved_at=? WHERE hyp_id=?",
                      (float(verdict.confidence), new_status, outcome, grounded_n, resolved_at, hyp_id))
            c.commit()
    except Exception:
        pass
    return {"status": "ok", "confidence": verdict.confidence, "hyp_status": new_status,
            "outcome": outcome, "acts": verdict.acts, "reason": verdict.reason}


# ── Trigger-detektion: tilbagevendende meningsfulde kausal-kanter ────────────────────
def detect_causal_convergence_candidates(*, window: int = _EDGE_WINDOW,
                                         min_recurrence: int = _MIN_RECURRENCE) -> list[dict[str, Any]]:
    """Find familie-par (X→Y) der optræder ≥ min_recurrence gange blandt de seneste MENINGSFULDE
    kausal-kanter (Tier-1/2/explicit, ikke Tier-3-støj — bygger på Fase 1d). Self-safe."""
    try:
        from core.runtime.db import connect
        placeholders = ",".join("?" for _ in _MEANINGFUL_SOURCES)
        with connect() as c:
            rows = c.execute(
                f"SELECT pe.kind AS pk, che.kind AS ck, ce.id AS eid "
                f"FROM causal_edges ce "
                f"JOIN events pe ON pe.id = ce.parent_event_id "
                f"JOIN events che ON che.id = ce.child_event_id "
                f"WHERE ce.source IN ({placeholders}) "
                f"ORDER BY ce.id DESC LIMIT ?",
                (*_MEANINGFUL_SOURCES, max(int(window), 1))).fetchall()
    except Exception:
        return []
    pairs: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        pf = str(r["pk"] or "").split(".", 1)[0]
        cf = str(r["ck"] or "").split(".", 1)[0]
        if not pf or not cf or pf == cf:
            continue
        key = (pf, cf)
        d = pairs.setdefault(key, {"count": 0, "cursor": 0})
        d["count"] += 1
        d["cursor"] = max(d["cursor"], int(r["eid"] or 0))
    out = []
    for (pf, cf), d in pairs.items():
        if d["count"] >= int(min_recurrence):
            out.append({"parent_family": pf, "child_family": cf,
                        "count": d["count"], "cursor": d["cursor"]})
    out.sort(key=lambda x: x["count"], reverse=True)
    return out


def formulate_correlation_hypothesis(cand: dict[str, Any]) -> dict[str, Any]:
    """Omsæt en detekteret korrelation til en EKSPLICIT, menneske-læsbar, pre-registreret hypotese
    (så cellen kan have URET synligt — rådets falsifikations-etik)."""
    x, y, n = cand["parent_family"], cand["child_family"], cand["count"]
    return {
        "source": "causal_convergence",
        "statement": f"Events i '{x}' forudsiger events i '{y}' (set {n}× i kausalgrafen)",
        "prediction": f"Efter en '{x}'-event følger en '{y}'-event inden for samme session/vindue "
                      f"oftere end baseline",
        "null_hypothesis": f"'{y}'-events er uafhængige af '{x}'-events (ingen forhøjet rate)",
        "success_criterion": f">= {_DEFAULT_SAMPLE_SIZE} jordede samples hvor '{y}' følger '{x}'",
        "sample_size": _DEFAULT_SAMPLE_SIZE,
        "ttl_seconds": _DEFAULT_TTL_S,
        "provenance": {"mechanism": "causal_edges", "family": f"{x}->{y}", "cursor_id": cand["cursor"]},
        "confidence": _INITIAL_CONFIDENCE,
    }


# ── Trigger v2: OUTCOME-DIVERGENS (rådets dybeste indsigt: konflikt, ikke konvergens) ─
# Samme årsag → MODSATTE udfald = en skjult faktor afgør. Det er dér refleksion/vækst opstår.
# Kuraterede modsat-udfald-par (gode ↔ dårlige) — grounded i eksisterende event-kinds.
_OPPOSING_OUTCOMES = (
    ("tool.completed", "tool.error"),
    ("behavioral_decision_review.kept", "behavioral_decision_review.broken"),
)


def detect_outcome_divergence_candidates(*, window: int = _EDGE_WINDOW,
                                         min_each: int = 2) -> list[dict[str, Any]]:
    """Find parent-familier der MENINGSFULDT fører til BEGGE sider af et modsat-udfald-par (≥ min_each
    hver). Samme årsag, modsatte udfald = divergens → en skjult indre faktor afgør. Self-safe."""
    try:
        from core.runtime.db import connect
        placeholders = ",".join("?" for _ in _MEANINGFUL_SOURCES)
        with connect() as c:
            rows = c.execute(
                f"SELECT pe.kind AS pk, che.kind AS ck, ce.id AS eid "
                f"FROM causal_edges ce "
                f"JOIN events pe ON pe.id = ce.parent_event_id "
                f"JOIN events che ON che.id = ce.child_event_id "
                f"WHERE ce.source IN ({placeholders}) "
                f"ORDER BY ce.id DESC LIMIT ?",
                (*_MEANINGFUL_SOURCES, max(int(window), 1))).fetchall()
    except Exception:
        return []
    # family → {child_kind: {count, cursor}}
    fam_children: dict[str, dict[str, dict[str, int]]] = {}
    for r in rows:
        pf = str(r["pk"] or "").split(".", 1)[0]
        ck = str(r["ck"] or "")
        if not pf or not ck:
            continue
        d = fam_children.setdefault(pf, {}).setdefault(ck, {"count": 0, "cursor": 0})
        d["count"] += 1
        d["cursor"] = max(d["cursor"], int(r["eid"] or 0))
    out = []
    for fam, children in fam_children.items():
        for good, bad in _OPPOSING_OUTCOMES:
            g = children.get(good)
            b = children.get(bad)
            if g and b and g["count"] >= min_each and b["count"] >= min_each:
                out.append({"parent_family": fam, "good": good, "bad": bad,
                            "good_count": g["count"], "bad_count": b["count"],
                            "cursor": max(g["cursor"], b["cursor"])})
    out.sort(key=lambda x: (x["good_count"] + x["bad_count"]), reverse=True)
    return out


def formulate_divergence_hypothesis(cand: dict[str, Any]) -> dict[str, Any]:
    """Divergens → hypotese om en SKJULT diskriminerende faktor. Rådet: 'konflikt mellem organer er
    kilden til refleksion' — denne hypotese peger direkte på at finde den faktor der afgør udfaldet."""
    fam, good, bad = cand["parent_family"], cand["good"], cand["bad"]
    gc, bc = cand["good_count"], cand["bad_count"]
    return {
        "source": "causal_divergence",
        "statement": f"'{fam}' fører nogle gange til '{good}' ({gc}×) og andre gange til '{bad}' ({bc}×) "
                     f"— en skjult indre faktor afgør udfaldet",
        "prediction": f"Der findes en målbar indre tilstand (somatik/affekt/kontekst) der adskiller "
                      f"'{fam}'→'{good}' fra '{fam}'→'{bad}'",
        "null_hypothesis": f"'{fam}'-udfaldet er uafhængigt af indre tilstand (ren tilfældighed)",
        "success_criterion": f">= {_DEFAULT_SAMPLE_SIZE} jordede samples der forbinder en indre "
                             f"tilstand med udfaldet",
        "sample_size": _DEFAULT_SAMPLE_SIZE,
        "ttl_seconds": _DEFAULT_TTL_S,
        "provenance": {"mechanism": "causal_divergence", "family": f"{fam}:{good}|{bad}",
                       "cursor_id": cand["cursor"]},
        "confidence": _INITIAL_CONFIDENCE,
    }


def detect_stance_divergence_candidates(*, min_count: int = 3) -> list[dict[str, Any]]:
    """Trigger v3: tvær-modal stance-divergens ('organer uenige i nuet'). Læser GENTAGNE tensions
    fra central_stance (to organer der holder modsatte holdninger samtidig, set ≥ min_count gange).
    Rådets dybeste: konflikt mellem organer er kilden til refleksion. Self-safe."""
    try:
        from core.services.central_stance import recurring_tensions
        return recurring_tensions(min_count=min_count)
    except Exception:
        return []


def formulate_stance_divergence_hypothesis(t: dict[str, Any]) -> dict[str, Any]:
    """Tvær-modal tension → hypotese om hvad uenigheden mellem organerne forudsiger/afgør."""
    key, desc, n = t["key"], t.get("desc", ""), t.get("count", 0)
    return {
        "source": "stance_divergence",
        "statement": f"To af dine organer er gentagne gange UENIGE: {desc or key} (set {n}×)",
        "prediction": f"Når denne uenighed ({key}) opstår, adskiller run-udfaldet sig målbart fra "
                      f"når organerne er enige",
        "null_hypothesis": f"Uenigheden ({key}) er uden betydning for udfaldet",
        "success_criterion": f">= {_DEFAULT_SAMPLE_SIZE} jordede samples der forbinder uenigheden "
                             f"med et udfald",
        "sample_size": _DEFAULT_SAMPLE_SIZE,
        "ttl_seconds": _DEFAULT_TTL_S,
        "provenance": {"mechanism": "stance_divergence", "family": key, "cursor_id": int(n)},
        "confidence": _INITIAL_CONFIDENCE,
    }


def _active_provenance_families() -> set[str]:
    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute("SELECT provenance_json FROM central_hypotheses "
                             "WHERE status='active'").fetchall()
        fams = set()
        for r in rows:
            try:
                fams.add(json.loads(r["provenance_json"]).get("family"))
            except Exception:
                pass
        return fams
    except Exception:
        return set()


def run_hypothesis_generation_tick(*, trigger: str = "cadence",
                                   last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: detektér KONVERGENS (korrelation) + DIVERGENS (konflikt) → formulér →
    governance-gated registrér. OBSERVE-ONLY (handler aldrig). Dedup mod aktive. Egress-fri. Self-safe."""
    ensure_schema()
    conv = [formulate_correlation_hypothesis(c) for c in detect_causal_convergence_candidates()]
    div = [formulate_divergence_hypothesis(c) for c in detect_outcome_divergence_candidates()]
    stance = [formulate_stance_divergence_hypothesis(t) for t in detect_stance_divergence_candidates()]
    candidates = conv + div + stance
    existing = _active_provenance_families()
    registered, rejected, dup, divergence = 0, 0, 0, 0
    for hyp in candidates:
        if hyp["provenance"]["family"] in existing:
            dup += 1
            continue
        res = register_governed_hypothesis(hyp)
        st = res.get("status")
        if st == "registered":
            registered += 1
            if hyp["source"] in ("causal_divergence", "stance_divergence"):
                divergence += 1
        elif st == "rejected":
            rejected += 1
        elif st == "duplicate":
            dup += 1
    # Egress-fri observe (kun tællere — hypotese-STATEMENTS er meta-niveau, men holdes owner-lokalt).
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "hypothesis_generation",
                       value=float(registered),
                       meta={"candidates": len(candidates), "registered": registered,
                             "divergence": divergence, "rejected": rejected, "duplicate": dup})
    except Exception:
        pass
    return {"status": "ok", "candidates": len(candidates), "registered": registered,
            "divergence": divergence, "convergence": len(conv), "rejected": rejected, "duplicate": dup}


def register_hypothesis_generator_producer() -> None:
    """Registrér Lag 3-generatoren som cadence-producer (~hvert 60 min, lav prioritet)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_hypothesis_generator",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=run_hypothesis_generation_tick,
        priority=7,
    ))


def list_active_hypotheses(*, limit: int = 10) -> list[dict[str, Any]]:
    ensure_schema()
    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT hyp_id, statement, confidence, grounded_samples, sample_size, created_at "
                "FROM central_hypotheses WHERE status='active' "
                "ORDER BY confidence DESC LIMIT ?", (max(int(limit), 1),)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def format_governed_hypotheses_for_awareness(*, limit: int = 3) -> str | None:
    """Gør Centralens SELV-GENEREREDE hypoteser synlige for Jarvis selv (awareness). Rådets visionær:
    'et system hvis emergens ingen kan SE, kan ingen stole på.' Kun observerende — Jarvis VED at
    Centralen har bemærket disse mønstre om ham selv; han HANDLER ikke tvunget på dem. Self-safe."""
    active = list_active_hypotheses(limit=limit)
    if not active:
        return None
    lines = ["Centralen har (fra runtime-mønstre, IKKE fra din model) dannet disse falsificerbare "
             "formodninger om dig selv — under observation, endnu ikke bekræftet:"]
    for h in active:
        conf = float(h.get("confidence") or 0.0)
        gs, ss = int(h.get("grounded_samples") or 0), int(h.get("sample_size") or 0)
        lines.append(f"  • {h.get('statement')} (tiltro {conf:.2f}, {gs}/{ss} jordede samples)")
    return "\n".join(lines)


def build_central_hypothesis_generator_surface() -> dict[str, object]:
    """Mission Control surface — read-only projektion af den governede hypotese-population."""
    ensure_schema()
    counts: dict[str, int] = {}
    try:
        from core.runtime.db import connect
        with connect() as c:
            for r in c.execute("SELECT status, COUNT(*) n FROM central_hypotheses GROUP BY status"):
                counts[str(r["status"])] = int(r["n"])
    except Exception:
        pass
    return {"active": True, "by_status": counts, "top_active": list_active_hypotheses(limit=5)}
