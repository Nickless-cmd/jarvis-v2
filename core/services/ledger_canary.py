"""Efterfyld en session i ledgeren og slå skyggen til.

## Hvorfor efterfyldningen skal ske FØRST

En session der har kørt i månedsvis har hundredvis af beskeder i
`chat_messages` som ledgeren aldrig har set. Slog man bare skyggen til, ville
ledgeren have 3 beskeder og tabellen 300 — drift-detektionen ville melde
uenighed for altid, og porten til et skifte ville aldrig kunne åbne. Skyggen
ville måle ingenting.

Så: skriv historikken ind, og slå SÅ skyggen til. Rækkefølgen er ikke en
detalje. Gjorde man det omvendt, ville nye beskeder få lave sekvensnumre og
historikken lande bagved dem — samme samtale, forkert orden, og en uenighed
der ligner data-tab men er en fejl i overførslen.

## Hvorfor den kan køres igen

`event_id` er beskedens eget `message_id`. En gentagen efterfyldning bliver
derfor til nul nye hændelser. Det er med vilje: det farlige øjeblik er ikke
det første forsøg, men det andet — når nogen er i tvivl om det gik godt.

## Vinduet imellem

Mellem sidste efterfyldte besked og skiftet til `shadow` er der et øjeblik
hvor en ny besked kun lander i tabellen. Derfor rapporterer denne funktion
drift MED DET SAMME bagefter: er der uenighed, er den opdaget i samme minut,
og skyggen kan slås fra igen med `abandon_shadow`.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Felterne der udgør en besked. `git_sha` er en DOVEN kolonne — den står ikke
#: i CREATE TABLE, kun i en migration der køres af den der skriver
#: kompakt-markører. En frisk database har den ikke, så listen skæres ned til
#: det tabellen FAKTISK har frem for at antage en form.
_FELTER = ("message_id", "role", "content", "user_id", "workspace_name",
           "reasoning_content", "git_sha", "content_json", "created_at")


def _kolonner(conn) -> list[str]:
    findes = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)")}
    return [k for k in _FELTER if k in findes]


def backfill(session_id: str) -> dict[str, Any]:
    """Skriv sessionens eksisterende beskeder ind i ledgeren. Idempotent."""
    from core.runtime.db import connect
    from core.runtime.db_session_ledger import (
        acquire_write_lease, append_session_events, read_session_events,
        release_write_lease,
    )

    sid = str(session_id or "").strip()
    with connect() as conn:
        kols = _kolonner(conn)
        rows = conn.execute(
            f"SELECT {', '.join(kols)} FROM chat_messages WHERE session_id = ? "
            "ORDER BY id", (sid,)
        ).fetchall()
    if not rows:
        return {"session_id": sid, "beskeder": 0, "skrevet": 0,
                "grund": "sessionen har ingen beskeder"}

    haendelser = []
    for r in rows:
        p = {k: r[i] for i, k in enumerate(kols)}
        haendelser.append({"event_id": str(p["message_id"]),
                           "kind": "message", "payload": p})

    # En efterfyldning kan kun FØJE TIL. Mangler der noget i MIDTEN, lander det
    # bagerst — og så er rækkefølgen forkert fra hullet og frem.
    #
    # Målt 9/9-2026 på «Kode-session»: én kompakt-markør manglede på plads 474.
    # Efterfyldningen lagde den på seq 579, og drift meldte 291 uenigheder.
    # Detektoren gjorde præcis sit arbejde; efterfyldningen gjorde ikke sit.
    #
    # Derfor: hvis ledgeren ikke er et PRÆFIKS af tabellen, afvises det med en
    # henvisning til `reseed`. At føje til alligevel ville lave en ledger der
    # ser fyldt ud og er forkert.
    findes = [e["event_id"] for e in read_session_events(sid)]
    vil = [h["event_id"] for h in haendelser]
    if findes and findes != vil[:len(findes)]:
        for i, (a, b) in enumerate(zip(findes, vil)):
            if a != b:
                break
        else:
            i = len(findes)
        return {"session_id": sid, "beskeder": len(rows), "skrevet": 0,
                "grund": f"ledgeren afviger fra tabellen ved plads {i} — "
                         "en efterfyldning ville lande bagerst og gøre "
                         "rækkefølgen forkert; brug reseed()"}

    token = acquire_write_lease(sid, owner="canary_backfill")
    if token is None:
        return {"session_id": sid, "beskeder": len(rows), "skrevet": 0,
                "grund": "en anden proces holder leasen"}
    try:
        r = append_session_events(sid, owner="canary_backfill",
                                  token=token, events=haendelser)
    finally:
        release_write_lease(sid, owner="canary_backfill", token=token)
    return {"session_id": sid, "beskeder": len(rows),
            "skrevet": r["written"], "dubletter": r["duplicates"]}


def enable_shadow(session_id: str) -> dict[str, Any]:
    """Efterfyld, slå skyggen til, og MÅL med det samme om det holdt."""
    from core.runtime.db_session_ledger import advance_storage_mode, storage_mode
    from core.services.projection_drift import compare

    sid = str(session_id or "").strip()
    nu = storage_mode(sid)
    if nu != "legacy":
        return {"session_id": sid, "ok": False, "grund": f"sessionen er allerede {nu!r}"}

    fyld = backfill(sid)
    # EN TOM SESSION ER DEN RENESTE SAG, IKKE EN FEJL (10/9-2026).
    # `enable_shadow` var bygget til at efterfylde en EKSISTERENDE session, og
    # afviste derfor en helt ny. Da armeringen blev koblet paa oprettelsen,
    # fyrede den praecis dér hvor der var nul beskeder — mekanismen koerte og
    # gjorde ingenting. Nul historik betyder at der intet er at tabe: der er
    # ingen tidligere beskeder som ledgeren kan komme til at mangle.
    _tom = fyld["skrevet"] == 0 and fyld["beskeder"] == 0
    if fyld.get("grund") and _tom and "ingen beskeder" not in str(fyld.get("grund")):
        return {"session_id": sid, "ok": False, "grund": fyld["grund"], "backfill": fyld}

    if not advance_storage_mode(sid, to="shadow"):
        return {"session_id": sid, "ok": False,
                "grund": "kunne ikke skifte til shadow — findes sessionen?",
                "backfill": fyld}

    # Måles NU, ikke om en uge. Vinduet mellem efterfyldning og skifte er kort,
    # men det findes, og en uenighed skal opdages i samme minut.
    d = compare(sid)
    return {"session_id": sid, "ok": bool(d["enige"]), "backfill": fyld,
            "drift": {"enige": d["enige"], "ledger": d["ledger_beskeder"],
                      "tabel": d["tabel_beskeder"],
                      "uenigheder": d["uenigheder"][:5]}}


def reseed(session_id: str) -> dict[str, Any]:
    """Skriv sessionens ledger-hændelser HELT om, i tabellens rækkefølge.

    Nødvendig fordi en efterfyldning kun kan føje til: opdages et hul i midten
    bagefter, kan det ikke lappes ved at appende.

    Sikker PRÆCIS fordi sessionen er i `shadow`: dér er ledgeren ikke sandheden,
    og der er derfor ingen kanonisk hændelse at slette. Kaldet afviser en
    session der er i `ledger` — dér ville dette være at kassere historik.
    """
    from core.runtime.db import connect
    from core.runtime.db_session_ledger import storage_mode

    sid = str(session_id or "").strip()
    nu = storage_mode(sid)
    if nu != "shadow":
        return {"session_id": sid, "ok": False,
                "grund": f"kun for shadow-sessioner; denne er {nu!r}"}
    from core.services.projection_runtime import _ensure_checkpoint_table
    with connect() as conn:
        conn.execute("DELETE FROM session_events WHERE session_id = ?", (sid,))
        # Markøren skal OGSÅ væk: en projektion der troede den var foldet til
        # seq 579, ville springe det hele over efter en omskrivning.
        _ensure_checkpoint_table(conn)
        conn.execute("DELETE FROM projection_checkpoints WHERE session_id = ?", (sid,))
    r = backfill(sid)

    from core.services.projection_drift import compare
    d = compare(sid)
    return {"session_id": sid, "ok": bool(d["enige"]), "backfill": r,
            "drift": {"enige": d["enige"], "ledger": d["ledger_beskeder"],
                      "tabel": d["tabel_beskeder"],
                      "uenigheder": d["uenigheder"][:5]}}


# ── Armering: den NAESTE nye session baerer vinduet ─────────────────────────
#
# Bjoerns valg 10/9-2026. Alternativet var at indrullere hans igangvaerende
# samtale (729 beskeder), men `advance_storage_mode` er ENVEJS med vilje, og en
# ren start uden efterfyldning giver et vindue der loeber paa aegte trafik fra
# foerste besked — uden en irreversibel aendring paa en samtale der er i gang.
#
# Grunden til at armeringen overhovedet skal bygges: kanariefuglen sad paa TO
# sessioner der havde vaeret doede i 20 timer, mens dagens trafik loeb et andet
# sted. Et observationsvindue der ikke foelger trafikken, er et lukket vindue.

_ARM_FIL = "ledger_canary_armed"


def _arm_sti():
    from core.runtime.workspace_paths import shared_dir
    return shared_dir() / "runtime" / f"{_ARM_FIL}.json"


def arm_next_session(*, note: str = "") -> dict[str, Any]:
    """Indrullér den NAESTE nye chat-session i skyggen. Én gang."""
    import json
    from datetime import UTC, datetime
    sti = _arm_sti()
    try:
        sti.parent.mkdir(parents=True, exist_ok=True)
        sti.write_text(json.dumps({
            "armed": True, "armed_at": datetime.now(UTC).isoformat(),
            "note": str(note or ""),
        }), encoding="utf-8")
        return {"ok": True, "sti": str(sti)}
    except Exception as exc:
        return {"ok": False, "grund": f"{type(exc).__name__}: {exc}"}


def is_armed() -> bool:
    import json
    try:
        return bool(json.loads(_arm_sti().read_text(encoding="utf-8")).get("armed"))
    except Exception:
        return False


def disarm() -> None:
    try:
        _arm_sti().unlink()
    except Exception:
        pass


def maybe_enroll_new_session(session_id: str) -> dict[str, Any] | None:
    """Kaldes naar en ny session oprettes. Fejler ALDRIG opad.

    En kanariefugl maa ikke kunne vaelte oprettelsen af en samtale. Gaar noget
    galt, forbliver sessionen `legacy` — altsaa praecis som foer — og det staar
    i loggen.
    """
    sid = str(session_id or "").strip()
    if not sid or not is_armed():
        return None
    try:
        ud = enable_shadow(sid)
        disarm()                      # kun ÉN session, uanset udfald
        if ud.get("ok"):
            logger.info("ledger-kanariefugl indrulleret: %s", sid)
        else:
            # Loggen sagde foer «indrulleret» ogsaa naar ok=False. En linje der
            # melder succes og baerer sin egen fejl er vaerre end ingen linje.
            logger.warning("ledger-kanariefugl kunne IKKE indrullere %s: %s",
                           sid, ud.get("grund") or ud)
        return ud
    except Exception:
        logger.warning("kunne ikke indrullere %s i ledger-skyggen — "
                       "sessionen forbliver legacy", sid, exc_info=True)
        disarm()
        return None
