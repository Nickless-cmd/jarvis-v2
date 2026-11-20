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

Den registrering er TRINVIS (+0.05 / −0.03) og byggede på bogholderi — «runnet
kaldte ét værktøj». Den er fjernet 20/11-2026, fordi den gjorde arbejde til en
måling. Denne sætter den målte værdi DIREKTE og kræver derfor en `evidence`-
streng der siger hvad der blev målt. Uden bevis skrives intet.

## To ting sporet SKAL kunne, som det ikke kunne i første udgave

1. **Skelne en måling fra en rettelse.** Begge skriver et skridt i
   `confidence_by_domain`. Uden `kind` blev en tilbagerulning af et forkert
   løft læst som «domænet er målt» — og så kunne et spøgelse blive stående som
   en målt svaghed. Kun `kind="measurement"` tæller.
2. **Ikke kunne skrives af en test.** Stien var en modul-konstant beregnet ved
   import, så `isolated_runtime`s `HOME`-ompegning ikke flyttede den. Målt i
   den levende fil: `clamp`, `ny-evne` og «Souls-Build  Analyse» med beviset
   «målt i test» lå side om side med de ægte målinger. Et bevis der kan
   skrives af en fixtur beviser intet.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: En måling er en observeret sandhed om evnen.
_MAALING = "measurement"
#: En rettelse flytter tallet tilbage til det målte — den beviser ikke noget nyt.
_RETTELSE = "correction"
_KINDS = (_MAALING, _RETTELSE)


def _ledger_path() -> Path:
    """Stien afgøres ved KALDSTID, ikke ved import.

    `state_store._STATE_DIR` foretrækkes, fordi husets autouse-værn
    (`_guard_prod_state_dir`) allerede peger den mod en tmp-mappe i tests. Uden
    den falder vi tilbage på den eksplicitte miljøvariabel — aldrig på en
    gættet sti.
    """
    try:
        from core.runtime import state_store

        return Path(state_store._STATE_DIR) / "capability_measurements.jsonl"
    except Exception as exc:  # noqa: BLE001 — uden state_store skal sporet stadig kunne skrives
        # Importen kan fejle i en enkelt kommando-linje-kørsel uden runtime.
        logger.warning("capability_measurement: state_store utilgængelig: %s", exc)
        base = os.getenv("JARVIS_STATE_DIR") or str(
            Path.home() / ".jarvis-v2" / "state"
        )
        return Path(base) / "capability_measurements.jsonl"


def _skriv_maalingsspor(domain: str, value: float, evidence: str, kind: str) -> None:
    """Én linje pr. hændelse. Uden sporet er «målt» et ord uden indhold."""

    def _write() -> None:
        sti = _ledger_path()
        sti.parent.mkdir(parents=True, exist_ok=True)
        with sti.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "domain": domain,
                        "value": value,
                        "evidence": evidence,
                        "kind": kind,
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
    """Domæne → den senest MÅLTE værdi. Tom når sporet ikke findes.

    Linjer uden `kind` tælles som målinger: det var feltets betydning i den
    første udgave, og en gammel linje skal ikke tavst forsvinde.
    """
    sti = _ledger_path()
    if not sti.exists():
        return {}
    nyeste: dict[str, float] = {}
    try:
        lines = sti.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("capability_measurement: målingsspor kunne ikke læses: %s", exc)
        return {}
    for linje in lines:
        try:
            rad = json.loads(linje)
            if str(rad.get("kind") or _MAALING) != _MAALING:
                # En rettelse flytter tallet; den beviser ikke evnen.
                continue
            nyeste[str(rad["domain"])] = round(float(rad["value"]), 4)
        except (ValueError, KeyError, TypeError):
            # Uparsbar linje: den kan ikke bære et bevis, så den tælles ikke.
            continue
    return nyeste


def set_domain_confidence(
    domain: str, value: float, *, evidence: str, kind: str = _MAALING
) -> dict[str, Any]:
    """Sæt domænets confidence til en MÅLT værdi.

    `evidence` er ikke pynt: den er betingelsen for at skrive. En måling uden
    et bevis er en selvrapport med et finere navn.

    `kind="correction"` bruges når et forkert løft rulles tilbage. Værdien
    skrives, men sporet mærker den som en rettelse, så `_mekanisk_maalte` ikke
    kalder domænet målt på baggrund af den.
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
    if kind not in _KINDS:
        return {"recorded": False, "reason": f"ukendt kind: {kind}"}

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
    _skriv_maalingsspor(name, after, evidence, kind)
    logger.info(
        "capability_measurement: %s %s -> %s [%s] (%s)",
        name,
        before,
        after,
        kind,
        evidence,
    )
    return {
        "recorded": True,
        "domain": name,
        "before": before,
        "after": after,
        "evidence": evidence,
        "kind": kind,
    }
