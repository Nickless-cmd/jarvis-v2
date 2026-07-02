"""core/services/central_hypothesis_governance.py

§8 (LivingNeuron v3): HYPOTESE-DØDSMEKANISMEN — ufravigelig FØR Lag 3 bygges.

Rådets konsensus (skeptiker + videnskab + filosof): et system der genererer hypoteser OG
bedømmer dem OG handler på dem OG fodrer resultatet tilbage er en CONFIRMATION-BIAS-MASKINE
uden strukturelle værn. Specens påstand "hver hypotese kan bevises/afvises fra data" er TOM
uden en mekanisme der TVINGER en falsk hypotese til at dø. Byg dødsmekanismen FØR generatoren.

Dette modul er REN POLITIK (ingen egen DB — undgår dual-truth-kopi af meta_learning_hypotheses).
Den fremtidige Lag 3-generator SKAL route sine hypoteser gennem disse værn. Alt self-safe.

De 7 værn (rådet):
  1. Pre-registrering + TTL     — validate_preregistration / is_expired
  2. Popper-asymmetri           — apply_outcome
  3. Circular-karantæne         — is_circular
  4. Ekstern grounding          — is_externally_grounded
  5. Shadow-first (Lag 4)       — may_apply_adaptation
  6. Multiple-comparisons       — convergence_threshold
  7. Kontrol-arm                — is_control_arm
Samlet dom: evaluate.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# ── 1. Pre-registrering: en hypotese må ALDRIG fødes uden sin egen dødsdom ──────────
# Hvert felt er en forudsætning for at hypotesen KAN falsificeres. Mangler ét → afvis.
REQUIRED_FIELDS = (
    "statement",         # menneske-læsbar formodning
    "prediction",        # konkret fremtidig observation ("nerve X > tærskel Y inden T")
    "null_hypothesis",   # hvad der gælder hvis formodningen er falsk
    "success_criterion", # hvornår regnes den bekræftet
    "sample_size",       # antal uafhængige samples FØR resolve
    "ttl_seconds",       # dør automatisk hvis ikke bekræftet inden T
    "provenance",        # {mechanism, family, cursor_id} — hvor signalet kom fra
)
_PROVENANCE_KEYS = ("mechanism", "family", "cursor_id")


def validate_preregistration(hyp: dict[str, Any]) -> tuple[bool, list[str]]:
    """Returnerer (ok, mangler). En hypotese uden falsifikations-forudsigelse, TTL, null-
    hypotese, success-kriterium, sample_size og provenance er ikke falsificerbar → afvis."""
    missing: list[str] = []
    if not isinstance(hyp, dict):
        return False, list(REQUIRED_FIELDS)
    for f in REQUIRED_FIELDS:
        v = hyp.get(f)
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(f)
    # sample_size + ttl skal være positive tal
    if isinstance(hyp.get("sample_size"), bool) or not isinstance(hyp.get("sample_size"), int) or int(hyp.get("sample_size") or 0) <= 0:
        if "sample_size" not in missing:
            missing.append("sample_size")
    if not isinstance(hyp.get("ttl_seconds"), (int, float)) or float(hyp.get("ttl_seconds") or 0) <= 0:
        if "ttl_seconds" not in missing:
            missing.append("ttl_seconds")
    prov = hyp.get("provenance")
    if not isinstance(prov, dict) or any(k not in prov for k in _PROVENANCE_KEYS):
        if "provenance" not in missing:
            missing.append("provenance")
    return (len(missing) == 0), missing


def is_expired(created_at_iso: str, ttl_seconds: float, *, now: datetime | None = None) -> bool:
    """Er hypotesens TTL udløbet? En udløbet-uden-bekræftelse hypotese DØR (falsificeret via tavshed)."""
    try:
        t = datetime.fromisoformat(str(created_at_iso).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except Exception:
        return False
    n = now or datetime.now(timezone.utc)
    return (n - t).total_seconds() > float(ttl_seconds)


# ── 2. Popper-asymmetri: dør let, bekræftes svært ──────────────────────────────────
def apply_outcome(confidence: float, *, falsified: bool,
                  up_rate: float = 0.05, down_rate: float = 0.5) -> float:
    """En hypotese kan aldrig blive mere end SVAGT bekræftet af bekræftende evidens, men KAN
    dø af én modsigelse (Popper). Falsifikation: hård multiplikativ nedtrækning. Bekræftelse:
    langsom mættet opjustering mod (men aldrig til) 1.0."""
    c = max(0.0, min(1.0, float(confidence)))
    if falsified:
        return max(0.0, c * (1.0 - max(0.0, min(1.0, down_rate))))
    return min(1.0, c + max(0.0, up_rate) * (1.0 - c))


# ── 3. Circular-karantæne: selv-opfyldende bekræftelse tæller ikke ─────────────────
def is_circular(hyp_id: str, confirming_evidence: list[dict[str, Any]]) -> bool:
    """Hvis hypotesens ENESTE bekræftende evidens stammer fra en handling hypotesen SELV
    udløste (evidence['triggered_by'] == hyp_id), er bekræftelsen selv-opfyldende → karantæne."""
    conf = [e for e in (confirming_evidence or []) if e.get("supports")]
    if not conf:
        return False
    return all(str(e.get("triggered_by") or "") == str(hyp_id) for e in conf)


# ── 4. Ekstern grounding: loopet må kun lukkes af virkeligheden ────────────────────
GROUNDED_SOURCES = frozenset({"run_outcome", "user_reaction", "world_consequence", "external_metric"})


def is_externally_grounded(evidence: dict[str, Any]) -> bool:
    """Krop→hypotese→adaptation→krop uden ekstern jording driver mod en intern attraktor.
    Et outcome der lukker loopet SKAL komme fra virkeligheden, ikke et rent internt signal."""
    return str((evidence or {}).get("source") or "") in GROUNDED_SOURCES


# ── 5. Shadow-first (Lag 4): ingen aktiv adaptation før skygge + menneske-godkendelse ─
SHADOW_FIRST_MIN_DAYS = 2


def may_apply_adaptation(*, shadow_days_elapsed: float, human_approved: bool,
                         min_days: float = SHADOW_FIRST_MIN_DAYS) -> bool:
    """Enhver Lag 4-adaptation kører i shadow (beregn, log, ændr INTET) i mindst N dage, og en
    menneske-læsbar diff SKAL godkendes af Bjørn før første aktive adaptation. Fail-closed."""
    return bool(human_approved) and float(shadow_days_elapsed) >= float(min_days)


# ── 6. Multiple-comparisons: 3-signal-tilfælde er hyppige med ~157 familier ─────────
def convergence_threshold(base_alpha: float, n_comparisons: int) -> float:
    """Bonferroni-korrektion. Med mange samtidige familie-sammenligninger er tilfældige
    3-signal-convergenser ekstremt hyppige (fødselsdags-paradoks på steroider). Skærp tærsklen."""
    return max(0.0, float(base_alpha)) / max(int(n_comparisons), 1)


# ── 7. Kontrol-arm: mål om adaptation FAKTISK hjælper vs. selv-bekræftende drift ────
def is_control_arm(hyp_id: str, *, fraction: float = 0.2) -> bool:
    """Deterministisk (hash-baseret, reproducerbar) split: en fast andel hypoteser hvor
    Centralen IKKE handler på outcome. Uden en kontrol-arm kan man ikke BEVISE at adaptation
    forbedrer noget — kun tro det."""
    frac = max(0.0, min(1.0, float(fraction)))
    h = int(hashlib.sha1(str(hyp_id).encode("utf-8")).hexdigest(), 16)
    return (h % 1000) < int(round(frac * 1000))


# ── Samlet dom ─────────────────────────────────────────────────────────────────────
@dataclass(slots=True)
class GovernanceVerdict:
    alive: bool
    confidence: float
    acts: bool           # False = kontrol-arm ELLER død/karantæne → Centralen handler IKKE
    reason: str
    quarantined: bool = False


def evaluate(hyp: dict[str, Any], *, confirming_evidence: list[dict[str, Any]] | None = None,
             now: datetime | None = None) -> GovernanceVerdict:
    """Anvend alle værn på en hypotese + dens evidens → samlet dom. Self-safe."""
    try:
        ok, missing = validate_preregistration(hyp)
        if not ok:
            return GovernanceVerdict(False, 0.0, False,
                                     f"ikke-preregistreret: mangler {','.join(missing)}")
        hyp_id = str(hyp.get("id") or hyp.get("hypothesis_id") or hyp.get("statement") or "")
        evidence = confirming_evidence or []

        # Død ved TTL (falsificeret via tavshed)?
        created = str(hyp.get("created_at") or "")
        if created and is_expired(created, hyp.get("ttl_seconds") or 0, now=now):
            resolved = any(e.get("supports") and is_externally_grounded(e) for e in evidence)
            if not resolved:
                return GovernanceVerdict(False, 0.0, False, "død: TTL udløb uden ekstern bekræftelse")

        # Circular-karantæne?
        if is_circular(hyp_id, evidence):
            return GovernanceVerdict(True, float(hyp.get("confidence") or 0.0), False,
                                     "karantæne: kun selv-udløst bekræftelse", quarantined=True)

        # Popper-opdatering på KUN eksternt-jordet evidens.
        conf = float(hyp.get("confidence") or 0.0)
        for e in evidence:
            if not is_externally_grounded(e):
                continue  # internt signal må ikke flytte confidence
            conf = apply_outcome(conf, falsified=bool(e.get("falsifies")))

        acts = not is_control_arm(hyp_id)
        return GovernanceVerdict(True, round(conf, 4), acts,
                                 "levende" + ("" if acts else " (kontrol-arm — observér, handl ikke)"))
    except Exception as exc:  # aldrig vælt kalderen
        return GovernanceVerdict(False, 0.0, False, f"governance-fejl: {exc}")
