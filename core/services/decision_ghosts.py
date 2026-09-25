"""Decision Ghosts — de veje der blev fravalgt, og dem der holdt.

Brudte beslutninger efterlader et spoergsmaal («hvad nu hvis jeg havde…»);
holdte efterlader et ekko han kan gentage. Sammen er de hans
beslutningslandskab — ikke kun stemmerne fra det der gik galt.

HVAD DER STOD HER INDTIL 25/9-2026

    "regret_potential": random.uniform(0.1, 0.6),
    "success_echo": random.uniform(0.3, 0.9),

    _rejected_paths: list[dict] = []
    _confirmed_paths: list[dict] = []

To modul-globale lister der doede ved genstart, og to tal trukket af en
terning. `describe_ghost_decision` valgte den «mest saliente» fortrydelse ved
`max(..., key=regret_potential)` — altsaa det hoejeste terningkast. Han ville
have faaet at vide hvad han fortrød mest, og svaret var tilfaeldigt.

Modulet havde INGEN kalder. `record_reaffirmed_decision`s egen docstring sagde
«Called from behavioral_decision_review when verdict is kept or partial» — den
kalder fandtes bare ikke.

HVOR TALLENE KOMMER FRA NU

`behavioral_decision_reviews` har 1101 raekker med en rigtig dom og en rigtig
`adherence_score` (maalt 25/9-2026):

    kept 538 · broken 299 · partial 263 · fulfilled 1

  * holdt/delvist/opfyldt -> `success_echo = adherence_score`
  * brudt                 -> `regret_potential = 1 - adherence_score`

Begge er maalt. Mangler scoren, gemmes `None` — ikke et gaet. En post uden tal
kan stadig ses; den kan bare ikke rangeres, og saa vaelges den nyeste i stedet.
Det staar i `describe_*`, saa ingen tror rangeringen betyder mere end den goer.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime import state_store

logger = logging.getLogger(__name__)

_MAX_PATHS = 50


#: Noeglen i `core/runtime/state_store`. Laa foer i
#: `shared_dir()/runtime/decision_ghosts.json` med haandskrevet load/save.
_FIL = "decision_ghosts"


def _load() -> dict[str, list[dict[str, Any]]]:
    tom: dict[str, list[dict[str, Any]]] = {"rejected": [], "confirmed": []}
    d = state_store.load_json(_FIL, None)
    if d is None:
        return tom
    if not isinstance(d, dict):
        logger.warning("decision_ghosts: uventet form i state — starter forfra")
        return tom
    return {"rejected": list(d.get("rejected") or []),
            "confirmed": list(d.get("confirmed") or [])}


def _save(data: dict[str, list[dict[str, Any]]]) -> None:
    state_store.save_json(_FIL, {
        "rejected": data["rejected"][-_MAX_PATHS:],
        "confirmed": data["confirmed"][-_MAX_PATHS:],
    })


def _vaelg(poster: list[dict[str, Any]], felt: str) -> dict[str, Any] | None:
    """Den mest saliente — eller den nyeste hvis ingen har et maalt tal.

    Foer valgte den `max(..., key=random.uniform(...))`. Et tal der ikke er
    maalt maa ikke bestemme hvad han faar at vide han fortryder mest.
    """
    if not poster:
        return None
    med_tal = [p for p in poster if isinstance(p.get(felt), (int, float))]
    if med_tal:
        return max(med_tal, key=lambda x: float(x[felt]))
    return poster[-1]


def record_rejected_path(decision: str, reason: str, alternative: str,
                         regret_potential: float | None = None) -> None:
    """Gem en vej der blev fravalgt eller brudt.

    `regret_potential` skal komme fra en maaling (fx `1 - adherence_score` paa
    en brudt beslutning). Udelades den, gemmes `None` — aldrig et gaet.
    """
    # Laas: to processer skriver, og hver gemning skriver HELE filen — uden
    # laas forsvinder den andens beslutning sporloest.
    with state_store.med_laas(_FIL):
        data = _load()
        data["rejected"].append({
            "decision": decision,
            "reason": reason,
            "alternative": alternative,
            "regret_potential": (float(regret_potential)
                                 if regret_potential is not None else None),
            "recorded_at": datetime.now(UTC).isoformat(),
        })
        _save(data)


def record_confirmed_path(decision: str, outcome: str, key_factor: str = "",
                          success_echo: float | None = None) -> None:
    """Gem en beslutning der holdt. `success_echo` er `adherence_score`."""
    with state_store.med_laas(_FIL):
        data = _load()
        data["confirmed"].append({
            "decision": decision,
            "outcome": outcome,
            "key_factor": key_factor or "",
            "success_echo": (float(success_echo) if success_echo is not None else None),
            "recorded_at": datetime.now(UTC).isoformat(),
        })
        _save(data)


def record_reaffirmed_decision(decision_id: str, title: str, verdict: str,
                               adherence_score: float | None = None) -> None:
    """Kaldes fra `behavioral_decisions.review_decision`.

    Den kalder manglede indtil 25/9-2026, selv om docstringen sagde at den
    fandtes.
    """
    factor = ("Delvist holdt — fortsat opmærksomhed" if verdict == "partial"
              else "Beslutningen var rigtig")
    record_confirmed_path(
        decision=title or decision_id,
        outcome=f"Decision review verdict: {verdict}",
        key_factor=factor,
        success_echo=adherence_score,
    )


def record_broken_decision(decision_id: str, title: str,
                           adherence_score: float | None = None,
                           note: str = "") -> None:
    """En brudt beslutning er den rigtige kilde til en fortrydelse.

    `regret_potential = 1 - adherence_score`: jo mindre han fulgte den, jo mere
    er der at spoerge om.
    """
    fortrydelse = (max(0.0, 1.0 - float(adherence_score))
                   if adherence_score is not None else None)
    record_rejected_path(
        decision=title or decision_id,
        reason="Decision review verdict: broken",
        alternative=note or "det jeg gjorde i stedet",
        regret_potential=fortrydelse,
    )


def describe_ghost_decision() -> str:
    top = _vaelg(_load()["rejected"], "regret_potential")
    if not top:
        return ""
    return (f"Af og til tænker jeg: Hvis jeg havde valgt "
            f"{top['alternative']} i stedet for...")


def describe_success_echo() -> str:
    top = _vaelg(_load()["confirmed"], "success_echo")
    if not top:
        return ""
    factor = f" — fordi {top['key_factor']}" if top.get("key_factor") else ""
    return f"Jeg husker: {top['decision']} førte til {top['outcome']}{factor}"


def format_decision_ghost_for_prompt() -> str:
    desc = describe_ghost_decision()
    return f"[BESLUTNINGSSPØGELSE: {desc}]" if desc else ""


def format_decision_echo_for_prompt() -> str:
    desc = describe_success_echo()
    return f"[BESLUTNINGSEKKO: {desc}]" if desc else ""


def reset_decision_ghosts() -> None:
    _save({"rejected": [], "confirmed": []})


def build_decision_ghosts_surface() -> dict[str, Any]:
    data = _load()
    afvist, holdt = data["rejected"], data["confirmed"]
    return {
        "active": bool(afvist or holdt),
        "rejected_count": len(afvist),
        "confirmed_count": len(holdt),
        "top_regret": _vaelg(afvist, "regret_potential"),
        "top_echo": _vaelg(holdt, "success_echo"),
        "summary": (
            f"{len(holdt)} beslutninger der holdt, {len(afvist)} der brast"
            if afvist or holdt else "Ingen beslutningsspor endnu"
        ),
    }
