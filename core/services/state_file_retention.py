"""Rotation af operationel runtime-tilstand i ``~/.jarvis-v2``.

Dækker to ting: de operationelle JSON-filer i ``state/`` og forældreløse
vedhæftnings-mapper i ``uploads/``.

Målt 2026-08-30 — fire filer havde aldrig fået ryddet:

    plan_proposals.json            400 poster, ALLE over 7 dage, ældste 125 dage
    pending_approvals.json         164 poster, 161 over 7 dage, ældste 125 dage
    in_flight_runs.json            110 poster, 108 over 7 dage, ældste 118 dage
    agentic_run_checkpoints.json    79 poster,  78 over 7 dage, ældste  47 dage

Til sammenligning roterer ``nudge_broend.json`` pænt (488 poster, ingen over
6 dage) — mønsteret findes altså i huset, det var bare ikke anvendt her.

De prompt-sektioner der læser filerne er session-scopede, så gamle poster fra
andre sessioner når aldrig Jarvis' prompt. De hober sig bare op. Det er derfor
rotation og ikke en hastesag: filerne er små, men de vokser uden loft, og en
zombie-post er stadig en post nogen en dag kommer til at tro på.

Vinduerne er bevidst rundhåndede — formålet er at fjerne det der er dødt uden
tvivl, ikke at trimme tæt på kanten. En kørende tur må ALDRIG kunne rammes.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

# Felter der kan bære postens alder, i prioriteret rækkefølge. Filerne bruger
# forskellige navne (``created_at``, ``interrupted_at``, ``started_at`` …), så
# vi prøver dem i rækkefølge og bruger den første der kan parses.
_TS_FIELDS: tuple[str, ...] = (
    "resolved_at", "interrupted_at", "created_at", "started_at",
    "updated_at", "requested_at", "ts", "timestamp",
)

# fil → hvor længe en post må ligge før den er død.
# in_flight_runs er kortest: en tur der har været "i gang" i tre døgn er en
# zombie, ikke et arbejde. Resten er rundhåndede.
POLICIES: dict[str, int] = {
    "in_flight_runs.json": 3,
    "agentic_run_checkpoints.json": 7,
    "pending_approvals.json": 14,
    "plan_proposals.json": 30,
}


def _state_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".jarvis-v2", "state")


def parse_ts(value: object) -> datetime | None:
    """Tolk et tidsstempel. Ukendt form → None (posten regnes som ung)."""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def record_age_days(record: object, now: datetime) -> float | None:
    """Postens alder i dage, eller None hvis den ikke bærer et brugbart stempel."""
    if not isinstance(record, dict):
        return None
    for field in _TS_FIELDS:
        if field in record:
            ts = parse_ts(record.get(field))
            if ts is not None:
                return (now - ts).total_seconds() / 86400.0
    return None


def select_expired(
    records: dict[str, object], *, max_age_days: int, now: datetime
) -> list[str]:
    """Nøgler på poster der er ældre end vinduet. Ren funktion.

    Poster UDEN brugbart tidsstempel beholdes altid — vi sletter aldrig noget
    vi ikke kan datere. Hellere en efterladt post end en slettet aktiv tur.
    """
    out: list[str] = []
    for key, rec in (records or {}).items():
        age = record_age_days(rec, now)
        if age is not None and age > max_age_days:
            out.append(str(key))
    return out


def prune_state_file(
    path: str, *, max_age_days: int, now: datetime | None = None
) -> int:
    """Fjern udløbne poster fra én fil. Returnér antal fjernede.

    Self-safe: enhver fejl (manglende fil, ugyldig JSON, uventet form) → 0.
    Skriver atomisk via tmp + replace, så en afbrudt kørsel aldrig efterlader
    en halv fil.
    """
    _now = now or datetime.now(UTC)
    try:
        if not os.path.exists(path):
            return 0
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not data:
            return 0
        expired = select_expired(data, max_age_days=max_age_days, now=_now)
        if not expired:
            return 0
        for key in expired:
            data.pop(key, None)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(tmp, path)
        return len(expired)
    except Exception:
        return 0


def prune_all_state_files(*, now: datetime | None = None) -> dict[str, int]:
    """Kør rotationen på alle filer i ``POLICIES``. Returnér {fil: antal fjernet}."""
    directory = _state_dir()
    result: dict[str, int] = {}
    for name, days in POLICIES.items():
        removed = prune_state_file(
            os.path.join(directory, name), max_age_days=days, now=now
        )
        if removed:
            result[name] = removed
    return result


# ── Forældreløse uploads ────────────────────────────────────────────────────
#
# Vedhæftninger gemmes som ``uploads/{session_id}/{uuid}_{filnavn}``
# (``routes/attachments.py``). Når en session forsvinder, bliver mappen liggende.
# Målt 2026-08-30: 166 af 169 filer (92,3 MB) lå i mapper uden sessions-række.
#
# MEN en manglende sessions-række betyder IKKE at samtalen er væk: 7 af de 19
# mapper hørte til sessioner der stadig havde beskeder i ``chat_messages`` —
# én med 3.799. Havde vi slettet på "ingen sessions-række", havde vi revet
# vedhæftninger ud af levende samtaler. Reglen kræver derfor BEGGE dele.

def find_orphan_upload_dirs(
    upload_root: str, *, session_is_known
) -> list[str]:
    """Mapper hvis session hverken har en række eller beskeder. Ren udvælgelse.

    ``session_is_known(session_id) -> bool`` slås op udefra, så logikken kan
    testes uden database. Løse filer i roden røres aldrig — de hører ikke til
    en session og kan stadig være refereret.
    """
    out: list[str] = []
    try:
        for name in sorted(os.listdir(upload_root)):
            path = os.path.join(upload_root, name)
            if not os.path.isdir(path):
                continue
            try:
                if not session_is_known(name):
                    out.append(name)
            except Exception:
                continue          # tvivl → behold
    except Exception:
        return []
    return out


def cleanup_orphan_uploads() -> dict[str, int]:
    """Fjern vedhæftnings-mapper for sessioner der hverken har række eller beskeder.

    Returnerer ``{"dirs": n, "files": n, "bytes": n}``. Self-safe.
    """
    import shutil

    root = os.path.join(os.path.expanduser("~"), ".jarvis-v2", "uploads")
    stats = {"dirs": 0, "files": 0, "bytes": 0}
    try:
        from core.runtime.db import connect
    except Exception:
        return stats

    def _known(session_id: str) -> bool:
        with connect() as conn:
            if conn.execute(
                "SELECT 1 FROM chat_sessions WHERE id = ? LIMIT 1", (session_id,)
            ).fetchone():
                return True
            return conn.execute(
                "SELECT 1 FROM chat_messages WHERE session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone() is not None

    try:
        for name in find_orphan_upload_dirs(root, session_is_known=_known):
            path = os.path.join(root, name)
            for base, _dirs, files in os.walk(path):
                for f in files:
                    try:
                        stats["bytes"] += os.path.getsize(os.path.join(base, f))
                        stats["files"] += 1
                    except Exception:
                        pass
            shutil.rmtree(path, ignore_errors=True)
            stats["dirs"] += 1
    except Exception:
        pass
    return stats


# ---------------------------------------------------------------------------
# Roterede logfiler (2026-09-27)
# ---------------------------------------------------------------------------
#
# `~/.jarvis-v2/logs` roteres af skrivernes egne cron-jobs, men INGEN sletter
# det roterede bagefter. Målt 27/9-2026: `cache_warmer.jsonl.1` (28 MB) og
# `cache_warmer_cron.log.1` (19 MB) lå fra 13. september — 47 MB der aldrig
# kunne læses igen af nogen.
#
# Kun ROTEREDE filer røres. Den aktive `cache_warmer.jsonl` skrives der til
# hvert tiende minut, og en oprydning der ikke kan kende forskel på de to er
# farligere end de 47 MB er værd.

_ROTEREDE_ENDELSER: tuple[str, ...] = (".1", ".2", ".3", ".gz", ".old")

#: Rundhåndet med vilje. En roteret log er død i samme øjeblik den roteres;
#: fjorten dage er kun til at kunne kigge tilbage på en hændelse der lige var.
_LOG_MAX_AGE_DAGE = 14


def _log_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".jarvis-v2", "logs")


def er_roteret(navn: str) -> bool:
    """Sandt for en logfil der er rullet fra, falsk for den der skrives til.

    Endelsen alene er ikke nok: `foo.1` er roteret, men en fil der HEDDER
    `.gz` uden noget foran er ikke en log. Der kræves et navn før endelsen.
    """
    for endelse in _ROTEREDE_ENDELSER:
        if navn.endswith(endelse) and len(navn) > len(endelse):
            return True
    return False


def prune_rotated_logs(
    *, max_age_days: int = _LOG_MAX_AGE_DAGE, now: datetime | None = None
) -> dict[str, int]:
    """Slet roterede logfiler ældre end ``max_age_days``. Self-safe.

    Returnerer ``{"fjernet": n, "bytes": n}``. Aldre måles på filens mtime —
    en roteret fil skrives ikke til, så mtime ER tidspunktet den blev rullet
    fra.
    """
    stats = {"fjernet": 0, "bytes": 0}
    rod = _log_dir()
    if not os.path.isdir(rod):
        return stats
    graense = (now or datetime.now(UTC)) - timedelta(days=max(max_age_days, 0))
    try:
        navne = os.listdir(rod)
    except OSError:
        # Kan mappen ikke listes (rettigheder, mount væk), er der intet at
        # rydde op i — og en baggrundsdæmon skal ikke vælte af det. Samme
        # holdning som `if not os.path.isdir(rod)` ovenfor.
        return stats
    for navn in navne:
        if not er_roteret(navn):
            continue
        sti = os.path.join(rod, navn)
        try:
            # Samme link-disciplin som `cleanup_old_results`: en oprydning der
            # kører af sig selv må aldrig følge et link ud af sin egen mappe.
            #
            # `islink` er nok her, og der stod oprindeligt en realpath-kontrol
            # ved siden af. Den blev fjernet igen: listningen er ikke rekursiv,
            # så hver sti er et navn DIREKTE i mappen, og er det ikke et link,
            # kan dens realpath ikke ligge et andet sted. Grenen kunne ikke
            # nås af nogen test — og et værn ingen test kan ramme er ikke et
            # værn, det er kode man tror på.
            if os.path.islink(sti) or not os.path.isfile(sti):
                continue
            st = os.stat(sti)
            if datetime.fromtimestamp(st.st_mtime, UTC) > graense:
                continue
            os.unlink(sti)
        except OSError:
            # Én fil vi ikke kunne stat'e eller slette må ikke stoppe de
            # øvrige. Den forsvinder bare ikke i denne runde, og næste
            # kørsel prøver igen — den er stadig gammel til den tid.
            continue
        stats["fjernet"] += 1
        stats["bytes"] += int(st.st_size)
    return stats
