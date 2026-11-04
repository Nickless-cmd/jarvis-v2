"""core/services/central_hypothesis_sampler.py

Lag 3 loop-lukning (OBSERVE-siden): TEST aktive hypoteser mod virkeligheden → grounded samples.

Hullet der lukkes: generatoren DANNER hypoteser, men intet TESTEDE dem → de sad på 0/sample_size og
resolvede aldrig. Denne sampler tester hver aktiv causal-hypotese (X→Y) mod event-strømmen med en
ÆGTE baseline-sammenligning (betinget rate vs. baseline-rate) — IKKE ren co-occurrence (undgår at
gen-udlede den graf der fødte hypotesen). Ét grounded sample pr. tick pr. hypotese → resolver via
§8-dødsmekanismen (record_governed_sample → evaluate).

Grounding: events ER virkelighedens optegnelse → source="world_consequence", ground_ref = event-id
(verificerbart anker, ikke en selvrapporteret label). OBSERVE-ONLY: tester + registrerer, HANDLER aldrig.

Testmetoden er sit EGET begreb (`EVALUATORS`), adskilt fra hvor hypotesen opstod. En hypotese
uden en registreret evaluator rapporteres som `unevaluable` — strukturel gæld, ikke manglende
data — i stedet for at forsvinde i et samlet `skipped`-tal.
Alt read-only, self-safe, kaster ALDRIG.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from core.services import central_hypothesis_governance as gov

logger = logging.getLogger(__name__)

_WINDOW = 3000            # events der scannes
_FOLLOW_S = 60            # Y skal følge X inden for dette vindue for at "tælle"
_MIN_EVENTS = 30          # for lidt data → spring over (ingen falsk resolution)
_MIN_X = 5                # for få X-events → ikke nok til en betinget rate
_LIFT = 1.5               # betinget rate skal overstige baseline × dette for "supports"


def _parse(ts: Any) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return t
    except Exception:
        return None


def test_causal_hypothesis(x_fam: str, y_fam: str, *, window: int = _WINDOW,
                           follow_s: int = _FOLLOW_S) -> dict[str, Any] | None:
    """Betinget rate P(Y følger X inden for follow_s) vs. baseline P(Y overhovedet). Self-safe.
    Returnerer None ved for lidt data (ingen falsk resolution)."""
    try:
        from core.eventbus.bus import event_bus
        rows = event_bus.recent(limit=int(window))
    except Exception:
        return None
    evs = []
    for e in rows:
        fam = str(e.get("kind") or "").split(".", 1)[0]
        evs.append((int(e.get("id") or 0), fam, _parse(e.get("created_at"))))
    evs.sort(key=lambda z: z[0])
    n = len(evs)
    if n < _MIN_EVENTS:
        return None
    y_total = sum(1 for _, f, _ in evs if f == y_fam)
    baseline = y_total / n if n else 0.0
    x_events = [(i, t) for i, f, t in evs if f == x_fam]
    if len(x_events) < _MIN_X:
        return None
    y_ts = [t for _, f, t in evs if f == y_fam and t is not None]
    hits = 0
    for _, xt in x_events:
        if xt and any(0 < (yt - xt).total_seconds() <= follow_s for yt in y_ts):
            hits += 1
    conditional = hits / len(x_events)
    supports = (conditional > baseline * _LIFT) and (conditional > 0.05)
    # falsificerer HVIS betinget rate IKKE overstiger baseline (null-hypotesen holder)
    falsifies = conditional <= baseline
    return {"conditional": round(conditional, 4), "baseline": round(baseline, 4),
            "supports": supports, "falsifies": falsifies, "cursor": evs[-1][0],
            "x_events": len(x_events)}


def test_divergence_persistence(family: str) -> dict[str, Any] | None:
    """causal_divergence (§8.4): 'X → BÅDE godt og dårligt udfald'. Test PERSISTENS mod friske data —
    er divergensen der stadig (X fører stadig til begge sider)? Ja → supports; nej (kollapset til én
    side) → falsifies. family = 'parent:good|bad'. Self-safe."""
    try:
        parent, _, rest = str(family).partition(":")
        good, _, bad = rest.partition("|")
        if not (parent and good and bad):
            return None
        from core.services import central_hypothesis_generator as gen
        cands = gen.detect_outcome_divergence_candidates()
        match = next((c for c in cands if c["parent_family"] == parent
                      and c["good"] == good and c["bad"] == bad), None)
        cursor = match["cursor"] if match else 0
        return {"supports": bool(match), "falsifies": not bool(match), "cursor": cursor}
    except Exception:
        return None


def test_stance_persistence(tension_key: str) -> dict[str, Any] | None:
    """stance_divergence (§8.4): 'to organer er gentagne gange uenige'. Test PERSISTENS — gentager
    tension'en sig stadig? Ja → supports; nej (organerne enige nu) → falsifies. Self-safe."""
    try:
        from core.services.central_stance import recurring_tensions
        rec = recurring_tensions(min_count=1)   # findes den overhovedet stadig i vinduet?
        still = any(r.get("key") == str(tension_key) for r in rec)
        cnt = next((r.get("count", 0) for r in rec if r.get("key") == str(tension_key)), 0)
        return {"supports": bool(still), "falsifies": not bool(still), "cursor": int(cnt)}
    except Exception:
        return None


# ── Evaluator-laget ────────────────────────────────────────────────────────────
# TESTMETODE er sit eget begreb, ikke en egenskab ved oprindelsen.
#
# `provenance_json.mechanism` svarer på HVOR hypotesen opstod — hver generator skriver
# sit eget navn der. At bruge det som dispatch-nøgle blandede de to sammen: en hypotese
# født i en drømmeløkke kunne ikke testes af en sekvensanalyse, fordi navnet ikke matchede
# en gren. Målt 4/11-2026: 10 mekanismer, 5 grene, og 18 aktive hypoteser faldt tavst
# igennem `else: res = None` — de blev hentet hvert 30. minut i ugevis uden at nogen
# kunne se hvorfor. Kontraktens kvalitet og dens testbarhed var omvendt korreleret:
# de 14 med den mest eksplicitte kontrakt (`dream_hypothesis_judge`) havde nul samples.
#
# `EVALUATORS` er nøglet på TESTMETODEN. `_ORIGIN_TO_EVALUATOR` er en midlertidig bro,
# fordi kontrakten endnu ikke bærer et `evaluator`-felt. Den dag det findes, skal
# `evaluator_for()` læse det felt FØRST — broen er kun fallback.


def _eval_causal_sequence(prov: dict[str, Any], contract: dict[str, Any] | None = None,
                          hyp_id: str = "") -> dict[str, Any] | None:
    """Betinget rate P(Y følger X) vs. baseline. Kræver family 'X->Y'."""
    fam = str(prov.get("family") or "")
    if "->" not in fam:
        return None
    x_fam, y_fam = fam.split("->", 1)
    return test_causal_hypothesis(x_fam, y_fam)


def _observation_fingerprint(subject: str, comparator: str, *, window: int = 300) -> str:
    """Hash af det FAKTISKE datagrundlag — ikke af hvor mange rækker der indgik.

    Et antal er ikke en identitet. Målt 4/11-2026 havde `ground_ref` formen ``"23:5"``
    (subject-runs : comparator-runs), og det fejler på to måder:

    (a) **Korrigeret måling.** Rettes en `finished_at` (og dermed latency) ændrer
        antallet sig ikke. Ny data, samme nøgle → dedup'en i `record_governed_sample`
        afviser den som duplikat, og Centralen ser ikke at grundlaget flyttede sig.
    (b) **Rullende vindue.** `aggregate_model_outcomes` læser de seneste 300 runs. Når
        de nyeste kommer ind, falder de ældste ud. ``"23:5"`` kan altså dække to helt
        forskellige sæt runs.

    Hashen dækker præcis de felter latency-målet beregnes fra (`run_id`, `started_at`,
    `finished_at`), så identiteten flytter sig hvis og kun hvis grundlaget gør.

    Returnerer "" ved fejl — kalderen falder da tilbage til antals-nøglen frem for en
    tom streng, der ville kollapse alle observationer til én.
    """
    try:
        from core.runtime.db import recent_visible_runs
        parts: list[str] = []
        for r in recent_visible_runs(limit=int(window)):
            if f"{r.get('provider')}/{r.get('model')}" not in (subject, comparator):
                continue
            parts.append(f"{r.get('run_id')}|{r.get('started_at')}|{r.get('finished_at')}")
        parts.sort()
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:12]
    except Exception as exc:
        logger.warning("central_hypothesis_sampler: kunne ikke fingeraftrykke grundlaget: %s", exc)
        return ""


def _ensure_evidence_schema() -> None:
    """Evidens-ledgeren: hvilke run-ID'er har DENNE hypotese allerede talt med?

    Grunden til at den findes (målt 4/11-2026, fjerde runde): `units` blev talt som
    antallet af runs i det RULLENDE vindue — men vinduet genbruges hvert tick. De samme
    23 runs blev derfor talt som 23 enheder igen og igen, og `min_samples: 5` kunne
    opfyldes af én observation målt fem gange. Det var præcis den fejl hele
    undersøgelsen startede med, blot et lag dybere: nu var enheden navngivet korrekt
    (`per_run`) og alligevel ikke uafhængig.

    Invarianten er derfor: **et run-ID må højst bidrage én gang til en given hypoteses
    optjente evidens.** Ledgeren er det eneste sted det kan håndhæves, fordi den er
    den eneste der husker på tværs af ticks.
    """
    try:
        from core.runtime.db import connect
        with connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS central_hypothesis_evidence_runs (
                  hyp_id TEXT NOT NULL,
                  run_id TEXT NOT NULL,
                  first_seen_at TEXT NOT NULL,
                  PRIMARY KEY (hyp_id, run_id)
                );
                CREATE INDEX IF NOT EXISTS idx_cher_hyp
                  ON central_hypothesis_evidence_runs(hyp_id);
                """
            )
            c.commit()
    except Exception as exc:
        logger.warning("central_hypothesis_sampler: kunne ikke sikre evidens-skema: %s", exc)


def _seen_run_ids(hyp_id: str) -> set[str]:
    """De run-ID'er denne hypotese allerede har talt med. Tom mængde ved fejl."""
    if not hyp_id:
        return set()
    try:
        from core.runtime.db import connect
        _ensure_evidence_schema()
        with connect() as c:
            rows = c.execute(
                "SELECT run_id FROM central_hypothesis_evidence_runs WHERE hyp_id=?",
                (str(hyp_id),)).fetchall()
        return {str(r["run_id"]) for r in rows}
    except Exception as exc:
        logger.warning("central_hypothesis_sampler: kunne ikke laese sete runs: %s", exc)
        return set()


def _mark_run_ids(hyp_id: str, run_ids: list[str]) -> int:
    """Registrér run-ID'er som sete for denne hypotese. → antal nye rækker.

    Kaldes EFTER et sample er gemt, ikke inde i evaluatoren: en evaluator der selv
    skriver ville markere runs som sete selv når samplet blev afvist som duplikat —
    og så ville evidensen være tabt uden at nogen havde set den.
    """
    if not hyp_id or not run_ids:
        return 0
    try:
        from core.runtime.db import connect
        _ensure_evidence_schema()
        now = datetime.now(timezone.utc).isoformat()
        with connect() as c:
            before = c.total_changes
            c.executemany(
                "INSERT OR IGNORE INTO central_hypothesis_evidence_runs"
                " (hyp_id, run_id, first_seen_at) VALUES (?,?,?)",
                [(str(hyp_id), str(r), now) for r in run_ids if r])
            c.commit()
            return int(c.total_changes) - int(before)
    except Exception as exc:
        logger.warning("central_hypothesis_sampler: kunne ikke markere runs: %s", exc)
        return 0


def _eval_contract_comparative(contract: dict[str, Any],
                               hyp_id: str = "") -> dict[str, Any] | None:
    """Evaluer en `comparative_latency`-kontrakt. RETNINGEN KOMMER FRA KONTRAKTEN.

    Legacy-stien kodede retningen to steder: i family-konventionen ``"latency:W>L"``
    (W er ALTID vinderen) og i et ``if/else``. En hypotese der påstod det modsatte
    kunne derfor ikke udtrykkes — og to hypoteser med modsatrettede forventninger
    ville få samme dom på samme data. Her læses `expected_relation` og parterne fra
    kontrakten, så A ("X hurtigere end Y") og B ("X langsommere end Y") får modsatte
    domme på PRÆCIS samme observationer.

    Returnerer None når der ikke er data nok — det er operationel tilgængelighed,
    ikke en ugyldig kontrakt.
    """
    from core.services import central_model_meta as mm
    from core.services import central_test_contract as tc
    subject, comparator = tc.subject_of(contract)
    rel = tc.relation_of(contract)
    if not subject or not comparator or rel not in ("less_than", "greater_than"):
        return None
    # ENHEDEN SKAL VÆRE DEKLARERET (4/11-2026). Uden den ved dommen ikke hvad den har
    # talt: `min_samples: 5` kan betyde fem uafhængige observationer eller én målt fem
    # gange. Den primære port er `evaluator_for()`, som giver `unevaluable` (strukturel
    # gæld) — dette er kun så en direkte kalder ikke får en dom på et grundlag
    # kontrakten ikke nævner.
    if tc.evidence_of(contract) is None:
        return None
    ev = tc.evidence_of(contract)
    min_samples = int(contract.get("min_samples") or 0)
    agg = mm.aggregate_model_outcomes()
    sa, ca = agg.get(subject), agg.get(comparator)
    if not sa or not ca:
        return None

    # HVOR MANGE *NYE* ENHEDER BÆRER GRUNDLAGET? (4/11-2026, fjerde runde.)
    #
    # Før blev `units` talt som antallet af runs i det RULLENDE vindue. Men vinduet
    # genbruges hvert tick, så de samme 23 runs blev talt som 23 enheder igen og igen —
    # og `min_samples: 5` kunne opfyldes af én observation målt fem gange. Det var
    # præcis den fejl hele undersøgelsen startede med, nu et lag dybere: enheden var
    # navngivet korrekt (`per_run`) og alligevel ikke uafhængig.
    #
    # Ledgeren husker hvilke run-ID'er hypotesen allerede har talt med. `units` er nu
    # hvor meget grundlaget er VOKSET siden sidst — og et run kan aldrig bidrage to
    # gange til samme hypotese. Målt 4/11-2026: subject fik 0,40 nye runs pr. tick,
    # comparator 3,17, så fem samples over 2,5 timer byggede på grundlag der voksede
    # 1,09x (97,8 % overlap). Med denne port er det umuligt.
    #
    # ID'ERNE KOMMER FRA AGGREGATET, ikke fra en ny læsning: to læsninger kan se to
    # forskellige sæt, og så beskriver nøglen noget andet end dommen bygger på.
    window_ids = list(sa.get("run_ids") or []) + list(ca.get("run_ids") or [])
    if str(ev.get("units_from")) == "runs":
        seen = _seen_run_ids(hyp_id) if hyp_id else set()
        subj_new = [r for r in (sa.get("run_ids") or []) if r not in seen]
        comp_new = [r for r in (ca.get("run_ids") or []) if r not in seen]
        # EN KOMPARATIV OBSERVATION ER ET PAR, IKKE ET ENKELT RUN (4/11-2026, fjerde
        # runde). Du kan ikke lave 130 sammenligninger af 40 mod 90 runs — grundlaget
        # bærer kun så mange NYE sammenligninger som den mindst voksende part. Det er
        # også svaret på hvorfor den levende hypotese sad fast: subject fik 0,40 nye
        # runs pr. tick mens comparator fik 3,17, så der kom ingen nye par — og uden
        # denne grænse ville comparators travlhed alene blive talt som ny evidens om
        # en sammenligning der ikke havde fået ny modpart.
        units = min(len(subj_new), len(comp_new))
        new_ids = subj_new[:units] + comp_new[:units]
        total_units = min(len(sa.get("run_ids") or []), len(ca.get("run_ids") or []))
    else:
        # Et pooled vindue ER ét bevis uanset hvor mange runs det summerer. Det kan
        # derfor kun bidrage én gang — derefter er der ingen ny observation.
        already = bool(hyp_id) and bool(_seen_run_ids(hyp_id))
        new_ids = [] if already else window_ids
        units = 0 if already else 1
        total_units = 1
    if units < min_samples:
        return None

    # ESTIMANDEN FØLGER KONTRAKTENS OPERATION — ikke et navn på en vægtning.
    # `median` er robust over for halen; `mean` er det aritmetiske gennemsnit. Begge
    # vejer hvert run 1, så valget mellem dem er en selvstændig beslutning og ikke en
    # følge af enheden. Før hed valgene `equal_weight` og `pooled`: det første navn
    # beskrev vægtningen og valgte alligevel medianen, og det andet påstod
    # varighedsvægtning mens `aggregate_model_outcomes` tager `statistics.mean`.
    if str(ev.get("aggregation")) == "median":
        s_lat = float(sa.get("latency_median_ms") or 0.0)
        c_lat = float(ca.get("latency_median_ms") or 0.0)
    else:
        s_lat = float(sa.get("latency_ms") or 0.0)
        c_lat = float(ca.get("latency_ms") or 0.0)
    if s_lat <= 0 or c_lat <= 0:
        return None

    # Beslutningsreglen kommer fra kontraktens PINNEDE politik — ikke fra en
    # modul-konstant. Lånte vi `_LATENCY_MARGIN`, kunne en kodeændring et helt andet
    # sted ændre dommen for en hypotese der aldrig blev rørt.
    policy = tc.policy_of(contract)
    if policy is None:
        return None
    support = float(policy["support_ratio"])
    contradict = float(policy["contradict_ratio"])
    # ground_ref identificerer OBSERVATIONEN — og observationen er BEGGE parters
    # aggregerede tilstand, ikke kun subject's. Målt 4/11-2026: `cur` var
    # `sa["samples"]` alene, så når kun comparator fik nye runs ændrede latency-målet
    # sig mens ground_ref stod stille — og dedup'en i `record_governed_sample`
    # (nøgle: source+ground_ref) afviste den nye observation som «duplikat».
    # Centralen kunne altså overse ny evidens om præcis den hypotese den testede.
    #
    # Et ANTAL er stadig ikke en identitet (målt 4/11-2026, anden runde): to forskellige
    # datasæt kan have samme antal runs — en korrigeret `finished_at` ændrer latency uden
    # at ændre antallet, og det rullende 300-runs-vindue kan udskifte grundlaget helt
    # uden at tællerne rykker. Nøglen bærer derfor også en hash af de faktiske rækker.
    s_n, c_n = int(sa.get("samples") or 0), int(ca.get("samples") or 0)
    fp = _observation_fingerprint(subject, comparator)
    # `units` staar FOERST i noeglen: to kontrakter med forskellige enheder kan se samme
    # raekker men besidde et forskelligt antal observationer. Uden tallet kunne en
    # `per_run`-dom (288 enheder) og en `aggregate_window`-dom (1) dele evidensidentitet
    # og blokere hinanden som duplikater.
    cur = f"{units}u/{total_units}u:{s_n}:{c_n}:{fp}" if fp else f"{units}u/{total_units}u:{s_n}:{c_n}"
    # ENHEDEN ER EN DEL AF OBSERVATIONENS IDENTITET (4/11-2026). Dedup'en i
    # `record_governed_sample` nøgler på source+ground_ref. To kontrakter der tæller
    # FORSKELLIGE enheder — fx `per_run` og `per_model_call` — måler hvert sit grundlag
    # på samme data, så uden signaturen ville den ene blokere den andens observation som
    # «duplikat». Centralen ville da tie om netop den kontrast der vender dommen (målt
    # 4/11-2026: 16/16 per kørsel mod 0/16 per kald på samme 16 dage).
    ev_sig = tc.evidence_signature(contract)
    if ev_sig:
        cur = f"{cur}@{ev_sig}"

    # TRE udfald, ikke to: «hurtigere, men ikke markant nok» er ikke et modbevis.
    # Et binært udfald ville stemple al utydelig evidens som modsigelse — samme
    # fejlform som `0/0 → 0.0` og som `stott > mods` uden flertalskrav.
    #
    # `run_ids` følger med dommen: de er det grundlag der netop blev talt, og tick'en
    # markerer dem som sete EFTER samplet er gemt. Markerede evaluatoren selv, ville et
    # afvist sample efterlade runs som «sete» uden at nogen havde set dem.
    base = {"cursor": cur, "run_ids": new_ids, "new_units": units, "total_units": total_units}
    if rel == "less_than":
        if s_lat * support <= c_lat:
            return {**base, "supports": True, "falsifies": False}
        if s_lat > c_lat * contradict:
            return {**base, "supports": False, "falsifies": True}
    else:
        if c_lat * support <= s_lat:
            return {**base, "supports": True, "falsifies": False}
        if c_lat > s_lat * contradict:
            return {**base, "supports": False, "falsifies": True}
    # I båndet mellem contradict- og support-tærsklen: observationen er uafgjort.
    # Den registreres som jordet evidens uden retning — ikke som en dom.
    return {**base, "supports": False, "falsifies": False}


def _eval_model_meta(prov: dict[str, Any], contract: dict[str, Any] | None = None,
                     hyp_id: str = "") -> dict[str, Any] | None:
    """Holder model-dominansen (latency/success) i friske runs?

    Bærer hypotesen en kontrakt, er DEN autoritativ for retningen. Ellers legacy:
    family 'A:B' hvor A er vinderen.
    """
    if contract:
        return _eval_contract_comparative(contract, hyp_id)
    fam = str(prov.get("family") or "")
    if ":" not in fam:
        return None
    from core.services import central_model_meta as mm
    return mm.test_model_meta_persistence(fam)


def _eval_divergence(prov: dict[str, Any], contract: dict[str, Any] | None = None,
                     hyp_id: str = "") -> dict[str, Any] | None:
    """Er divergensen der stadig, eller kollapsede den til én side? Kræver 'parent:good|bad'."""
    fam = str(prov.get("family") or "")
    if ":" not in fam:
        return None
    return test_divergence_persistence(fam)


def _eval_stance(prov: dict[str, Any], contract: dict[str, Any] | None = None,
                 hyp_id: str = "") -> dict[str, Any] | None:
    """Gentager tension'en sig stadig? Kræver family = tension-nøgle."""
    return test_stance_persistence(str(prov.get("family") or ""))


# Hver evaluator DEKLARERER hvilken kontraktform den kan teste, og kravet HÅNDHÆVES i
# `evaluator_for()` — ikke først inde i evaluatoren. Forskellen er ikke kosmetisk: en
# evaluator der selv opdager mismatch returnerer `None`, og `None` betyder «for lidt data
# lige nu». Så blev en PERMANENT utestbar hypotese talt som forbigående og prøvet igen
# hvert 30. minut for evigt. Målt 4/11-2026: 0 aktive ramt (fejlen var latent), men den
# bliver aktiv den dag en generator skriver en family i en anden form.
def _kraever_pil(fam: str) -> bool:
    return "->" in fam


def _kraever_kolon(fam: str) -> bool:
    return ":" in fam


def _kraever_ikke_tom(fam: str) -> bool:
    return bool(fam)


EVALUATORS: dict[str, dict[str, Any]] = {
    "causal_sequence": {"fn": _eval_causal_sequence,
                        "accepts": _kraever_pil,
                        "requires": "family 'X->Y'"},
    "model_meta_persistence": {"fn": _eval_model_meta,
                               "accepts": _kraever_kolon,
                               "requires": "family 'A:B'"},
    "divergence_persistence": {"fn": _eval_divergence,
                               "accepts": _kraever_kolon,
                               "requires": "family 'parent:good|bad'"},
    "stance_persistence": {"fn": _eval_stance,
                           "accepts": _kraever_ikke_tom,
                           "requires": "family = tension-nøgle"},
}

_ORIGIN_TO_EVALUATOR: dict[str, str] = {
    "causal_edges": "causal_sequence",
    "prediction_error": "causal_sequence",
    "model_meta": "model_meta_persistence",
    "causal_divergence": "divergence_persistence",
    "stance_divergence": "stance_persistence",
}


def evaluator_for(prov: dict[str, Any],
                  contract: dict[str, Any] | None = None) -> tuple[str | None, str | None, str]:
    """Hvilken evaluator kan teste DENNE hypotese? → (navn, grund, kilde).

    `kilde` er `"contract"` når hypotesen bærer en VALIDERET testkontrakt, og `"legacy"`
    når den blev koblet på via broen fra sin oprindelse. Skelnen er ikke pynt: målt
    4/11-2026 havde 0 af 505 aktive hypoteser en kontrakt, så broen var den operative
    sandhed for hele populationen — og Centralen måtte ikke rapportere det som om alle
    hypoteser var valideret.

    En kontrakt der IKKE validerer falder ikke tilbage til broen: så ville en ugyldig
    kontrakt se ud som en gyldig legacy-kobling. Den rapporteres som strukturel gæld.

    Kravet i `EVALUATORS[name]["accepts"]` håndhæves for legacy-stien, så en
    kontrakt-evaluator-mismatch bliver strukturel gæld med navn i stedet for at
    forsvinde som «mangler data».
    """
    if contract:
        from core.services import central_test_contract as tc
        cok, cmissing = tc.validate(contract)
        if not cok:
            return (None, f"test_contract er ugyldig: {'; '.join(cmissing)}", "contract")
        name = tc.evaluator_of(contract)
        if name not in EVALUATORS:
            return (None, f"evaluator {name!r} er ikke registreret", "contract")
        return name, None, "contract"

    explicit = str(prov.get("evaluator") or "").strip()
    origin = str(prov.get("mechanism") or "")
    name = explicit or _ORIGIN_TO_EVALUATOR.get(origin, "")
    # Et NAVN i provenance er ikke en kontrakt. `explicit` betyder at hypotesen selv
    # pegede på en evaluator, men uden en valideret testkontrakt — den er derfor ikke
    # mere verificeret end broen, bare mere præcis om hvad den peger på.
    kilde = "explicit" if explicit else "legacy"
    if not name:
        return None, f"ingen evaluator registreret for oprindelse {origin!r}", kilde
    if name not in EVALUATORS:
        return None, f"evaluator {name!r} er ikke registreret", kilde
    accepts = EVALUATORS[name].get("accepts")
    fam = str(prov.get("family") or "")
    if callable(accepts) and not accepts(fam):
        return (None,
                f"evaluator {name!r} kraever {EVALUATORS[name].get('requires')!r},"
                f" men family er {fam!r}", kilde)
    return name, None, kilde


def _parse_contract(raw: Any) -> dict[str, Any] | None:
    """Læs `test_contract_json`. Ulaeselig → None med en loglinje (aldrig tavst)."""
    if not raw:
        return None
    try:
        c = json.loads(str(raw))
        return c if isinstance(c, dict) else None
    except Exception as exc:
        logger.warning("central_hypothesis_sampler: ulaeselig test_contract: %s", exc)
        return None


def list_unevaluable_active() -> list[dict[str, str]]:
    """Aktive hypoteser der ALDRIG kan testes med den nuværende evaluator-registry.

    Adskilt fra hypoteser der blot mangler data lige nu. Self-safe — kaster ALDRIG.
    """
    out: list[dict[str, str]] = []
    try:
        from core.runtime.db import connect
        from core.services import central_hypothesis_generator as gen
        gen.ensure_schema()      # migreringen af test_contract_json skal vaere sket foer laesning
        with connect() as c:
            rows = c.execute(
                "SELECT hyp_id, provenance_json, test_contract_json, created_at, ttl_seconds "
                "FROM central_hypotheses WHERE status='active'").fetchall()
        now = datetime.now(timezone.utc)
        for r in rows:
            if gov.is_expired(r["created_at"], r["ttl_seconds"], now=now):
                continue
            prov = json.loads(r["provenance_json"] or "{}")
            name, why, kilde = evaluator_for(prov, _parse_contract(r["test_contract_json"]))
            if name is None:
                out.append({"hyp_id": str(r["hyp_id"]), "reason": str(why),
                            "origin": str(prov.get("mechanism") or ""),
                            "kilde": kilde})
    except Exception as exc:  # self-safe: en læsefejl må ikke vælte cadence-tick'et
        logger.warning("central_hypothesis_sampler: kunne ikke liste utestbare: %s", exc)
        return out
    return out


def evaluator_provenance() -> dict[str, int]:
    """Hvor mange aktive hypoteser er koblet på via KONTRAKT vs. via LEGACY-broen?

    Broen er en overgangsløsning, ikke en garanti: den kobler en testmetode på ud fra
    hvor hypotesen blev født. Så længe den bærer næsten hele populationen, må Centralen
    ikke kunne rapportere at «alle hypoteser har en evaluator» som om det var valideret.
    Målt 4/11-2026: 529 aktive havde en evaluator — fordelingen stod ikke nogen steder.
    """
    ud: dict[str, int] = {"contract": 0, "explicit": 0, "legacy": 0, "unevaluable": 0}
    try:
        from core.runtime.db import connect
        from core.services import central_hypothesis_generator as gen
        gen.ensure_schema()      # migreringen af test_contract_json skal vaere sket foer laesning
        with connect() as c:
            rows = c.execute(
                "SELECT provenance_json, test_contract_json, created_at, ttl_seconds "
                "FROM central_hypotheses WHERE status='active'").fetchall()
        now = datetime.now(timezone.utc)
        for r in rows:
            if gov.is_expired(r["created_at"], r["ttl_seconds"], now=now):
                continue
            prov = json.loads(r["provenance_json"] or "{}")
            name, _why, kilde = evaluator_for(prov, _parse_contract(r["test_contract_json"]))
            ud["unevaluable" if name is None else kilde] = (
                ud.get("unevaluable" if name is None else kilde, 0) + 1)
    except Exception as exc:
        logger.warning("central_hypothesis_sampler: kunne ikke tælle evaluator-kilder: %s", exc)
    return ud


def run_hypothesis_sampler_tick(*, trigger: str = "cadence",
                                last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: test hver aktiv CAUSAL-hypotese mod event-strømmen, registrér ét grounded
    sample. OBSERVE-ONLY. Self-safe."""
    from core.services import central_hypothesis_generator as gen
    gen.ensure_schema()
    tested, supported, contradicted = 0, 0, 0
    # `skipped` var ÉT tal for to helt forskellige ting: hypoteser der ALDRIG kan testes
    # (ingen evaluator — strukturel gæld) og hypoteser der ikke KUNNE måles lige nu
    # (for lidt data — forbigående). Målt 4/11-2026: 18 aktive lå i den første gruppe.
    unevaluable: dict[str, list[str]] = {}
    no_data: list[str] = []
    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT hyp_id, provenance_json, test_contract_json, created_at, ttl_seconds "
                "FROM central_hypotheses WHERE status='active'").fetchall()
        # 30/10-2026: TTL-filteret manglede. Målt i den levende base: 478 af 872 aktive
        # havde passeret deres frist, og sampler'en brugte kræfter på dem hvert 30. minut.
        # Filtreringen sker i Python via SAMME `is_expired` som dødsdommen i evaluate()
        # bruger — `created_at` er ISO med tidszone-offset, som SQLites strftime ikke
        # læser ensartet, så et SQL-filter ville kunne svigte tavst.
        _now = datetime.now(timezone.utc)
        active = [
            (str(r["hyp_id"]), json.loads(r["provenance_json"] or "{}"),
             _parse_contract(r["test_contract_json"]))
            for r in rows
            if not gov.is_expired(r["created_at"], r["ttl_seconds"], now=_now)
        ]
    except Exception:
        active = []
    for hyp_id, prov, contract in active:
        name, why, _kilde = evaluator_for(prov, contract)
        if name is None:
            # Strukturel gæld: ingen evaluator kan teste denne hypotese — heller ikke selv om
            # der kom data nok. Den blev før talt som «skipped» sammen med dem der blot
            # manglede data, og senere som «no_data» når evaluatoren selv afviste formen.
            unevaluable.setdefault(str(why), []).append(hyp_id)
            continue
        res = EVALUATORS[name]["fn"](prov, contract, hyp_id)
        if res is None:
            # Evaluatoren kunne ikke måle NU (for lidt data, eller family matcher ikke det
            # den kræver). Forbigående — ikke strukturelt.
            no_data.append(hyp_id)
            continue
        tested += 1
        # triggered_by='world': frisk verdens-observation, IKKE selv-udløst (circular-korrekt, §8.5).
        rec = gen.record_governed_sample(
            hyp_id, supports=bool(res["supports"]), falsifies=bool(res["falsifies"]),
            source="world_consequence", ground_ref=str(res["cursor"]),
            triggered_by="world")
        # EVIDENS-LEDGEREN (4/11-2026, fjerde runde). Markeringen sker EFTER samplet er
        # gemt — ikke inde i evaluatoren. Markerede den selv, ville et sample der blev
        # afvist alligevel efterlade runs som «sete», og så var evidensen tabt uden at
        # nogen havde set den. `noop` tælles med: et duplikat betyder netop at grundlaget
        # allerede er talt, og så må det ikke tælles igen.
        if str(rec.get("status") or "") in ("ok", "noop"):
            _mark_run_ids(hyp_id, list(res.get("run_ids") or []))
        if res["supports"]:
            supported += 1
        elif res["falsifies"]:
            contradicted += 1
    # egress-fri observe (kun tællere)
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "hypothesis_sampling", value=float(tested),
                       meta={"tested": tested, "supported": supported,
                             "contradicted": contradicted,
                             "unevaluable": sum(len(v) for v in unevaluable.values()),
                             "no_data": len(no_data)})
    except Exception:
        pass
    return {"status": "ok", "tested": tested, "supported": supported,
            "contradicted": contradicted,
            "unevaluable": unevaluable, "no_data": no_data}


def register_hypothesis_sampler_producer() -> None:
    """Registrér samleren som cadence-producer (~hvert 30 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_hypothesis_sampler",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=run_hypothesis_sampler_tick,
        priority=7,
    ))
