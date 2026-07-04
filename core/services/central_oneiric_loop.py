"""DEN ONEIRISKE SLØJFE — drømme får dags-konsekvenser + beviser sig mod virkeligheden.

LivingNeuron-roadmap §4 (4. jul). FØRSTE SKRIDT: broen der — hver gang dream_bias
har sat en `loop_persistence`-bias — PRE-REGISTRERER en falsificerbar hypotese gennem
den EKSISTERENDE §8-dødsmekanisme (central_hypothesis_governance via
central_hypothesis_generator.register_governed_hypothesis), OG markerer ~20% af de
drøm-biaserede dage som KONTROL-arm (bias beregnet, IKKE anvendt) så Centralen senere
kan BEVISE at drømmen hjalp — i stedet for at selv-bekræfte sig.

Bygbar fordi:
  * dream_bias-pipelinen skriver ALLEREDE biasen (get_active_dream_bias læser den).
  * governance-stien findes ALLEREDE (register_governed_hypothesis → §8).
Det er en NY BRO, ikke en ny hjerne.

VÆRN (ufravigelige, roadmap §4):
  * Hypotesen routes gennem §8-dødsmekanismen — den kan DØ (TTL-udløb uden ekstern
    bekræftelse falsificerer den via tavshed). Vi omgår ALDRIG governance.
  * KONTROL-armen er OBLIGATORISK: uden den er sløjfen en confirmation-bias-maskine.
    ~20% af drøm-dage er kontrol-dage (deterministisk, salt-baseret via
    gov.is_control_arm på DAG-strengen — ingen RNG, ugrindeligt).
  * OBSERVE/RECORD-ONLY: dette skridt SKRIVER kun en governet hypotese + markerer
    dagens arm. Det ANVENDER eller UNDERTRYKKER IKKE selv biasen (den wiring er et
    opfølgnings-skridt, beskrevet nederst) — så det MUTERER INTET ud over at skrive en
    governet hypotese.

ÆRLIGT (ingen skjult begrænsning): prædiktions-målet `no_progress_finalize` er en ÆGTE
nerve (visible_runs.py, via central().observe under cluster="loop"), MEN den skrives kun
til trace-sinken (in-memory, restart-flygtig) — der er ENDNU intet aggregat rate-signal
og ingen sampler der GROUNDER denne hypotese. Derfor: hypotesen pre-registreres nu og DØR
korrekt ved TTL hvis intet grounder den (§8-falsifikation-ved-tavshed — netop det rigtige,
ingen falsk selv-bekræftelse). En opfølgnings-sampler (analog til
central_hypothesis_sampler) skal tælle nerve-raten før/efter for at ground'e den.

Self-safe: kaster ALDRIG. Egress-frit: kun skalarer via record_private.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# Durable dagsnøgle: hvilken dag registrerede vi sidst en oneirisk prædiktion.
# Idempotens — max én hypotese pr. dag pr. workspace, uanset hvor tit cadencen tikker.
_LAST_DAY_KEY = "oneiric_loop_last_registered_day"

# Kontrol-arm-andel: ~20% af drøm-biaserede dage kører som kontrol (bias IKKE anvendt).
_CONTROL_FRACTION = 0.2

# Hvor stor en |loop_persistence|-bias skal være før den er "sat nok" til en prædiktion.
_MIN_ABS_BIAS = 0.1

# Hypotese-defaults (spejler central_hypothesis_generator's tal for konsistens).
_DEFAULT_SAMPLE_SIZE = 5
_DEFAULT_TTL_S = 7 * 24 * 3600
_INITIAL_CONFIDENCE = 0.3

# Prædiktions-målet: den ÆGTE loop-nerve fra visible_runs.py.
_TARGET_METRIC = "loop/no_progress_finalize"


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


def _today() -> str:
    """Kanonisk dags-streng (hus-konvention: date().isoformat()). Dagen er den eksperimentelle enhed."""
    return datetime.now(UTC).date().isoformat()


def is_control_day(day: str, *, fraction: float = _CONTROL_FRACTION) -> bool:
    """Er `day` en KONTROL-dag (bias beregnet men IKKE anvendt)? Deterministisk + salt-baseret
    via §8's gov.is_control_arm — samme dag → samme arm, ~fraction over tid, ugrindeligt (kan
    ikke omformuleres væk, fordi splittet er på den rå dags-streng, ikke på hypotese-teksten).
    Self-safe: ved governance-import-fejl → fail-open til IKKE-kontrol (konservativt: hellere
    observér en ægte drøm-dag end at tabe den)."""
    try:
        from core.services import central_hypothesis_governance as gov
        return bool(gov.is_control_arm(str(day), fraction=fraction))
    except Exception:
        return False


def _read_loop_persistence_bias(*, workspace_id: str) -> float | None:
    """Læs den aktive dream_bias' loop_persistence-værdi (honorerer kill-switch + TTL). Returnerer
    None hvis dream_bias er slukket, ingen aktiv bias, eller |loop_persistence| < _MIN_ABS_BIAS.
    Self-safe."""
    try:
        from core.services.dream_bias_engine import get_active_dream_bias
        bias = get_active_dream_bias(workspace_id=workspace_id)
    except Exception:
        return None
    if not bias:
        return None
    try:
        thr = bias.get("threshold_bias") or {}
        v = float(thr.get("loop_persistence", 0.0))
    except Exception:
        return None
    if abs(v) < _MIN_ABS_BIAS:
        return None
    return v


def compose_oneiric_hypothesis(*, loop_persistence: float, day: str,
                               control_arm: bool) -> dict[str, Any]:
    """Omsæt en loop_persistence-bias til en EKSPLICIT, menneske-læsbar, PRE-REGISTRERET,
    falsificerbar hypotese (spejler central_hypothesis_generator's felt-form, så §8's
    validate_preregistration accepterer den).

    Retning: en POSITIV loop_persistence-bias = "hold loopet længere" → forudsigelsen er at
    `no_progress_finalize`-raten FALDER (færre tvungne stop pga. reel fremdrift). En NEGATIV
    bias = "slip loopet før" → forudsigelsen er at raten STIGER (flere tidlige stop). Kontrol-
    dage bærer control_arm=True i provenance så udfaldet aldrig fejl-læses som drømmens fortjeneste.
    """
    direction = "falder" if loop_persistence > 0 else "stiger"
    predicted_direction = "down" if loop_persistence > 0 else "up"
    signed = f"{loop_persistence:+.2f}"
    arm = "KONTROL (bias beregnet, IKKE anvendt)" if control_arm else "aktiv (bias anvendt)"
    return {
        "source": "oneiric_loop",
        "statement": (
            f"Nattens drøm satte loop_persistence {signed}. Hvis den bias faktisk former "
            f"vågen-cyklussen, ændrer den hvor længe jeg holder et fastlåst loop."
        ),
        "prediction": (
            f"På {day} ({arm}) {direction} raten af '{_TARGET_METRIC}' (tvungne no-progress-stop) "
            f"i forhold til baseline"
        ),
        "null_hypothesis": (
            f"loop_persistence-biasen ({signed}) er uden betydning for '{_TARGET_METRIC}'-raten "
            f"(ingen målbar forskel fra baseline; kontrol- og aktiv-dage ser ens ud)"
        ),
        "success_criterion": (
            f">= {_DEFAULT_SAMPLE_SIZE} jordede dags-observationer hvor aktiv-arm-raten bevæger sig "
            f"'{predicted_direction}' MERE end kontrol-arm-raten (drømmen skal slå kontrol, ikke bare "
            f"korrelere)"
        ),
        "sample_size": _DEFAULT_SAMPLE_SIZE,
        "ttl_seconds": _DEFAULT_TTL_S,
        "provenance": {
            "mechanism": "dream_bias.loop_persistence",
            # family er stabil pr. (dag, arm) → §8-generatorens dedup rammer højst én pr. dag.
            "family": f"oneiric:{day}:{'control' if control_arm else 'active'}",
            "cursor_id": day,
            # ekstra kontekst (skalarer) — læses af sampler/awareness senere.
            "loop_persistence": round(float(loop_persistence), 4),
            "predicted_direction": predicted_direction,
            "target_metric": _TARGET_METRIC,
            "control_arm": bool(control_arm),
        },
        "confidence": _INITIAL_CONFIDENCE,
    }


def run_oneiric_loop_tick(*, trigger: str = "cadence",
                          workspace_id: str = "default", **_: Any) -> dict[str, object]:
    """Cadence: hvis der i dag er en (stærk nok) loop_persistence dream_bias OG vi ikke allerede
    har pre-registreret for i dag → afgør dagens arm (~20% kontrol), komponér en falsificerbar
    hypotese, og REGISTRÉR den gennem §8-dødsmekanismen (register_governed_hypothesis). Emit en
    egress-fri nerve `dreams/oneiric_prediction`. RECORD-ONLY — anvender/undertrykker ALDRIG selv
    biasen. Self-safe: kaster ALDRIG."""
    try:
        day = _today()

        # Idempotens: max én pre-registrering pr. dag pr. workspace.
        last = _kv_get(_LAST_DAY_KEY, {}) or {}
        if isinstance(last, dict) and last.get(workspace_id) == day:
            return {"status": "skip", "reason": "allerede pre-registreret i dag", "day": day}

        loop_persistence = _read_loop_persistence_bias(workspace_id=workspace_id)
        if loop_persistence is None:
            return {"status": "skip", "reason": "ingen (stærk nok) loop_persistence-bias", "day": day}

        control_arm = is_control_day(day)
        hyp = compose_oneiric_hypothesis(
            loop_persistence=loop_persistence, day=day, control_arm=control_arm)

        # §8-GATE: routes gennem validate_preregistration → kan DØ. Vi omgår ALDRIG governance.
        try:
            from core.services.central_hypothesis_generator import register_governed_hypothesis
            reg = register_governed_hypothesis(hyp)
        except Exception as exc:
            reg = {"status": "error", "error": str(exc)}

        reg_status = str(reg.get("status") or "error")

        # Egress-fri nerve: kun skalarer (control_arm/retning/mål). ALDRIG hypotese-tekst.
        try:
            from core.services.central_private_observe import record_private
            record_private(
                "dreams", "oneiric_prediction",
                value=1.0 if control_arm else 0.0,
                meta={
                    "control_arm": bool(control_arm),
                    "predicted_direction": "down" if loop_persistence > 0 else "up",
                    "target_metric": _TARGET_METRIC,
                    "loop_persistence": round(float(loop_persistence), 4),
                    "registered": reg_status,
                    "day": day,
                },
                reason="oneiric pre-registration")
        except Exception:
            pass

        # Markér dagen som håndteret KUN hvis den faktisk blev registreret (ellers prøv igen næste tick).
        if reg_status in ("registered", "duplicate", "ok"):
            if not isinstance(last, dict):
                last = {}
            last[workspace_id] = day
            _kv_set(_LAST_DAY_KEY, last)

        return {"status": "ok", "day": day, "control_arm": control_arm,
                "loop_persistence": round(float(loop_persistence), 4),
                "registered": reg_status, "hyp_id": reg.get("hyp_id")}
    except Exception as exc:
        # Self-safe: en cadence-producer må aldrig vælte hubben.
        return {"status": "error", "error": str(exc)}


def register_oneiric_loop_producer() -> None:
    """Cadence-producer ~hver 6. time (langsom — dagen er enheden; idempotens gør flere tik/dag
    harmløse). Lav prioritet: musklerne/målingerne kører først. Egress-frit, observe/record-only."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_oneiric_loop",
        cooldown_minutes=360,
        visible_grace_minutes=0,
        run_fn=run_oneiric_loop_tick,
        priority=9,
    ))


def build_oneiric_loop_surface(*, workspace_id: str = "default") -> dict[str, object]:
    """Read-only projektion: i dag en drøm-prædiktions-dag? hvilken arm? hvilken retning?"""
    day = _today()
    lp = _read_loop_persistence_bias(workspace_id=workspace_id)
    return {
        "active": True,
        "day": day,
        "has_bias": lp is not None,
        "loop_persistence": round(float(lp), 4) if lp is not None else None,
        "control_arm": is_control_day(day) if lp is not None else None,
        "predicted_direction": (None if lp is None else ("down" if lp > 0 else "up")),
        "target_metric": _TARGET_METRIC,
    }


# ── OPFØLGNING (IKKE i dette skridt — beskrevet for integratoren) ────────────────────
# 1. GROUNDING-SAMPLER: en producer (analog til central_hypothesis_sampler) der pr. dag
#    tæller `no_progress_finalize`-raten og kalder record_governed_sample(hyp_id, ...,
#    source="world_consequence", ground_ref=<dag/run-id>) → §8-evaluate afgør supports/
#    falsifies. FORUDSÆTTER at nerven mirrores til et DURABLE aggregat (events-tabel eller
#    central_timeseries) — i dag skrives den kun til den restart-flygtige trace-sink.
# 2. KONTROL-ARM-KONSUMTION: visible_runs' loop_persistence-anvendelse skal LÆSE
#    is_control_day(_today()) og springe anvendelsen over på kontrol-dage. DETTE er den
#    eneste MUTATION — bevidst udskudt til efter shadow-observation + Bjørn-godkendelse
#    (roadmap §4-værn: shadow-first via MANIFOLD → arver membranen).
