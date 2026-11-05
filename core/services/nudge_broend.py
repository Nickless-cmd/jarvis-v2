"""Nudge-broend — daemons drop nudges, Jarvis inspects and decides.

A persistent store for pending proactive messages. Daemons call push() to
deposit. The visible Jarvis calls inspect/pull/send/dismiss to decide what
reaches the user.

Structure: JSON file at ~/.jarvis-v2/state/nudge_broend.json
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_PATH = Path.home() / ".jarvis-v2" / "state" / "nudge_broend.json"
_MAX_NUDGES = 300  # auto-clean oldest dismissed/sent

#: Kadence-loftet (eskaleringstrappen, besluttet 5/11-2026): højst én prik pr.
#: emne pr. dag. Loftet er ikke kosmetik — det er forudsætningen for at trin 4
#: («hold op, men vent på et skift») kan eksistere. En stemme der aldrig holder
#: op er ikke vedholden, den er død for tillid.
_KADENCE_MIN_INTERVAL = timedelta(hours=24)

#: Trin 4's tilstand. Den er ikke `dismissed` (opgivet) og ikke `pending`
#: (klar til at blive sagt): den venter på at verden flytter sig.
STATUS_VENTER = "venter"

#: Hvor længe en registreret ændring må være gammel og stadig tælle som «et
#: skift der er tilgængeligt» for en hvilende nudge. Uden et vindue ville en
#: nudge fra i sidste uge blive genoptaget af et skift fra i går aftes.
_SKIFT_VINDUE = timedelta(hours=72)


def _load() -> list[dict[str, Any]]:
    if not _STORAGE_PATH.exists():
        return []
    try:
        with _STORAGE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("nudge_broend: load failed: %s", exc)
    return []


def _save(nudges: list[dict[str, Any]]) -> None:
    try:
        _STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STORAGE_PATH.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(nudges, f, ensure_ascii=False, indent=2)
        tmp.replace(_STORAGE_PATH)
    except Exception as exc:
        logger.warning("nudge_broend: save failed: %s", exc)


def _cleanup(nudges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove oldest non-pending nudges if over max.

    ``venter`` beskyttes som ``pending``: en hvilende nudge er en åben dør, og
    en oprydning der kaster den væk gør trin 4 til tavshed — præcis den fejl
    tilstanden findes for at undgå.
    """
    if len(nudges) <= _MAX_NUDGES:
        return nudges
    beskyttet = [n for n in nudges if n.get("status") in ("pending", STATUS_VENTER)]
    non_pending = sorted(
        [n for n in nudges if n.get("status") not in ("pending", STATUS_VENTER)],
        key=lambda n: n.get("created_at", ""),
        reverse=True,
    )
    return beskyttet + non_pending[:_MAX_NUDGES - len(beskyttet)]


def push(
    *,
    source: str = "",
    kind: str = "info",
    message: str = "",
    importance: str = "normal",
    raw_payload: dict[str, Any] | None = None,
    emne: str = "",
) -> str:
    """Deposit a nudge in the broend. Returns nudge_id.

    ``emne`` er emne-nøglen (trin 4, 5/11-2026). To nudges med samme emne er
    samme sag set to gange — det er den nøgle kadence-loftet tæller på. Uden
    den kan loftet ikke skelne «han nævner opvasken igen» fra «han nævner noget
    nyt», og så tæller det alt som ét emne.
    """
    nudges = _load()
    nudge_id = f"nudge-{uuid4().hex[:10]}"
    entry = {
        "nudge_id": nudge_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "pending",
        "source": source[:100],
        "kind": kind[:50],
        "message": message[:1000],
        "importance": importance[:20],
        "emne": (emne or _emne_for(source, message))[:120],
        "trin": 1,
        "prik": 0,
    }
    if raw_payload:
        entry["raw"] = raw_payload
    nudges.append(entry)
    _save(_cleanup(nudges))
    logger.info("nudge_broend: %s deposited from %s (importance=%s)", nudge_id, source, importance)
    # Dual-write to outbound_nudges DB (2026-05-13): nudges used to live
    # ONLY in JSON brønden — never reached Jarvis' prompt. Now mirrors to
    # the unified ledger so awareness picks them up. Kind passed through so
    # Matrix-character nudges (kind="matrix_character") surface correctly.
    try:
        from core.services.outbound_nudges import push_nudge
        _kind = kind[:50] if kind and kind not in ("info", "") else "action_router"
        push_nudge(
            source=source or "action_router",
            kind=_kind,
            message=message,
            importance=importance if importance in {"low", "normal", "high", "critical"} else "normal",
        )
    except Exception as exc:
        logger.debug("nudge_broend: dual-write to outbound_nudges failed: %s", exc)
    return nudge_id


def list_pending(limit: int = 10) -> list[dict[str, Any]]:
    """List pending nudges, newest first.

    Nudges i ``venter`` er bevidst udeladt: de er ikke klar til at blive sagt.
    Det er hele forskellen mellem trin 4 og trin 1.
    """
    nudges = _load()
    pending = [n for n in nudges if n.get("status") == "pending"]
    pending.sort(key=lambda n: n.get("created_at", ""), reverse=True)
    return pending[:limit]


def _emne_for(source: str, message: str) -> str:
    """Udled en emne-nøgle når kalderen ikke giver en.

    Kilden alene er for grov (én daemon kan melde om mange ting), og beskeden
    alene er for skør (den ændrer sig ved hver formulering). Kilde + de første
    indholdsord er den mindste nøgle der stadig samler samme sag.
    """
    ord_ = [
        w.strip(".,:;!?()[]\"'").lower()
        for w in str(message or "").split()
        if len(w.strip(".,:;!?()[]\"'")) > 3
    ]
    hale = "-".join(ord_[:4]) or "ukendt"
    return f"{str(source or 'ukendt')[:40]}:{hale}"[:120]


def _parse_ts(value: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):  # ukendt/ugyldigt tidsstempel → None = «tid ukendt»
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def sidst_naevnt(emne: str) -> datetime | None:
    """Hvornår emnet sidst blev SAGT. None = aldrig.

    Kun ``sent`` tæller. En nudge der blev flyttet til ``venter`` uden at blive
    sagt er ikke en prik — den er et spørgsmål der blev holdt tilbage. Tæller
    man den med, låser loftet sig selv: en hvilende nudge kan aldrig genoptages,
    fordi det tidspunkt den blev lagt til hvile på ville blokere for den.
    """
    nyeste: datetime | None = None
    for n in _load():
        if n.get("emne") != emne:
            continue
        if n.get("status") != "sent":
            continue
        ts = _parse_ts(n.get("sent_at") or n.get("created_at"))
        if ts and (nyeste is None or ts > nyeste):
            nyeste = ts
    return nyeste


def kadence_tillader(emne: str, *, nu: datetime | None = None) -> bool:
    """Må emnet nævnes nu? Højst én prik pr. emne pr. dag."""
    nu = nu or datetime.now(UTC)
    sidst = sidst_naevnt(emne)
    if sidst is None:
        return True
    return (nu - sidst) >= _KADENCE_MIN_INTERVAL


def mark_venter(nudge_id: str, *, grund: str = "kadence-loft") -> bool:
    """Trin 4: flyt en nudge til ``venter`` — ikke kasseret, ikke gentaget.

    Forskellen fra ``mark_dismissed`` er hele pointen: en afvist nudge er
    opgivet, en hvilende nudge holder døren åben. Den bevarer emne-nøglen,
    antallet af prik og tidspunktet, så trin 5 kan genoptage den som et nyt
    tilbud i stedet for en gentagelse.
    """
    nudges = _load()
    for n in nudges:
        if n.get("nudge_id") != nudge_id:
            continue
        if n.get("status") not in ("pending", STATUS_VENTER):
            return False
        n["status"] = STATUS_VENTER
        n["venter_siden"] = datetime.now(UTC).isoformat()
        n["venter_grund"] = str(grund)[:120]
        # Prik tælles KUN ved afsendelse (mark_sent). En nudge der hviler tre
        # gange uden at være sagt er ikke sagt tre gange — tæller man her,
        # ser den ud som en gentagelse den aldrig var.
        n["trin"] = 4
        _save(nudges)
        return True
    return False


def list_ventende(limit: int = 20) -> list[dict[str, Any]]:
    """Nudges der venter på at verden flytter sig."""
    ventende = [n for n in _load() if n.get("status") == STATUS_VENTER]
    ventende.sort(key=lambda n: n.get("venter_siden", ""), reverse=True)
    return ventende[:limit]


def genoptag_ved_skift(
    skift: dict[str, Any] | None,
    *,
    nu: datetime | None = None,
) -> list[dict[str, Any]]:
    """Trin 5: genoptag hvilende nudges NÅR et registreret skift er tilgængeligt.

    ``skift`` er et percept fra sanse-broen (``change_type`` = ``sensory-change-*``,
    ``evidence.change_kind`` = ``mood_shift`` m.fl.). Er der intet skift, eller er
    det for gammelt, genoptages INTET — det er den betingelse der gør trin 5 til
    andet end «prik igen efter X dage».

    Returnerer de nudges der blev flyttet tilbage til ``pending``, hver med
    ``genoptaget_ved`` og en tilbudsformulering der spørger i stedet for at gentage.
    """
    nu = nu or datetime.now(UTC)
    if not isinstance(skift, dict) or not skift:
        return []

    observed = _parse_ts(skift.get("observed_at"))
    if observed is None or (nu - observed) > _SKIFT_VINDUE:
        return []

    change_type = str(skift.get("change_type") or "")
    if not change_type.startswith("sensory-change-"):
        return []

    evidence = skift.get("evidence") if isinstance(skift.get("evidence"), dict) else {}
    skift_kind = str(evidence.get("change_kind") or change_type)
    beskrivelse = str(skift.get("summary") or change_type)[:160]

    nudges = _load()
    ventende = [n for n in nudges if n.get("status") == STATUS_VENTER]
    if not ventende:
        return []

    # Ét tilbud pr. skift — ikke en maskinpistol. Et stemningsskift der
    # genoptager baade opvasken og «ring til tandlaegen» er ikke et tilbud,
    # det er en byge. Vi vaelger den sag der har ventet laengst paa netop et
    # skift, med vigtighed som foerste noegle.
    _rang = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    ventende.sort(
        key=lambda n: (
            _rang.get(str(n.get("importance") or "normal"), 2),
            str(n.get("venter_siden") or ""),
        )
    )

    valgt: dict[str, Any] | None = None
    for n in ventende:
        if not kadence_tillader(str(n.get("emne") or ""), nu=nu):
            continue
        valgt = n
        break
    if valgt is None:
        return []

    valgt["status"] = "pending"
    valgt["trin"] = 5
    valgt["genoptaget_ved"] = {
        "emne": str(valgt.get("emne") or ""),
        "change_type": change_type,
        "change_kind": skift_kind,
        "observed_at": str(skift.get("observed_at") or ""),
        "summary": beskrivelse,
    }
    valgt["tilbud"] = (
        f"Skal vi tage den nu, eller lader vi den stå? "
        f"(noget har flyttet sig: {beskrivelse})"
    )[:400]
    _save(nudges)
    return [valgt]


# ── Trin 0-3: grovheden styres af HISTORIK, ikke af et valg (5/11-2026) ──────
#
# Trappen er besluttet i samtale 5/11-2026. Trin 4-5 (hvile/genoptag) laa
# allerede her; trin 0-3 er formulerings-laget UNDER dem:
#
#   0  Ser det, siger intet       — registreret, ikke sagt
#   1  Nævner det i forbifarten    — én sætning, ingen opfordring
#   2  Nævner det med historik     — «det stod der også før», stadig ingen opfordring
#   3  Siger det direkte           — må gerne spørge om handling
#
# Uden dette lag er «trin» et felt nogen sætter i hånden. Med det er grovheden
# en funktion af hvor mange gange emnet faktisk er sagt — og det er den eneste
# definition der ikke kan lyve om sig selv.

#: Hvor mange dage der skal gå før et emne rykker op uden at være sagt igen.
_TRIN_DAGE = (1.0, 3.0)  # til trin 2 og trin 3


def trin_for(emne: str, *, nu: datetime | None = None) -> int:
    """Hvilket trin er emnet på? 0-3, beregnet af historikken.

    Kun ``sent`` tæller som «sagt» — en hvilende nudge er et spørgsmål der blev
    holdt tilbage, ikke en prik. Det er samme regel som ``sidst_naevnt``.
    """
    nu = nu or datetime.now(UTC)
    sagt = [
        n for n in _load()
        if n.get("emne") == emne and n.get("status") == "sent"
    ]
    if not sagt:
        return 0
    antal = len(sagt)
    nyeste: datetime | None = None
    for n in sagt:
        ts = _parse_ts(n.get("sent_at") or n.get("created_at"))
        if ts and (nyeste is None or ts > nyeste):
            nyeste = ts
    dage = ((nu - nyeste).total_seconds() / 86400.0) if nyeste else 0.0

    if antal >= 3 or dage >= _TRIN_DAGE[1]:
        return 3
    if antal >= 2 or dage >= _TRIN_DAGE[0]:
        return 2
    return 1


def formuler_for_trin(trin: int, message: str, emne: str = "") -> str:
    """Formulér beskeden efter trinnet. Grovheden er FORMEN, ikke indholdet.

    Trin 0 returnerer ``""``: den skal ikke siges. Det er ikke en fejl at få en
    tom streng tilbage — det er trinnet der virker.
    """
    tekst = " ".join(str(message or "").split())
    if not tekst or trin <= 0:
        return ""
    if trin == 1:
        return tekst[:1000]
    if trin == 2:
        return f"Forresten — {tekst} Det har stået der før."[:1200]
    return f"{tekst} Skal vi gøre noget ved det nu?"[:1200]


def count_pending() -> int:
    """Return count of pending nudges."""
    nudges = _load()
    return sum(1 for n in nudges if n.get("status") == "pending")


def get(nudge_id: str) -> dict[str, Any] | None:
    """Get a single nudge by ID."""
    nudges = _load()
    for n in nudges:
        if n.get("nudge_id") == nudge_id:
            return n
    return None


def mark_sent(nudge_id: str, *, trin: int | None = None) -> bool:
    """Mark a nudge as sent.

    ``trin`` er det trin beskeden blev formuleret paa (0-3). Gives det ikke,
    bevares nudgens eget trin — men en afsendelse er altid mindst trin 1.
    """
    nudges = _load()
    for n in nudges:
        if n.get("nudge_id") == nudge_id and n.get("status") == "pending":
            n["status"] = "sent"
            n["sent_at"] = datetime.now(UTC).isoformat()
            # Prik tælles ved afsendelse — det er dét kadence-loftet måler på.
            n["prik"] = int(n.get("prik") or 0) + 1
            n["trin"] = int(trin) if trin is not None else max(1, int(n.get("trin") or 1))
            _save(nudges)
            return True
    return False


def mark_dismissed(nudge_id: str, reason: str = "") -> bool:
    """Mark a single nudge as dismissed."""
    nudges = _load()
    for n in nudges:
        if n.get("nudge_id") == nudge_id and n.get("status") == "pending":
            n["status"] = "dismissed"
            n["dismissed_at"] = datetime.now(UTC).isoformat()
            if reason:
                n["dismiss_reason"] = reason[:200]
            _save(nudges)
            return True
    return False


def dismiss_all(reason: str = "") -> int:
    """Dismiss all pending nudges. Returns count."""
    nudges = _load()
    count = 0
    now = datetime.now(UTC).isoformat()
    for n in nudges:
        if n.get("status") == "pending":
            n["status"] = "dismissed"
            n["dismissed_at"] = now
            if reason:
                n["dismiss_reason"] = reason[:200]
            count += 1
    if count:
        _save(nudges)
    return count


