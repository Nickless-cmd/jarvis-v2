"""Tiny JSON-file state store for module-globals that must survive restart.

Pattern matches the one used by ``calm_anchor`` and ``valence_trajectory``
(commit 5ca8488): module loads its globals from disk on import, saves them
back after every mutation. Files live under ``~/.jarvis-v2/state/`` and are
small (<100 KB worst case), so atomic write-then-rename is fine.

Why exists: prior to this helper every daemon that fixed the same problem
re-implemented load/save inline. Five more daemons (desire, curiosity,
thought_action_proposal, user_model, visible_runs._PENDING_APPROVALS)
needed the same treatment, so the pattern is now centralized.
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STATE_DIR = Path.home() / ".jarvis-v2" / "state"


def _path(name: str) -> Path:
    return _STATE_DIR / f"{name}.json"


def _meld_fejl(name: str, handling: str, exc: BaseException) -> None:
    """Gør en state-fejl SYNLIG: WARNING + anomali-kanal. Self-safe.

    Hvorfor (17/10-2026): begge stier loggede paa ``debug``, men driften
    koerer ``INFO`` (``apps/api/jarvis_api/app.py:213``). En fejlet skrivning
    var derfor 100 % usynlig — praecis den klasse der lod 80 wakeups forsvinde
    uden et eneste spor. At rapportere fejlen maa aldrig selv fejle.
    """
    logger.warning("state_store: kunne IKKE %s %s: %s", handling, name, exc)
    try:
        from core.services.central_anomaly import record_anomaly

        record_anomaly(
            source="state_store",
            exc_type=type(exc).__name__,
            message=f"state_store kunne ikke {handling} {name}: {exc}",
            module=__name__,
        )
    except Exception:
        # Anomali-kanalen er selv self-safe, men dens IMPORT kan fejle (cirkulaer
        # sti under opstart). WARNING'en ovenfor er allerede skrevet — den staar
        # tilbage som det primaere spor, saa intet gaar tabt her.
        return


def load_json(name: str, default: Any) -> Any:
    """Read ``state/<name>.json``; return ``default`` if missing/corrupt.

    Never raises — callers want a usable value, not an exception. En MANGLENDE
    fil er normal drift og logges ikke; en KORRUPT fil er en fejl og meldes
    synligt (17/10-2026), fordi en laeser ellers stiltiende ser ``default``.
    """
    p = _path(name)
    try:
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        _meld_fejl(name, "læse", exc)
        return default


def er_ulaesbar(name: str) -> bool:
    """True naar filen findes, har indhold, men ikke kan parses som JSON.

    Hvorfor den findes (17/10-2026): :func:`load_json` svarer ``default`` i
    BEGGE tilfaelde — filen findes ikke, og filen er korrupt. For en LAESER er
    det rigtigt. For en SKRIVER er det et tab: den skriver hele listen tilbage,
    og 80 poster bliver til nul, uden at noget i svaret eller loggen viser det.
    Skrive-stien spoerger derfor her FOERST og naegter at skrive.

    Sikker mod samtidig skrivning: :func:`save_json_strict` skriver til en
    temp-fil og omdoeber den, saa en laeser ser enten den gamle eller den nye
    fil — aldrig en halv.
    """
    p = _path(name)
    try:
        if not p.exists():
            return False
        tekst = p.read_text(encoding="utf-8")
    except OSError as exc:  # ulaesbar fil er ikke det samme som korrupt JSON
        logger.debug("state_store: kunne ikke laese %s: %s", name, exc)
        return False
    if not tekst.strip():
        return False
    try:
        json.loads(tekst)
    except ValueError:  # ugyldig JSON er netop svaret her: filen ER ulaesbar
        return True
    return False


def save_json(name: str, data: Any) -> None:
    """Atomically persist ``data`` to ``state/<name>.json``.

    Write-temp-then-rename so a crash mid-write can't leave a half-file.

    Self-safe med vilje: de 83 kaldesteder er daemon-tilstande, og en fejlet
    skrivning maa ikke draebe traaden. Men fejlen er ikke laengere TAVS
    (17/10-2026): den meldes som WARNING og til anomali-kanalen. Foer dette var
    et tab af en hel state-fil sporloest — kun et tal der var for lavt.
    """
    try:
        save_json_strict(name, data)
    except Exception as exc:
        _meld_fejl(name, "skrive", exc)


def save_json_strict(name: str, data: Any) -> None:
    """Atomically persist JSON and propagate failures to authoritative callers.

    Most state-store users are optional daemons and deliberately use
    :func:`save_json`, which is self-safe. Recovery ownership is different: a
    caller must not announce a successful settlement if the durable write
    failed. The unique temp name also prevents two threads from sharing one
    ``.tmp`` file before an outer cross-process lock is acquired.
    """
    p = _path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(
        p.suffix + f".{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8"
        )
        os.replace(tmp, p)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


@contextmanager
def med_laas(name: str):
    """Serialisér read-modify-write paa én state-fil paa tvaers af processer.

    `jarvis-api` og `jarvis-runtime` koerer samme kode i hver sin proces og
    deler disse filer. Uden en laas er «laes, aendr, gem» tre skridt hvor den
    ene proces kan naa at skrive imellem — og da hver gemning skriver HELE
    filen, forsvinder den andens aendring sporloest.

    Moensteret er taget fra `in_flight_runs._med_laas`, hvor det har vaeret i
    drift siden 12/9-2026 med samme begrundelse. Det bor her nu, saa den naeste
    delte fil ikke skal opfinde det igen.
    """
    p = _path(name).with_suffix(".lock")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def aendret_ns(name: str) -> int:
    """Filens mtime i nanosekunder, eller 0 naar den ikke findes.

    Hvorfor: `jarvis-api` og `jarvis-runtime` deler disse filer, men kun den
    ene muterer. Et modul der laeser sine globaler ÉN gang ved import viser
    derfor tilstanden som den saa ud da DENS proces startede — for api'en er
    det «tom», for altid. Maalt 25/9-2026 paa CT105: `continuity_kernel`,
    `initiative_accumulator` og `boredom_curiosity_bridge` stod alle tre paa
    nul i `/mc/runtime`, mens runtime-processen havde tikket dem hele dagen.

    At laese filen paa hver opslag retter det, men parser JSON hver gang.
    Denne lader kalderen gate paa mtime, saa et opslag koster ét `stat()`.
    """
    try:
        return _path(name).stat().st_mtime_ns
    except OSError:  # findes ikke / ikke laesbar — 0 betyder «ingen fil», ikke fejl
        return 0
