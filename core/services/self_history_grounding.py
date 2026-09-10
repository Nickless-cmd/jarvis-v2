"""Prompten maa ikke forveksle et rygte med en kendsgerning.

Her naar alt det foregaaende prompten, og her afgoeres det om Jarvis kan
skelne mellem tre par der ellers flyder sammen:

  * hvad han HAR OBSERVERET   mod   hvad nogen har SAGT til ham,
  * hvad han er FORTOLKET til at vaere   mod   hvad der er maalt,
  * hvad et alias BEVISER (at et navn peger et sted)   mod   hvad det IKKE
    beviser (at en ny model er rullet ud bag navnet).

EN MODSIGELSE MAERKES, den loeses ikke i stilhed. At vaelge én side uden at
sige det er den vaerste udgave: laeseren tror han ser hele billedet.

SEKTIONEN KOMMER KUN NAAR DER SPOERGES. En grounding-blok i hver eneste tur
ville laere modellen at ignorere den — og saa ville den vaere vaerre end
ingenting, fordi den ser ud til at virke.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QueryProfile:
    wants_grounding: bool = False
    wants_self_history: bool = False
    wants_model_truth: bool = False
    wants_world_fact: bool = False
    terms: list[str] = field(default_factory=list)


# Bevidst SMALLE moenstre. En bred udloeser ville saette blokken i hver tur.
_SELV_HISTORIK = (
    r"\b(sagde|mente|troede) du .*(dig selv|din egen)",
    r"\b(din|dit) selv(opfattelse|billede|model)",
    r"\bself[- ]?model\b",
    r"\bhvad er du blevet (bedre|daarligere|værre) til\b",
    r"\bhar du (ændret|udviklet) dig\b",
    r"\bwhat did you (say|think) about yourself\b",
)
_MODEL_SANDHED = (
    r"\bhvilken model\b",
    r"\bwhich model\b",
    r"\bhvad kører du på\b",
    r"\bwhat (model|backend) (actually )?(answered|served|responded)\b",
    r"\bsvarede egentlig\b",
)
_VERDENS_FAKTA = (
    r"\ber .* (offentlig|udgivet|public|published)\b",
    r"\bis .* (public|published|open source)\b",
    r"\bpassede det\b",
)


def classify_self_history_query(text: str) -> QueryProfile:
    """Hvad spoerges der om? Deterministisk, uden model."""
    t = str(text or "").strip().lower()
    if not t:
        return QueryProfile()
    selv = any(re.search(m, t) for m in _SELV_HISTORIK)
    model = any(re.search(m, t) for m in _MODEL_SANDHED)
    verden = any(re.search(m, t) for m in _VERDENS_FAKTA)
    return QueryProfile(
        wants_grounding=bool(selv or model or verden),
        wants_self_history=selv, wants_model_truth=model, wants_world_fact=verden,
        terms=[o for o in re.findall(r"[a-zæøå0-9-]{4,}", t)][:8],
    )


def _verdens_fakta(limit: int = 6) -> list[dict]:
    from core.runtime.db_world_self_truth import select_world_facts
    return list(select_world_facts(limit=limit) or [])


def _emner(limit: int = 6) -> list[dict]:
    from core.runtime.db_world_self_truth import select_conversation_topics
    return list(select_conversation_topics(limit=limit) or [])


def _selvbilleder(limit: int = 3) -> list[dict]:
    from core.services.self_model_history import list_self_model_snapshots
    return list(list_self_model_snapshots(limit=limit) or [])


def _model_epoke() -> dict | None:
    from core.runtime.db_core import connect
    from core.services.provider_model_epochs import _ensure, _row
    with connect() as conn:
        _ensure(conn)
        return _row(conn.execute(
            "SELECT * FROM provider_model_epochs "
            "ORDER BY last_seen_at DESC, rowid DESC LIMIT 1").fetchone())


def build_self_history_grounding_section(text: str, *, session_id: str = "") -> str | None:
    """Byg blokken — eller `None` naar der ikke spoerges om noget af det."""
    profil = classify_self_history_query(text)
    if not profil.wants_grounding:
        return None

    dele: list[str] = ["## Grundlag for spørgsmål om dig selv og verden"]

    if profil.wants_world_fact:
        try:
            fakta = _verdens_fakta()
        except Exception:
            logger.warning("kunne ikke laese verdens-fakta", exc_info=True)
            fakta = []
        if fakta:
            dele.append("\n### Efterprøvede kendsgerninger")
            for f in fakta[:4]:
                dele.append(
                    f"- [{f.get('status')}/{f.get('confidence')}] "
                    f"{f.get('statement')} (kilde: {f.get('source_kind')}"
                    f"{', ' + str(f.get('source_ref')) if f.get('source_ref') else ''})")
        try:
            emner = _emner()
        except Exception:
            emner = []
        if emner:
            # EMNER ER IKKE FAKTA. Overskriften siger det, og hver linje siger
            # det igen — en laeser der kun ser linjen skal ogsaa vide det.
            dele.append("\n### Omtalt i samtaler (dette er IKKE efterprøvet)")
            for e in emner[:3]:
                dele.append(
                    f"- «{e.get('title')}» — samtale-emne, "
                    f"{e.get('support_count', 0)} kørsel/kørsler i "
                    f"{e.get('session_count', 0)} session(er). At det er blevet "
                    "omtalt siger intet om at det er sandt.")
            if fakta:
                dele.append(
                    "\nSTÅR DE I MODSTRID: den efterprøvede kendsgerning gælder. "
                    "Sig at der er en modstrid frem for at vælge side i stilhed.")

    if profil.wants_self_history:
        try:
            billeder = _selvbilleder()
        except Exception:
            logger.warning("kunne ikke laese selvbilleder", exc_info=True)
            billeder = []
        if billeder:
            dele.append("\n### Dine seneste selvbilleder (FORTOLKEDE, ikke målte)")
            for b in billeder:
                dele.append(
                    f"- v{b.get('version')} ({b.get('created_at', '')[:16]}): "
                    f"fokus «{b.get('identity_focus')}», spænding "
                    f"«{b.get('recurring_tension')}», retning "
                    f"«{b.get('growth_direction')}» — tillid {b.get('confidence')}")
            dele.append(
                "Disse er DESTILLEREDE FORTOLKNINGER af dine egne ture, ikke "
                "målinger af hvad du er. Et skift kan lige så godt skyldes "
                "hvad der blev talt om som en ændring i dig.")

    if profil.wants_model_truth:
        try:
            epoke = _model_epoke()
        except Exception:
            logger.warning("kunne ikke laese model-epoken", exc_info=True)
            epoke = None
        if epoke is None:
            dele.append(
                "\n### Model\nVi har ingen observation af hvilken model der "
                "svarede. Det betyder at vi IKKE VED det — ikke at intet skiftede.")
        else:
            dele.append("\n### Model: ønsket mod observeret")
            dele.append(
                f"- Bedt om: `{epoke['requested_model']}` — svaret kom fra "
                f"`{epoke['observed_model']}` ({epoke['provider']}), set "
                f"{epoke['observation_count']} gang(e).")
            if epoke.get("previous_observed_model"):
                dele.append(
                    f"- Skiftede fra `{epoke['previous_observed_model']}` "
                    f"den {str(epoke['first_seen_at'])[:16]}.")
            dele.append(
                "ET ALIAS BEVISER IKKE EN UDRULNING. At navnet peger et andet "
                "sted viser at NAVNET blev flyttet — ikke at en ny model er "
                "rullet ud bag det. Sig hvad du har set, ikke hvad det kunne "
                "betyde.")

    if len(dele) == 1:
        return None                 # der blev spurgt, men vi har intet at svare med
    return "\n".join(dele)
