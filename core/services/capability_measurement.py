"""Fælles skrivevej for MÅLTE capability-værdier.

## Hvorfor den findes

20/11-2026 boede `set_domain_confidence` inde i `desk_render_capability.py`.
Den var ~55 linjer, selvstændig, og havde intet med browser-målinger at gøre —
den skrev blot en målt værdi ind i `confidence_by_domain` med et bevis.

Da den anden måler (`db_schema_capability`) skulle skrive gennem samme vej,
var valget: kopiér 55 linjer, eller flyt dem. Kopien ville drive fra hinanden
præcis som de to cache-hit-kilder gjorde, og så ville to domæner blive skrevet
efter to forskellige regler uden at nogen opdagede det.

## Forskellen fra `task_worker.record_curriculum_outcome`

Den registrering er TRINVIS (+0.05 / −0.03) og bygger på bogholderi — «runnet
kaldte ét værktøj». Denne sætter den målte værdi DIREKTE og kræver derfor en
`evidence`-streng der siger hvad der blev målt. Uden bevis skrives intet.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Målings-loggen. `self_experiments._mekanisk_maalte` skal kunne afgøre om det
#: tal der STÅR i vektoren kom fra en måling eller fra et skøn. Skridt-detektoren
#: kan ikke se forskellen: en måling skriver en absolut værdi (0,32 → 0,85), men
#: en korrektion skriver også et skridt, og et skøn kan lande tilfældigt på 0,05.
#: Sporet gør svaret efterprøveligt i stedet for gættet.
_LEDGER = Path.home() / ".jarvis-v2" / "state" / "capability_measurements.jsonl"


def _skriv_maalingsspor(domain: str, value: float, evidence: str) -> None:
    """Én linje pr. måling. Uden sporet er «målt» et ord uden indhold."""

    def _write() -> None:
        _LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with _LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "domain": domain,
                        "value": value,
                        "evidence": evidence,
                        "measured_at": datetime.now(UTC).isoformat(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    try:
        _write()
    except OSError as exc:
        # Sporet er et supplement, ikke betingelsen for at skrive værdien —
        # men et manglende spor skal kunne ses i loggen, ikke forsvinde.
        logger.warning("capability_measurement: målingsspor kunne ikke skrives: %s", exc)


def maalte_vaerdier() -> dict[str, float]:
    """Domæne → den senest MÅLTE værdi. Tom når sporet ikke findes."""
    if not _LEDGER.exists():
        return {}
    nyeste: dict[str, float] = {}
    try:
        lines = _LEDGER.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("capability_measurement: målingsspor kunne ikke læses: %s", exc)
        return {}
    for linje in lines:
        try:
            rad = json.loads(linje)
            nyeste[str(rad["domain"])] = round(float(rad["value"]), 4)
        except (ValueError, KeyError, TypeError):
            # Uparsbar linje: den kan ikke bære et bevis, så den tælles ikke.
            continue
    return nyeste


def set_domain_confidence(
    domain: str, value: float, *, evidence: str
) -> dict[str, Any]:
    """Sæt domænets confidence til en MÅLT værdi.

    `evidence` er ikke pynt: den er betingelsen for at skrive. En måling uden
    et bevis er en selvrapport med et finere navn.
    """
    from core.runtime.db_cognitive import (
        get_latest_cognitive_personality_vector,
        upsert_cognitive_personality_vector,
    )

    key = " ".join(str(domain or "").lower().split())[:120]
    if not key:
        return {"recorded": False, "reason": "intet domæne"}
    if not str(evidence or "").strip():
        return {"recorded": False, "reason": "målt værdi kræver et bevis"}

    current = get_latest_cognitive_personality_vector() or {}
    try:
        domains = json.loads(str(current.get("confidence_by_domain") or "{}"))
    except ValueError:
        domains = {}
    if not isinstance(domains, dict):
        domains = {}

    existing = next(
        (k for k in domains if str(k).lower().split() == key.split()), None
    )
    name = existing or key
    before = float(domains.get(name, 0.3))
    after = max(0.0, min(1.0, round(float(value), 3)))
    if existing is not None and after == before:
        return {
            "recorded": False,
            "reason": "uændret",
            "before": before,
            "after": after,
            "evidence": evidence,
        }

    domains[name] = after
    upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps(domains, ensure_ascii=False),
        communication_style=str(current.get("communication_style", "{}")),
        learned_preferences=str(current.get("learned_preferences", "[]")),
        recurring_mistakes=str(current.get("recurring_mistakes", "[]")),
        strengths_discovered=str(current.get("strengths_discovered", "[]")),
        current_bearing=str(current.get("current_bearing", "")),
        emotional_baseline=str(current.get("emotional_baseline", "{}")),
    )
    _skriv_maalingsspor(name, after, evidence)
    logger.info(
        "capability_measurement: %s %s -> %s (%s)", name, before, after, evidence
    )
    return {
        "recorded": True,
        "domain": name,
        "before": before,
        "after": after,
        "evidence": evidence,
    }
