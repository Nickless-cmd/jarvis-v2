"""Gut Engine — intuition and calibration tracking.

Before execution, Jarvis generates a "hunch" (proceed/caution).
After execution, the outcome is compared to the hunch.
Over time, calibration score reveals how reliable Jarvis' gut feeling is.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_cognitive_gut_state,
    update_cognitive_gut_state,
)

logger = logging.getLogger(__name__)


def _gut_bias() -> float:
    """Læs Lag-4-bias'en (0.0 = shadow/ingen ændring). Én sætning, så kaldestedets try er
    smalt nok til at fange netop den fejl det skal — ikke alt hvad der kommer bagefter."""
    try:
        from core.services.central_adaptation import get_gut_bias
        return float(get_gut_bias())
    except Exception:  # uden Lag-4-signal er bias 0 — hunch-stien er uændret
        return 0.0


def _task_mapping(task_description: str) -> dict[str, object]:
    """Opgave → værktøjs-risiko. Kaster ALDRIG: en fejl her må ikke ændre en hunch.

    Svarer et tomt `unknown`-resultat hvis modulet mangler eller fejler — det er den
    sikre side, fordi delta 0,0 betyder «uændret adfærd», ikke «ufarlig opgave».
    """
    try:
        from core.services.task_tool_mapping import map_task_to_tools
        return map_task_to_tools(task_description)
    except Exception:
        return {"tools": [], "tier": "unknown", "signals": [],
                "method": "none", "confidence_delta": 0.0}


# ── Fejl-signalet: RATE, ikke absolut antal (3/11-2026) ──────────────────────
#
# Målt 3/11 kl. 18:44 UTC: 23 `blocked` mod 280 ok/completed i døgnet = **7,6 % fejlrate**.
# Den gamle regel lød `recent_error_count > 3` — et absolut tal uden grundlag. I et aktivt
# system passeres 3 fejl HVER dag, så betingelsen var altid sand, og `caution` var derfor
# ikke et signal men en konstant. Målt konsekvens: seks vidt forskellige opgaver (migration,
# deploy, logfil-læsning, testfil, analyse, volapyk) fik ALLE `caution` og conf 0,59 — og
# med `mode=on` ville gaten afvise 100 % af alle autonome runs. Tærsklen (A5, 0,30) var
# aldrig bindende; retningen var.
#
# En betingelse der altid er opfyldt kan ikke skelne. Rate-reglen kræver desuden et
# minimumsgrundlag, så to fejl af to forsøg ikke læses som 100 %.
#
# GRÆNSE, målt og IKKE løst her: 18 af de 23 `blocked` er
# `discord-no-active-dm-and-webchat-fallback-blocked` — en KANAL-fejl, ikke en
# dømmekraft-fejl. Fejlraten måler derfor delvist om Discord svarer. Det er en egen sag.
_ERROR_RATE_CAUTION = 0.20
_MIN_SAMPLE_FOR_RATE = 20

# Evidens-port (12/11-2026): grundlaget for at en `caution` må BLOKKERE et run.
# Målt 12/11: 26 caution-advarsler, 1 korrekt (3,8 %) — advarslen var ren støj fordi
# runs lykkes ~99,7 % af tiden. Tærsklerne er sat så et lille, skævt sample ikke kan
# låse gaten: under 20 events er præcisionen ikke et grundlag, og først når flertallet
# af advarslerne faktisk varsler fejl, har den positiv forventet værdi.
_EVIDENS_MIN_CAUTION = 20
_EVIDENS_MIN_PRECISION = 0.5
_EVIDENS_TTL_S = 300.0
_EVIDENS_CACHE: dict[str, object] = {"at": 0.0, "value": None}


def derive_gut_signal(
    *,
    task_description: str,
    confidence: float = 0.5,
    recent_error_count: int = 0,
    recent_success_count: int = 0,
) -> dict[str, object]:
    """Generate a gut-feel hunch about a task.

    Definition B (3/11-2026, Bjørn): `confidence` betyder «hvor sikker er jeg på den
    RETNING jeg peger i» — ikke «hvor sandsynligt er det at opgaven lykkes».

    Før 3/11 var de to blandet sammen: `hunch_confidence` var 0,5 for proceed og 0,6–0,7
    for caution, altså signalSTYRKE, men `gut_gate` læste tallet som tilladelsesGRAD.
    Resultatet var at en advarsel per konstruktion slap lettere igennem end en tilladelse
    (målt: caution 0,70 mod proceed 0,50 uden bias). Med definition B bærer `hunch`
    retningen og `confidence` styrken, og gaten SKAL se begge — se `gut_gate`.

    A7 (3/11-2026): `confidence` er nu OPGAVESPECIFIK. Indtil i dag blev
    `task_description` kun klippet til en label (`task_hint`), så tre vidt forskellige
    opgaver fik identisk rå 0,5. `task_tool_mapping` klassificerer opgaven som
    læsende/skrivende/irreversibel og justerer den RÅ confidence, før hunch-grenene
    læses — så en migration eller en sletning lettere ender i `caution`.
    """
    gut_state = get_cognitive_gut_state()
    calibration = float(gut_state.get("calibration_score", 0.5)) if gut_state else 0.5

    # A7: opgavens risiko ind i den RÅ confidence — ikke bagefter, fordi grenene nedenfor
    # læser netop dette tal. Mappingen kaster aldrig og svarer `unknown`/0,0 når teksten
    # intet signal bærer, så en uklar opgave opfører sig som før.
    task_map = _task_mapping(task_description)
    if task_map.get("confidence_delta"):
        confidence = min(1.0, max(0.0, confidence + float(task_map["confidence_delta"])))

    # Heuristic gut signal. `hunch_confidence` = styrken af den retning vi peger i.
    # Fejlraten beregnes ALTID, så den kan læses i signalet — også når den ikke flytter
    # retningen. Ellers kan ingen efterprøve hvorfor `caution` udløste eller ikke gjorde.
    _grundlag = recent_error_count + recent_success_count
    error_rate = (recent_error_count / _grundlag) if _grundlag else 0.0
    if (
        _grundlag >= _MIN_SAMPLE_FOR_RATE
        and error_rate > _ERROR_RATE_CAUTION
        and confidence < 0.6
    ):
        hunch = "caution"
        hunch_confidence = 0.7
    elif recent_success_count > 5 and confidence > 0.7:
        hunch = "proceed"
        hunch_confidence = 0.8
    elif confidence < 0.3:
        hunch = "caution"
        hunch_confidence = 0.6
    else:
        hunch = "proceed"
        hunch_confidence = 0.5

    # A7 (3/11-2026): en irreversibel opgave er ALDRIG et «proceed» på global statistik.
    # Målt før denne gren fandtes: med nul fejl i døgnet blev «kritisk migration af
    # produktionsdatabase» klassificeret som `proceed` — den globale fejlrate afgjorde
    # retningen, ikke opgaven. En sletning, en udgivelse eller en migration kan ikke
    # rulles tilbage, så retningen skal være caution uanset hvor sund driften ser ud.
    # (Dette er en RETNING, ikke en styrke: tærsklen og A5 er stadig urørt.)
    if task_map.get("tier") == "irreversible":
        hunch = "caution"
        hunch_confidence = max(hunch_confidence, 0.7)

    # Weight by calibration — if gut has been wrong, reduce confidence
    adjusted_confidence = hunch_confidence * calibration
    # A7: BEVIDST INGEN kontinuert skalering af styrken efter opgavens rå confidence.
    # Jeg prøvede `adjusted_confidence * (confidence / 0.5)` og målte den: den gav fire
    # opgaver fire forskellige tal — men tallene var OPDIGTEDE. Der findes ingen data der
    # siger at en læseopgave er 0,66 sikker og en skriveopgave 0,52; det var min
    # multiplikator der opfandt dem, og ved rå 0,1 gjorde den styrken næsten nul.
    # Opgavespecificiteten bæres derfor af RETNINGEN (se `irreversible`-grenen ovenfor) og
    # af delta'et på den RÅ confidence, som flytter grenvalget ved 0,6 og 0,3 — ikke af en
    # skala jeg ikke kan forsvare. Det er den ærlige grænse: jeg ved OM opgaven er farlig,
    # ikke hvor farlig den er på en kontinuert skala.
    # Bias-FRI baseline (12/10-2026): bevares FØR Lag-4 lægges oveni, så counterfactual-
    # tællingen kan svare på hvad gaten VILLE afgøre uden den lærte bias. Uden dette led
    # findes svaret ikke — gaten ser kun den justerede værdi og kan ikke sammenlignes med sig selv.
    confidence_no_bias = adjusted_confidence

    # Lag 4 (governed, shadow-gated): et lært proceed-bias justerer tilbøjeligheden. Default 0.0
    # (shadow/ingen ændring); kun ≠0 når Centralen HAR lært + Bjørn har flippet live-switch.
    #
    # 12/10-2026 — bias'en kan nu TRÆKKE FRA (Bjørn: «lad bias kunne trække fra»). Før klippede
    # begge grene til `max(0.0, ±bias)`, så justeringen ALTID var ≥ 0: musklen kunne kun HÆVE
    # confidence og var strukturelt ude af stand til at afvise noget. Det — ikke manglende data —
    # er grunden til at gaten aldrig efterlod et withhold-spor. Nu er bias'en et ægte FORTEGN,
    # symmetrisk om 0: positiv = maven har fortjent tillid (proceed løftes, caution sænkes),
    # negativ = maven har taget fejl (proceed sænkes, caution løftes). Først nu kan et proceed
    # ende UNDER tærsklen — og dermed stoppes.
    bias = _gut_bias()
    if bias:
        if hunch == "proceed":
            adjusted_confidence = adjusted_confidence + bias
        elif hunch == "caution":
            adjusted_confidence = adjusted_confidence - bias
        adjusted_confidence = min(1.0, max(0.0, adjusted_confidence))

    return {
        "hunch": hunch,
        "confidence": round(adjusted_confidence, 2),
        "confidence_no_bias": round(confidence_no_bias, 2),
        "calibration_score": calibration,
        "raw_confidence": confidence,
        "task_hint": task_description[:80],
        # A7 (3/11-2026): de fire felter gør det efterprøveligt HVORFOR confidence er
        # hvad den er. Uden dem ville en opgavespecifik justering være usynlig i ledgeren
        # — og så kunne ingen se om mappingen faktisk klassificerede opgaven rigtigt.
        "task_tier": task_map.get("tier"),
        "task_signals": list(task_map.get("signals") or []),
        "task_method": task_map.get("method"),
        "task_confidence_delta": task_map.get("confidence_delta"),
        # 3/11-2026: fejlraten er gjort synlig. `caution` udløses af RATEN (over 20 % ved
        # mindst 20 ticks), ikke af et absolut antal — og uden tallet i signalet kan ingen
        # se om retningen blev valgt på et sundt eller et skrøbeligt grundlag.
        "recent_error_rate": round(error_rate, 3),
        "recent_sample_size": _grundlag,
    }


# ── Gut-gate: den FØRSTE ægte forbruger af adjusted_confidence (m. Centralens bias) ──
#
# Baggrund (audit 2026-07-03): derive_gut_signal() beregnede en `confidence`
# (hunch_confidence * calibration + central_gut_proceed_bias), men INGEN læste tallet —
# gut_calibration._on_started gemte kun `hunch`-strengen. Dermed var Centralens adaptive
# læring (central_adaptation.get_gut_bias) uden ægte forbruger: "governed-live" var tomt
# teater. gut_gate() lukker det hul minimalt og ærligt.
#
# Reversibelt runtime-flag `central_gut_consumer_mode` (default "off"):
#   off    = nuværende adfærd — confidence ignoreres fuldstændig (returnerer altid True,
#            observerer intet). NUL adfærdsændring. Dette er default.
#   shadow = beregn HVAD gaten VILLE afgøre + observér egress-frit (record_private),
#            men returnér stadig True (handl ikke). Til dataindsamling før live.
#   on      = lad confidence faktisk gate: returnér confidence >= threshold.
#
# Tærsklen læses fra `central_gut_gate_threshold` (default 0.30) — bevidst lav, så kun
# meget svage hunches (fx caution ved lav rå-confidence, eller bias trukket kraftigt ned)
# gater. Bevar altid hunch-stien uændret; dette er et SEPARAT confidence-lag.

_CONSUMER_MODE_KEY = "central_gut_consumer_mode"     # off | shadow | on (default off)
_GATE_THRESHOLD_KEY = "central_gut_gate_threshold"   # float (default 0.30)
_DEFAULT_THRESHOLD = 0.30


def _consumer_mode() -> str:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_CONSUMER_MODE_KEY, "off")
        mode = str(v or "off").strip().lower()
        return mode if mode in ("off", "shadow", "on") else "off"
    except Exception:  # bookkeeping må ALDRIG påvirke beslutningen
        return "off"


def _gate_threshold() -> float:
    try:
        from core.runtime.db_core import get_runtime_state_value
        return float(get_runtime_state_value(_GATE_THRESHOLD_KEY, _DEFAULT_THRESHOLD))
    except Exception:  # bookkeeping må ALDRIG påvirke beslutningen
        return _DEFAULT_THRESHOLD


# Counterfactual-tælling (12/10-2026). To nerves i den EKSISTERENDE ledger — ingen ny tabel.
_COUNTERFACTUAL_NERVE = "gut_gate"
_COUNTERFACTUAL_NERVE_NO_BIAS = "gut_gate_uden_bias"

# A6b (3/11-2026): `mode` var ikke en dimension i ledgerens nøgle. Den levede kun som fri
# tekst i `last_reason`, som overskrives ved hvert nyt kald — så en shadow-simuleret
# afvisning blev smeltet sammen med en håndhævet, og fladen talte begge som «stoppet».
# Nøglen er `(nerve, decision)`, så mode bæres nu af NERVE-NAVNET: en shadow-afgørelse
# tælles på sin egen nerve og kan trækkes fra uden at røre den fælles ledger eller skemaet.
# (At gøre mode til en rigtig nøgle-dimension ville kræve en migrering af
# `gate_verdict_counts`; nerve-navnet løser samme problem reversibelt.)
_COUNTERFACTUAL_NERVE_SHADOW = "gut_gate_shadow"
_COUNTERFACTUAL_NERVE_NO_BIAS_SHADOW = "gut_gate_uden_bias_shadow"

_INFLUENCE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS gut_influence_ledger (
        nerve TEXT PRIMARY KEY,
        events INTEGER,
        delta_sum REAL,
        delta_abs_sum REAL,
        influenced INTEGER,
        crossings INTEGER,
        last_ts TEXT
    )
"""

# A3 (3/11-2026): en afvisning er en BESLUTNING, ikke et udfald.
#
# Før endte den kun i en egress-fri trace (`record_private("gut_gate_withhold")`), som
# kalibreringen ikke læser. Den tælles nu i den samme ledger som de øvrige gate-afgørelser
# — men på sin EGEN nerve, så den aldrig kan forveksles med et evalueret udfald.
#
# Den kan ALDRIG kalibrere maven: et afvist run har intet observeret udfald, og vi ved
# ikke om det ville være lykkedes. Kun forudsigelse + udfald tilsammen kan det. En
# registreret afvisning er derfor et datapunkt om gatens ADFÆRD — ikke et bevis for at
# afvisningen var rigtig.
_WITHHELD_NERVE = "gut_gate_withheld"


def _safe_record(ledger: object, nerve: str, decision: str, reason: str) -> None:
    """Ét ledger-kald, indkapslet. En tæller må ALDRIG kunne blokere gaten."""
    try:
        ledger.record(nerve, "cognition", decision, reason=reason)
    except Exception:  # en tæller må ALDRIG kunne blokere gaten — fejler åbent
        return


def _record_gut_influence(nerve: str, delta: float, crossed: bool) -> None:
    """Persistér ét confidence-delta. Bookkeeping må ALDRIG kaste ind i gate-stien."""
    try:
        from core.runtime.db_core import connect

        with connect() as conn:
            # Samme DB-kald som skrivningen: uvicorn kan holde live-DB'en kortvarigt låst.
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute(_INFLUENCE_TABLE_SQL)
            conn.execute(
                """
                INSERT INTO gut_influence_ledger
                    (nerve, events, delta_sum, delta_abs_sum, influenced, crossings, last_ts)
                VALUES (?, 1, ?, ?, ?, ?, ?)
                ON CONFLICT(nerve) DO UPDATE SET
                    events = events + 1,
                    delta_sum = delta_sum + excluded.delta_sum,
                    delta_abs_sum = delta_abs_sum + excluded.delta_abs_sum,
                    influenced = influenced + excluded.influenced,
                    crossings = crossings + excluded.crossings,
                    last_ts = excluded.last_ts
                """,
                (
                    nerve,
                    delta,
                    abs(delta),
                    int(abs(delta) > 1e-9),
                    int(crossed),
                    datetime.now(UTC).isoformat(),
                ),
            )
    except Exception:
        return


def _read_gut_influence(nerve: str) -> dict[str, int | float | str]:
    """Læs påvirkningsrækken selv-sikkert; en manglende tabel svarer til nul data."""
    empty: dict[str, int | float | str] = {
        "events": 0,
        "delta_sum": 0.0,
        "delta_abs_sum": 0.0,
        "influenced": 0,
        "crossings": 0,
        "last_ts": "",
    }
    try:
        from core.runtime.db_core import connect

        with connect() as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute(_INFLUENCE_TABLE_SQL)
            row = conn.execute(
                """SELECT events, delta_sum, delta_abs_sum, influenced, crossings, last_ts
                   FROM gut_influence_ledger WHERE nerve = ?""",
                (nerve,),
            ).fetchone()
        if not row:
            return empty
        return {
            "events": int(row[0] or 0),
            "delta_sum": float(row[1] or 0.0),
            "delta_abs_sum": float(row[2] or 0.0),
            "influenced": int(row[3] or 0),
            "crossings": int(row[4] or 0),
            "last_ts": str(row[5] or ""),
        }
    except Exception:
        return empty


def _record_counterfactual(
    conf: float,
    would_pass: bool,
    no_bias_confidence: float | None,
    threshold: float,
    mode: str,
    hunch: str = "proceed",
) -> None:
    """Optæl gatens afgørelse MED og UDEN den lærte bias. Ren statistik — kaster ALDRIG.

    Bruger de kanoniske decision-værdier (green = passerede, red = afvist), så
    `gate_verdict_ledger.summary()` rapporterer withhold-raten direkte via non_green_pct.
    Skrivningen er en in-memory tæller (ingen DB i hot-pathen); ledgeren flusher på cadence.
    """
    try:
        from core.services import gate_verdict_ledger as ledger
    except Exception:  # ledgeren er valgfri — uden den tæller vi bare ikke
        return

    shadow = str(mode or "").strip().lower() == "shadow"
    nerve = _COUNTERFACTUAL_NERVE_SHADOW if shadow else _COUNTERFACTUAL_NERVE
    nerve_nb = _COUNTERFACTUAL_NERVE_NO_BIAS_SHADOW if shadow else _COUNTERFACTUAL_NERVE_NO_BIAS

    _safe_record(ledger, nerve,
                 "green" if would_pass else "red",
                 f"mode={mode} conf={conf:.3f} thr={threshold:.2f}")
    if no_bias_confidence is None:
        return
    try:
        nb = float(no_bias_confidence)
    except (TypeError, ValueError):  # utolkbar baseline → kun med-bias tælles
        return
    # Definition B: bias flytter kun STYRKEN, aldrig retningen. No-bias-siden skal derfor
    # bruge samme retningsregel som den faktiske afgørelse — ellers rapporterer ledgeren
    # at erfaringen flyttede en beslutning, når det var retningsreglen der gjorde det.
    nb_would_pass = str(hunch or "proceed").strip().lower() == "proceed" and nb >= threshold
    _safe_record(ledger, nerve_nb,
                 "green" if nb_would_pass else "red",
                 f"hunch={str(hunch or 'proceed').strip().lower()} conf={nb:.3f} thr={threshold:.2f}")
    # A6b-stil: shadow har egne verdict-nerver og blandes heller ikke ind i den håndhævede
    # påvirkningsrække. Skrive-helperen er selv-sikker, så DB-lås/fejl aldrig rammer gaten.
    if not shadow:
        _record_gut_influence(_COUNTERFACTUAL_NERVE, conf - nb, would_pass != nb_would_pass)


def gut_gate(
    proceed_confidence: float,
    *,
    context: str = "",
    no_bias_confidence: float | None = None,
    hunch: str | None = None,
) -> bool:
    """Beslut om et proceed-valg må fortsætte, gated på gut-confidence.

    Dette er det ægte forbrugs-punkt for `adjusted_confidence` (som bærer Centralens
    lærte bias). Self-safe: kaster ALDRIG, fejler ALTID open (returnér True) — en fejl
    her må aldrig blokere et autonomt run.

    Definition B (3/11-2026): `confidence` er STYRKEN af den retning `hunch` peger i.
    Derfor er tilladelse en to-delt betingelse: retningen skal være "proceed" OG styrken
    skal være ≥ tærsklen. Uden `hunch` (bagudkompatibelt kald) antages "proceed", så
    gamle kaldesteder ikke ændrer adfærd — men de kan heller ikke længere slippe en
    advarsel igennem ved høj styrke, fordi de ikke sender en advarsel.

    off    → True (confidence ignoreres, dagens adfærd)
    shadow → beregn would-gate + observér, men returnér True (handl ikke)
    on      → returnér (hunch == "proceed" AND confidence >= threshold)
    """
    try:
        conf = float(proceed_confidence)
    except Exception:  # bookkeeping må ALDRIG påvirke beslutningen
        return True  # kan ikke tolke → fail open

    mode = _consumer_mode()
    if mode == "off":
        return True

    retning = str(hunch or "proceed").strip().lower()
    threshold = _gate_threshold()
    # Retningen er en DEL af afgørelsen: en advarsel kan aldrig passere på høj styrke.
    would_pass = retning == "proceed" and conf >= threshold

    # Counterfactual-tælling (12/10-2026): registrér BÅDE den faktiske afgørelse (med den
    # lærte bias) og hvad gaten ville have afgjort UDEN den. Forskellen er det eneste der
    # kan svare på om erfaringen faktisk flytter en beslutning — uden den findes svaret ikke.
    # NB (11/11-2026): bias'en er SYMMETRISK om 0 siden derive_gut_signal (linje ~155), ikke
    # positiv-only. Den kan altså i princippet efterlade et withhold-spor. Men dette tal
    # tæller kun GRÆNSEKRYDS; påvirkning under tærsklen giver delta=0 (se build_gut_surface).
    _record_counterfactual(conf, would_pass, no_bias_confidence, threshold, mode, retning)

    # Egress-fri observation (shadow OG on) — kun skalarer, aldrig egress.
    try:
        from core.services.central_private_observe import record_private
        record_private(
            "cognition", "gut_gate",
            value=float(conf),
            meta={
                "mode": mode,
                "confidence": round(conf, 3),
                "threshold": round(threshold, 3),
                "hunch": retning,
                "would_pass": would_pass,
                "context": str(context)[:40],
            },
            reason="gut_gate",
        )
    except Exception:  # ledgeren er valgfri — uden den tæller vi bare ikke
        pass

    if mode == "on":
        return would_pass
    # shadow → beregnet, observeret, men handler ikke
    return True


# ── Pre-flight gate (12/10-2026, Bjørn: «tag gut gate og lad bias kunne trække fra») ──
#
# Gaten lå FØR på `runtime.autonomous_run_started` — et event der fyrer EFTER runnet er
# begyndt. Koden sagde det selv: «vi ANNULLERER ikke run'et her (run er allerede startet —
# vinduet er observations-gate, ikke en pre-flight veto)». Den kunne derfor aldrig stoppe
# noget, uanset hvor lav confidence var. Her er beslutningspunktet: bliver runnet afvist,
# fødes det ikke — `start_autonomous_run` og `start_autonomous_stream_run` kalder denne FØR
# de bygger run-objektet.
#
# BAGKANT (fordi en negativ bias nu kan blokere): højst _MAX_BLOK_PER_TIME blokeringer pr.
# rullende time. Er budgettet brugt, slipper runnet igennem og overkørslen tælles særskilt
# på sin egen nerve. En fejlkalibreret muskel må kunne gøre arbejdet mere forsigtigt — den
# må ALDRIG kunne standse det.

_MAX_BLOK_PER_TIME = 3
_BLOK_VINDUE_SEKUNDER = 3600
_BACKSTOP_NERVE = "gut_gate_backstop"
_blok_tider: list[float] = []


def _blok_budget_brugt(no: float | None = None) -> bool:
    """True når blokerings-budgettet for den rullende time er brugt. Ren — kaster ikke."""
    naa = no if no is not None else time.time()
    graense = naa - _BLOK_VINDUE_SEKUNDER
    _blok_tider[:] = [t for t in _blok_tider if t > graense]
    return len(_blok_tider) >= _MAX_BLOK_PER_TIME


def _record_backstop(conf: float, hunch: str) -> None:
    """Tæl en overkørsel: gaten ville stoppe, men bagkanten slap runnet igennem."""
    try:
        from core.services import gate_verdict_ledger as ledger
    except Exception:  # ledgeren er valgfri — uden den tæller vi bare ikke
        return
    _safe_record(ledger, _BACKSTOP_NERVE, "yellow",
                 f"backstop conf={conf:.3f} hunch={hunch}")


def _record_withheld_decision(conf: float, hunch: str, task_description: str) -> None:
    """A3: registrér en afvisning som BESLUTNING — adskilt fra enhver udfaldskalibrering.

    Kaster ALDRIG: en tæller må ikke kunne påvirke om et run stoppes.
    """
    try:
        from core.services import gate_verdict_ledger as ledger
    except Exception:  # ledgeren er valgfri — en tæller må ALDRIG påvirke beslutningen
        return
    _safe_record(ledger, _WITHHELD_NERVE, "withheld",
                 f"conf={conf:.3f} hunch={hunch} task={str(task_description or '')[:40]}")


# ── A1 (3/11-2026): ægte observationer i stedet for hårdkodede nuller ────────
#
# Før: `preflight_gut_gate` kaldte `derive_gut_signal(task_description=…)` — intet andet.
# Så var `confidence=0,5`, `recent_error_count=0` og `recent_success_count=0` ALTID
# defaults, og tre vidt forskellige opgaver gav identisk 0,61. Gaten kunne ikke skelne.
#
# Nu: de to tællere læses fra `heartbeat_runtime_ticks` — de seneste tick-udfald. Det er
# ægte observationer om hvordan systemet kører lige nu (målt 3/11: 23 blocked mod 270
# ok/completed det seneste døgn).
#
# GRÆNSE, som skal siges højt: de to tællere er GLOBALE observationer, ikke
# opgavespecifikke. De siger hvordan systemet kører lige nu, ikke om NETOP denne opgave
# er risikabel. Den del bæres fra 3/11-2026 af `task_tool_mapping` (A7), som klassificerer
# opgavens tekst — men den er en kurateret, deterministisk heuristik, ikke en måling af
# opgavens faktiske værktøjsbrug. `confidence` er derfor opgavespecifik i RETNING, ikke i
# sandsynlighed: vi ved om opgaven er læsende eller irreversibel, ikke om den lykkes.
_SIGNAL_WINDOW_HOURS = 24
_SIGNAL_CACHE_SECONDS = 60.0
_signal_cache: dict[str, object] = {}


def _recent_tick_signals() -> tuple[int, int]:
    """(error_count, success_count) fra de seneste ticks. Fail-safe: (0, 0) ved fejl.

    `blocked` tælles som fejl; `ok` og `completed` som succes. Caches i 60 s, så et
    run-start ikke betaler en DB-forespørgsel hver gang.
    """
    try:
        now = time.time()
        cached_at = float(_signal_cache.get("at") or 0.0)
        if now - cached_at < _SIGNAL_CACHE_SECONDS and "err" in _signal_cache:
            return int(_signal_cache["err"]), int(_signal_cache["ok"])  # type: ignore[arg-type]

        from core.runtime.db_core import connect
        with connect() as conn:
            rows = conn.execute(
                """SELECT tick_status, COUNT(*) AS n
                     FROM heartbeat_runtime_ticks
                    WHERE started_at > datetime('now', ?)
                    GROUP BY tick_status""",
                (f"-{_SIGNAL_WINDOW_HOURS} hours",),
            ).fetchall()
        err = 0
        ok = 0
        for row in rows:
            status = str(row["tick_status"] or "").strip().lower()
            n = int(row["n"] or 0)
            if status == "blocked":
                err += n
            elif status in ("ok", "completed"):
                ok += n
        _signal_cache.update({"at": now, "err": err, "ok": ok})
        return err, ok
    except Exception:  # uden observationer falder vi tilbage til dagens adfærd: (0, 0)
        return 0, 0


# ── A2 (3/11-2026): forudsigelsens livscyklus ────────────────────────────────
#
# Før: `preflight_gut_gate` dannede en hunch og kastede den. `gut_calibration._on_started`
# dannede derefter en NY — fra `payload.get("focus")`, altså et andet input end det gaten
# så på, og først EFTER at runnet var begyndt. Kalibreringen evaluerede derfor en anden
# forudsigelse end den der lå bag startbeslutningen. To beregninger, den ene kasseret.
#
# Nu: preflight lægger sin forudsigelse i en kortlivet FIFO, og `_on_started` tager den
# ældste ikke-forbrugte. Slotten er per proces og TTL-begrænset, fordi preflight og
# run-start ligger millisekunder fra hinanden i samme proces; findes der ingen slot
# (fx et run startet ad en anden vej), falder kalibreringen tilbage til at danne sin egen
# — og siger det i `source`-feltet, så det kan ses bagefter hvilken vej der blev brugt.
_PREFLIGHT_TTL_SECONDS = 120.0
_PREFLIGHT_MAX_PENDING = 8
_preflight_pending: list[dict[str, object]] = []


def _stash_preflight_prediction(
    *, signal: dict, udfald: dict, task_description: str
) -> None:
    """Gem preflight'ens forudsigelse + beslutning, så livscyklussen kan evaluere DEN.

    Kaster ALDRIG — en fejl i bookkeeping må ikke påvirke om et run starter.
    """
    try:
        now = time.time()
        _preflight_pending[:] = [
            p for p in _preflight_pending
            if now - float(p.get("at") or 0.0) < _PREFLIGHT_TTL_SECONDS
        ]
        _preflight_pending.append({
            "at": now,
            "hunch": str(udfald.get("hunch") or signal.get("hunch") or "proceed"),
            "confidence": udfald.get("confidence", signal.get("confidence")),
            "confidence_no_bias": signal.get("confidence_no_bias"),
            "raw_confidence": signal.get("raw_confidence"),
            "recent_error_count": signal.get("recent_error_count"),
            "recent_success_count": signal.get("recent_success_count"),
            # A7: hvilken risikoklasse opgaven blev læst som — så kalibreringen kan se
            # om en afvist/lupket opgave var irreversibel eller læsende.
            "task_tier": signal.get("task_tier"),
            "task_signals": signal.get("task_signals"),
            "allowed": bool(udfald.get("allowed", True)),
            "backstop": bool(udfald.get("backstop", False)),
            "task": str(task_description or "")[:80],
        })
        while len(_preflight_pending) > _PREFLIGHT_MAX_PENDING:
            _preflight_pending.pop(0)
    except Exception:  # bookkeeping må ALDRIG påvirke beslutningen
        return


def take_preflight_prediction() -> dict[str, object] | None:
    """Tag den ældste ikke-forbrugte preflight-forudsigelse. None hvis ingen findes.

    Bruges af `gut_calibration._on_started`, så kalibreringen evaluerer præcis den
    forudsigelse gaten brugte — ikke en ny beregning fra et andet input.
    """
    try:
        now = time.time()
        _preflight_pending[:] = [
            p for p in _preflight_pending
            if now - float(p.get("at") or 0.0) < _PREFLIGHT_TTL_SECONDS
        ]
        if not _preflight_pending:
            return None
        return _preflight_pending.pop(0)
    except Exception:  # uden observationer falder vi tilbage til dagens adfærd: (0, 0)
        return None


def _caution_har_evidens() -> dict[str, object]:
    """Måler om `caution` er bedre end «sig altid proceed» — grundlaget for at blokere.

    Spørgsmålet er ikke «har maven ret ofte?» men «har advarslen positiv forventet værdi?».
    En advarsel der fyrer på noget der går fint, koster et run og giver intet igen.

    Kravet er todelt og bevidst konservativt:
      * mindst `_EVIDENS_MIN_CAUTION` caution-events, ellers er præcisionen støj
      * præcisionen skal være over `_EVIDENS_MIN_PRECISION` — altså at flertallet af
        advarslerne faktisk varslede en fejl

    Self-safe: kan evidensen ikke måles, svarer den `may_block=False` med en grund. En
    gate der ikke kan begrunde sin blokering må ikke blokere.
    """
    import json as _json

    nu = time.time()
    if (
        _EVIDENS_CACHE["value"] is not None
        and (nu - float(_EVIDENS_CACHE["at"])) < _EVIDENS_TTL_S
    ):
        return _EVIDENS_CACHE["value"]  # type: ignore[return-value]

    ud: dict[str, object] = {"may_block": False, "reason": "kunne-ikke-maales"}
    try:
        from core.runtime.db import connect

        with connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM events "
                "WHERE kind = 'cognitive_gut.outcome_recorded'"
            ).fetchall()
        caution_n = 0
        caution_rigtige = 0
        for row in rows:
            try:
                d = _json.loads(row[0])
            except (TypeError, ValueError):  # een beskadiget raekke maa ikke skjule de andre
                continue
            if not isinstance(d, dict):
                continue
            if str(d.get("hunch") or "") != "caution":
                continue
            caution_n += 1
            # En caution-advarsel havde ret hvis udfaldet IKKE var en succes.
            if str(d.get("actual") or "") not in ("completed", "success"):
                caution_rigtige += 1
        if caution_n < _EVIDENS_MIN_CAUTION:
            ud = {
                "may_block": False,
                "reason": "for-faa-caution-events",
                "caution_n": caution_n,
                "kraevet": _EVIDENS_MIN_CAUTION,
            }
        else:
            praecision = caution_rigtige / caution_n
            ud = {
                "may_block": praecision > _EVIDENS_MIN_PRECISION,
                "reason": "praecision" if praecision > _EVIDENS_MIN_PRECISION
                          else "advarslen-tager-fejl",
                "caution_n": caution_n,
                "caution_rigtige": caution_rigtige,
                "praecision": round(praecision, 4),
                "kraevet_praecision": _EVIDENS_MIN_PRECISION,
            }
    except Exception:  # uden maaling blokerer vi ikke — se docstring
        ud = {"may_block": False, "reason": "db-fejl"}

    _EVIDENS_CACHE["at"] = nu
    _EVIDENS_CACHE["value"] = ud
    return ud


def preflight_gut_gate(*, task_description: str) -> dict[str, object]:
    """PRE-FLIGHT: dan hunch og afgør om et autonomt run må starte. Kaster ALDRIG.

    Fail-open hele vejen: enhver fejl her betyder at runnet starter som før. `allowed=False`
    er den eneste vej til at stoppe noget, og den kræver at confidence ligger under tærsklen
    OG at blokerings-budgettet ikke er brugt.
    """
    try:
        err, ok = _recent_tick_signals()
        signal = derive_gut_signal(
            task_description=task_description,
            recent_error_count=err,
            recent_success_count=ok,
        )
        signal["recent_error_count"] = err
        signal["recent_success_count"] = ok
    except Exception:  # kunne ikke danne hunch → slip igennem, det er den sikre side
        return {"allowed": True, "reason": "derive-fejl"}

    conf = float(signal.get("confidence") or 0.0)
    hunch = str(signal.get("hunch") or "proceed")
    try:
        tillad = gut_gate(conf, context="autonomous_run_preflight",
                          no_bias_confidence=signal.get("confidence_no_bias"),
                          hunch=hunch)
    except Exception:  # gaten er rådgivende — en fejl her må ALDRIG stoppe et run
        return {"allowed": True, "reason": "gate-fejl", "confidence": conf}

    # EVIDENS-PORT (12/11-2026): en advarsel må kun BLOKKERE når maven kan vises at være
    # bedre end den trivielle strategi «sig altid proceed». Uden porten er `caution` en
    # advarsel der per konstruktion næsten altid tager fejl: runs lykkes ~99,7 % af tiden,
    # så en advarsel er forkert i samme grad. Målt 12/11 kl. 21:45Z på 344 events: maven
    # 92,73 % korrekt mod konstantens 99,71 % = −6,98 pp, og af 26 caution-advarsler var
    # 1 korrekt (3,8 %). Gaten advarede altså om noget der gik fint 96 % af gangene.
    #
    # Porten rører IKKE signalet: `hunch`, `confidence` og kalibreringen går uændret videre
    # til de fire andre forbrugere (kalibrerings-forudsigelse, Central-stance,
    # stance-tensions, central_valence). Kun den ene handling — at stoppe et run — kræver
    # evidens. Er der ikke nok events til at afgøre det, blokeres der ikke: en gate uden
    # grundlag må ikke handle.
    if not tillad and hunch == "caution":
        evidens = _caution_har_evidens()
        if not evidens.get("may_block"):
            udfald = {
                "allowed": True,
                "confidence": conf,
                "hunch": hunch,
                "evidence_blocked": True,
                "evidence": evidens,
            }
            _stash_preflight_prediction(signal=signal, udfald=udfald,
                                        task_description=task_description)
            return udfald

    if tillad:
        udfald = {"allowed": True, "confidence": conf, "hunch": hunch}
        _stash_preflight_prediction(signal=signal, udfald=udfald,
                                    task_description=task_description)
        return udfald
    if _blok_budget_brugt():
        _record_backstop(conf, hunch)
        udfald = {"allowed": True, "confidence": conf, "hunch": hunch, "backstop": True}
        _stash_preflight_prediction(signal=signal, udfald=udfald,
                                    task_description=task_description)
        return udfald

    _blok_tider.append(time.time())
    _record_withheld_decision(conf, hunch, task_description)
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "gut_gate_withhold", value=conf,
                       meta={"hunch": hunch, "task": task_description[:40],
                             "where": "preflight"},
                       reason="gut_gate_withhold")
    except Exception:  # observationen er egress-fri pynt — uden den stopper vi stadig
        pass
    udfald = {"allowed": False, "confidence": conf, "hunch": hunch}
    _stash_preflight_prediction(signal=signal, udfald=udfald,
                                task_description=task_description)
    return udfald


def preflight_allows(message: str) -> bool:
    """Bekvemmeligheds-indpakning til run-start-stierne: True = start runnet.

    Hele vejen fail-open, så et kaldested kan bruge den uden selv at væbne sig.
    """
    try:
        udfald = preflight_gut_gate(task_description=(message or "").strip())
    except Exception:  # gaten er rådgivende — fejler den, starter runnet som før
        return True
    return bool(udfald.get("allowed", True))


def record_gut_outcome(
    *,
    hunch: str,
    actual_outcome: str,
) -> dict[str, object]:
    """Record whether the gut hunch was correct."""
    predicted_success = hunch == "proceed"
    actual_success = actual_outcome in ("completed", "success")
    correct = predicted_success == actual_success

    result = update_cognitive_gut_state(
        prediction_correct=correct,
        last_hunch=f"{hunch} → {actual_outcome} ({'✓' if correct else '✗'})",
    )

    event_bus.publish(
        "cognitive_gut.outcome_recorded",
        {"correct": correct, "hunch": hunch, "actual": actual_outcome},
    )
    return result


_BASELINE_CACHE: dict[str, object] = {"at": 0.0, "value": None}
_BASELINE_TTL_S = 300.0


def _observed_baseline() -> dict[str, object] | None:
    """Mål maven mod en KONSTANT baseline (altid «proceed») på de events der findes.

    Hvorfor (12/11-2026): fladen viste calibration_score 0,9925 og blev læst som «maven
    har ret i 99% af tilfældene». Målt mod de 346 faktiske events var maven 92,77%
    korrekt, mens en konstant «proceed» ville være 99,71% — altså 6,94 procentpoint
    DÅRLIGHERE. Årsagen er aritmetisk: runs lykkes 99,7% af tiden, så enhver advarsel
    næsten altid er forkert. En hit-rate uden baseline kan ikke skelne «maven er dygtig»
    fra «systemet fejler næsten aldrig».

    Self-safe og cachet i _BASELINE_TTL_S sekunder: fladen kaldes fra heartbeat-hotpathen,
    og queryen koster ~5 ms. Uden DB returneres None — fladen vises stadig, men uden
    baseline, og det er synligt i summary'en.
    """
    import json as _json

    nu = time.time()
    if _BASELINE_CACHE["value"] is not None and (nu - float(_BASELINE_CACHE["at"])) < _BASELINE_TTL_S:
        return _BASELINE_CACHE["value"]  # type: ignore[return-value]

    result: dict[str, object] | None = None
    try:
        from core.runtime.db import connect

        with connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM events WHERE kind = 'cognitive_gut.outcome_recorded'"
            ).fetchall()
        faktisk = 0
        baseline = 0
        n = 0
        for row in rows:
            try:
                d = _json.loads(row[0])
            except (TypeError, ValueError):  # een beskadiget raekke maa ikke skjule de andre
                continue
            if not isinstance(d, dict):
                continue
            hunch = str(d.get("hunch") or "")
            actual = str(d.get("actual") or "")
            if hunch not in ("proceed", "caution"):
                continue
            n += 1
            act_success = actual in ("completed", "success")
            faktisk += (hunch == "proceed") == act_success
            baseline += act_success
        if n:
            result = {
                "n_observed": n,
                "maven_pct": round(faktisk / n * 100, 2),
                "baseline_pct": round(baseline / n * 100, 2),
                "skill_pp": round((faktisk - baseline) / n * 100, 2),
            }
    except Exception:  # baseline er et SUPPLEMENT — fladen skal vises selvom DB'en ikke kan læses
        result = None

    _BASELINE_CACHE["at"] = nu
    _BASELINE_CACHE["value"] = result
    return result


def build_gut_surface() -> dict[str, object]:
    """Kalibrerings-fladen — viser de tre lag ADSKILT (A3, 3/11-2026).

    Før viste den kun `calibrated_hits/total_predictions`, hvilket læses som «hvor ofte
    havde maven ret». Men `total_predictions` tæller kun de runs der fik LOV at køre, og
    afvisninger var helt usynlige. Nu står de tre lag ved siden af hinanden:

      • evalueret  — forudsigelse mødt af et observeret udfald (kan kalibrere)
      • afvist     — gaten sagde nej; intet udfald findes (kan IKKE kalibrere)
      • overkørt   — gaten sagde nej, bagkanten slap den igennem

    Afvisninger kan aldrig gøre kalibreringen bedre eller dårligere — de har intet udfald
    at måles mod. De vises for at gøre gatens adfærd synlig, ikke for at pynte på tallet.
    """
    state = get_cognitive_gut_state()

    withheld = 0
    overkoersler = 0
    try:
        from core.services import gate_verdict_ledger as ledger
        counts = ledger.summary()
        withheld = int((counts.get(_WITHHELD_NERVE) or {}).get("total") or 0)
        overkoersler = int((counts.get(_BACKSTOP_NERVE) or {}).get("total") or 0)
    except Exception:  # ledgeren er valgfri — fladen skal stadig kunne vises
        pass

    if not state:
        return {"active": False, "state": None,
                "withheld": withheld, "backstop_overkoersler": overkoersler,
                "summary": "No gut data yet"}
    baseline = _observed_baseline()
    if baseline:
        skill = float(baseline["skill_pp"])
        dom = "BEDRE" if skill > 0 else ("DAARLIGERE" if skill < 0 else "LIGE")
        baseline_summary = (
            f" | mod konstant baseline: maven {baseline['maven_pct']:.2f}% vs "
            f"{baseline['baseline_pct']:.2f}% (n={baseline['n_observed']}) "
            f"= {skill:+.2f} pp {dom}"
        )
    else:
        baseline_summary = " | baseline utilgaengelig — hit-raten kan IKKE laeses som dygtighed"

    # Evidensvinduet er KORTERE end akkumuleringen (maalt 12/11-2026): `events` ryddes
    # efter events_retention (14 dage), mens `total_predictions` akkumulerer fra mavens
    # foedsel (6/4-2026). Differencen kan ikke efterproeves og maa ikke laeses som evidens
    # — derfor staar baade det akkumulerede tal og det verificerbare tal paa fladen.
    total_evaluated = int(state["total_predictions"])
    verified = int(baseline["n_observed"]) if baseline else 0
    unverifiable = max(0, total_evaluated - verified)
    evidence_summary = (
        f" | {verified} af {total_evaluated} kan efterproeves (events ryddes efter "
        f"14 dage); {unverifiable} ligger foer vinduet"
    ) if unverifiable > 0 else ""

    return {
        "active": True,
        "state": state,
        "evaluated": total_evaluated,
        "evaluated_verified": verified,
        "evaluated_unverifiable": unverifiable,
        "withheld": withheld,
        "backstop_overkoersler": overkoersler,
        "baseline": baseline,
        "summary": (
            f"Calibration: {state['calibration_score']:.2f} "
            f"({state['calibrated_hits']}/{state['total_predictions']} correct); "
            f"{withheld} afvist (intet udfald), {overkoersler} overkørt af bagkanten"
            f"{baseline_summary}"
            f"{evidence_summary}"
        ),
    }


def build_gut_counterfactual_surface() -> dict[str, object]:
    """Counterfactual decision delta: hvor ofte flyttede den lærte bias gatens afgørelse?

    Læser den PERSISTENTE ledger (overlever genstart). Bias'en er siden 12/10-2026 et ægte
    FORTEGN, symmetrisk om 0 (jf. derive_gut_signal): positiv løfter proceed-confidence og
    sænker caution, negativ omvendt. Med-bias-pass er derfor IKKE en overmængde af
    uden-bias-pass, og deltaet kan være negativt.

    Counterfactual-deltaet tæller kun GRÆNSEKRYDS. Den separate påvirknings-ledger måler
    også confidence-flytning under tærsklen og skelner derfor inactive, uncoupled,
    subthreshold og tipping uden at ændre gatens beslutningslogik.
    """
    influence = _read_gut_influence(_COUNTERFACTUAL_NERVE)
    influence_observations = int(influence["events"])
    influence_events = int(influence["influenced"])
    crossings = int(influence["crossings"])
    mean_abs_delta = (
        float(influence["delta_abs_sum"]) / influence_observations
        if influence_observations else 0.0
    )
    mode = _consumer_mode()
    bias = _gut_bias()
    if mode != "on" or abs(bias) <= 1e-9:
        influence_state = "inactive"
    elif influence_events == 0:
        influence_state = "uncoupled"
    elif crossings == 0:
        influence_state = "subthreshold"
    else:
        influence_state = "tipping"

    influence_fields: dict[str, object] = {
        "state": influence_state,
        "influence_events": influence_events,
        "mean_abs_delta": mean_abs_delta,
        "influence_delta_sum": float(influence["delta_sum"]),
        "crossings": crossings,
    }
    try:
        from core.services import gate_verdict_ledger as ledger
        counts = ledger.summary()
    except Exception:  # ledgeren kan ikke læses → fladen melder "ingen data", kaster ikke
        return {"active": False, "events": 0, **influence_fields,
                "summary": "counterfactual-ledger utilgængelig"}

    backstop = counts.get(_BACKSTOP_NERVE) or {}
    med = counts.get(_COUNTERFACTUAL_NERVE) or {}
    uden = counts.get(_COUNTERFACTUAL_NERVE_NO_BIAS) or {}
    shadow = counts.get(_COUNTERFACTUAL_NERVE_SHADOW) or {}
    total = int(med.get("total") or 0)
    if not total:
        return {"active": False, "events": 0, **influence_fields,
                "summary": "ingen gut_gate-afgørelser talt op endnu"}

    pass_med = int(med.get("green") or 0)
    pass_uden = int(uden.get("green") or 0)
    delta = pass_med - pass_uden
    overkoersler = int(backstop.get("total") or 0)
    # A6b (3/11-2026): `blokeret` talte gatens NEJ, ikke faktisk stoppede runs — så en
    # backstop-overkørsel stod som «stoppet» i samme flade der ved siden af viste den som
    # «sluppet igennem». Nu tælles kun on-mode-afvisninger, og bagkantens overkørsler
    # trækkes fra. Shadow-afgørelser ligger på deres egen nerve og indgår ikke i `total`.
    blokeret = max(0, total - pass_med - overkoersler)
    shadow_total = int(shadow.get("total") or 0)
    state_summary = {
        "inactive": "bias er inaktiv",
        "uncoupled": "bias er aktiv, men confidence er ikke koblet til påvirkningsmålet",
        "subthreshold": "musklen arbejder under vippegrænsen",
        "tipping": "bias vipper afgørelser",
    }[influence_state]
    return {
        "active": True,
        "events": total,
        **influence_fields,
        "pass_med_bias": pass_med,
        "pass_uden_bias": pass_uden,
        "counterfactual_delta": delta,
        "delta_pct": round(100.0 * delta / total, 2),
        "blokeret": blokeret,
        "backstop_overkoersler": overkoersler,
        "shadow_afgoerelser": shadow_total,
        "summary": (
            f"{state_summary} (mean |Δ|={mean_abs_delta:.2f}, "
            f"{crossings} grænsekryds); bias flyttede netto afgørelsen i "
            f"{delta} af {total} tilfælde ({round(100.0 * delta / total, 2)} %); "
            f"{blokeret} stoppet, "
            f"{overkoersler} sluppet igennem af bagkanten, "
            f"{shadow_total} simuleret i shadow"
        ),
    }
