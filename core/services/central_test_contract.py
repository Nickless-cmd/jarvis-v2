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

# Versionen af HELE evidens-specifikationen (enhed + vindue + aggregering). Den pinnes
# som ÉT tal fordi de tre tilsammen definerer hvad én observation ER: skifter en af dem
# betydning, er det en anden observation — og så må gamle kontrakter ikke arve den.
EVIDENCE_SPEC_VERSION = 1

# ── HVAD TÆLLES SOM ÉN OBSERVATION? ────────────────────────────────────────────
#
# Målt 4/11-2026, og det er grunden til at dette register findes: kontrakten bandt
# retningen, politikken og evaluatoren — men ikke ENHEDEN. `min_samples: 5` talte
# derfor 5 kald til `aggregate_model_outcomes()`, ikke 5 uafhængige observationer.
# De fem kald læste stort set samme rullende vindue (målt: 97,8 % overlap), så
# «fem beviser» var én observation målt fem gange.
#
# `implemented` er ikke pynt: en kontrakt må kun påstå en enhed Centralen faktisk kan
# måle — samme regel som `time_bases` nedenfor. En enhed der står her uden at være
# implementeret er dokumentation af hvad der MANGLER, ikke et tilbud.
EVIDENCE_UNITS: dict[str, dict[str, Any]] = {
    "per_run": {
        "version": 1,
        "description": ("én kørsel = én observation; hvert run vejer 1 uanset varighed,"
                        " så dommen falder på MEDIANEN (varighedsvægtning er pooled)"),
        "source": "visible_runs",
        # IKKE nok at skrive det: `min_samples` tælles mod antal RUNS, og dommen skal
        # læses som en fordelingsegenskab. Målt 4/11-2026: kontrakten deklarerede
        # `per_run` mens evaluatoren læste ét pooled gennemsnit — 288 run-enheder blev
        # til ÉT sample. En enhed der er deklareret men ikke implementeret er værre end
        # ingen enhed, fordi den ser valideret ud.
        "units_from": "runs",
        "implemented": True,
    },
    "aggregate_window": {
        "version": 1,
        "description": ("vinduet er ÉN observation (pooled gennemsnit over alle runs i"
                        " det); grundlaget kan bære præcis 1 enhed"),
        "source": "visible_runs",
        # Dette er hvad `pooled`-gennemsnittet faktisk ER. Den hed tidligere ikke noget,
        # så `per_run` blev brugt som et navn på det — og navnet påstod 288 gange mere
        # uafhængighed end beregningen kunne levere.
        "units_from": "window",
        "implemented": True,
    },
    "per_model_call": {
        "version": 1,
        "description": "ét model-kald = én observation (modellens egen hastighed)",
        "source": "costs",
        "units_from": "model_calls",
        "implemented": False,
        "reason": ("`costs` bærer `created_at` pr. ledger-række, men intet per-kald "
                   "start/slut. Ægte per-kald-latency kan derfor ikke måles; "
                   "`run_latency / call_count` er en FORDELING, ikke en måling — og "
                   "målt 4/11-2026 er forskellen afgørende: comparator har 11,3 kald "
                   "pr. kørsel mod subject's 1,0, så per-kørsel og per-kald giver "
                   "modsatte domme (16/16 vs 0/16)."),
    },
}

# ── HVORDAN VÆLGES OBSERVATIONERNE? ───────────────────────────────────────────
#
# Målt 4/11-2026: `_WINDOW = 300` er et ANTALS-vindue, ikke et tidsvindue. Dets
# udstrækning i tid bestemmes af hvor travl den mest aktive part er — de 300 rækker
# dækkede 1,5 døgn fordi 265 af dem var comparator-runs. En kontrakt der påstår
# «konsekvent hurtigere» kan derfor ikke afsiges på et vindue hvis længde i tid
# afhænger af den anden parts trafik.
WINDOW_SEMANTICS: dict[str, dict[str, Any]] = {
    "rolling_run_count": {
        "version": 1,
        "description": "de seneste N rækker; udstrækningen i tid er en artefakt af trafikken",
        "implemented": True,
    },
    "fixed_duration": {
        "version": 1,
        "description": "et fast tidsrum (fx 7 døgn) uanset antal rækker",
        "implemented": False,
        "reason": "aggregatet tager kun et antal; et tidsvindue kræver et nyt filter i kilden",
    },
    "non_overlapping_periods": {
        "version": 1,
        "description": "adskilte perioder hvor ingen observation genbruges mellem enheder",
        "implemented": False,
        "reason": ("kræver at observationer kan tildeles perioder og at genbrug kan "
                   "afvises — det er den ægte uafhængighed og den er ikke bygget"),
    },
}

# ── HVORDAN VÆGTES OBSERVATIONERNE? ───────────────────────────────────────────
#
# Målt 4/11-2026, 30 døgn: per-observation-vægtet gav 1,062 (modsiger), per-periode-
# vægtet gav 0,988 (støtter) — vægtforskellen var 5,5x fordi comparator havde op til
# 224 runs på en dag mod subject's 3-25. Det er ikke støj: det er to forskellige
# estimander, og de besvarer hvert sit spørgsmål.
AGGREGATIONS: dict[str, dict[str, Any]] = {
    "pooled": {
        "version": 1,
        "description": "gennemsnit vægtet pr. observation (mange runs vejer tungest)",
        # Varighedsvægtning: et run på 30 minutter vejer 100x mere end et på 18 sekunder.
        # Det er derfor `pooled` hører til `aggregate_window` og ikke til `per_run`.
        "weights": "duration",
        "implemented": True,
    },
    "equal_weight": {
        "version": 1,
        "description": "hvert run vejer 1 uanset varighed → medianen, ikke gennemsnittet",
        # Målt 4/11-2026: `per_run` blev deklareret sammen med `pooled`. De to er ikke
        # uafhængige felter — `pooled` kollapser netop de runs `per_run` påstår at tælle
        # enkeltvis. En kontrakt der bad om begge bad om én observation og kaldte den 288.
        "weights": "per_run",
        "implemented": True,
    },
    "per_period": {
        "version": 1,
        "description": "hver periode vejer lige meget uanset antal observationer",
        "implemented": False,
        "reason": "aggregatet summerer råt; periode-opdeling er ikke bygget",
    },
}

# Hvilken aggregering en enhed overhovedet KAN bære. Ikke en anbefaling — en
# begrænsning: `pooled` over en enkelt kørsel er ikke en aggregering, og `per_run`
# over et pooled gennemsnit er ikke per run. Uden denne tabel kunne kontrakten
# deklarere en enhed dens egen beregning modsiger.
UNIT_AGGREGATIONS: dict[str, tuple[str, ...]] = {
    "per_run": ("equal_weight",),
    "aggregate_window": ("pooled",),
}

# Hvor mange SAMPLES en enhed kan levere fra ÉN observation. `None` = operationelt
# loft (antallet af runs i vinduet), som først kendes ved evalueringen. `1` = et
# strukturelt loft: et pooled vindue ER ét bevis, uanset hvor mange runs det summerer.
# Uden dette loft ville en kontrakt med `aggregate_window` og `min_samples: 5` stå som
# «mangler data» for evigt i stedet for at blive afvist ved oprettelsen.
UNIT_SAMPLE_CEILING: dict[str, int | None] = {
    "per_run": None,
    "aggregate_window": 1,
}

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
        # `evidence_unit`, `window_semantics` og `aggregation` er PÅKRÆVEDE. Uden dem
        # ved dommen ikke hvad den har talt — og `min_samples: 5` kan betyde fem
        # uafhængige observationer eller én målt fem gange. Kontrakten må ikke kunne
        # afsige en dom den ikke kan redegøre for.
        "required": ("subject", "comparator", "expected_relation", "min_samples",
                     "evaluation_policy", "evidence_unit", "window_semantics",
                     "aggregation"),
        "relations": ("less_than", "greater_than"),
        # `event_time` er IKKE implementeret: `central_hypothesis_samples.created_at`
        # sættes ved indsættelse. En kontrakt må ikke påstå at måle en tidsbasis
        # infrastrukturen ikke bærer.
        "time_bases": ("ingestion_time",),
        "policies": ("latency_margin_v1",),
        "metric": "latency_ms",
        # HVAD TYPEN MÅLT PÅSTÅR (4/11-2026). Navnet `comparative_latency` var bredere end
        # målingen: den læser `visible_runs.started_at/finished_at`, altså hvor længe en
        # SAMLET KØRSEL tog — inkl. routing, køtid og alle værktøjskald. Målt samme dag:
        # comparator har 11,3 model-kald pr. kørsel mod subject's 1,0, så «hurtigst per
        # kørsel» og «hurtigst per kald» peger i hver sin retning (16/16 vs 0/16).
        # Påstanden skal derfor siges præcist, ellers læser en dom som en anden dom.
        "claim": ("hvilken rute giver den laveste OBSERVEREDE run-latency — den ventetid"
                  " en samlet kørsel gav — under de målte betingelser"),
        "does_not_claim": ("at måle modellens inferenshastighed: run-latency rummer"
                           " routing, køtid og alle model-kald i kørslen"),
    },
    # IKKE IMPLEMENTERET — dokumentation af hvad der mangler, ikke et tilbud. Samme
    # regel som `per_model_call` og `event_time`: en kontrakt må kun påstå det
    # infrastrukturen kan bære. `costs` har `created_at` pr. ledger-række men intet
    # per-kald start/slut, og `time_to_first_token`/`tokens_per_second` findes slet
    # ikke. Registreret her så navnet ikke opfindes ad hoc senere.
    "model_inference_latency": {
        "version": 1,
        "evaluator": None,
        "evaluator_version": 0,
        "implemented": False,
        "reason": ("kræver per-kald start/slut samt token-tal pr. kald; `costs` bærer"
                   " kun `created_at` pr. ledger-række, så et per-kald-latency kan"
                   " afledes som fordeling men ikke måles"),
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

    # Evidens-specifikationen: hvad tælles, hvordan vælges det, hvordan vægtes det.
    # Et ukendt navn er en tastefejl; et KENDT navn der ikke er implementeret er en
    # kontrakt der påstår at måle noget Centralen ikke kan måle. De to fejl er ikke ens,
    # og beskeden skal sige hvilken det er.
    for felt, register in (("evidence_unit", EVIDENCE_UNITS),
                           ("window_semantics", WINDOW_SEMANTICS),
                           ("aggregation", AGGREGATIONS)):
        navn = str(contract.get(felt) or "")
        es = register.get(navn)
        if es is None:
            missing.append(f"{felt} {navn!r} er ikke en af {tuple(register)}")
        elif not es.get("implemented"):
            missing.append(f"{felt} {navn!r} er registreret men IKKE implementeret:"
                           f" {es.get('reason', 'ingen grund angivet')}")

    ev_ver = int(contract.get("evidence_version") or 0)
    if ev_ver and ev_ver != EVIDENCE_SPEC_VERSION:
        missing.append(f"evidence_version skal være {EVIDENCE_SPEC_VERSION}"
                       f" (kontrakten bærer {ev_ver})")

    # ENHEDEN OG AGGREGERINGEN MÅ IKKE MODSIGE HINANDEN (4/11-2026). De er ikke to
    # uafhængige valg: `pooled` er varighedsvægtning, som kollapser netop de runs
    # `per_run` påstår at tælle enkeltvis. Målt samme dag stod den levende kontrakt med
    # `per_run` + `pooled` — den deklarerede 288 enheder og udførte 1. Det er værre end
    # ingen enhed, fordi den så valideret ud.
    unit_navn = str(contract.get("evidence_unit") or "")
    agg_navn = str(contract.get("aggregation") or "")
    tilladt = UNIT_AGGREGATIONS.get(unit_navn)
    if tilladt and agg_navn and agg_navn not in tilladt:
        missing.append(f"evidence_unit {unit_navn!r} kan ikke bære aggregation"
                       f" {agg_navn!r} (kun {tilladt}) — enheden og vægtningen"
                       f" beskriver to forskellige observationer")

    # MIN_SAMPLES KAN IKKE OVERSTIGE HVAD ENHEDEN LEVERER PR. OBSERVATION. Et pooled
    # vindue er ÉT bevis uanset hvor mange runs det summerer; en kontrakt der kræver 5
    # samples af et enkelt aggregat kan aldrig opfyldes, og ville stå som «mangler data»
    # for evigt i stedet for at blive afvist. Loftet håndhæves her, så fejlen er
    # strukturel og synlig ved oprettelsen.
    # Loftet tjekkes kun naar `min_samples` faktisk ER et tal — ellers er den allerede
    # rapporteret som ugyldig i blokken ovenfor, og en tvangskonvertering her ville
    # kaste paa netop den fejl der er beskrevet. Ingen try/except: betingelsen er
    # spurgt, ikke gættet.
    loft = UNIT_SAMPLE_CEILING.get(unit_navn)
    raa_ms = contract.get("min_samples")
    if loft is not None and isinstance(raa_ms, int) and not isinstance(raa_ms, bool) \
            and int(raa_ms) > loft:
        missing.append(f"min_samples {int(raa_ms)} overstiger hvad evidence_unit"
                       f" {unit_navn!r} kan levere (højst {loft} pr. observation)"
                       f" — vælg 'per_run' for at tælle flere")

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


def evidence_of(contract: dict[str, Any]) -> dict[str, Any] | None:
    """Hvad dommen tæller: (enhed, vindue, aggregering). None hvis spec'en er ugyldig.

    Evaluatoren SKAL læse enheden her og ikke antage sin egen: `min_samples` betyder
    «samples i den deklarerede enhed», og en kontrakt uden en deklareret enhed har
    ingen dom at afsige — kun en beregning nogen kan fortolke bagefter.
    """
    unit = EVIDENCE_UNITS.get(str(contract.get("evidence_unit") or ""))
    win = WINDOW_SEMANTICS.get(str(contract.get("window_semantics") or ""))
    agg = AGGREGATIONS.get(str(contract.get("aggregation") or ""))
    if not (unit and win and agg):
        return None
    if not (unit.get("implemented") and win.get("implemented") and agg.get("implemented")):
        return None
    return {
        "unit": str(contract.get("evidence_unit")),
        "window": str(contract.get("window_semantics")),
        "aggregation": str(contract.get("aggregation")),
        "version": EVIDENCE_SPEC_VERSION,
        "source": unit.get("source", ""),
        # Hvor mange enheder grundlaget kan bære: `runs` = antallet af kørsler i vinduet,
        # `window` = præcis 1. Evaluatoren SKAL læse dette og ikke gætte — det er
        # forskellen mellem 288 og 1, og den forskel var hele fejlen.
        "units_from": str(unit.get("units_from") or ""),
    }


def claim_of(contract: dict[str, Any]) -> str:
    """Hvad kontrakttypen må påstå — ikke hvad navnet antyder.

    Målt 4/11-2026: `comparative_latency` læser run-latency (inkl. routing, køtid og
    alle model-kald), men navnet kunne læses som modellens egen hastighed. To domme
    der lyder ens kan derfor svare på to forskellige spørgsmål.
    """
    spec = CONTRACT_TYPES.get(str(contract.get("contract_type") or ""))
    return str((spec or {}).get("claim") or "")


def evidence_signature(contract: dict[str, Any]) -> str:
    """Kort, stabil signatur af evidens-spec'en — bæres i `ground_ref`.

    Uden den kunne to kontrakter med FORSKELLIGE enheder dele evidensidentitet og
    dermed blokere hinandens observationer som «duplikater», selv om de talte hver
    sit grundlag.
    """
    ev = evidence_of(contract)
    if not ev:
        return ""
    return f"{ev['unit']}/{ev['window']}/{ev['aggregation']}/v{ev['version']}"


def supersedes_of(provenance: dict[str, Any] | None) -> list[str]:
    """Hvilke tidligere hypoteser denne undersøgelse ERSTATTER — i rækkefølge.

    Bæres i `provenance_json.supersedes`, ikke i en ny kolonne: det er historie, ikke
    testmetode, og det kræver ingen migration.

    Grunden til at feltet findes (4/11-2026): da evidens-enheden blev påkrævet, blev
    den eneste kontrakt-hypotese `unevaluable` — dens kontrakt deklarerede ingen enhed.
    At oprette en ny er korrekt (en præregistreret kontrakt må ikke ændres stiltiende),
    men uden referencen forsvinder den gamle som en teknisk rest, og Centralen kan ikke
    længere svare på HVORFOR undersøgelsen blev erstattet. En hypotese der dør af en
    utilstrækkelig kontrakt er et fund, ikke skrald.
    """
    if not isinstance(provenance, dict):
        return []
    raw = provenance.get("supersedes")
    if isinstance(raw, str):
        return [raw] if raw else []
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw if x]
    return []


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
    ev = evidence_of(contract)
    ev_txt = f", {ev['unit']}/{ev['window']}/{ev['aggregation']}" if ev else ", UDEN enhed"
    return (f"{subj} {arrow} {comp} på {metric}"
            f" (min {contract.get('min_samples')} samples{ev_txt})")
