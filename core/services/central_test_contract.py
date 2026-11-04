"""core/services/central_test_contract.py

Den BINDENDE testkontrakt — forbindelsen mellem hvad en hypotese påstår og hvordan
den bliver efterprøvet.

Målt 4/11-2026: 0 af 505 aktive hypoteser bar en valideret kontrakt. Retningen lå
hardkodet to steder: i family-konventionen ``"latency:W>L"`` (W er ALTID vinderen)
og i evaluatorens ``if/else``. Konsekvensen var ikke kosmetisk — en hypotese der
påstod det MODSATTE ("X er langsommere end Y") kunne slet ikke udtrykkes, og to
hypoteser med modsatrettede forventninger ville få samme dom på samme data.

Kontrakten gemmes PÅ hypotesen (``test_contract_json``), ikke som en reference til
en fil: ellers kunne en kodeopdatering ændre betydningen af en hypotese der blev
oprettet for måneder siden.

Autoritetsfordelingen er med vilje skæv: en model må FORESLÅ en kontrakt, men
Centralen VALIDERER den mod ``CONTRACT_TYPES`` og afviser den, hvis typen, versionen
eller evaluatoren ikke findes. Et gyldigt JSON-objekt er ikke en gyldig kontrakt.
"""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1

# Navngivne, versionerede EVALUERINGSPOLITIKKER — hvornår en observation tæller som
# støtte, som modsigelse, og hvornår den hverken er det ene eller det andet.
#
# Grunden til at politikken er pinnet i kontrakten og ikke lånt fra evaluatorens
# modul-konstanter: målt 4/11-2026 læste kontrakt-stien `_LATENCY_MARGIN` fra
# `central_model_meta` med en hardkodet fallback. Ændrede nogen den konstant, ville
# hypoteser oprettet for måneder siden få en anden dom — uden at nogen havde rørt
# deres kontrakt. En kontrakt der ikke selv bærer sin beslutningsregel er ikke bindende.
#
# Tredelingen er ikke kosmetisk: "hurtigere, men ikke markant nok" er IKKE det samme
# som "modbevist". Et binært udfald ville stemple al utydelig evidens som modsigelse —
# samme fejlform som `0/0 → 0.0` og som `stott > mods` uden flertalskrav.
POLICIES: dict[str, dict[str, Any]] = {
    "latency_margin_v1": {
        "version": 1,
        "metric": "latency_ms",
        # subject skal være mindst 25 % hurtigere end comparator → støtte
        "support_ratio": 1.25,
        # subject er ikke hurtigere overhovedet → modsigelse
        "contradict_ratio": 1.0,
    },
}

# Versioneret register over de kontrakttyper Centralen faktisk kan efterprøve.
# `evaluator_version` pinnes sammen med typen: ændrer evaluatorens domsregel sig,
# skal det være en NY version — ellers ændrer gamle hypoteser betydning bagudrettet.
CONTRACT_TYPES: dict[str, dict[str, Any]] = {
    "comparative_latency": {
        "version": 1,
        "evaluator": "model_meta_persistence",
        "evaluator_version": 1,
        "required": ("subject", "comparator", "expected_relation", "min_samples",
                     "evaluation_policy"),
        "relations": ("less_than", "greater_than"),
        # `event_time` er IKKE implementeret: `central_hypothesis_samples.created_at`
        # sættes ved indsættelse. En kontrakt må ikke påstå at måle en tidsbasis
        # infrastrukturen ikke bærer.
        "time_bases": ("ingestion_time",),
        "policies": ("latency_margin_v1",),
        "metric": "latency_ms",
    },
}


def validate(contract: Any) -> tuple[bool, list[str]]:
    """Strukturel + semantisk kompatibilitet. → (ok, manglende/ugyldige felter).

    Tjekker IKKE om der findes data lige nu — det er operationel tilgængelighed og
    hører i evaluatoren, som skal rapportere `None` (for lidt data), ikke afvise
    kontrakten som ugyldig.
    """
    missing: list[str] = []
    if not isinstance(contract, dict) or not contract:
        return False, ["kontrakten er ikke et objekt"]

    if int(contract.get("schema_version") or 0) != SCHEMA_VERSION:
        missing.append(f"schema_version skal være {SCHEMA_VERSION}")

    ctype = str(contract.get("contract_type") or "")
    spec = CONTRACT_TYPES.get(ctype)
    if spec is None:
        missing.append(f"ukendt contract_type {ctype!r}")
        return False, missing

    for field in spec["required"]:
        val = contract.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(f"feltet {field!r} mangler")

    rel = str(contract.get("expected_relation") or "")
    if rel and rel not in spec["relations"]:
        missing.append(f"expected_relation {rel!r} er ikke en af {spec['relations']}")

    # Semantisk kompatibilitet: evaluatoren SKAL være den type kontrakten kræver.
    ev = str(contract.get("evaluator") or "")
    if ev != spec["evaluator"]:
        missing.append(f"contract_type {ctype!r} kræver evaluator {spec['evaluator']!r},"
                       f" ikke {ev!r}")
    evv = int(contract.get("evaluator_version") or 0)
    if evv != spec["evaluator_version"]:
        missing.append(f"evaluator_version skal være {spec['evaluator_version']}")

    tb = str(contract.get("time_basis") or "ingestion_time")
    if tb not in spec["time_bases"]:
        missing.append(f"time_basis {tb!r} er ikke implementeret"
                       f" (kun {spec['time_bases']})")

    # Beslutningskriteriet skal være pinnet i kontrakten — ellers kan evaluatorens
    # kode ændre dommen for hypoteser der aldrig blev rørt.
    pol = str(contract.get("evaluation_policy") or "")
    if pol not in spec.get("policies", ()):
        missing.append(f"evaluation_policy {pol!r} er ikke en af {spec.get('policies')}")
    else:
        pver = int(contract.get("policy_version") or 0)
        expected_ver = int(POLICIES[pol]["version"])
        if pver and pver != expected_ver:
            missing.append(f"policy_version skal være {expected_ver} for {pol!r}")

    try:
        if int(contract.get("min_samples") or 0) < 1:
            missing.append("min_samples skal være ≥ 1")
    except (TypeError, ValueError):
        missing.append("min_samples skal være et tal")

    return (not missing), missing


def policy_of(contract: dict[str, Any]) -> dict[str, Any] | None:
    """Den pinnede beslutningsregel. None hvis politikken ikke findes.

    Evaluatoren SKAL bruge denne og ikke sine egne modul-konstanter: ellers er
    kontrakten deklarativ, men dommen imperativ — og de to kan glide fra hinanden
    uden at nogen rører hypotesen.
    """
    name = str(contract.get("evaluation_policy") or "")
    spec = POLICIES.get(name)
    if spec is None:
        return None
    return dict(spec)


def relation_of(contract: dict[str, Any]) -> str:
    """Retningen kontrakten hævder — 'less_than' eller 'greater_than'. Tom ved fejl."""
    return str(contract.get("expected_relation") or "")


def subject_of(contract: dict[str, Any]) -> tuple[str, str]:
    """(subject, comparator) — de to størrelser der sammenlignes."""
    return (str(contract.get("subject") or ""), str(contract.get("comparator") or ""))


def evaluator_of(contract: dict[str, Any]) -> str:
    return str(contract.get("evaluator") or "")


def describe(contract: dict[str, Any]) -> str:
    """Kort menneskelæsbar form til logs og surfaces."""
    subj, comp = subject_of(contract)
    rel = relation_of(contract)
    arrow = "<" if rel == "less_than" else ">"
    metric = str(contract.get("metric") or "")
    return f"{subj} {arrow} {comp} på {metric} (min {contract.get('min_samples')} samples)"
