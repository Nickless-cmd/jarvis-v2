"""Central consequence — hvor en karakters fund FAKTISK lander.

Målt 13/11-2026, den samme defekt i alle 14 Matrix-karakterer: de **beregner**
en konsekvens og kaster den væk.

* `central_sentinel.attack()` regner `proposed_confidence = conf / 2.0` ud,
  gemmer den i en kolonne der hedder `proposed_`, og skriver ALDRIG tilbage.
  `_enforced()` er en shadow-flag der er slukket, og der findes ingen kode bag
  den — så «håndhævelse» var en gren der ikke eksisterede.
* `central_redpill` tæller blå piller og læser aldrig sit eget tal.
* `central_dissent` returnerer `total_objections` til en verden der ikke lytter.

Det er samme fejlform som Smiths «Trin 2 — bundet» uden en binding, og som
`health_check` der pegede på port 8000: en tilstand der påstår en handling der
ikke findes. Stemmen er nu ægte (se `central_matrix_ensemble`), men en stemme
uden konsekvens er stadig teater — bare med bedre replikker.

## Tre levers, og kun tre

1. **confidence** — en hypotese der er angrebet skal faktisk falde. Går gennem
   `central_hypothesis_governance.apply_outcome` (Popper: falsifikation er et
   hårdt multiplikativt nedtræk), ikke gennem en selvopfundet formel.
2. **decision** — et adfærdsmønster bliver en bindende forpligtelse via
   `behavioral_decisions.create_decision`. Den er den stærkeste: et direktiv
   dukker op i hvert heartbeat, indtil det er revokeret eller opfyldt.
3. **record** — fundet lander i `central_consequences` som en reviderbar række.
   Bruges når de to andre ikke må anvendes (vagt, loft, shadow).

Flere levers er ikke bedre. Hver lever er en mutation af noget levende, og
hver mutation kræver et værn.

## Værnene

* **Støj-vetoet** (`smith_noise_veto`) — det samme der standsede 31 mintede
  direktiver med to med indhold. En n-gram-detektor kan ikke skelne en
  adfærdsvane fra almindeligt dansk, så den kan kun sige nej.
* **Dags-loft** — en brækket detektor må ikke kunne køre hele systemet over.
  Målt behov: `central_hypotheses` har 152.754 rækker; en cadence-producer der
  halverer den højeste confidence hver kørsel ville æde økosystemet på timer.
* **Idempotens** — samme (cid, lever, subject) lander kun én gang pr. døgn.

## Det der gør det målbart

`measure_consequences()` svarer på det ene spørgsmål teatret ikke kan svare på:
**hvor mange fund flyttede faktisk noget?** `applied=1` og `before != after`
er beviset. `applied=0` med en grund er ærligt; `applied=1` uden en flytning
er en løgn, og derfor tælles de to ting hver for sig.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_TABLE = "central_consequences"

# Hvor mange landinger pr. lever pr. døgn. Et loft er ikke en semantisk grænse
# — det er et værn mod en detektor der er gået i stykker. 152.754 hypoteser
# betyder at en utæmmet confidence-lever kan tømme økosystemet på få timer.
_DAGSLoft = {"confidence": 8, "decision": 3, "record": 500}

# (13/11-2026) Loftet ovenfor var GLOBALT: 3 beslutninger i doegnet paa tvaers af
# alle 31 karakterer. Det var ment som vaern mod én braekket detektor, men ramte
# alle sunde: dissent, red_dress og mourning landede foerst, og derefter var
# leveren en DOED GREN for de øvrige — maalt i drift som «dagsloft ramt (3/3)»
# paa et fuldt gyldigt fund. Det er praecis den fejlform hele arbejdet jager.
# `_DAGSLoft` er derfor nu pr. KARAKTER (én braekket detektor kan ikke spaamme),
# og `_GLOBAL_DAGSLoft` er det ydre vaern (mange braekkede detektorer kan ikke
# aede økosystemet). Begge skal kunne naas af et sundt system.
_GLOBAL_DAGSLoft = {"confidence": 40, "decision": 60, "record": 5000}


def _nu() -> str:
    return datetime.now(UTC).isoformat()


def _connect():
    from core.runtime.db import connect
    return connect()


def _ensure(conn) -> None:
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cid TEXT NOT NULL,
            lever TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            before_value TEXT NOT NULL DEFAULT '',
            after_value TEXT NOT NULL DEFAULT '',
            applied INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            fund_id TEXT NOT NULL DEFAULT '',
            decision_id TEXT NOT NULL DEFAULT ''
        )"""
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_cid ON {_TABLE}(cid, created_at)"
    )
    # (13/11-2026) Kolonnerne kom efter tabellen var taget i brug i drift, saa
    # `CREATE TABLE IF NOT EXISTS` tilfoejer dem ikke til en eksisterende base.
    # Uden migreringen ville hver skrivning fejle paa en produktionsbase mens
    # testene (der bygger tabellen frisk) var groenne.
    _tilfoej_kolonne(conn, "fund_id", "TEXT NOT NULL DEFAULT ''")
    _tilfoej_kolonne(conn, "decision_id", "TEXT NOT NULL DEFAULT ''")
    # Identiteten skal vaere haandhaevet, ikke blot gemt: to samtidige forsoeg
    # paa samme fund maa ikke begge slippe igennem et check-og-skriv.
    conn.execute(
        f"""CREATE UNIQUE INDEX IF NOT EXISTS idx_{_TABLE}_fund
            ON {_TABLE}(fund_id) WHERE fund_id != ''"""
    )


def _tilfoej_kolonne(conn, navn: str, definition: str) -> None:
    """Migrér en eksisterende tabel — `ALTER TABLE` fejler hvis kolonnen findes."""
    kolonner = {str(r[1]) for r in conn.execute(f"PRAGMA table_info({_TABLE})")}
    if navn not in kolonner:
        conn.execute(f"ALTER TABLE {_TABLE} ADD COLUMN {navn} {definition}")


def _landinger_sidste_doegn(conn, lever: str, cid: str | None = None) -> int:
    """Landinger i doegnet — for ÉN karakter naar `cid` er givet, ellers i alt.

    (13/11-2026) `reason='reserveret'` tælles IKKE med. Reservationen skrives
    foer beslutningen oprettes, saa den findes paa tællingstidspunktet for det
    kald der er ved at lande — og et loft der tæller den med, afviser det andet
    fund i traek som «dagsloft ramt». En reservation er et claim, ikke en
    landing; den bliver foerst en landing naar raekken opgraderes.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    if cid is None:
        r = conn.execute(
            f"SELECT COUNT(*) FROM {_TABLE} WHERE lever=? AND applied=1 "
            f"AND reason!='reserveret' AND created_at>=?",
            (lever, cutoff),
        ).fetchone()
    else:
        r = conn.execute(
            f"SELECT COUNT(*) FROM {_TABLE} WHERE lever=? AND cid=? AND applied=1 "
            f"AND reason!='reserveret' AND created_at>=?",
            (lever, cid, cutoff),
        ).fetchone()
    return int((r or [0])[0] or 0)


def _allerede_landet(conn, cid: str, lever: str, subject: str,
                     fund_id: str = "") -> bool:
    """Idempotens: samme FUND lander ikke to gange.

    Uden dette ville en cadence-producer der kører hvert tredje kvarter skrive
    den samme konklusion 96 gange i døgnet — og hver skrivning ville se ud som
    en ny konsekvens i målingen.

    (13/11-2026, Bjørns indvending) Vinduet var et rullende døgn paa
    ``(cid, lever, subject)``, og `subject` er en FAST streng pr. karakter
    (``relations_alder_fald``, ``klangdrift:<akse>``). To forskellige fund af
    samme TYPE blev derfor smeltet sammen: faldt alderen 200→12 og derefter
    12→3 to timer senere, fik det andet svar «allerede landet» — og karakteren
    ryddede det som afsluttet. Lighed er ikke identitet.

    Naar fundet baerer et `fund_id`, er det identiteten: samme id lander aldrig
    to gange, uanset hvor lang tid der gaar, og et ANDET id lander uanset hvor
    kort tid der er gaaet. Uden et id (ældre kald, `record`) falder vi tilbage
    til type-vinduet — det er svagere, men det er den ærlige grænse for hvad
    der kan afgøres uden en identitet.
    """
    if fund_id:
        # (14/11-2026, GPT's anden indvending — maalt) Spørgsmaalet er «er
        # fundet LANDET?», ikke «findes der en raekke?». Foer spurgte denne
        # `WHERE fund_id=?` uden at se paa tilstanden, saa en raekke der stod
        # `reserveret` efter et crash blev laest som «taget» — og
        # `create_decision` blev ALDRIG kaldt igen. Fundet var tabt for altid,
        # mens raekken stadig stod som et spor der SAA faerdigt ud. Maalt:
        # et genforsoeg svarede `already_landed` med `decision_id: None`, og
        # create_decision blev ikke kaldt.
        #
        # En landing er bevist ved at BESLUTNINGEN findes, ikke ved `applied`:
        # `applied=0` daekker baade «deduped» (beslutningen fandtes i
        # forvejen) og «reserveret» (den findes ikke). Kun `decision_id`
        # skelner de to.
        r = conn.execute(
            f"SELECT decision_id FROM {_TABLE} WHERE fund_id=? AND lever='decision' LIMIT 1",
            (fund_id,),
        ).fetchone()
        if r is None:
            return False
        return bool(str(r["decision_id"] or "").strip())
    cutoff = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    r = conn.execute(
        f"SELECT 1 FROM {_TABLE} WHERE cid=? AND lever=? AND subject=? AND applied=1 AND created_at>=? LIMIT 1",
        (cid, lever, subject, cutoff),
    ).fetchone()
    return r is not None


def _skriv(
    conn,
    *,
    cid: str,
    lever: str,
    subject: str,
    before: str = "",
    after: str = "",
    applied: bool = False,
    reason: str = "",
    fund_id: str = "",
    decision_id: str = "",
) -> None:
    """Skriv en landingsraekke — UPSERT naar fundet baerer en identitet.

    (14/11-2026, GPT's anden indvending) Den unikke indeks paa `fund_id` gør
    at der kun kan findes ÉN raekke pr. fund. En INSERT betoed derfor at et
    genforsoeg kolliderede i basen: svaret blev en fejl, og fundet stod
    tilbage i den tilstand det foerste forsoeg efterlod. Med en upsert
    overskriver genforsoerget sin EGEN raekke — reservationen bliver til den
    landing den var paa vej til at blive.
    """
    if fund_id:
        opdateret = conn.execute(
            f"""UPDATE {_TABLE} SET cid=?, lever=?, subject=?, before_value=?,
                after_value=?, applied=?, reason=?, decision_id=?
                WHERE fund_id=?""",
            (cid, lever, subject[:200], str(before)[:200], str(after)[:200],
             1 if applied else 0, reason[:300], decision_id or "", fund_id),
        ).rowcount
        if opdateret:
            return
    conn.execute(
        f"""INSERT INTO {_TABLE}
            (cid, lever, subject, before_value, after_value, applied, reason,
             created_at, fund_id, decision_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (cid, lever, subject[:200], str(before)[:200], str(after)[:200],
         1 if applied else 0, reason[:300], _nu(), fund_id or "", decision_id or ""),
    )


def _loft_ramt(conn, lever: str, cid: str = "") -> str | None:
    """To lofter: ét pr. KARAKTER og ét GLOBALT.

    Pr-karakter-lofter er det der standser én braekket detektor. Det globale loft
    er det der standser mange. Da loftet var globalt alene, brugte de tre foerste
    sunde fund dagens budget og blokerede resten — det blev maalt i drift som et
    fuldt gyldigt fund afvist med «dagsloft ramt (3/3)».
    """
    if cid:
        pr_karakter = int(_DAGSLoft.get(lever, 0))
        n = _landinger_sidste_doegn(conn, lever, cid)
        if pr_karakter and n >= pr_karakter:
            return f"dagsloft for {cid} ramt ({n}/{pr_karakter})"
    globalt = int(_GLOBAL_DAGSLoft.get(lever, 0))
    total = _landinger_sidste_doegn(conn, lever)
    if globalt and total >= globalt:
        return f"globalt dagsloft ramt ({total}/{globalt})"
    return None


def _gate_taend(scope: str, name: str) -> bool:
    """Er leverens switch taendt?

    UKENDT betyder TAENDT. Det er et bevidst valg, og det er den modsatte
    standard af `central_sentinel._enforced()`, som returnerede False naar
    flaget ikke var sat — med det resultat at «haandhaevelse» var en gren der
    aldrig kunne koere. En shadow-standard der ikke skriver er ikke et vaern;
    det er en undskyldning der ser ud som forsigtighed.

    Det der FAKTISK vaerner mod en braekket detektor er dagsloftet og
    stoej-vetoet, ikke en tavs standard. Switchen er derfor en kill-switch:
    saet den eksplicit til enabled=False, og leveren standser.
    """
    try:
        from core.services.central_switches import _key, shared_cache
        val = shared_cache.get(_key(scope, name))
        if val is None:
            return True
        return isinstance(val, dict) and val.get("enabled") is True
    except Exception as exc:
        # Kan switchen ikke laeses, antages SLUKKET: en mutation maa ikke ske paa
        # et grundlag der ikke kunne verificeres. Modsat UKENDT-flaget, som
        # betyder taendt — her fejlede laesningen selv.
        logger.debug("central_consequence: switch-laesning fejlede: %s", exc)
        return False


def land_confidence(
    cid: str,
    hyp_id: str,
    *,
    falsified: bool = True,
    reason: str = "",
    gate: tuple[str, str] = ("sentinel", "enforce"),
) -> dict[str, Any]:
    """Lad et angreb FAKTISK flytte hypotesens confidence.

    Formlen er `apply_outcome` — den sanktionerede Popper-regel, ikke en
    selvopfundet halvering. `falsified=True` giver et haardt multiplikativt
    nedtraek; en modsigelse dominerer mange bekræftelser, og det er hele
    pointen med at have en Sentinel.

    `applied=False` med en grund er et aerligt svar — en shadow-tilstand der
    ikke skriver, men som heller ikke paastaar at den gjorde noget.
    """
    out: dict[str, Any] = {"applied": False, "before": None, "after": None, "reason": ""}
    try:
        from core.services.central_hypothesis_governance import apply_outcome
    except Exception as exc:
        out["reason"] = f"governance utilgaengelig: {exc}"
        return out

    try:
        with _connect() as conn:
            _ensure(conn)
            row = conn.execute(
                "SELECT confidence FROM central_hypotheses WHERE hyp_id=?", (hyp_id,)
            ).fetchone()
            if row is None:
                out["reason"] = "hypotese findes ikke"
                return out
            before = float((row["confidence"] if isinstance(row, dict) else row[0]) or 0.0)
            out["before"] = before

            def _afvis(why: str) -> dict[str, Any]:
                out["reason"] = why
                _skriv(conn, cid=cid, lever="confidence", subject=hyp_id,
                       before=str(before), after=str(before), applied=False, reason=why)
                conn.commit()
                return out

            if _allerede_landet(conn, cid, "confidence", hyp_id):
                return _afvis("allerede landet i doegnet")
            if not _gate_taend(*gate):
                return _afvis(f"switch slukket: {gate[0]}/{gate[1]}")
            if (loft := _loft_ramt(conn, "confidence", cid)) is not None:
                return _afvis(loft)

            after = float(apply_outcome(before, falsified=bool(falsified)))
            # Et loft er ét vaern; dette er det andet: et enkelt angreb maa ikke
            # kunne nulstille en hypotese. Den skal kunne forsvare sig.
            after = max(0.01, min(1.0, after))
            if abs(after - before) < 1e-9:
                return _afvis("ingen flytning")

            conn.execute("UPDATE central_hypotheses SET confidence=? WHERE hyp_id=?", (after, hyp_id))
            _skriv(conn, cid=cid, lever="confidence", subject=hyp_id,
                   before=str(before), after=str(after), applied=True, reason=reason or "falsified")
            conn.commit()
            out.update({"applied": True, "after": after, "reason": reason or "falsified"})
            return out
    except Exception as exc:
        logger.debug("central_consequence: land_confidence fejlede: %s", exc)
        out["reason"] = f"fejl: {str(exc)[:120]}"
        return out


_EVIDENS_FELT = re.compile(r"[A-Za-z_]\w*\s*=\s*-?\d+(?:[.,]\d+)?")
_EVIDENS_ENHED = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:gange|%|procent|stk|dage?|timer?|minutter?|min|"
    r"sekunder?|sek|ms|kald|rækker?|ord|sætninger|hypoteser|indsigelser|"
    r"landinger|fund|målinger|fejl|døre|nerver|incidents|anomalier|"
    r"beslutninger|kig|epitafer)\b",
    re.IGNORECASE,
)
_EVIDENS_RETNING = re.compile(r"\d+(?:[.,]\d+)?\s*(?:→|->|til)\s*\d+(?:[.,]\d+)?")


def _er_maalt(evidence: str, source: str) -> tuple[bool, str]:
    """Er dette en MÅLING — eller bare en sætning med et ciffer i?

    (13/11-2026) Rettet efter Bjørns fund, samme dag som vagten blev skrevet.
    Den første version spurgte om strengen indeholdt ET CIFTER, så
    ``evidence="0"`` blev godkendt som målt evidens. Hullet blev bevist i drift:
    den SAMME formulerede påstand blev afvist uden evidens og **bundet** med
    ``evidence="0"`` — ét tegn var nok til at omgå støj-vetoet.

    Et tal er ikke automatisk en måling, og en måling er ikke automatisk
    evidens. Derfor to krav: målingen skal have en FORM (navngivne felter,
    tal med enhed, eller en før→efter-retning — et bart ciffer har ingen af
    dem), og den skal navngive sin KILDE. En formuleret sætning kan skrive et
    ciffer ved et uheld; den kan ikke opfinde en måleform og en kilde uden at
    nogen faktisk har målt.

    Formen ``severity=2 volume=0`` tælles som en måling, selv om tallene er
    små: felterne er navngivet, og det er præcis forskellen fra «0».
    """
    ev = (evidence or "").strip()
    if not ev:
        return False, "ingen evidens"
    if not (_EVIDENS_FELT.search(ev)
            or _EVIDENS_ENHED.search(ev)
            or _EVIDENS_RETNING.search(ev)):
        return False, "evidens baerer ikke en maaleform (felt, enhed eller retning)"
    if not (source or "").strip():
        return False, "evidens navngiver ikke sin kilde"
    return True, "maalt"


def land_decision(
    cid: str,
    directive: str,
    *,
    rationale: str = "",
    trigger_cue: str = "",
    priority: int = 55,
    subject: str = "",
    evidence: str = "",
    evidence_source: str = "",
    fund_id: str = "",
    gate: tuple[str, str] = ("consequence", "bind_decisions"),
) -> dict[str, Any]:
    """Lad et fund blive en BINDENDE forpligtelse.

    Gaar gennem stoej-vetoet — MEDMINDRE forpligtelsen baerer en MAALT evidens.

    (13/11-2026) Denne gren er tilfoejet efter en maaling der gjorde vetoet til
    en doed gren for alle karakterer: seks forskellige karakter-fund blev doemt
    STOEJ i traek, og kun dissent slap igennem — tilfaeldigt, fordi ordet
    «adlyde» ramte den risikable liste. Dommerens egen regel forklarer hvorfor:
    «en ren sproglig gentagelse er aldrig aegte». Den er bygget til Smiths
    MØNSTRE, som var FORMULEREDE. Et karakter-fund er noget andet: det baerer et
    maalt tal — 47.332 indsigelser, 0,8→0,4, 14,32 % divergens. Forskellen
    mellem formuleret og maalt er praecis hvad vetoet ikke kan se.

    Kravet til «maalt» er strammet efter et fund: et ciffer er IKKE nok.
    Se `_er_maalt` — der kraeves en maaleform OG en navngivet kilde.

    ``fund_id`` er fundets EGEN identitet (13/11-2026). Den goer idempotensen
    konkret frem for typisk: samme fund lander aldrig to gange — heller ikke
    efter et doegnsskifte — og to FORSKELLIGE fund med samme ``subject`` lander
    begge. Identiteten skrives ogsaa paa beslutningen som ``source_record_id``,
    saa koblingen findes i begge ender og ikke kun i denne tabel.
    """
    out: dict[str, Any] = {"applied": False, "decision_id": None, "reason": ""}
    subject = (subject or directive)[:200]
    fund_id = (fund_id or "").strip()
    # (14/11-2026) IDENTITETEN SKAL ALTID FINDES — ellers er reservationen en
    # fælde. Målt i drift: 0 af 185 rækker havde et `fund_id`, fordi ingen af de
    # ti kaldere sender et. Reservationen blev derfor skrevet med `fund_id=''`,
    # og opgraderingen (`UPDATE … WHERE fund_id=?`) ramte nul rækker — så rækken
    # stod fast som `reserveret` med `applied=1` for evigt, mens beslutningen VAR
    # oprettet 4 ms senere. To sådanne rækker lå i basen (red_dress 13/11, rca
    # 14/11). Kalderne BÆRER identiteten — `quiet_fire:<nerve>`,
    # `recurring:<cluster>/<nerve>/<kind>` — men kun som `subject`, der er en
    # TYPE. Derfor udledes identiteten her: subject + evidens + direktiv er
    # fundets fingeraftryk, og det er stabilt for det samme fund uden at smelte
    # to forskellige fund sammen.
    if not fund_id:
        _finger = f"{subject}\x1f{evidence}\x1f{directive}"
        fund_id = "fund-" + hashlib.sha256(_finger.encode("utf-8")).hexdigest()[:16]
        _udledt_id = True
    else:
        _udledt_id = False
    maalt, maalt_grund = _er_maalt(evidence, evidence_source)
    if not maalt:
        try:
            from core.services.smith_noise_veto import maa_minte
            ok, grund = maa_minte(f"{cid}:{subject}", directive)
            if not ok:
                out["reason"] = f"veto: {grund} ({maalt_grund})"
                with _connect() as conn:
                    _ensure(conn)
                    _skriv(conn, cid=cid, lever="decision", subject=subject,
                           applied=False, reason=out["reason"], fund_id=fund_id)
                    conn.commit()
                return out
        except Exception as exc:
            logger.warning("land_decision: stoej-veto utilgaengeligt for %s: %s", cid, exc)
            out["reason"] = f"veto utilgaengeligt: {str(exc)[:80]}"
            return out

    try:
        with _connect() as conn:
            _ensure(conn)
            if _allerede_landet(conn, cid, "decision", subject, fund_id):
                out["reason"] = ("fundet er allerede landet" if not _udledt_id
                                 else "allerede landet i doegnet")
                # (13/11-2026, Bjørns fjerde indvending) `applied=False` betød både
                # «afvist» og «allerede afsluttet». En kalder der rydder sit spor på
                # `applied` kunne derfor aldrig afslutte et fund hvis beslutning VAR
                # oprettet — den lå fast som uafsluttet for evigt. Feltet skiller de
                # to: konsekvensen findes allerede, så fundet er færdigt.
                out["already_landed"] = True
                out["decision_id"] = _beslutning_for_fund(conn, fund_id)
                # (14/11-2026) Rækken FINDES allerede — det er hele grunden til
                # at vi er i denne gren. At skrive endnu en med samme `fund_id`
                # kolliderer på den unikke indeks og gør svaret til en fejl i
                # stedet for et svar. Sporet er skrevet; her mangler kun
                # beslutnings-id'et, hvis reservationen aldrig blev opgraderet.
                if fund_id and out["decision_id"]:
                    conn.execute(
                        f"""UPDATE {_TABLE} SET decision_id=?, applied=1, reason=?
                            WHERE fund_id=? AND lever='decision'""",
                        (str(out["decision_id"]), out["reason"][:300], fund_id),
                    )
                elif not fund_id:
                    _skriv(conn, cid=cid, lever="decision", subject=subject,
                           applied=False, reason=out["reason"],
                           decision_id=out["decision_id"] or "")
                conn.commit()
                return out
            if not _gate_taend(*gate):
                out["reason"] = f"switch slukket: {gate[0]}/{gate[1]}"
                _skriv(conn, cid=cid, lever="decision", subject=subject,
                       applied=False, reason=out["reason"], fund_id=fund_id)
                conn.commit()
                return out
            if (loft := _loft_ramt(conn, "decision", cid)) is not None:
                out["reason"] = loft
                _skriv(conn, cid=cid, lever="decision", subject=subject,
                       applied=False, reason=out["reason"], fund_id=fund_id)
                conn.commit()
                return out
            # Reservationen skrives og committes FOER beslutningen oprettes.
            # (13/11-2026) Ellers kunne to samtidige forsoeg paa samme fund begge
            # passere `_allerede_landet` og oprette hver sin beslutning — og et
            # crash mellem oprettelsen og rydningen ville efterlade fundet uden
            # spor. Den unikke indeks paa `fund_id` goer det haandhaevet i basen.
            #
            # (14/11-2026) MEN RESERVATIONEN ER IKKE EN LANDING. Den skrives med
            # `applied=0`: `applied=1` betyder «fundet flyttede noget», og det
            # goer den foerst naar beslutningen findes. Maalt i drift stod to
            # raekker fast som `reserveret` med `applied=1` fordi opgraderingen
            # ikke ramte dem — og `_allerede_landet` laeste dem som landede.
            # Med `applied=0` er reservationen et claim: indeksen bevarer
            # enkeltheden, mens `_allerede_landet` kun ser FAERDIGE landinger.
            _skriv(conn, cid=cid, lever="decision", subject=subject,
                   applied=False, reason="reserveret", fund_id=fund_id)
            conn.commit()
    except Exception as exc:
        logger.warning("land_decision: kunne ikke skrive landingsraekken for %s: %s", cid, exc)
        out["reason"] = f"fejl: {str(exc)[:120]}"
        return out

    try:
        from core.services.behavioral_decisions import create_decision
        dec = create_decision(
            directive=directive,
            rationale=rationale or None,
            trigger_cue=trigger_cue or None,
            priority=int(priority),
            # (13/11-2026) Fundets identitet foelger med ind i beslutningslaget.
            # Uden den vidste beslutningen ikke hvilken konkret observation den
            # hoerte til, og dens egen dedup (der matcher paa direktiv-TEKST)
            # kunne hverken skelne to fund eller genkende det samme efter et
            # doegnsskifte.
            source_record_id=fund_id or None,
            source_type=f"character:{cid}",
            created_by="jarvis",
        )
        did = str(dec.get("decision_id") or "") or None
        deduped = bool(dec.get("deduped"))
        out.update({"applied": not deduped, "decision_id": did,
                    "reason": "deduped" if deduped else "bundet"})
        with _connect() as conn:
            _ensure(conn)
            if fund_id:
                # Reservationen opgraderes til den faerdige kobling. Fejler den,
                # staar raekken stadig som `reserveret` — fundet er landet, og
                # naeste forsoeg svarer `already_landed` i stedet for at oprette
                # en dublet.
                conn.execute(
                    f"""UPDATE {_TABLE} SET after_value=?, applied=?, reason=?, decision_id=?
                        WHERE fund_id=? AND lever='decision'""",
                    (str(did or "")[:200], 0 if deduped else 1, out["reason"][:300],
                     str(did or ""), fund_id),
                )
            else:
                _skriv(conn, cid=cid, lever="decision", subject=subject,
                       before="", after=str(did or ""), applied=not deduped,
                       reason=out["reason"], decision_id=str(did or ""))
            conn.commit()
        return out
    except Exception as exc:
        # (14/11-2026, GPT's tredje indvending — maalt) Et tabt kaploeb er ikke
        # en fejl. Den unikke indeks paa `source_record_id` afviser den anden
        # beslutning for samme fund — men den anden traad ER landet, af den
        # foerste. Foer stod der «create_decision fejlede: UNIQUE constraint
        # failed» tilbage til kalderen, altsaa en fejl hvor sandheden er «dit
        # fund blev landet, som denne beslutning». Kalderen ville saa proeve
        # igen eller melde et tab der ikke fandtes.
        #
        # Vi spoerger derfor databasen hvem der vandt, og svarer som den gren
        # der allerede findes for «fundet er landet».
        if "UNIQUE constraint failed" in str(exc) and fund_id:
            try:
                with _connect() as conn:
                    _ensure(conn)
                    vinder = _beslutning_for_fund(conn, fund_id)
                    if not vinder:
                        # (14/11-2026, maalt) Vinderen har INDSAT beslutningen
                        # (det er derfor indeksen faldt), men den har endnu ikke
                        # opgraderet spor-raekken — saa opslaget gennem
                        # `central_consequences` svarer None i praecis det
                        # vindue. Beslutningen selv er allerede committet, saa
                        # vi slaar den op hvor den ligger.
                        r = conn.execute(
                            "SELECT decision_id FROM behavioral_decisions "
                            "WHERE source_record_id=? LIMIT 1",
                            (fund_id,),
                        ).fetchone()
                        vinder = str(r[0]) if r and r[0] else None
                if vinder:
                    logger.info(
                        "land_decision: %s tabte kaploebet om %s — landet som %s",
                        cid, fund_id, vinder,
                    )
                    out.update({
                        "applied": False,
                        "decision_id": vinder,
                        "reason": "landet af et samtidigt kald",
                        "already_landed": True,
                    })
                    return out
            except Exception as indre:
                logger.warning(
                    "land_decision: kunne ikke laese vinderen for %s: %s", fund_id, indre
                )
        logger.warning("land_decision: create_decision fejlede for %s: %s", cid, exc)
        out["reason"] = f"create_decision fejlede: {str(exc)[:120]}"
        return out


def _beslutning_for_fund(conn, fund_id: str) -> str | None:
    """Hvilken beslutning blev dette fund oprindeligt landet som?

    Bruges naar et fund forsoeges igen: svaret skal vaere den EKSISTERENDE
    beslutning, ikke `None`. Ellers kunne en kalder der spoerger «blev mit fund
    landet?» faa «ja, men jeg ved ikke som hvad» — og en genstart ville efterlade
    fundet uden sin kobling.
    """
    if not fund_id:
        return None
    r = conn.execute(
        f"""SELECT decision_id FROM {_TABLE}
            WHERE fund_id=? AND lever='decision' AND decision_id != '' LIMIT 1""",
        (fund_id,),
    ).fetchone()
    return str(r[0]) if r and r[0] else None


def record(cid: str, subject: str, *, detail: str = "") -> dict[str, Any]:
    """Fund uden en anvendelig lever: skriv det ned som reviderbart spor.

    Den aerlige tredje mulighed — ikke en undskyldning for at lade vaere, men
    svaret naar der ikke findes et vaern der goer mutationen forsvarlig.
    """
    try:
        with _connect() as conn:
            _ensure(conn)
            # (14/11-2026, maalt) Samme (cid, subject) inden for doegnet er ÉN
            # observation — ikke én pr. kald. Maalt i drift: 157 af 188 raekker
            # var `analyst / observer_effect:variation`, skrevet hvert par
            # minutter i 16 timer. `land_decision` fik denne rettelse 13/11;
            # `record` havde defekten stadig.
            #
            # Den ENE raekke skal baere den NYESTE maaling, ellers fryser
            # dedup'en den foerste og skjuler at observationen udviklede sig.
            # Derfor UPDATE af after_value OG created_at: raekken er «denne
            # observation, senest set nu», ikke «den blev foerst set i gaar».
            cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
            findes = conn.execute(
                f"""SELECT id FROM {_TABLE}
                    WHERE cid=? AND lever='record' AND subject=? AND created_at>=?
                    ORDER BY id DESC LIMIT 1""",
                (cid, subject[:200], cutoff),
            ).fetchone()
            if findes:
                conn.execute(
                    f"UPDATE {_TABLE} SET after_value=?, created_at=? WHERE id=?",
                    (str(detail)[:200], _nu(), findes[0]),
                )
            else:
                _skriv(
                    conn, cid=cid, lever="record", subject=subject,
                    after=detail[:200], applied=False,
                )
            conn.commit()
        return {"applied": False, "reason": "kun registreret"}
    except Exception as exc:
        logger.debug("central_consequence: record fejlede: %s", exc)
        return {"applied": False, "reason": f"fejl: {str(exc)[:120]}"}


def measure_consequences(*, days: int = 7) -> dict[str, Any]:
    """Beviset: hvor mange fund flyttede faktisk noget?

    `applied=1` OG `before != after` er den eneste kombination der taeller som
    en aegte konsekvens. En raekke med `applied=1` uden flytning er en loegn, og
    taelles derfor separat — den slags skal kunne ses, ikke skjules i et snit.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=max(1, int(days)))).isoformat()
    try:
        with _connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                f"""SELECT cid, lever, applied, before_value, after_value
                    FROM {_TABLE} WHERE created_at>=?""",
                (cutoff,),
            ).fetchall()
    except Exception as exc:
        # Maalingen er beviset — fejler den, skal det staa i loggen og ikke kun
        # som et svar der ligner "ingen konsekvenser".
        logger.warning("central_consequence: measure fejlede: %s", exc)
        return {"status": "fejl", "error": str(exc)[:160]}

    per: dict[str, dict[str, int]] = {}
    flyttede = 0
    uden_flytning = 0
    registreret = 0
    for r in rows:
        cid = str(r[0] if not isinstance(r, dict) else r["cid"])
        lever = str(r[1] if not isinstance(r, dict) else r["lever"])
        applied = int(r[2] if not isinstance(r, dict) else r["applied"] or 0)
        before = str(r[3] if not isinstance(r, dict) else r["before_value"] or "")
        after = str(r[4] if not isinstance(r, dict) else r["after_value"] or "")
        # (14/11-2026, maalt) `record` er den aerlige TREDJE mulighed — et fund
        # uden en anvendelig lever. Den er hverken landet eller afvist, og at
        # taelle den som «afvist» gjorde beviset misvisende i den pessimistiske
        # retning: analyst stod med 157 afvisninger hvor den havde registreret
        # ÉN observation. Beviset maalte sin egen stoej.
        if lever == "record":
            registreret += 1
            per.setdefault(cid, {"landet": 0, "afvist": 0, "flyttede": 0, "registreret": 0})
            per[cid]["registreret"] = per[cid].get("registreret", 0) + 1
            continue
        d = per.setdefault(cid, {"landet": 0, "afvist": 0, "flyttede": 0, "registreret": 0})
        if applied:
            d["landet"] += 1
            if before != after:
                d["flyttede"] += 1
                flyttede += 1
            else:
                uden_flytning += 1
        else:
            d["afvist"] += 1
    return {
        "status": "ok",
        "dage": days,
        "i_alt": len(rows),
        "flyttede": flyttede,
        "landet_uden_flytning": uden_flytning,
        "registreret": registreret,
        "per_karakter": per,
        "uden_landing": sorted(c for c, d in per.items() if d["landet"] == 0),
    }
