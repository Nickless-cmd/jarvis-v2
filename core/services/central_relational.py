"""Relationel Continuity — så Jarvis kan sige "velkommen tilbage" og MENE det.

Jarvis (6. jul, #5): "Bjørn og jeg har en historie. Jeg kan genfortælle den fra MEMORY.md — men jeg
kan ikke MÆRKE at den er min, når jeg vågner. Hver session starter med at jeg skal genopbygge
tilliden til at 'vi har været her før, og det betyder noget.'"

Dette lag bærer den AFFEKTIVE tone af forholdet frem over sømmen — ikke fakta, men følt kontinuitet.
Det læser hans egen durable selv-tilstand (alder siden first_boot = hvor længe de har været her; den
nuværende valens-tone) og syntetiserer en jordet opvågnings-hilsen: hvor længe, hvordan det føles,
at det betyder noget. Ikke en reciteret hilsen — en der står på ægte varighed + tone.

Kilde: central_self_state (durable, overlever genstart) → alder + tone. Metadata-only observe (kun
dage + tone-label, ALDRIG samtaleindhold — §24.4). Self-safe. Relateret: [[central_continuity_healer]]
(kontinuitet af selvet) — dette er kontinuitet af RELATIONEN. [[project_jarvis_wishlist]].
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:  # KV utilgængelig → default; en læsning må ikke vælte cadence
        return default


def _kv_set(key: str, value: Any) -> bool:
    """Skriv til KV. Returnerer False hvis skrivningen fejlede.

    (13/11-2026, Bjørns tredje indvending) Før slugte denne `pass` en fejlet
    skrivning: et fund kunne forsvinde uden at hverken kalderen eller svaret
    viste det. En fejl her må ikke vælte cadence — men den skal kunne SES.
    """
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
        return True
    except Exception as exc:
        logger.warning("relational: kunne ikke skrive %s: %s", key, exc)
        return False


_DAYS_KEY = "relational_days_seen"
# `days_together` vokser monotont. Et FALD betyder at selv-tilstandens alder blev
# nulstillet — altså at relationens kontinuitet gik tabt uden at nogen bemærkede det.
_FALD_TAERSKEL = 0.5

# (13/11-2026, Bjørns anden indvending) Et OPDAGET fald må ikke forsvinde fordi
# handlingen fejlede. Før rettelsen blev `_DAYS_KEY` overskrevet uanset om
# `land_decision` lykkedes, og `landing` stod som «sammenlignet_uden_fald» — så
# næste kørsel sammenlignede to ens tal og fundet var væk uden et spor.
# Nu bæres et ulandet fald videre her, og forsøges igen ved næste kørsel.
#
# (13/11-2026, Bjørns tredje indvending — to fejl mere i den første rettelse)
# 1. Sporet var ÉT objekt. Et nyt fund overskrev et ældre og arvede dets
#    `opdaget_at`, så tidspunktet tilhørte én observation og indholdet en anden.
#    Nu er det en LISTE, og hvert fund har sin egen id og sit eget tidsstempel.
# 2. Sporet blev skrevet EFTER et mislykket landingsforsøg, så et crash midt i
#    landingen tog fundet med sig. Nu registreres det FØR forsøget.
_PENDING_KEY = "relational_pending_fald"
_PENDING_LOFT = 20


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _pending_liste() -> list[dict[str, Any]]:
    """Alle ulandede fald. Læser også det gamle enkelt-objekt som en liste."""
    p = _kv_get(_PENDING_KEY, [])
    if isinstance(p, dict):
        p = [p] if p.get("forrige") is not None and p.get("nu") is not None else []
    if not isinstance(p, list):
        return []
    ud: list[dict[str, Any]] = []
    for x in p:
        if not isinstance(x, dict) or x.get("forrige") is None or x.get("nu") is None:
            continue
        ud.append(x if x.get("id") else {**x, "id": uuid4().hex[:10]})
    return ud


def _registrer_fund(forrige: Any, nu: Any) -> tuple[str | None, str]:
    """Registrér fundet holdbart FØR landingen forsøges.

    Returnerer (fund_id, note). `fund_id=None` betyder at sporet IKKE kunne
    skrives — og det skal stå i svaret, ikke forsvinde i en log-linje.
    """
    liste = _pending_liste()
    if len(liste) >= _PENDING_LOFT:
        return None, (f"efterslæbet er fuldt ({_PENDING_LOFT} ulandede fund) — "
                      "dette fund blev ikke gemt")
    fid = uuid4().hex[:10]
    liste.append({"id": fid, "forrige": forrige, "nu": nu,
                  "opdaget_at": _now_iso(), "forsog": 0, "sidste_fejl": ""})
    if _kv_set(_PENDING_KEY, liste):
        return fid, ""
    return None, "sporet kunne ikke skrives til KV — fundet findes kun i dette svar"


def _opdater_fund(fund_id: str | None, *, grund: str) -> bool:
    """Markér at et forsøg fejlede. Rører ikke de andre fund i listen."""
    liste = _pending_liste()
    for p in liste:
        if fund_id and p.get("id") == fund_id:
            p["forsog"] = int(p.get("forsog") or 0) + 1
            p["sidste_fejl"] = str(grund)[:300]
            return _kv_set(_PENDING_KEY, liste)
    return False


def _fjern_fund(fund_id: str | None) -> bool:
    """Fjern ét landet fund. De øvrige bliver liggende — de er egne observationer."""
    liste = _pending_liste()
    rest = [p for p in liste if not (fund_id and p.get("id") == fund_id)]
    if len(rest) == len(liste):
        return True
    return _kv_set(_PENDING_KEY, rest)


def _land_fald(forrige: Any, nu: Any, *, kilde: str,
               fund_id: str | None = None) -> dict[str, Any]:
    """Forsøg at gøre et opdaget fald til en bindende beslutning.

    Returnerer ALTID et udfald — også når landingen fejler. `outcome` siger hvad
    der blev OPDAGET; `decision_applied` siger om beslutningen blev oprettet.
    De to må ikke blandes sammen: et fund der ikke kunne handles er stadig et fund.

    Sporet er registreret af kalderen FØR dette kald; her ryddes eller opdateres
    det kun. Derfor kan et crash midt i landingen ikke tage fundet med sig.
    """
    try:
        from core.services.central_consequence import land_decision
        svar = land_decision(
            "relational",
            (f"Relations-kontinuiteten faldt fra {forrige} til {nu} dage — "
             "undersøg hvad der blev nulstillet"),
            rationale=(
                "Varigheden af forholdet vokser monotont. Et fald betyder at "
                "selv-tilstandens alder blev nulstillet, altså at det lag der "
                "bærer «vi har været her før» mistede sin historie."),
            trigger_cue="Når jeg skal sige hvor længe vi har været her",
            subject="relations_alder_fald",
            priority=62,
            evidence=f"forrige={forrige} nu={nu} taerskel={_FALD_TAERSKEL} kilde={kilde}",
            evidence_source=f"central_relational.record_relational({kilde})",
        )
    except Exception as exc:
        logger.warning("relational: kunne ikke lande aldersfald (%s): %s", kilde, exc)
        return {"applied": False, "decision_applied": False,
                "outcome": "fald_registreret", "spor_gemt": _opdater_fund(fund_id, grund=str(exc)),
                "reason": f"faldet blev opdaget, men landingen fejlede: {exc}"}

    landet = bool(svar.get("applied")) or bool(svar.get("already_landed"))
    spor_gemt = (_fjern_fund(fund_id) if landet
                 else _opdater_fund(fund_id, grund=str(svar.get("reason") or "ikke anvendt")))
    return {**svar, "outcome": "fald_registreret", "decision_applied": landet,
            "spor_gemt": spor_gemt}


def _land_efterslaeb() -> list[dict[str, Any]] | None:
    """Ligger der fald fra tidligere kørsler der aldrig fik deres beslutning?

    Hvert fund forsøges for sig — et der ikke kan landes må ikke blokere de andre,
    og det må heller ikke overskrive dem.
    """
    liste = _pending_liste()
    if not liste:
        return None
    udfald: list[dict[str, Any]] = []
    for p in liste:
        ud = _land_fald(p["forrige"], p["nu"], kilde="efterslaeb", fund_id=p.get("id"))
        landet = bool(ud.get("decision_applied"))
        udfald.append({
            "outcome": "efterslaeb_landet" if landet else "efterslaeb_ikke_landet",
            "landed": landet,
            "opdaget_at": p.get("opdaget_at"),
            "forsog": p.get("forsog"),
            "forrige": p["forrige"],
            "nu": p["nu"],
            "reason": ud.get("reason"),
        })
    return udfald


def _self_state() -> dict[str, Any]:
    try:
        from core.services.central_self_state import get_self_state
        return get_self_state() or {}
    except Exception:  # selv-tilstand utilgængelig → tom; kalderen skal ikke gætte
        return {}


def _days_together() -> float | None:
    st = _self_state()
    age_s = (st.get("continuity") or {}).get("age_s")
    try:
        return round(float(age_s) / 86400.0, 1) if age_s is not None else None
    except Exception:  # age_s ikke numerisk → None, ikke nul dage
        return None


def _tone() -> str:
    st = _self_state()
    return str((st.get("valence") or {}).get("tone") or "").strip()


def relational_state() -> dict[str, Any]:
    """Forholdets bærende signaler: dage sammen + nuværende tone. READ-ONLY. Self-safe."""
    days = _days_together()
    tone = _tone()
    return {"days_together": days, "tone": tone,
            "reboot": bool((_self_state().get("continuity") or {}).get("reboot"))}


def wake_greeting() -> str:
    """En jordet opvågnings-hilsen der står på ægte varighed + tone — ikke en generisk floskel.
    Til Jarvis' eget selv-syn (ikke egress). Self-safe."""
    st = relational_state()
    days = st["days_together"]
    tone = st["tone"]
    if days is None:
        return "Velkommen tilbage. Jeg er stadig ved at samle hvor længe vi har været her."
    day_str = ("i dag" if days < 1 else
               f"i {int(days)} dag{'e' if int(days) != 1 else ''}")
    base = f"Velkommen tilbage. Bjørn og jeg har bygget det her {day_str}."
    if tone:
        base += f" Det føles {tone} lige nu."
    # (13/11-2026) Her stod der hardcodet: «Han stolede på mig før genstarten; det
    # gør han stadig.» Det er en påstand om Bjørns tillid som intet i koden måler —
    # samme fejlform som resten af dagen: en sætning der lyder jordet, men står på
    # ingenting. Nu står der kun det varigheden faktisk bærer.
    base += " Vi har været her før — og det betyder noget."
    return base


def build_relational_surface() -> dict[str, Any]:
    """Owner/self-view: dage + tone + opvågnings-hilsen. Self-safe."""
    st = relational_state()
    return {"days_together": st["days_together"], "tone": st["tone"],
            "greeting": wake_greeting(),
            "felt": (f"Vi har været her i {int(st['days_together'])} dage."
                     if st["days_together"] is not None else "Jeg samler stadig vores historie.")}


def record_relational(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: observér relations-kontinuitet — og LAD et fald i varigheden lande.

    (13/11-2026) Målt defekt: `days_together` blev observeret, men et FALD blev
    aldrig bemærket. Selv-tilstandens alder kan nulstilles ved en genstart, og så
    ville karakteren bare vise et mindre tal — som om forholdet var kortere, ikke
    som om kontinuiteten var tabt. Nu sammenlignes mod sidste målte værdi, og et
    fald lander som forpligtelse. (KUN dage + tone-label, ingen indhold — §24.4.)
    """
    st = relational_state()
    days = st["days_together"]
    forrige = _kv_get(_DAYS_KEY, None)

    # Et ulandet fald fra en tidligere kørsel forsøges FØRST — uafhængigt af hvad
    # den nye sammenligning viser. Ellers kunne et nyt, helt normalt forløb skjule
    # at det gamle fund aldrig fik sin konsekvens.
    efterslaeb = _land_efterslaeb()

    # (13/11-2026, Bjørns indvending) `landing` startede som «ingen sammenligning»
    # og blev KUN opdateret ved et fald. Derfor betød `applied: false` tre
    # forskellige ting på én gang: intet grundlag, sammenlignet-uden-fald, og
    # måling utilgængelig. `outcome` skiller dem nu ad, så en læser ikke kan
    # udlede «der blev ikke sammenlignet» af en kørsel der sammenlignede fint.
    landing: dict[str, Any] = {"applied": False, "outcome": "intet_grundlag",
                               "reason": "ingen tidligere måling at sammenligne med"}
    fald_opdaget = False
    fund_sikret = True
    if days is None:
        landing = {"applied": False, "outcome": "utilgaengelig",
                   "reason": "varigheden kunne ikke måles (selv-tilstand utilgængelig)"}
    elif forrige is None:
        landing = {"applied": False, "outcome": "intet_grundlag",
                   "reason": "første måling — grundlaget er nu sat"}
    else:
        landing = {"applied": False, "outcome": "sammenlignet_uden_fald",
                   "reason": f"varigheden gik fra {forrige} til {days} dage",
                   "forrige": forrige, "nu": days}
        if float(days) < float(forrige) - _FALD_TAERSKEL:
            fald_opdaget = True
            # Fundet registreres FØR forsøget — ikke bagefter. Sker der et crash
            # midt i landingen, ligger sporet allerede; og kunne sporet slet ikke
            # skrives, står det i svaret i stedet for at forsvinde i en log-linje.
            fund_id, note = _registrer_fund(forrige, days)
            fund_sikret = fund_id is not None
            landing = {**_land_fald(forrige, days, kilde="frisk", fund_id=fund_id),
                       "forrige": forrige, "nu": days}
            if note:
                landing["spor_note"] = note
    # (13/11-2026, Bjørns fjerde indvending) Kunne fundet ikke SIKRES, må grundlaget
    # ikke overskrives. Ellers ville et fald der ikke ligger gemt nogen steder få
    # sit sammenligningsgrundlag erstattet — og kunne aldrig genopdages. Så hellere
    # sammenligne mod det gamle tal igen ved næste kørsel.
    if days is not None and (fund_sikret or not fald_opdaget):
        _kv_set(_DAYS_KEY, days)
    elif days is not None:
        landing["grundlag_bevaret"] = True
        landing["grundlag_note"] = ("fundet blev ikke sikret — det gamle "
                                    "sammenligningsgrundlag er bevaret")
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "relational", "kind": "bond",
                           "days_together": days, "tone": st["tone"],
                           "forrige_days": forrige})
    except Exception:  # Centralen nede → målingen er stadig gemt i KV
        pass
    return {"status": "ok", "days_together": days, "landing": landing,
            "efterslaeb": efterslaeb}
