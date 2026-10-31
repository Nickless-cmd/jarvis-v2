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
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime import state_store

logger = logging.getLogger(__name__)

#: Hvor mange erindringer arbejdssaettet maa fylde. Faldne ryddes foerst.
_MAX_SPOR = 500


#: Noeglen i `core/runtime/state_store`. Laa foer i
#: `shared_dir()/runtime/forgetting_curve.json` med haandskrevet load/save.
_FIL = "forgetting_curve"


def _load() -> dict[str, dict[str, Any]]:
    d = state_store.load_json(_FIL, None)
    if d is None:
        return {}
    if not isinstance(d, dict):
        logger.warning("forgetting_curve: uventet form i state — starter forfra")
        return {}
    return d


def _save(reg: dict[str, dict[str, Any]]) -> None:
    if len(reg) > _MAX_SPOR:
        # Ryd de mest faldne foerst — de er allerede ude af injektionen.
        orden = sorted(reg.items(), key=lambda kv: float(kv[1].get("decay_score") or 0.0))
        reg = dict(orden[:_MAX_SPOR])
    state_store.save_json(_FIL, reg)


def noegle_for(focus: str, summary: str) -> str:
    """Stabil identitet for et erindrings-udtraek. Udtraek baerer intet id."""
    raa = f"{str(focus or '').strip()}|{str(summary or '').strip()}"
    return hashlib.sha256(raa.encode("utf-8")).hexdigest()[:16]


#: Normalisering til dublet-genkendelse. MAALT 31/10-2026 paa den levende
#: `forgetting_curve.json` (500 poster): fem grupper delte ORDRET samme
#: `content_preview` under forskellige noegler — «tankestroem: Jeg vil foerst
#: taelle kolonner og vaerdier …» laa tre gange. Det er ren dublet: samme
#: udtraek registreret igen, fordi noeglen hasher `focus|summary` og udtraekket
#: blev formuleret med en anden `focus`.
#:
#: HVORFOR IKKE EN LIGHEDS-TAERSKEL (Jaccard over ord): det blev maalt, og det
#: kan ikke skelne i denne korpus. Inden for ét emne (de 42 poster om «den
#: afbrudte koersel») topper parrene paa 0,667; paa tvaers af hele filen naar
#: tilfaeldige par 1,000 — fordi «somatisk tilstand: cpu 4% · 47°C · 11.2GB fri»
#: og «… cpu 8% · 49°C · 12.2GB fri» er samme skabelon med andre tal. Ved
#: taerskel 0,50 fanges 13 aegte emne-par — men ogsaa 92 tvaers-par, altsaa syv
#: falske for hver aegte. En taerskel der matcher alt er lige saa ubrugelig som
#: ingen dedup: den ville goere glemselskurven til én klump.
#:
#: Derfor: KUN normaliseret eksakt match. Det fanger de fem maalte dubletter og
#: kan pr. konstruktion ikke smelte to forskellige emner sammen.
def _normaliser(preview: str) -> str:
    """Sammenligningsform: smaa bogstaver, ingen tegnsaetning, eet mellemrum."""
    tekst = str(preview or "").lower()
    tekst = re.sub(r"[^a-zæøå0-9]+", " ", tekst)
    return " ".join(tekst.split())


def _find_dublet(reg: dict[str, dict[str, Any]], tekst: str) -> str | None:
    """Noeglen paa en post med SAMME normaliserede indhold, hvis nogen.

    Sammenligner mod postens `summary`-felt naar det findes. `content_preview`
    baerer `focus` som praefiks («tankestroem: …»), saa to identiske udtraek
    med forskelligt `focus` ville aldrig matche hinanden — og det er praecis
    den form dubletterne har. Posten skriver derfor `summary` ved siden af.
    """
    noegle = _normaliser(tekst)
    if not noegle:
        return None
    for eksisterende, post in reg.items():
        sammenlign = post.get("summary")
        if sammenlign is None:
            sammenlign = post.get("content_preview") or ""
        if _normaliser(str(sammenlign)) == noegle:
            return eksisterende
    return None


def register_memory(
    *,
    memory_key: str,
    content_preview: str = "",
    initial_decay: float = 0.0,
) -> None:
    """Register a memory for decay tracking.

    Er indholdet allerede sporet under en ANDEN noegle, forstaerkes den post i
    stedet for at der oprettes en ny. Maalt 31/10-2026: fem grupper i den
    levende fil havde ordret samme preview under forskellige noegler, saa
    emnet fik frisk `decay_score` hver gang og strukturelt ikke kunne falme.
    """
    with state_store.med_laas(_FIL):
        reg = _load()
        dublet = _find_dublet(reg, content_preview)
        if dublet is not None and dublet != memory_key:
            post = reg[dublet]
            post["decay_score"] = 0.0
            post["reinforcement_count"] = int(post.get("reinforcement_count", 0)) + 1
            post["last_referenced_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            _save(reg)
            return
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
    with state_store.med_laas(_FIL):
        reg = _load()
        entry = reg.get(memory_key)
        if entry:
            entry["decay_score"] = 0.0
            entry["reinforcement_count"] = int(entry.get("reinforcement_count", 0)) + 1
            entry["last_referenced_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            _save(reg)


def apply_decay_tick(decay_increment: float = 0.01) -> dict[str, object]:
    """Apply one decay tick to all registered memories."""
    faded: list[tuple[str, float]] = []
    with state_store.med_laas(_FIL):
        reg = _load()
        for key, entry in list(reg.items()):
            old_decay = float(entry.get("decay_score", 0.0))
            # Reinforced memories decay slower
            reinforcements = int(entry.get("reinforcement_count", 0))
            adjusted_increment = decay_increment / max(1, reinforcements * 0.5 + 1)
            new_decay = min(1.0, old_decay + adjusted_increment)
            entry["decay_score"] = new_decay

            if new_decay > 0.9:
                faded.append((key, new_decay))

        _save(reg)
        sporet = len(reg)

    # Haendelserne UDEN for laasen. En abonnent maa ikke kunne holde den anden
    # proces ude af glemselskurven mens den arbejder paa noget helt andet.
    for key, decay in faded:
        event_bus.publish(
            "cognitive_forgetting.memory_faded",
            {"memory_key": key, "decay_score": decay},
        )

    return {
        "tick_applied": True,
        "total_tracked": sporet,
        "faded_count": len(faded),
        "faded_keys": [k for k, _ in faded],
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
    # Laasen slippes FOER `apply_decay_tick`, som tager den selv. To
    # `med_laas` paa samme noegle i samme proces er to `flock` paa hver sin
    # fd — den inderste ville vente paa den yderste for evigt.
    with state_store.med_laas(_FIL):
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
                preview = (f"{focus}: {summary}" if focus else summary)[:100]
                # Samme udtraek under en ANDEN `focus` giver en anden noegle.
                # Uden dette blev det talt som nyt og fik frisk henfald —
                # maalt 31/10-2026 som fem dublet-grupper i den levende fil.
                #
                # Der sammenlignes paa `summary` ALENE, ikke paa `preview`:
                # preview baerer `focus` som praefiks, saa to identiske udtraek
                # med forskelligt `focus` ville aldrig matche hinanden — og det
                # er praecis den form dubletterne har.
                dublet = _find_dublet(reg, summary)
                if dublet is not None:
                    d_post = reg[dublet]
                    d_post["decay_score"] = 0.0
                    d_post["reinforcement_count"] = int(d_post.get("reinforcement_count", 0)) + 1
                    d_post["last_referenced_at"] = nu
                    genset += 1
                    continue
                reg[noegle] = {
                    "decay_score": 0.0,
                    "reinforcement_count": 0,
                    "content_preview": preview,
                    "summary": summary,
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
