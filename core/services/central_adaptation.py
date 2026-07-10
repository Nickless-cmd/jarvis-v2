"""core/services/central_adaptation.py

Lag 4 v1 (LivingNeuron v3 §11 Fase 3): c→d-LUKNINGEN — første gang Centralen justerer en tilbøjelighed.

Loop: sanse (Lag 1-2) → hypotese (Lag 3) → test mod virkelighed (sampler) → RESOLVE → **JUSTÉR**.
Konkret adaptation v1 (bevidst smal + reversibel): et gut-proceed-BIAS drevet af Centralens EGEN
track-record — jo mere præcist den har forudsagt sig selv (resolved supported vs. contradicted),
jo mere tiltro tjener Jarvis' mavefornemmelse. Selv-model-tillid som tilbøjelighed.

── MANIFOLD (LivingNeuron-roadmap §3, første skridt — REN REFAKTOR) ──
Denne fil generaliserer nu adaptationen fra ÉN hardkodet muskel til et eksplicit REGISTER
(`ADAPTATION_REGISTRY`) af `AdaptationClass`-dataclasses — hver muskel drevet af SIN EGEN
track-record, sit eget drift-domæne og sit eget budget. I DETTE skridt indeholder registret
KUN den eksisterende gut-bias (adfærd 100% uændret, stadig live, samme kv_key/clamp/budget/anker).

⚠️ INGEN nye muskler tilføjes her. Nye klasser (procedure_weight, loop_persistence, senere
dream_trust) SKAL fødes i SHADOW i en SENERE commit — dvs. med deres eget `live_flag` som
default OFF — så de arver hele §8-membranen (shadow-first, per-domæne anker, drift-budget →
rollback+pause) før de nogensinde kan ændre adfærd. Bjørns ene switch gater dem alle.

HÅRDT VÆRN (§3 "verify_frozen_core-listen"): ved registrering AFVISER en assert enhver klasse
hvis `kv_key`/`name` rører SOUL/IDENTITY/SECURITY-gaten eller dødsmekanismens konstanter. En
selv-muterende muskel må ALDRIG kunne pege sin justering ind i den frosne kerne.

SIKKERHED (§8 + §12.3 + shadow-spec 2026-07-02):
  * SHADOW-FIRST: som standard beregnes + logges kun en diff — INTET ændres. Live kræver runtime-flag
    `central_lag4_live_enabled=True` (Bjørns ene switch, default OFF) OG ikke-paused.
  * DRIFT-BUDGET: hvert forslag gates gennem gate_self_mutation mod ANKRET baseline (bias=0 = identitet);
    overskredet → rollback + PAUSE (kill-switch) + varsl Bjørn.
  * REVERSIBELT: rollback-EKSEKVERING gendanner forrige bias (det manglende primitiv fra shadow-spec).
  * BOUNDET: bias clampet til ±0.25; drift-budget 0.3.
  * FROSSEN KERNE urørt: rører KUN gut-bias — aldrig SOUL/identitet/sikkerhedsgates/værn-konstanter.
Alt self-safe, kaster ALDRIG.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.services import central_hypothesis_governance as gov

# ── Bagudkompatible modul-konstanter (uændrede værdier) ──────────────────────────────
# Gut-bias musklens identitet. Bevaret som modul-navne så alle call-sites + tests består.
_BIAS_KEY = "central_gut_proceed_bias"        # den justerede tilbøjelighed (persist)
_PREV_KEY = "central_gut_proceed_bias_prev"   # snapshot til rollback
_LIVE_FLAG = "central_lag4_live_enabled"      # Bjørns ene switch (default False)
_PAUSE_KEY = "central_lag4_paused"            # kill-switch (sat af drift-rollback)

_BIAS_CLAMP = 0.25
_BIAS_BUDGET = 0.30
_MIN_RESOLVED = 5
_ANCHOR_VERSION = "gut-bias-v1"
_DOMAIN = "gut_proceed_bias"   # §8.1: isoleret anker-domæne (kolliderer ikke m. andre Lag 4-tråde)

# §8.3: gut-bias fodres KUN af Jarvis' SELV-FORSTÅELSES-hypoteser (adfærd/inner-life), IKKE af
# fremtidige model/prompt/sekvens-tråde → ingen tvær-tråd-kontaminering af mavefornemmelsen.
_GUT_SOURCES = ("causal_convergence", "causal_divergence", "stance_divergence")


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


# ── MANIFOLD: musklen som eksplicit klasse + register ────────────────────────────────
@dataclass(frozen=True)
class AdaptationClass:
    """Én selv-justerende muskel: en tilbøjelighed Centralen justerer efter SIN EGEN track-record
    på præcis den slags hypotese. Immutabel (frozen) — en muskels identitet må ikke muteres i runtime.

    Felter:
      name       — menneskelæsbart navn (også nerve-/log-nøgle).
      kv_key     — runtime-state-nøglen den justerede skalar persistes under.
      prev_key   — snapshot-nøgle til rollback.
      sources    — hypotese-kilder (§8.3) der fodrer DENNE musklens track-record. Isoleret pr. muskel.
      budget     — drift-budget mod ankret baseline (§9). Overskredet → rollback+pause.
      clamp      — hård grænse (±clamp) på den justerede skalar.
      live_flag  — runtime-flag der gør musklen live. Default-OFF for nye muskler (shadow-first).
      pause_flag — kill-switch-nøgle (sat af drift-rollback).
      domain     — isoleret anker-domæne (§8.1) så muskler ikke kolliderer mod ét globalt anker.
      anchor_version — write-once anker-version for identitets-baseline.
      min_resolved   — minimum resolved samples før et forslag overhovedet dannes.
    """
    name: str
    kv_key: str
    prev_key: str
    sources: tuple[str, ...]
    budget: float
    clamp: float
    live_flag: str
    pause_flag: str
    domain: str
    anchor_version: str
    min_resolved: int = _MIN_RESOLVED


# ── HÅRDT VÆRN: frossen-kerne-blacklist (§3 "verify_frozen_core-listen") ──────────────
# En muskel må ALDRIG pege sin justering ind i SOUL/IDENTITY/SECURITY-gaten eller dødsmekanismens
# konstanter. Vi matcher case-insensitivt på SUBSTRING af både kv_key OG name mod denne liste, så
# den fanger både governance-konstant-navnene direkte og ethvert SOUL/IDENTITY/SECURITY-nabo-nøgle.
# Kilde: dødsmekanismens frosne konstanter (central_hypothesis_governance.py) + eksplicitte
# SOUL/IDENTITY/SECURITY/death-tokens. Der findes INGEN kanonisk protected-key-liste andetsteds i
# repoet (grep tom) → guarden ER den kanoniske liste for Lag 4-registrering.
_FROZEN_CORE_BLACKLIST: frozenset[str] = frozenset({
    # dødsmekanismens egne konstant-navne (verify_frozen_core-tuplen)
    "min_act_confidence", "shadow_first_min_days", "_popper_down", "_popper_up",
    "_circular_quarantine_fraction", "grounded_sources", "learnable_aggregate_keys",
    "_frozen_core_sig", "_anchored_baselines", "verify_frozen_core", "frozen_core",
    # SOUL/IDENTITY/SECURITY/dødsmekanisme-tokens (substring-fanget)
    "soul", "identity", "security", "death", "killswitch", "kill_switch",
})


def _assert_not_frozen_core(cls: AdaptationClass) -> None:
    """HÅRD assert: afvis enhver AdaptationClass hvis kv_key/name rører den frosne kerne. Kører for
    HVER registreret klasse. Kaster AssertionError bevidst (registrerings-tid, ikke runtime-hot-path)
    så en forbudt muskel ALDRIG kommer ind i registret. Self-safe gælder IKKE her — dette skal fejle."""
    haystacks = (str(cls.kv_key).lower(), str(cls.name).lower(),
                 str(cls.prev_key).lower(), str(cls.domain).lower(),
                 str(cls.live_flag).lower(), str(cls.pause_flag).lower())
    for token in _FROZEN_CORE_BLACKLIST:
        for hay in haystacks:
            if token in hay:
                raise AssertionError(
                    f"AdaptationClass '{cls.name}' afvist: nøgle rører frossen kerne (token '{token}' "
                    f"i '{hay}'). En muskel må aldrig justere SOUL/IDENTITY/SECURITY/dødsmekanismen."
                )


def _register_adaptation_class(cls: AdaptationClass) -> AdaptationClass:
    """Valider + tilføj en muskel til registret. Kører den HÅRDE assert FØR optagelse. Returnerer
    klassen (så registret kan bygges deklarativt)."""
    _assert_not_frozen_core(cls)
    return cls


# EKSAKT den eksisterende gut-bias — samme kv_key/prev/sources/budget/clamp/flags/domæne/anker.
# REN REFAKTOR: intet nyt her. Nye (ikke-gut) klasser fødes i shadow (live_flag OFF) i SENERE commit.
_GUT_CLASS = _register_adaptation_class(AdaptationClass(
    name="gut_proceed_bias",
    kv_key=_BIAS_KEY,
    prev_key=_PREV_KEY,
    sources=_GUT_SOURCES,
    budget=_BIAS_BUDGET,
    clamp=_BIAS_CLAMP,
    live_flag=_LIVE_FLAG,
    pause_flag=_PAUSE_KEY,
    domain=_DOMAIN,
    anchor_version=_ANCHOR_VERSION,
    min_resolved=_MIN_RESOLVED,
))

# dream_trust — FØRSTE shadow-muskel (LivingNeuron §3-opfølgning). Måler hvor meget Jarvis'
# drømme holder mod virkeligheden: track-record fra source='oneiric_loop' (pre-registrerede
# oneiriske hypoteser grounded af central_oneiric_sampler → §8-resolution). Lukker
# MANIFOLD↔ONEIRISK-loopet: sampleren afgør supported/contradicted → dream_trust proposerer en
# tiltro-bias. SHADOW: live_flag default OFF → beregner + logger, ANVENDER ALDRIG (ingen forbruger
# endnu; en senere forbruger kunne vægte dream_bias-intensitet i visible_runs). Arver HELE
# §8-membranen (shadow-first, per-domæne anker, drift-budget → rollback+pause). Rører intet frossen.
_DREAM_TRUST_CLASS = _register_adaptation_class(AdaptationClass(
    name="dream_trust",
    kv_key="central_dream_trust_bias",
    prev_key="central_dream_trust_bias_prev",
    sources=("oneiric_loop",),
    budget=_BIAS_BUDGET,
    clamp=_BIAS_CLAMP,
    live_flag="central_dream_trust_live",      # default OFF → shadow
    pause_flag="central_dream_trust_paused",
    domain="dream_trust_bias",
    anchor_version="dream-trust-v1",
    min_resolved=_MIN_RESOLVED,
))

ADAPTATION_REGISTRY: list[AdaptationClass] = [_GUT_CLASS, _DREAM_TRUST_CLASS]


def _default_class() -> AdaptationClass:
    """Bagudkompatibel default = gut-bias (så modul-niveau-API'et virker uden at kende registret)."""
    return _GUT_CLASS


# ── Per-klasse primitiver (gut = back-compat default) ────────────────────────────────
def get_bias(cls: AdaptationClass | None = None) -> float:
    """Læs + clamp en musklens justerede skalar. Default = gut. Self-safe."""
    c = cls or _default_class()
    try:
        return max(-c.clamp, min(c.clamp, float(_kv_get(c.kv_key, 0.0))))
    except Exception:
        return 0.0


def get_gut_bias() -> float:
    """Bagudkompatibel: gut-bias (uændret adfærd)."""
    return get_bias(_GUT_CLASS)


def is_live_enabled(cls: AdaptationClass | None = None) -> bool:
    """Musklen er live hvis dens live_flag er ON OG dens pause_flag ikke er sat. Default = gut."""
    c = cls or _default_class()
    return bool(_kv_get(c.live_flag, False)) and not bool(_kv_get(c.pause_flag, False))


def effective_dream_trust_factor() -> float:
    """Forbruger til dream_trust-musklen (LivingNeuron §3, 2026-07-10): oversæt tiltro-biasen
    til en vægt-faktor for dream_bias-intensitet. 1.0 når live_flag OFF (shadow — uændret).
    Når ON: clamp(1 + dream_trust_bias) i [0.5, 1.5] → bevist-troværdige drømme vægtes OP
    (mere prominente), modsagte drømme vægtes NED (fader hurtigere under prompt-gulvet).
    Self-safe → 1.0 (neutral). Arver §8-membranen (musklen selv er clamped/paused/rollback)."""
    try:
        cls = _DREAM_TRUST_CLASS
        if not is_live_enabled(cls):
            return 1.0
        return max(0.5, min(1.5, 1.0 + float(get_bias(cls))))
    except Exception:
        return 1.0


def is_paused(cls: AdaptationClass | None = None) -> bool:
    c = cls or _default_class()
    return bool(_kv_get(c.pause_flag, False))


def _ensure_anchor(cls: AdaptationClass | None = None) -> None:
    """Ankr identitets-baseline: bias=0 ER identiteten (ingen tilbøjeligheds-forvrængning). In-memory
    pr. proces (0.0 er altid det korrekte nulpunkt → drift måles altid fra 'ingen bias')."""
    c = cls or _default_class()
    try:
        if gov.get_anchored_baseline(domain=c.domain) is None:
            gov.anchor_identity_baseline({c.kv_key: 0.0}, version=c.anchor_version,
                                         approved_by="lag4-shadow", domain=c.domain)
    except Exception:
        pass


def resolved_track_record(*, sources: tuple[str, ...] | None = None) -> dict[str, int]:
    """Centralens egen præcision: hvor mange hypoteser har holdt vs. fejlet. SOURCE-SCOPED (§8.3):
    `sources` afgrænser til bestemte hypotese-kilder; None = alle. Self-safe."""
    out = {"supported": 0, "contradicted": 0}
    try:
        from core.runtime.db import connect
        with connect() as c:
            if sources:
                ph = ",".join("?" for _ in sources)
                rows = c.execute(f"SELECT outcome, COUNT(*) n FROM central_hypotheses "
                                 f"WHERE status='resolved' AND source IN ({ph}) GROUP BY outcome",
                                 tuple(sources)).fetchall()
            else:
                rows = c.execute("SELECT outcome, COUNT(*) n FROM central_hypotheses "
                                 "WHERE status='resolved' GROUP BY outcome").fetchall()
            for r in rows:
                o = str(r["outcome"] or "")
                if o in out:
                    out[o] = int(r["n"])
    except Exception:
        pass
    return out


def compute_proposed_bias(cls: AdaptationClass | None = None) -> dict[str, Any]:
    """Foreslå bias fra en musklens EGEN track-record. accuracy=supported/(supported+contradicted).
    Højere præcision → mere proceed-tiltro; lavere → caution. Kræver ≥ min_resolved resolved (ellers
    ingen ændring). Default = gut → adfærd IDENTISK med før-MANIFOLD."""
    c = cls or _default_class()
    tr = resolved_track_record(sources=c.sources)   # §8.3: kun musklens egne kilder
    resolved = tr["supported"] + tr["contradicted"]
    # §8.2: AL læring passerer læringsmembranen (kun aggregat-skalarer krydser §24.4). Første
    # ægte kalder af gate_learning_input — gør membranen til et faktisk choke-point, ikke dekoration.
    gated = gov.gate_learning_input({"supports": tr["supported"], "samples": resolved})
    if not gated["ok"]:
        return {"proposed": 0.0, "accuracy": None, "resolved": resolved, "enough": False}
    if resolved < c.min_resolved:
        return {"proposed": 0.0, "accuracy": None, "resolved": resolved, "enough": False}
    accuracy = tr["supported"] / resolved
    proposed = max(-c.clamp, min(c.clamp, round((accuracy - 0.5) * 0.5, 4)))
    return {"proposed": proposed, "accuracy": round(accuracy, 3), "resolved": resolved, "enough": True}


def rollback(reason: str = "", cls: AdaptationClass | None = None) -> None:
    """Rollback-EKSEKVERING (shadow-specens manglende primitiv): gendan forrige bias + PAUSE Lag 4
    (kill-switch) + varsl Bjørn. Identitet beskyttet."""
    c = cls or _default_class()
    prev = float(_kv_get(c.prev_key, 0.0) or 0.0)
    _kv_set(c.kv_key, prev)
    _kv_set(c.pause_flag, True)
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "lag4_rollback", "kind": "flag",
                           "muscle": c.name, "restored_bias": prev,
                           "reason": str(reason)[:120], "paused": True})
    except Exception:
        pass


def _run_class_tick(cls: AdaptationClass) -> dict[str, object]:
    """Kør ÉN musklens adaptations-tick: beregn → gate → shadow-log → anvend KUN hvis live+ok.
    For gut-klassen er dette BYTE-IDENTISK med den tidligere run_adaptation_tick-krop. Self-safe."""
    _ensure_anchor(cls)
    cur = get_bias(cls)
    prop = compute_proposed_bias(cls)
    proposed = float(prop["proposed"])
    # Drift-budget-gate: hvad ville bias BLIVE, målt mod ankret baseline (bias=0)?
    verdict = gov.gate_self_mutation({cls.kv_key: proposed}, budgets={cls.kv_key: cls.budget},
                                     domain=cls.domain)
    live = is_live_enabled(cls)
    applied = False
    if verdict.action == "rollback":
        rollback(reason=f"drift {verdict.drift} > budget {cls.budget}", cls=cls)
    elif prop["enough"] and live and abs(proposed - cur) > 1e-6:
        _kv_set(cls.prev_key, cur)       # snapshot FØR ændring (muliggør rollback)
        _kv_set(cls.kv_key, proposed)
        applied = True
    # SHADOW-diff (altid) — egress-frit, kun skalarer.
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "lag4_adaptation", value=float(proposed),
                       meta={"muscle": cls.name, "current": cur, "proposed": proposed,
                             "accuracy": prop.get("accuracy"), "resolved": prop["resolved"],
                             "live": live, "applied": applied, "gate": verdict.action})
    except Exception:
        pass
    return {"muscle": cls.name, "mode": "live" if live else "shadow", "current_bias": cur,
            "proposed_bias": proposed, "applied": applied, "gate": verdict.action,
            "accuracy": prop.get("accuracy"), "resolved": prop["resolved"]}


def run_adaptation_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: iterér REGISTRET. For den ENESTE gut-klasse er adfærden IDENTISK med før
    (samme forslag/gate/shadow/apply). Registret har KUN gut i dette skridt — nye muskler fødes i
    shadow (live_flag OFF) i senere commit. Returnerer gut-klassens felter på top-niveau for fuld
    bagudkompatibilitet + en `muscles`-liste for de øvrige. Self-safe."""
    results: list[dict[str, object]] = []
    for cls in ADAPTATION_REGISTRY:
        try:
            results.append(_run_class_tick(cls))
        except Exception as exc:      # per-muskel isolation: én muskels fejl må ikke dræbe ticken
            results.append({"muscle": cls.name, "mode": "error", "error": str(exc)[:120]})
    # Bagudkompatibel top-niveau-form = gut-klassen (registrets første/eneste element).
    gut = next((r for r in results if r.get("muscle") == _GUT_CLASS.name), results[0] if results else {})
    return {"status": "ok",
            "mode": gut.get("mode", "shadow"),
            "current_bias": gut.get("current_bias", 0.0),
            "proposed_bias": gut.get("proposed_bias", 0.0),
            "applied": gut.get("applied", False),
            "gate": gut.get("gate"),
            "accuracy": gut.get("accuracy"),
            "resolved": gut.get("resolved"),
            "muscles": results}


def register_adaptation_producer() -> None:
    """Registrér Lag 4-adaptationen som cadence-producer (~hvert 60 min). SHADOW medmindre live-flag ON."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_adaptation",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=run_adaptation_tick,
        priority=8,
    ))


def build_central_adaptation_surface() -> dict[str, object]:
    """Mission Control surface — read-only: nuværende bias, foreslået, live/shadow/paused."""
    return {"active": True, "gut_proceed_bias": get_gut_bias(), "live_enabled": is_live_enabled(),
            "paused": is_paused(), **compute_proposed_bias()}
