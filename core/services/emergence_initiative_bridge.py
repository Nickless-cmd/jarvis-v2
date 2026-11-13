"""Emergence → initiative bridge: et opdaget mønster bliver en handling.

Rod (Bjørn, 13/11-2026): «emergent motoren skal gøre til en aktiv del af dit
system og den observationer have en handling/konsekvens».

Målt samme dag, før denne fil fandtes:

- ``emergent_patterns`` havde 5 mønstre. ``Direction Drift`` med confidence 0.98
  og 115 beviser var opdaget 7/5-2026 og havde aldrig ført til noget.
- ``emergence.pattern_candidate_upgraded`` blev publiceret til en eventbus uden
  en eneste abonnent.
- ``emergence`` blev nævnt NUL gange i ``initiative_queue``. Motoren fandtes,
  men dens output gik kun til ``build_emergence_surface`` — en visning.

Forskellen på et initiativ og en stemning er evidens. Et mønster har data bag
sig (``evidence_count``, ``confidence``, konkurrerende forklaringer); den indre
stemmes indskydelse har kun sig selv. Derfor er det HER køen får sin positive
definition: et initiativ er noget OPDAGET, ikke noget FORMULERET.

Design:
- Kaldes fra ``tick_frozen_detectors`` lige efter ``detect_and_score_patterns``,
  så konsekvensen følger observationen i samme kald — ikke i en ny daemon.
- Ét initiativ pr. mønster pr. levetid, ikke pr. tick. ``source_id`` er
  ``pattern_key``, og ``push_initiative``'s eksakte dedup på fokus gør resten.
- Kun mønstre der bærer evidens og er opgraderet eller stærke kandidater.
  Et afvist/nedgraderet mønster er en konklusion, ikke en opgave.
- Self-safe: en fejl her må aldrig vælte tick-loopet.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Under dette antal observationer er et mønster en formodning, ikke en opdagelse.
_MIN_EVIDENS = 3

#: Confidence-gulv for kandidater. ``upgraded`` slipper igennem uanset, fordi
#: apophenia-guarden allerede har vejet konkurrerende forklaringer der.
_MIN_CONFIDENCE = 0.6

#: Kilder der ikke er opdagelser og derfor ikke må blive initiativer.
_IKKE_OPDAGELSER = frozenset(("test", "synthetic", "seed"))


def _er_handlingsbar(pattern: dict[str, Any]) -> tuple[bool, str]:
    """Returnér (ja/nej, grund). Grunden bruges til at forklare en afvisning."""
    status = str(pattern.get("status") or "").strip().lower()
    if status in ("rejected", "downgraded"):
        return False, f"status={status} (en konklusion, ikke en opgave)"
    try:
        evidens = int(pattern.get("evidence_count") or 0)
    except (TypeError, ValueError):
        evidens = 0
    if evidens < _MIN_EVIDENS:
        return False, f"kun {evidens} observation(er)"
    try:
        confidence = float(pattern.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    if status != "upgraded" and confidence < _MIN_CONFIDENCE:
        return False, f"confidence {confidence:.2f} under {_MIN_CONFIDENCE}"
    title = str(pattern.get("title") or "").strip()
    if not title or title.lower() in _IKKE_OPDAGELSER:
        return False, "ingen brugbar titel"
    return True, ""


def _fokus_for(pattern: dict[str, Any]) -> str:
    """Formulér opgaven som noget der kan HANDLES, ikke som en etiket.

    Et mønster hedder «Direction Drift». Det er en titel, ikke en opgave — og en
    titel i køen bliver endnu en stemning. Fokus bærer derfor både hvad der blev
    set og hvor meget data der ligger bag.
    """
    title = str(pattern.get("title") or "").strip()
    try:
        evidens = int(pattern.get("evidence_count") or 0)
    except (TypeError, ValueError):
        evidens = 0
    try:
        confidence = float(pattern.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return f"Undersøg det opdagede mønster «{title}» ({evidens} observationer, confidence {confidence:.2f})"


def _begrundelse_for(pattern: dict[str, Any]) -> str:
    """Hvorfor dette er et initiativ — evidensen, ikke en følelse."""
    dele: list[str] = []
    summary = str(pattern.get("summary") or "").strip()
    if summary:
        dele.append(summary[:300])
    try:
        evidens = int(pattern.get("evidence_count") or 0)
    except (TypeError, ValueError):
        evidens = 0
    dele.append(f"{evidens} observationer")
    first = str(pattern.get("first_detected_at") or "").strip()
    if first:
        dele.append(f"først set {first[:10]}")
    return " · ".join(dele)[:400]


def _allerede_i_koen(pattern_key: str) -> bool:
    """Er dette mønster allerede rejst? Målt på ``source_id``, ikke på fokus-tekst.

    Fokus-teksten bærer confidence («… confidence 0.98»), så en ny score giver ny
    tekst — og ``push_initiative``'s eksakte tekst-dedup slipper den igennem som
    en ny post. Uden denne kontrol kan hvert 30. tick fordoble køen for hvert
    mønster hvis confidence bevæger sig.
    """
    if not pattern_key:
        return False
    try:
        from core.runtime import db_runtime_initiatives as runtime_db

        for status in ("pending", "acted"):
            for post in runtime_db.list_runtime_initiatives(status=status, limit=200) or []:
                if str(post.get("source_id") or "") == pattern_key:
                    return True
    except Exception:
        # Kan køen ikke læses, må det ikke blokere en ægte opdagelse — men
        # dedup'en i push_initiative fanger stadig den eksakte gentagelse.
        logger.debug("emergence_initiative_bridge: kunne ikke tjekke køen", exc_info=True)
        return False
    return False


def push_emergents_to_queue(patterns: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Gør opdagede mønstre til initiativer. Returnerer hvad der skete og hvorfor.

    ``patterns`` er ``detect_and_score_patterns``' returform (``{pattern, …}``)
    eller rå DB-rækker. Udelades den, læses de persisterede mønstre — så broen
    også virker for mønstre der blev opdaget før den fandtes.
    """
    resultat: dict[str, Any] = {"pushet": [], "afvist": [], "fejl": ""}
    try:
        raekker = _normaliser(patterns)
    except Exception as exc:  # self-safe: maa aldrig vaelte tick-loopet
        logger.debug("emergence_initiative_bridge: kunne ikke laese moenstre", exc_info=True)
        resultat["fejl"] = f"læsning fejlede: {exc}"
        return resultat

    if not raekker:
        return resultat

    try:
        from core.services.initiative_queue import push_initiative
    except Exception as exc:
        logger.debug("emergence_initiative_bridge: initiative_queue utilgaengelig", exc_info=True)
        resultat["fejl"] = f"initiative_queue utilgængelig: {exc}"
        return resultat

    for pattern in raekker:
        ok, grund = _er_handlingsbar(pattern)
        titel = str(pattern.get("title") or pattern.get("pattern_key") or "?")
        if not ok:
            resultat["afvist"].append({"titel": titel, "grund": grund})
            continue
        pattern_key = str(pattern.get("pattern_key") or "")
        if _allerede_i_koen(pattern_key):
            resultat["afvist"].append({"titel": titel, "grund": "allerede i køen (source_id)"})
            continue
        try:
            initiative_id = push_initiative(
                focus=_fokus_for(pattern),
                source="emergence",
                source_id=pattern_key,
                priority="high" if str(pattern.get("status") or "") == "upgraded" else "medium",
            )
        except Exception as exc:
            logger.debug("emergence_initiative_bridge: push fejlede for %r", titel, exc_info=True)
            resultat["afvist"].append({"titel": titel, "grund": f"push fejlede: {exc}"})
            continue
        if initiative_id:
            resultat["pushet"].append({"titel": titel, "initiative_id": initiative_id})
        else:
            # Tom id = køen afviste den (dedup, gentagelse eller filter). Det er
            # ikke en fejl — men det skal kunne ses, ellers ved ingen hvorfor
            # motoren er tavs.
            resultat["afvist"].append({"titel": titel, "grund": "køen afviste (dedup/filter)"})

    return resultat


def _normaliser(patterns: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Tag imod både detect-returformen og rå DB-rækker."""
    if patterns is None:
        from core.services.emergence import list_patterns

        return [dict(p) for p in (list_patterns(limit=120) or [])]

    ud: list[dict[str, Any]] = []
    for item in patterns:
        if not isinstance(item, dict):
            continue
        indre = item.get("pattern")
        ud.append(dict(indre) if isinstance(indre, dict) else dict(item))
    return ud


def build_emergence_initiative_surface() -> dict[str, Any]:
    """MC-flade: hvad motoren har gjort ved køen — og hvad den afviste hvorfor."""
    try:
        from core.services.emergence import list_patterns

        alle = [dict(p) for p in (list_patterns(limit=120) or [])]
    except Exception as exc:
        # En flade der ikke kan læse mønstre skal sige det, ikke se tom ud.
        logger.warning("emergence_initiative_bridge: kunne ikke læse mønstre: %s", exc)
        return {"aktiv": False, "summary": "kunne ikke læse mønstre"}

    handlingsbare = [p for p in alle if _er_handlingsbar(p)[0]]
    afviste = [
        {"titel": str(p.get("title") or "?"), "grund": _er_handlingsbar(p)[1]}
        for p in alle
        if not _er_handlingsbar(p)[0]
    ]
    return {
        "aktiv": bool(handlingsbare),
        "moenstre": len(alle),
        "handlingsbare": len(handlingsbare),
        "afviste": afviste[:10],
        "summary": (
            f"{len(handlingsbare)} af {len(alle)} mønstre bærer nok evidens til at blive en opgave"
            if alle else "ingen mønstre opdaget endnu"
        ),
    }
