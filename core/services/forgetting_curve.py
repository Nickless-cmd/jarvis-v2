"""Forgetting Curve — det jeg bliver ved at se, bliver. Resten falmer.

Ebbinghaus paa arbejdssaettet: en erindring der hentes frem igen nulstiller sit
henfald og falmer langsommere naeste gang. En der holder op med at blive hentet
glider ud af aktiv prompt-injektion — men slettes ALDRIG. `get_faded_memories`
giver dem stadig tilbage.

HVAD DER MANGLEDE (maalt 25/9-2026)

`_DECAY_REGISTRY` var en modul-global dict uden persistering, og
`register_memory` havde INGEN kalder i produktion. Henfaldet kunne koere; der
var bare aldrig noget at lade henfalde. Overfladen sagde «No memories tracked
yet» og ville have sagt det for altid.

`apply_decay_tick` kaldes kun naar beslutnings-motoren vaelger handlingen
`decay_forgotten_signals` (`heartbeat_runtime.py:5623`) — altsaa naar han
BESLUTTER at glemme. Den sti er bevaret.

HVORDAN ARBEJDSSAETTET FINDES

Ikke ved at registrere alle 166.618 private_brain_records. Kurven handler om
det der aktuelt injiceres i prompten, og det er `build_private_brain_context`s
udtraek. `tick()` kigger hvert hjerteslag paa hvad der ER i sind lige nu:
nye registreres, gensete forstaerkes, og saa henfalder alle et hak.

Det sker i hjerteslaget, ikke i prompt-samlingen. En fil-skrivning per prompt
ville ligge paa den varme sti, og «hvert kvarter» er den rigtige oploesning for
en glemselskurve alligevel.

Noeglen er en stabil hash af `focus|summary` — udtraekkene baerer intet id.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.workspace_paths import shared_dir

logger = logging.getLogger(__name__)

#: Hvor mange erindringer arbejdssaettet maa fylde. Faldne ryddes foerst.
_MAX_SPOR = 500


def _storage_path() -> Path:
    return shared_dir() / "runtime" / "forgetting_curve.json"


def _load() -> dict[str, dict[str, Any]]:
    p = _storage_path()
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception as exc:
        logger.warning("forgetting_curve: kunne ikke laeses: %s", exc)
        return {}


def _save(reg: dict[str, dict[str, Any]]) -> None:
    if len(reg) > _MAX_SPOR:
        # Ryd de mest faldne foerst — de er allerede ude af injektionen.
        orden = sorted(reg.items(), key=lambda kv: float(kv[1].get("decay_score") or 0.0))
        reg = dict(orden[:_MAX_SPOR])
    p = _storage_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
    except Exception as exc:
        logger.warning("forgetting_curve: kunne ikke gemmes: %s", exc)


def noegle_for(focus: str, summary: str) -> str:
    """Stabil identitet for et erindrings-udtraek. Udtraek baerer intet id."""
    raa = f"{str(focus or '').strip()}|{str(summary or '').strip()}"
    return hashlib.sha256(raa.encode("utf-8")).hexdigest()[:16]


def register_memory(
    *,
    memory_key: str,
    content_preview: str = "",
    initial_decay: float = 0.0,
) -> None:
    """Register a memory for decay tracking."""
    reg = _load()
    reg[memory_key] = {
        "decay_score": initial_decay,
        "reinforcement_count": 0,
        "content_preview": content_preview[:100],
        "registered_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "last_referenced_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    _save(reg)


def reinforce_memory(memory_key: str) -> None:
    """Reinforce a memory — reset decay, increment reinforcement count."""
    reg = _load()
    entry = reg.get(memory_key)
    if entry:
        entry["decay_score"] = 0.0
        entry["reinforcement_count"] = int(entry.get("reinforcement_count", 0)) + 1
        entry["last_referenced_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        _save(reg)


def apply_decay_tick(decay_increment: float = 0.01) -> dict[str, object]:
    """Apply one decay tick to all registered memories."""
    reg = _load()
    faded = []
    for key, entry in list(reg.items()):
        old_decay = float(entry.get("decay_score", 0.0))
        # Reinforced memories decay slower
        reinforcements = int(entry.get("reinforcement_count", 0))
        adjusted_increment = decay_increment / max(1, reinforcements * 0.5 + 1)
        new_decay = min(1.0, old_decay + adjusted_increment)
        entry["decay_score"] = new_decay

        if new_decay > 0.9:
            faded.append(key)
            event_bus.publish(
                "cognitive_forgetting.memory_faded",
                {"memory_key": key, "decay_score": new_decay},
            )

    _save(reg)
    return {
        "tick_applied": True,
        "total_tracked": len(reg),
        "faded_count": len(faded),
        "faded_keys": faded,
    }


def get_active_memories() -> list[dict[str, object]]:
    """Return memories with decay < 0.9 (still active)."""
    return [
        {"key": k, **v}
        for k, v in _load().items()
        if float(v.get("decay_score", 0)) < 0.9
    ]


def get_faded_memories() -> list[dict[str, object]]:
    """Return memories with decay >= 0.9 (faded but archived)."""
    return [
        {"key": k, **v}
        for k, v in _load().items()
        if float(v.get("decay_score", 0)) >= 0.9
    ]


def build_forgetting_curve_surface() -> dict[str, object]:
    reg = _load()
    active = get_active_memories()
    faded = get_faded_memories()
    return {
        "active": bool(reg),
        "active_memories": len(active),
        "faded_memories": len(faded),
        "total_tracked": len(reg),
        "top_reinforced": sorted(
            active, key=lambda x: x.get("reinforcement_count", 0), reverse=True
        )[:5],
        "most_faded": sorted(
            active, key=lambda x: x.get("decay_score", 0), reverse=True
        )[:5],
        "summary": (
            f"{len(active)} aktive, {len(faded)} falmede af {len(reg)} sporet"
            if reg else "Ingen erindringer spores endnu"
        ),
    }


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Hjerteslags-krog: se hvad der ER i sind nu, og lad resten falme.

    Nye udtraek registreres, gensete forstaerkes, og saa henfalder alle ét hak.
    Det er hele kurven: det der bliver hentet frem igen bliver, det der holder
    op med at blive hentet glider ud af injektionen.

    Registreringen sker HER og ikke i prompt-samlingen, fordi en fil-skrivning
    per prompt ville ligge paa den varme sti — og «hvert kvarter» er den
    rigtige oploesning for en glemselskurve alligevel.

    Kaster aldrig.
    """
    try:
        from core.services.session_distillation import build_private_brain_context
        hjerne = build_private_brain_context(limit=12) or {}
    except Exception as exc:
        logger.debug("forgetting_curve: arbejdssaettet kunne ikke laeses: %s", exc)
        return {"registreret": 0, "forstaerket": 0, "faldne": 0}

    # ÉN indlaesning og ÉN skrivning for hele tikket.
    #
    # Foerste udgave kaldte `register_memory`/`reinforce_memory` per udtraek, og
    # de laeser+skriver filen hver gang: tolv fulde cyklusser per tik. Vaerre —
    # dubletter blev talt som nye, fordi `noegle in reg` saa paa en kopi der
    # ikke fulgte med. Maalt: «registreret: 10» mens der kun stod 6.
    reg = _load()
    nu = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    nye = genset = 0
    for udtraek in list(hjerne.get("excerpts") or []):
        focus = str(udtraek.get("focus") or "")
        summary = str(udtraek.get("summary") or "")
        if not summary.strip():
            continue
        noegle = noegle_for(focus, summary)
        post = reg.get(noegle)
        if post:
            post["decay_score"] = 0.0
            post["reinforcement_count"] = int(post.get("reinforcement_count", 0)) + 1
            post["last_referenced_at"] = nu
            genset += 1
        else:
            reg[noegle] = {
                "decay_score": 0.0,
                "reinforcement_count": 0,
                "content_preview": (f"{focus}: {summary}" if focus else summary)[:100],
                "registered_at": nu,
                "last_referenced_at": nu,
            }
            nye += 1
    _save(reg)

    faldet = apply_decay_tick()
    return {
        "registreret": nye,
        "forstaerket": genset,
        "faldne": int(faldet.get("faded_count") or 0),
        "sporet": int(faldet.get("total_tracked") or 0),
    }
