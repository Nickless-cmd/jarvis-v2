"""R2.5-håndhævelse — en blok der ikke kan ignoreres.

R2.5 (``r2_5_blocking_gate``) var til nu KUN en prompt-tekst: «stop og
verificér». Den kunne læses og ignoreres, og det var netop den adfærd der
udløste den (lav heed-rate). Jarvis selv, 19/9-2026: «Den ærlige næste
beslutning er output-gating: at jeg ikke kan streame videre før et verify_*
er kørt.» Bjørn sagde ja samme dag.

Formen følger princippet fra 18/8-2026 (gates skal være non-blocking
in-loop): runnet dræbes ikke, og teksten holdes ikke tilbage — et stop midt
i streamen er netop den tavse fejlklasse vi har jagtet. I stedet:

  * Mens en R2.5-blok står åben, afvises næste MUTATION med et
    værktøjsresultat der siger hvad der skal til. Modellen læser det og
    retter kursen i samme run.
  * Læse- og verify-værktøjer slipper ALTID igennem, så han altid kan komme
    fri — og det er dem der løfter blokken.
  * Blokken løftes af det første kig tilbage efter den blev sat (verify_*,
    et readback-værktøj, eller en fil-skrivning der selv bærer sit
    readback), eller udløber efter samme vindue som gaten selv tæller i.
  * Gentagne afvisninger bliver en central-incident (dedup → eskalerende),
    så klienten kan se HVILKEN gate der slog til.

``bash_session*`` og ``operator_bash_session*`` gates ALDRIG: de er Bjørns
vej udenom systemet (19/9-2026: «lad de 2 være uanset hvad.. de er stadig
min bagdør»).

Sandheden om hvad der er sket, læses fra eventbussen (``tool.completed``) —
samme kilde som verification_gate tæller fra, så der ikke opstår en anden
sandhed om hvad der blev verificeret.

Kill-switch: ``central.switch.gate_enforce.r2_5_gate`` (gate_enforcement,
default ON). Fail-open: en fejl her må aldrig blokere et værktøj.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

NERVE = "r2_5_gate"

# Samme vindue som verification_gate tæller mutationer i. En blok der ikke
# er løftet efter 10 min, handler om mutationer gaten ikke længere ser.
_UDLOEB_MINUTTER = 10

# Bjørns bagdør. Aldrig gatet — heller ikke hvis de kommer på mutationslisten.
_BAGDOER_PRAEFIKSER = ("bash_session", "operator_bash_session")

_laas = threading.Lock()
_blok: dict[str, Any] | None = None
_afvist_i_blokken = 0


def _nu() -> datetime:
    return datetime.now(UTC)


def aktiver(blok: dict[str, Any], *, nu: datetime | None = None) -> None:
    """Åbn håndhævelsen. Kaldes af R2.5, når den beslutter at blokere."""
    global _blok, _afvist_i_blokken
    with _laas:
        _blok = {
            "siden": nu or _nu(),
            "action_line": str(blok.get("action_line") or ""),
            "tier": str(blok.get("tier") or ""),
            "threshold": blok.get("threshold"),
            "unverified_effective": blok.get("unverified_effective"),
        }
        _afvist_i_blokken = 0


def nulstil() -> None:
    """Luk håndhævelsen (tests og kill-switch)."""
    global _blok, _afvist_i_blokken
    with _laas:
        _blok = None
        _afvist_i_blokken = 0


def er_bagdoer(navn: str) -> bool:
    return str(navn or "").startswith(_BAGDOER_PRAEFIKSER)


def er_mutation(navn: str, argumenter: dict[str, Any] | None = None) -> bool:
    """Samme klassifikation som verification_gate tæller efter.

    Shell-kald er kun en mutation hvis kommandoen ændrer noget; et
    ``grep`` skal ikke kunne blive nægtet af en verifikations-gate."""
    from core.services import verification_gate as vg
    navn = str(navn or "")
    if er_bagdoer(navn) or navn not in vg._MUTATION_TOOLS:
        return False
    if navn in vg._MUTATION_TOOLS_SHELL:
        kommando = str((argumenter or {}).get("command") or "")
        return vg.shell_command_is_mutating(kommando)
    return True


def _kiggede_tilbage_efter(siden: datetime) -> bool:
    """Er der kommet et kig tilbage siden blokken blev sat?

    Klassifikationen er verification_gate's egen (_scan) — ét sted afgør hvad
    der tæller som et kig tilbage, både for R2's tælling og for at løfte en
    blok. Et fejlet verify_* ER et kig tilbage: han så efter og fandt noget."""
    from core.eventbus.bus import event_bus
    from core.services import verification_gate as vg
    graense = siden.isoformat()
    efter = [e for e in event_bus.recent_by_family("tool", limit=300)
             if str(e.get("created_at", "")) > graense]
    scan = vg._scan(efter)
    return bool(scan["strict_verifies"] or scan["light_verifies"])


def _publicer(kind: str, data: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"{NERVE}.{kind}", data)
    except Exception:
        logger.debug("r2.5-håndhævelse: publish %s fejlede", kind, exc_info=True)


def _aaben_blok(nu: datetime) -> dict[str, Any] | None:
    """Den åbne blok, eller None. Løfter den hvis den er udløbet eller besvaret."""
    global _blok
    with _laas:
        blok = dict(_blok) if _blok else None
    if blok is None:
        return None
    grund = None
    if nu - blok["siden"] > timedelta(minutes=_UDLOEB_MINUTTER):
        grund = "udløbet"
    else:
        try:
            if _kiggede_tilbage_efter(blok["siden"]):
                grund = "kig_tilbage"
        except Exception:
            # Kan vi ikke se om han har kigget, må vi ikke holde ham fast.
            logger.warning("r2.5-håndhævelse: kunne ikke læse tool-events", exc_info=True)
            grund = "læsefejl"
    if grund is None:
        return blok
    with _laas:
        if _blok is not None and _blok["siden"] == blok["siden"]:
            _blok = None
    _publicer("released", {"reason": grund, "refused": _afvist_i_blokken,
                           "since": blok["siden"].isoformat()})
    return None


def afvis_mutation(navn: str, argumenter: dict[str, Any] | None = None, *,
                   run_id: str = "", session_id: str = "",
                   nu: datetime | None = None) -> str | None:
    """Afvisningsteksten hvis værktøjet ikke må køre nu, ellers None.

    Kaster aldrig: enhver fejl → None (værktøjet kører)."""
    global _afvist_i_blokken
    try:
        if not er_mutation(navn, argumenter):
            return None
        blok = _aaben_blok(nu or _nu())
        if blok is None:
            return None
        from core.services import gate_enforcement
        from core.services.gate_kernel import GateClass
        grund = (f"R2.5: {blok.get('unverified_effective')} mutation(er) uden ét "
                 f"kig tilbage (tærskel {blok.get('threshold')}). «{navn}» kører "
                 "ikke før du har set efter at det forrige virkede.")
        if not gate_enforcement.is_enforced(NERVE, GateClass.COGNITIVE):
            gate_enforcement.note_suppressed_block(NERVE, "proactivity", grund)
            return None
        with _laas:
            _afvist_i_blokken += 1
            antal = _afvist_i_blokken
        naeste = blok.get("action_line") or (
            "Næste move: read_file / db_query / process_list / git_log på det du "
            "lige ændrede, eller et verify_*.")
        tekst = (f"{grund}\n{naeste}\nLæse- og verify-værktøjer kører som normalt, "
                 "og det første kig tilbage løfter blokken.")
        _publicer("mutation_refused", {"tool": navn, "refused": antal,
                                       "run_id": run_id, "tier": blok.get("tier")})
        if antal >= 2:
            _rapporter_gentagelse(navn, antal, run_id=run_id, session_id=session_id)
        return tekst
    except Exception:
        logger.warning("r2.5-håndhævelse fejlede — værktøjet kører (fail-open)",
                       exc_info=True)
        return None


def _rapporter_gentagelse(navn: str, antal: int, *, run_id: str, session_id: str) -> None:
    """Han prøver igen uden at kigge: gør det synligt (dedup = eskalerende tæller)."""
    try:
        from core.runtime.db_central_incidents import record_central_incident
        record_central_incident(
            cluster="proactivity", nerve=NERVE, kind="gate_fired", severity="warning",
            message=(f"R2.5 afviste «{navn}» for {antal}. gang i samme blok — "
                     "mutation forsøgt igen uden kig tilbage"),
            run_id=run_id, session_id=session_id, dedup=True,
        )
    except Exception:
        logger.debug("r2.5-håndhævelse: incident fejlede", exc_info=True)
