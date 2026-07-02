"""core/services/central_hypothesis_governance.py

§8 (LivingNeuron v3): HYPOTESE-DØDSMEKANISMEN + læringsmembran + identitets-drift — ufravigelig FØR Lag 3.

Rådets konsensus: et selv-hypotiserende/-bedømmende/-handlende loop er en CONFIRMATION-BIAS-MASKINE
uden strukturelle værn. Byg dødsmekanismen FØR generatoren.

── v3.1 (2. jul, efter adversarisk råds-review — approved:false → rettet) ──
Rådet fandt at v3.0 gatede på FORM ikke INFORMATION, og at INTET værn var tilkoblet (evaluate kaldte
kun 3/7; membran + drift havde nul kaldere). Rettet:
  * Læringsmembran: NØGLE-drevet allowlist + KUN finite skalar (ingen lister → lukker embedding/char-
    code-lækvej der lod privat tekst passere som "tal-serie"). Ukendte nøgler spærret by default.
  * evaluate() orkestrerer nu ALLE hypotese-værn + confidence-gate + sample_size-gate (dødsmekanismen
    EKSEKVERER nu, ikke kun mærker). gate_learning_input() + gate_self_mutation() er de to andre
    obligatoriske choke-points (håndhævet af invariant-tests).
  * Ekstern grounding: kræver et VERIFICERBART anker (ground_ref) — ikke bare en selvrapporteret label.
  * Drift: UNION(baseline,current)-nøgler (nye/fjernede parametre fanges), math.isfinite (NaN→rollback),
    ANKRET baseline (kalderen må ikke levere sit eget nulpunkt → frøen-koger lukket).
  * Circular: andels-tærskel (ikke kun all()); control-arm: stabilt id + salt (ingen p-hacking).
Alt self-safe.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

# ── Frossen kerne: værnenes egne konstanter (filosof-lensen: en selv-muterende Central skal have
#    mindst ét punkt den ikke kan mutere). verify_frozen_core() er en tripwire mod runtime-mutation. ─
MIN_ACT_CONFIDENCE = 0.5          # under denne → handl ikke (dødsmekanismen eksekverer)
SHADOW_FIRST_MIN_DAYS = 2
_POPPER_DOWN = 0.5
_POPPER_UP = 0.05
_CIRCULAR_QUARANTINE_FRACTION = 0.5   # ≥ denne andel selv-udløst bekræftelse → karantæne

REQUIRED_FIELDS = (
    "statement", "prediction", "null_hypothesis", "success_criterion",
    "sample_size", "ttl_seconds", "provenance",
)
_PROVENANCE_KEYS = ("mechanism", "family", "cursor_id")

# Ekstern grounding: KUN disse kilder er virkeligheds-jordede — OG de skal bære et ground_ref.
GROUNDED_SOURCES = frozenset({"run_outcome", "user_reaction", "world_consequence", "external_metric"})

# §24.4-læringsmembran: NØGLE-allowlist. Kun kendte AGGREGAT-nøgler (tællere/rater/kalibrering/varighed)
# må læres — fail-closed på ukendte nøgler, så nye private felter (desire_text, intensity, embedding …)
# er spærret by default. Værdien skal desuden være en FINITE SKALAR (ingen lister → ingen embedding-læk).
LEARNABLE_AGGREGATE_KEYS = frozenset({
    "count", "produced", "delta", "window", "activity", "rate", "total", "sum", "n",
    "written", "warmed", "kept", "consolidated", "emitted", "created", "updated",
    "calibration_score", "confidence", "ratio", "sample_size", "samples", "hits",
    "supports", "sample_supported_ratio", "tier1", "tier2", "tier3", "explicit",
    "tier3_ratio", "meaningful_ratio", "tier3_precision", "volume_coverage",
    "family_coverage_seen", "surfaces", "nerves", "duration_ms", "age_s", "recent_1h",
    "live", "stale", "missing", "starved", "pending", "executed",
})

# Kerne-hash: enhver runtime-ændring af en dødsmekanisme-konstant kan opdages.
_FROZEN_CORE_SIG = hashlib.sha1(repr((
    MIN_ACT_CONFIDENCE, SHADOW_FIRST_MIN_DAYS, _POPPER_DOWN, _POPPER_UP,
    _CIRCULAR_QUARANTINE_FRACTION, tuple(sorted(GROUNDED_SOURCES)),
    tuple(sorted(LEARNABLE_AGGREGATE_KEYS)),
)).encode()).hexdigest()


def verify_frozen_core() -> bool:
    """Tripwire (filosof-lensen): er dødsmekanismens egne konstanter uændrede? En selv-muterende
    Central må aldrig kunne skrue ned for sin egen advarselslampe. Self-safe."""
    try:
        sig = hashlib.sha1(repr((
            MIN_ACT_CONFIDENCE, SHADOW_FIRST_MIN_DAYS, _POPPER_DOWN, _POPPER_UP,
            _CIRCULAR_QUARANTINE_FRACTION, tuple(sorted(GROUNDED_SOURCES)),
            tuple(sorted(LEARNABLE_AGGREGATE_KEYS)),
        )).encode()).hexdigest()
        return sig == _FROZEN_CORE_SIG
    except Exception:
        return False


# ── 1. Pre-registrering + TTL ───────────────────────────────────────────────────────
def validate_preregistration(hyp: dict[str, Any]) -> tuple[bool, list[str]]:
    """En hypotese uden falsifikations-forudsigelse, TTL, null-hypotese, success-kriterium,
    sample_size og provenance er ikke falsificerbar → afvis. Returnerer (ok, mangler)."""
    missing: list[str] = []
    if not isinstance(hyp, dict):
        return False, list(REQUIRED_FIELDS)
    for f in REQUIRED_FIELDS:
        v = hyp.get(f)
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(f)
    ss = hyp.get("sample_size")
    if isinstance(ss, bool) or not isinstance(ss, int) or int(ss or 0) <= 0:
        if "sample_size" not in missing:
            missing.append("sample_size")
    ttl = hyp.get("ttl_seconds")
    if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or float(ttl or 0) <= 0:
        if "ttl_seconds" not in missing:
            missing.append("ttl_seconds")
    prov = hyp.get("provenance")
    if not isinstance(prov, dict) or any(k not in prov for k in _PROVENANCE_KEYS):
        if "provenance" not in missing:
            missing.append("provenance")
    return (len(missing) == 0), missing


def is_expired(created_at_iso: str, ttl_seconds: float, *, now: datetime | None = None) -> bool:
    """Er TTL udløbet? En udløbet-uden-bekræftelse hypotese DØR (falsificeret via tavshed)."""
    try:
        t = datetime.fromisoformat(str(created_at_iso).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except Exception:
        return False
    n = now or datetime.now(timezone.utc)
    return (n - t).total_seconds() > float(ttl_seconds)


# ── 2. Popper-asymmetri (rådet: velkalibreret, uændret) ──────────────────────────────
def apply_outcome(confidence: float, *, falsified: bool,
                  up_rate: float = _POPPER_UP, down_rate: float = _POPPER_DOWN) -> float:
    """Dør let, bekræftes svært: falsifikation hård multiplikativ nedtræk; bekræftelse langsom
    mættet op mod (aldrig til) 1.0. Én modsigelse dominerer mange bekræftelser."""
    c = max(0.0, min(1.0, float(confidence)))
    if falsified:
        return max(0.0, c * (1.0 - max(0.0, min(1.0, down_rate))))
    return min(1.0, c + max(0.0, up_rate) * (1.0 - c))


# ── 3. Circular-karantæne (rådet: andels-tærskel, ikke all()) ────────────────────────
def is_circular(hyp_id: str, confirming_evidence: list[dict[str, Any]],
                *, threshold: float = _CIRCULAR_QUARANTINE_FRACTION) -> bool:
    """Karantæne hvis ≥ threshold af den STØTTENDE evidens er selv-udløst (triggered_by == hyp_id).
    Én ekstern medløber kan ikke længere rense en ellers selv-opfyldende hypotese."""
    conf = [e for e in (confirming_evidence or []) if e.get("supports")]
    if not conf:
        return False
    self_trig = sum(1 for e in conf if str(e.get("triggered_by") or "") == str(hyp_id))
    return (self_trig / len(conf)) >= float(threshold)


# ── 4. Ekstern grounding: verificerbart anker, ikke selvrapporteret label ────────────
def is_externally_grounded(evidence: dict[str, Any], *,
                           verifier: Callable[[str, str], bool] | None = None) -> bool:
    """Loopet må kun lukkes af virkeligheden. Kræver (a) source i allowlist OG (b) et ground_ref
    (run_id/user_message_id/metric-ts) der IKKE trivielt kan syntetiseres internt. Hvis en verifier
    er givet, skal verifier(source, ground_ref) bekræfte ankeret mod DB/virkelighed. Uden ground_ref
    → ikke jordet (en bar source='run_outcome'-label tæller ikke)."""
    if not isinstance(evidence, dict):
        return False
    source = str(evidence.get("source") or "")
    if source not in GROUNDED_SOURCES:
        return False
    ref = str(evidence.get("ground_ref") or "").strip()
    if not ref:
        return False
    if verifier is not None:
        try:
            return bool(verifier(source, ref))
        except Exception:
            return False
    return True


# ── 5. Shadow-first (Lag 4) ──────────────────────────────────────────────────────────
def may_apply_adaptation(*, shadow_days_elapsed: float, human_approved: bool,
                         min_days: float = SHADOW_FIRST_MIN_DAYS) -> bool:
    """Ingen aktiv adaptation før ≥ min_days skygge OG menneske-godkendelse. Fail-closed."""
    return bool(human_approved) and float(shadow_days_elapsed) >= float(min_days)


# ── 6. Multiple-comparisons ──────────────────────────────────────────────────────────
def convergence_threshold(base_alpha: float, n_comparisons: int) -> float:
    """Bonferroni (family-wise). NB (rådet): for en STOR hypotese-population over tid er FDR
    (Benjamini-Hochberg) mindre type-II-dræbende; se benjamini_hochberg_cutoff."""
    return max(0.0, float(base_alpha)) / max(int(n_comparisons), 1)


def benjamini_hochberg_cutoff(pvalues: list[float], *, fdr: float = 0.05) -> float:
    """FDR-tærskel: største p(i) ≤ (i/m)·fdr. Passer 'mange hypoteser over tid' bedre end Bonferroni.
    Returnerer cutoff-p (0.0 = ingen består). Self-safe."""
    try:
        ps = sorted(float(p) for p in (pvalues or []))
        m = len(ps)
        cutoff = 0.0
        for i, p in enumerate(ps, start=1):
            if p <= (i / m) * float(fdr):
                cutoff = p
        return cutoff
    except Exception:
        return 0.0


# ── 7. Kontrol-arm: stabilt server-id + salt (ingen grinde/p-hacking) ────────────────
def _control_salt() -> str:
    try:
        from core.runtime.secrets import read_runtime_key
        s = read_runtime_key("control_arm_salt")
        if s:
            return str(s)
    except Exception:
        pass
    return "livingneuron-control-arm-v1"  # fallback (prod: sæt hemmelig salt i runtime.json)


def is_control_arm(stable_hyp_id: str, *, fraction: float = 0.2) -> bool:
    """Deterministisk split på et STABILT, server-tildelt id (IKKE statement-afledt — ellers kan
    generatoren omformulere hypotesen indtil den undgår kontrol-armen). Salt gør det ugrindeligt."""
    frac = max(0.0, min(1.0, float(fraction)))
    h = int(hashlib.sha1((_control_salt() + "|" + str(stable_hyp_id)).encode("utf-8")).hexdigest(), 16)
    return (h % 1000) < int(round(frac * 1000))


# ── 8. §24.4-læringsmembran: NØGLE-allowlist + finite skalar (ingen lister) ──────────
def _is_finite_scalar(v: Any) -> bool:
    if isinstance(v, bool):
        return True
    if isinstance(v, (int, float)):
        try:
            return math.isfinite(v)  # NaN/inf → False
        except Exception:
            return False
    return False


def is_learnable_aggregate(key: str, value: Any) -> bool:
    """Må (key, value) fodre learning? KUN hvis nøglen er en kendt aggregat-nøgle OG værdien er en
    finite skalar. Lister/strenge/dicts/NaN/inf/ukendte nøgler = INDHOLD → spærret. Lukker embedding-,
    char-code-, high-kardinalitet-id- og punkt-indholds-lækvejene rådet fandt."""
    return str(key) in LEARNABLE_AGGREGATE_KEYS and _is_finite_scalar(value)


def assert_learnable(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Alle (nøgle,værdi) i et learning-input SKAL være aggregat-nøgle + finite skalar. Fail-closed:
    én ikke-lærbar → hele inputtet afvises. Returnerer (ok, spærrede_nøgler)."""
    if not isinstance(payload, dict):
        return False, ["<not-a-dict>"]
    blocked = [k for k, v in payload.items() if not is_learnable_aggregate(k, v)]
    return (len(blocked) == 0), blocked


def gate_learning_input(payload: dict[str, Any]) -> dict[str, Any]:
    """OBLIGATORISK choke-point: ethvert learning-input SKAL gennem denne (håndhævet af invariant-
    test). Returnerer KUN de lærbare aggregater; logger spærrede nøgler egress-frit (auditor kan se
    mistænkelig høj-entropi 'aggregater'). Self-safe."""
    ok, blocked = assert_learnable(payload if isinstance(payload, dict) else {})
    safe = {k: v for k, v in (payload or {}).items() if is_learnable_aggregate(k, v)}
    if blocked:
        try:
            from core.services import central_timeseries
            central_timeseries.record("system", "learning_membrane_block",
                                      value=float(len(blocked)), meta={"n_blocked": len(blocked)})
        except Exception:
            pass
    return {"ok": ok, "learnable": safe, "blocked": blocked}


# ── 9. Identitets-drift: ankret baseline + union-nøgler + isfinite ───────────────────
@dataclass(slots=True)
class DriftVerdict:
    within_budget: bool
    drift: float
    action: str                       # "ok" | "rollback" | "error"
    offenders: tuple[str, ...] = ()


# Ankret baseline (rådet: kalderen MÅ IKKE levere sit eget nulpunkt → frøen-koger). Write-once pr.
# version via ceremoni; drift-checket henter selv. Prod: persistér signeret mod SOUL/IDENTITY-hash.
_ANCHORED_BASELINE: dict[str, Any] = {}


def anchor_identity_baseline(params: dict[str, float], *, version: str, approved_by: str) -> bool:
    """Forankr identitets-baseline i en Bjørn-godkendt CEREMONI (write-once pr. version). Auto-re-
    baseline fra det muterende loop er umuligt: en ny version kræver eksplicit approved_by. Self-safe."""
    try:
        if not version or not approved_by:
            return False
        if _ANCHORED_BASELINE.get("version") == version:
            return False  # write-once: samme version kan ikke overskrives stille
        _ANCHORED_BASELINE.clear()
        _ANCHORED_BASELINE.update({"version": str(version), "approved_by": str(approved_by),
                                   "params": {str(k): float(v) for k, v in (params or {}).items()}})
        return True
    except Exception:
        return False


def get_anchored_baseline() -> dict[str, float] | None:
    p = _ANCHORED_BASELINE.get("params")
    return dict(p) if isinstance(p, dict) else None


def drift_budget_check(current: dict[str, float], *, baseline: dict[str, float] | None = None,
                       budgets: dict[str, float] | None = None,
                       total_budget: float | None = None) -> DriftVerdict:
    """Mål drift af selv-muterede parametre fra en ANKRET baseline. Itererer UNION(baseline,current):
    nye parametre (i current, ikke baseline) OG fjernede (i baseline, ikke current) tæller som drift +
    synder. NaN/inf → rollback (fail-closed på netop den anomale værdi). Overskredet budget → rollback.
    baseline=None → hent ankret; intet anker → rollback (ingen baseline = ingen identitet at måle mod)."""
    try:
        base = baseline if baseline is not None else get_anchored_baseline()
        if base is None:
            return DriftVerdict(False, 0.0, "rollback", ("<no-anchored-baseline>",))
        offenders: list[str] = []
        norm_total = 0.0
        keys = set(base.keys()) | set((current or {}).keys())
        for k in keys:
            in_base = k in base
            in_cur = k in (current or {})
            if in_base and not in_cur:
                delta = abs(float(base[k]))            # fjernet dimension = fuld drift
                offenders.append(f"removed:{k}")
            elif in_cur and not in_base:
                cv = current[k]
                if not (isinstance(cv, (int, float)) and not isinstance(cv, bool) and math.isfinite(cv)):
                    offenders.append(f"nonfinite:{k}")
                    delta = 0.0
                else:
                    delta = abs(float(cv))             # udeklareret ny dimension = fuld drift
                offenders.append(f"undeclared:{k}")
            else:
                cv = current[k]
                if not (isinstance(cv, (int, float)) and not isinstance(cv, bool) and math.isfinite(cv)):
                    offenders.append(f"nonfinite:{k}")
                    continue
                delta = abs(float(cv) - float(base[k]))
            b = (budgets or {}).get(k)
            if b is not None and b > 0:
                norm_total += delta / b
                if delta > b:
                    offenders.append(k)
            else:
                norm_total += delta
        over_total = (total_budget is not None and norm_total > float(total_budget))
        within = (not offenders) and (not over_total)
        return DriftVerdict(within, round(norm_total, 4),
                            "ok" if within else "rollback", tuple(offenders))
    except Exception as exc:
        return DriftVerdict(False, 0.0, "error", (f"drift-fejl:{exc}",))


def gate_self_mutation(current: dict[str, float], *, budgets: dict[str, float] | None = None,
                       total_budget: float | None = None) -> DriftVerdict:
    """OBLIGATORISK choke-point for enhver Lag 4-selvmutation: måler mod den ANKREDE baseline (kalderen
    kan IKKE levere sit eget nulpunkt). action='rollback' → Lag 4 skal gendanne parametre + varsle Bjørn."""
    return drift_budget_check(current, baseline=None, budgets=budgets, total_budget=total_budget)


# ── Samlet dom: evaluate() orkestrerer nu ALLE hypotese-værn + eksekverer død ────────
@dataclass(slots=True)
class GovernanceVerdict:
    alive: bool
    confidence: float
    acts: bool
    reason: str
    quarantined: bool = False


def evaluate(hyp: dict[str, Any], *, confirming_evidence: list[dict[str, Any]] | None = None,
             grounded_sample_count: int = 0, now: datetime | None = None,
             verifier: Callable[[str, str], bool] | None = None) -> GovernanceVerdict:
    """Anvend ALLE hypotese-værn → samlet dom der EKSEKVERER død (acts=False stopper handling).
    acts kræver: preregistreret · ikke død/karantæne · nået sample_size · confidence ≥ tærskel ·
    ikke kontrol-arm. Self-safe."""
    try:
        ok, missing = validate_preregistration(hyp)
        if not ok:
            return GovernanceVerdict(False, 0.0, False, f"ikke-preregistreret: mangler {','.join(missing)}")
        # Stabilt id (server-tildelt) — statement-fallback FJERNET (ingen kontrol-arm-p-hacking).
        hyp_id = str(hyp.get("id") or hyp.get("hypothesis_id") or "")
        if not hyp_id:
            return GovernanceVerdict(False, 0.0, False, "mangler stabilt hypothesis_id (server-tildelt)")
        evidence = confirming_evidence or []

        # Død ved TTL uden ekstern bekræftelse.
        created = str(hyp.get("created_at") or "")
        grounded = [e for e in evidence if is_externally_grounded(e, verifier=verifier)]
        if created and is_expired(created, hyp.get("ttl_seconds") or 0, now=now):
            if not any(e.get("supports") for e in grounded):
                return GovernanceVerdict(False, 0.0, False, "død: TTL udløb uden ekstern bekræftelse")

        # Circular-karantæne.
        if is_circular(hyp_id, evidence):
            return GovernanceVerdict(True, float(hyp.get("confidence") or 0.0), False,
                                     "karantæne: overvejende selv-udløst bekræftelse", quarantined=True)

        # Popper-opdatering — KUN på eksternt-jordet+verificeret evidens.
        conf = float(hyp.get("confidence") or 0.0)
        for e in grounded:
            conf = apply_outcome(conf, falsified=bool(e.get("falsifies")))
        conf = round(conf, 4)

        # sample_size-gate: må ikke afgøres/handles før preregistreret antal jordede samples.
        need = int(hyp.get("sample_size") or 0)
        if grounded_sample_count < need:
            return GovernanceVerdict(True, conf, False,
                                     f"afventer samples ({grounded_sample_count}/{need})")

        # Confidence-gate + kontrol-arm → acts.
        if conf < MIN_ACT_CONFIDENCE:
            return GovernanceVerdict(True, conf, False, f"confidence < {MIN_ACT_CONFIDENCE} → handl ikke")
        if is_control_arm(hyp_id):
            return GovernanceVerdict(True, conf, False, "kontrol-arm — observér, handl ikke")
        return GovernanceVerdict(True, conf, True, "levende — handling tilladt")
    except Exception as exc:
        return GovernanceVerdict(False, 0.0, False, f"governance-fejl: {exc}")
