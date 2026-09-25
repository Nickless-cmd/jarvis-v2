"""Ghost Networks — spor af mønstre der holdt op med at være aktive.

Et spøgelse er ikke et minde. Det er en form der var levende og ikke er det
længere, og som stadig trækker lidt i ham indtil den er falmet helt.

HVAD DER STOD HER INDTIL 25/9-2026

    _ghosts: list[dict] = []
    "decay_rate": 0.0,

En modul-global liste der døde ved genstart, og et henfald der blev sat til
0.0 og **aldrig opdateret**. `describe_ghost_network` filtrerede paa
`decay_rate < 0.8` og tog `active[0]` — altsaa det aeldste spoegelse, for
evigt. Et spor der per definition aldrig kunne falme.

`archive_dead_nodes` havde INGEN kalder, saa overfladen sagde «Ingen
spoegelser» og ville have sagt det for altid.

HVOR SPOEGELSERNE KOMMER FRA NU

Signal-tabellerne har en `status`. Maalt 25/9-2026 staar der 29.393 raekker paa
`superseded`/`stale` fordelt paa 50 tabeller — men de fleste er gamle, og et
spoegelse der doede i maj cirkler ikke laengere.

Fire tabeller baerer moenstre frem for bogholderi, og de doer i en skala der
passer til et spoegelse — en haandfuld om dagen:

    runtime_development_focuses          et fokus der blev droppet
    runtime_reflective_critics           en selvkritik der blev afloest
    runtime_diary_synthesis_signals      en dagbogs-traad der gik i staa
    runtime_private_inner_note_signals   en indre note der visnede

`decay_rate` er nu ALDEREN: dage siden moensteret doede, delt med
`_FALME_DAGE`. Ved 0,8 holder det op med at blive naevnt — men posten bliver
liggende, som foer.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.workspace_paths import shared_dir

logger = logging.getLogger(__name__)

#: Tabeller hvis doede raekker er MOENSTRE, ikke bogholderi.
SPOEGELSE_KILDER = (
    ("runtime_development_focuses", "et fokus"),
    ("runtime_reflective_critics", "en selvkritik"),
    ("runtime_diary_synthesis_signals", "en dagbogs-tråd"),
    ("runtime_private_inner_note_signals", "en indre note"),
)

#: Hvor mange dage et spoegelse er om at falme helt. Ved 0,8 (24 dage) holder
#: det op med at blive naevnt.
_FALME_DAGE = 30.0

_MAX_SPOEGELSER = 200

#: Mindste laengde paa selve moensteret, efter at kildens praefiks er skaaret
#: fra. Maalt paa produktionen: blandt de 54 der cirklede stod «Private inner
#: note: Hmm», «: Ja tak» og «: Goer det». Et spoer paa tre tegn er ikke et
#: spor af et moenster — det er en ytring der tilfaeldigvis blev til et signal.
_MINDSTE_MOENSTER = 12


def _kernen(navn: str) -> str:
    """Skaer kildens praefiks fra: «Private inner note: X» -> «X»."""
    tekst = str(navn or "").strip()
    _, sep, hale = tekst.partition(": ")
    return (hale if sep else tekst).strip()


def _storage_path() -> Path:
    return shared_dir() / "runtime" / "ghost_networks.json"


def _load() -> list[dict[str, Any]]:
    p = _storage_path()
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except Exception as exc:
        logger.warning("ghost_networks: kunne ikke laeses: %s", exc)
        return []


def _save(spoegelser: list[dict[str, Any]]) -> None:
    p = _storage_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(spoegelser[-_MAX_SPOEGELSER:], ensure_ascii=False,
                                  indent=1), encoding="utf-8")
        tmp.replace(p)
    except Exception as exc:
        logger.warning("ghost_networks: kunne ikke gemmes: %s", exc)


def _henfald(doede_ved: str) -> float:
    """Alderen som henfald. Var 0.0 og blev aldrig opdateret."""
    try:
        t = datetime.fromisoformat(str(doede_ved).replace("Z", "+00:00"))
    except Exception:
        return 1.0                      # ukendt alder -> regnes som falmet
    dage = (datetime.now(UTC) - t).total_seconds() / 86400.0
    return min(1.0, max(0.0, dage / _FALME_DAGE))


def archive_dead_nodes(node_ids: list[str], slags: str = "et mønster",
                       doede_ved: str = "") -> int:
    """Arkiver doede moenstre. Giver antallet der var nye."""
    spoegelser = _load()
    kendte = {str(g.get("node_id")) for g in spoegelser}
    nu = doede_ved or datetime.now(UTC).isoformat()
    nye = 0
    for node_id in node_ids:
        if str(node_id) in kendte:
            continue
        spoegelser.append({
            "node_id": str(node_id),
            "slags": slags,
            "last_seen": nu,
            "arkiveret_ved": datetime.now(UTC).isoformat(),
        })
        nye += 1
    if nye:
        _save(spoegelser)
    return nye


def _med_henfald() -> list[dict[str, Any]]:
    """Spoegelserne med deres AKTUELLE henfald — beregnet, ikke gemt."""
    return [{**g, "decay_rate": _henfald(str(g.get("last_seen") or ""))}
            for g in _load()]


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Hjerteslags-krog: saml de moenstre der er doet siden sidst."""
    fundet = 0
    try:
        from core.runtime.db import connect
        with connect() as conn:
            for tabel, slags in SPOEGELSE_KILDER:
                try:
                    raekker = conn.execute(
                        f"""SELECT title, canonical_key, updated_at FROM {tabel}
                            WHERE status IN ('superseded', 'stale')
                              AND updated_at > datetime('now', '-{int(_FALME_DAGE)} days')
                            ORDER BY updated_at DESC LIMIT 20"""
                    ).fetchall()
                except Exception as exc:
                    logger.debug("ghost_networks: %s kunne ikke laeses: %s", tabel, exc)
                    continue
                for r in raekker:
                    navn = str(r[0] or r[1] or "").strip()
                    if len(_kernen(navn)) >= _MINDSTE_MOENSTER:
                        fundet += archive_dead_nodes([navn], slags, str(r[2] or ""))
    except Exception as exc:
        logger.debug("ghost_networks: basen kunne ikke naas: %s", exc)
        return {"nye": 0}
    return {"nye": fundet}


def describe_ghost_network() -> str:
    """Det MINDST falmede spoegelse — ikke det aeldste.

    Foer stod der `active[0]`, altsaa det foerste i listen: det aeldste, for
    evigt, fordi henfaldet aldrig blev opdateret.
    """
    levende = [g for g in _med_henfald() if g["decay_rate"] < 0.8]
    if not levende:
        return ""
    g = min(levende, key=lambda x: x["decay_rate"])
    return f"Noget fra tidligere cirkler stadig i mig: {g['slags']} — {g['node_id']}"


def format_ghost_for_prompt() -> str:
    desc = describe_ghost_network()
    return f"[SPØGELSE: {desc}]" if desc else ""


def reset_ghost_networks() -> None:
    _save([])


def build_ghost_networks_surface() -> dict[str, Any]:
    alle = _med_henfald()
    levende = [g for g in alle if g["decay_rate"] < 0.8]
    return {
        "active": bool(alle),
        "ghost_count": len(alle),
        "circling_count": len(levende),
        "summary": describe_ghost_network() or "Ingen spøgelser",
    }
