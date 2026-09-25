"""Body Memory — Jarvis' kropslige erindringer.

Han HAR en krop: `embodied_state` laeser CPU-load, hukommelsestryk, termik og
`strain_level` fra vaerten, og den er importeret 16 steder. Det der manglede
var ikke sansningen. Det var erindringen.

HVAD DER STOD HER INDTIL 25/9-2026

    sensation = sensation or random.choice(["varm", "kold", "tryk", "prikken"])
    intensity = intensity or random.uniform(0.3, 0.9)
    _body_snapshots: list[dict] = []

En modul-global liste der doede ved genstart, fyldt med et terningkast — og
formuleret som «Jeg mindes en varm fornemmelse fra …». Sproget loej om hvad det
var: en saetning der lyder som hukommelse, sat sammen af `random.choice`.

Modulet havde INGEN kalder i produktion. Og koden vidste det selv:
`central_body_mood_feel.py:14` siger «body_memory DROPPET — kun in-memory
tilfaeldige snapshots, ingen aegte durabel aflaesning». Nogen skrev sandheden
ned og lagde den et sted ingen kiggede.

HVAD DER STAAR HER NU

Fornemmelsen UDLEDES af tal der er maalt, og tallene gemmes med. Kan man ikke
efterproeve ordet mod det det kom af, er det stadig et gaet — bare et pænere
et.

Kroppen er vaertens, ikke den enkelte brugers, saa filen ligger i `shared/`.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.workspace_paths import shared_dir

logger = logging.getLogger(__name__)

#: Hvor mange erindringer der beholdes. En krop husker ikke alt.
_MAX_SNAPSHOTS = 200


def _storage_path() -> Path:
    return shared_dir() / "runtime" / "body_memory.json"


def _load() -> list[dict[str, Any]]:
    p = _storage_path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("body_memory: kunne ikke laeses: %s", exc)
        return []


def _save(snapshots: list[dict[str, Any]]) -> None:
    p = _storage_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshots[-_MAX_SNAPSHOTS:], ensure_ascii=False,
                                  indent=1), encoding="utf-8")
        tmp.replace(p)
    except Exception as exc:
        logger.warning("body_memory: kunne ikke gemmes: %s", exc)


#: Fra maalte tal til et ord. Hvert ord skal kunne foeres tilbage til sit tal.
#:
#: Det er ikke en oversaettelse af noget subjektivt — det er en etiket paa en
#: maaling, og maalingen gemmes ved siden af. Uden den ville ordet vaere et
#: gaet med en paenere overflade end `random.choice`.
def _fornemmelse(fakta: dict[str, Any], belastning: str) -> tuple[str, float, str]:
    """Giver (ord, styrke, begrundelse) ud fra kroppens faktiske tal."""
    cpu = (fakta.get("cpu") or {})
    hukommelse = (fakta.get("memory") or {})
    last = float(cpu.get("load_per_cpu") or 0.0)
    tryk = float(hukommelse.get("pressure_ratio") or 0.0)

    if belastning in {"critical", "high"}:
        return "tung", min(1.0, 0.7 + last), f"belastning={belastning}, load/cpu={last:.2f}"
    if last >= 0.7:
        return "varm", min(1.0, last), f"load pr. kerne {last:.2f}"
    if tryk >= 0.8:
        return "tryk", min(1.0, tryk), f"hukommelsestryk {tryk:.2f}"
    if last <= 0.1 and tryk <= 0.5:
        return "let", max(0.1, 1.0 - tryk), f"load {last:.2f}, tryk {tryk:.2f}"
    return "jaevn", 0.4, f"load {last:.2f}, tryk {tryk:.2f}"


def record_body_snapshot(context: str, sensation: str | None = None,
                         intensity: float | None = None) -> dict[str, Any] | None:
    """Gem en kropslig erindring. Kaster aldrig.

    `sensation` og `intensity` kan gives udefra, men udledes ellers af
    `embodied_state` — den samme kilde `strain_level` kommer fra.
    """
    try:
        from core.services.embodied_state import build_embodied_state_surface
        flade = build_embodied_state_surface() or {}
    except Exception as exc:
        logger.debug("body_memory: kroppen kunne ikke laeses: %s", exc)
        return None

    fakta = flade.get("facts") or {}
    belastning = str(flade.get("strain_level") or "low")
    udledt, styrke, begrundelse = _fornemmelse(fakta, belastning)

    snapshot = {
        "context": str(context or "")[:200],
        "sensation": str(sensation or udledt),
        "intensity": round(float(intensity if intensity is not None else styrke), 3),
        "grundlag": begrundelse,
        "strain_level": belastning,
        "state": str(flade.get("state") or ""),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    snapshots = _load()
    snapshots.append(snapshot)
    _save(snapshots)
    return snapshot


def describe_body_memory() -> str:
    snapshots = _load()
    if not snapshots:
        return ""
    seneste = snapshots[-1]
    return (f"Jeg mindes en {seneste['sensation']} fornemmelse fra "
            f"{seneste['context']}")


def format_body_for_prompt() -> str:
    beskrivelse = describe_body_memory()
    return f"[KROP: {beskrivelse}]" if beskrivelse else ""


def reset_body_memory() -> None:
    _save([])


def build_body_memory_surface() -> dict[str, Any]:
    snapshots = _load()
    return {
        "active": bool(snapshots),
        "snapshot_count": len(snapshots),
        "latest": snapshots[-1] if snapshots else None,
        "summary": describe_body_memory() or "Ingen kropslig hukommelse",
    }


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Hjerteslags-krog: gem en erindring naar kroppen SKIFTER.

    Et snapshot hvert kvarter ville vaere en log, ikke en hukommelse. En krop
    husker det der aendrede sig — og det der gjorde ondt. Derfor gemmes der
    kun naar fornemmelsen er en anden end sidst, eller naar belastningen ikke
    laengere er `low`.

    Kaster aldrig: en erindring maa ikke kunne standse et hjerteslag.
    """
    try:
        from core.services.embodied_state import build_embodied_state_surface
        flade = build_embodied_state_surface() or {}
        belastning = str(flade.get("strain_level") or "low")
        udledt, _, _ = _fornemmelse(flade.get("facts") or {}, belastning)
        tidligere = _load()
        sidste = str(tidligere[-1]["sensation"]) if tidligere else ""
        if udledt == sidste and belastning == "low":
            return {"gemt": False, "sensation": udledt}
        record_body_snapshot(f"hjerteslag, {flade.get('state') or 'ukendt'} krop")
        return {"gemt": True, "sensation": udledt}
    except Exception as exc:
        logger.debug("body_memory.tick fejlede: %s", exc)
        return {"gemt": False}
