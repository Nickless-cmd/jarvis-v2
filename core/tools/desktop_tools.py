"""Jarvis' desktop som ét kaldbart værktøj — ni medlemmer i én handling.

Skærmen i `/ws/desktop` er en FLADE vi deler: Bjørn ser den i Desk, og jeg ser
den her. Før dette modul kunne jeg kun nå den ved at kalde `x_session` direkte
fra Python, hvilket ikke er et værktøj — det er en genvej ind i min egen kode.
Et værktøj er ikke færdigt når det er skrevet: det skal også stå i
`tool_scoping.py`, ellers annonceres det ikke for modellen og findes reelt ikke
(se noten dér, 6/9-2026).

De tre medlemmer der kom til 5/11-2026 er ikke pynt:

- `wait` — efter et klik ved hverken jeg eller klienten om programmet har nået
  at tegne. En fast sleep er enten for kort eller spildt tid; her MÅLES der om
  skærmen ændrede sig, og svaret siger hvad der skete.
- `zoom` — hele skærmen skaleres ned før nogen kigger på den, så små ting bliver
  ramt dårligt. Zoom tager et udsnit og skalerer det OP. Koordinaterne er altid
  i fuld skærm-opløsning, som Anthropics computer-toolset kræver det.
- `cursor_position` — markøren ligger ikke i skærmgrebet (X11 tegner den uden
  for billedbufferen). Uden den kan man ikke se hvor man peger, og så ser musen
  død ud selv om den flytter sig (målt 5/11-2026).

Skærmbilleder svarer med en STI, ikke med bytes: rå base64 er ubrugelig for mig,
og et skærmbillede jeg ikke kan se er ikke et skærmbillede — det er data. Stien
går direkte videre til `analyze_image`.
"""
from __future__ import annotations

import logging
import tempfile
import time
from typing import Any

logger = logging.getLogger(__name__)

#: Skærmgreb og zoom skriver en fil; resten er små xdotool-kald.
_AKTIONER = (
    "status", "screenshot", "zoom", "cursor_position",
    "move", "click", "type", "key", "wait",
)


def _ejer_workspace() -> str:
    """Ejerens workspace-navn. Kontekstens default når intet er bundet."""
    try:
        from core.identity.users import get_owner

        o = get_owner()
        return str(getattr(o, "workspace", "") or "bjorn") if o else "bjorn"
    except Exception:  # ingen brugerliste: default-navnet ER ejerens
        return "bjorn"


def _session() -> Any:
    """Kalderens X-session, startet hvis den ikke kører.

    `self` betyder EJERENS skærm — det er den flade Bjørn ser i panelet. Ejeren
    og Jarvis er ikke indespærret; et medlem er låst til eget workspace og får
    sin egen skærm. Kan workspace ikke opløses, fejler værktøjet — intet
    fallback.
    """
    from core.desktop.x_session import (
        PRIVILEGE_MEMBER, PRIVILEGE_SELF, SELF_USER, session_for,
    )
    from core.identity.workspace_context import current_user_id, current_workspace_name

    uid = current_user_id()
    privilege, bruger = PRIVILEGE_SELF, SELF_USER
    if uid:
        from core.identity.users import find_user_by_discord_id

        u = find_user_by_discord_id(uid)
        if u is None or u.role != "owner":
            # Ukendt eller ikke-ejer: aldrig mere end member-rettigheder.
            privilege, bruger = PRIVILEGE_MEMBER, uid
    elif current_workspace_name() != _ejer_workspace():
        # Konteksten bærer hverken et bruger-id eller ejerens workspace. Siden
        # `self` nu betyder ejerens skærm, må vi ikke gætte: en medlems-samtale
        # uden bundet id ville ellers få ejerens skærm. Nægt frem for at give
        # mere adgang end konteksten kan dokumentere.
        raise RuntimeError(
            "desktop: kan ikke afgøre hvem der handler — nægter at bruge ejerens skærm"
        )
    sess = session_for(bruger, privilege)
    res = sess.start()
    if res.get("status") != "ok":
        raise RuntimeError(str(res.get("error") or "desktoppen kunne ikke startes"))
    return sess


def _gem(jpeg: bytes, navn: str) -> dict[str, Any]:
    """Skriv JPEG'en til en fil og svar med stien."""
    with tempfile.NamedTemporaryFile(
        prefix=f"jarvis-desktop-{navn}-", suffix=".jpg", delete=False,
    ) as f:
        f.write(jpeg)
        sti = f.name
    return {"path": sti, "bytes": len(jpeg), "format": "jpeg"}


def _svar(resultat: Any) -> dict[str, Any]:
    if isinstance(resultat, dict) and resultat.get("status") == "error":
        return {"status": "error", "error": resultat.get("error"), "code": resultat.get("code")}
    return {"status": "ok", "result": resultat}


def _koer(action: str, args: dict[str, Any]) -> dict[str, Any]:
    """Udfør én handling. Aldrig exception — en fejl er et svar, ikke et crash."""
    sess = _session()

    if action == "status":
        markor = sess.cursor()
        return {
            "status": "ok",
            "result": {
                "bredde": sess.bredde,
                "hoejde": sess.hoejde,
                "display": sess.display,
                "markor": {"x": markor.get("x"), "y": markor.get("y")}
                if markor.get("status") == "ok" else None,
            },
        }

    if action == "screenshot":
        ramme = sess.frame()
        if not isinstance(ramme, (bytes, bytearray)):
            return _svar(ramme)
        return {"status": "ok", "result": _gem(bytes(ramme), "skarm")}

    if action == "zoom":
        udsnit = sess.zoom(
            args.get("x"), args.get("y"),
            args.get("width"), args.get("height"),
            args.get("faktor", 2),
        )
        if not isinstance(udsnit, (bytes, bytearray)):
            return _svar(udsnit)
        return {"status": "ok", "result": _gem(bytes(udsnit), "zoom")}

    if action == "cursor_position":
        return _svar(sess.cursor())

    if action == "wait":
        return _svar(sess.wait(args.get("timeout_ms", 1500)))

    if action in ("move", "click"):
        msg: dict[str, Any] = {"t": "mouse", "x": args.get("x"), "y": args.get("y")}
        if action == "move":
            msg["kind"] = "move"
            return _svar(sess.input(msg))
        msg["kind"] = "down"
        msg["button"] = args.get("button") or "left"
        foerste = sess.input(msg)
        if foerste.get("status") != "ok":
            return _svar(foerste)
        # Et klik er to hændelser. Uden «up» hænger knappen nede, og næste
        # klik bliver et træk i stedet for et klik.
        andet = sess.input({**msg, "kind": "up"})
        return _svar(andet)

    if action == "type":
        tekst = args.get("text")
        if tekst in (None, ""):
            return {"status": "error", "error": "text er påkrævet"}
        return _svar(sess.input({"t": "text", "text": str(tekst)}))

    if action == "key":
        tast = args.get("key")
        if tast in (None, ""):
            return {"status": "error", "error": "key er påkrævet"}
        ned = sess.input({"t": "key", "kind": "down", "key": str(tast)})
        if ned.get("status") != "ok":
            return _svar(ned)
        return _svar(sess.input({"t": "key", "kind": "up", "key": str(tast)}))

    return {"status": "error", "error": f"ukendt action: {action}"}


def _exec_jarvis_desktop(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip()
    if action not in _AKTIONER:
        return {"status": "error", "error": "action skal være en af: " + ", ".join(_AKTIONER)}
    try:
        return _koer(action, args)
    except Exception as exc:  # en død desktop må ikke vælte hele turen: svar ærligt
        logger.warning("jarvis_desktop/%s fejlede: %s", action, exc)
        return {"status": "error", "error": f"desktoppen svarede ikke: {exc}"}


def _nr(desc: str) -> dict[str, Any]:
    return {"type": "number", "description": desc}


DESKTOP_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "jarvis_desktop",
            "description": (
                "Jarvis' OWN Linux desktop — the same screen the user sees in the Desk "
                "'Desktop' panel, so this is a SHARED surface, not a private sandbox. "
                "Actions: `screenshot` (returns a file path — pass it to `analyze_image` to "
                "actually look), `zoom` (a magnified crop, for hitting something small), "
                "`cursor_position` (where the pointer is), `move`, `click`, `type`, `key`, "
                "`wait` (blocks until the screen CHANGES, so you stop guessing with sleeps), "
                "`status`. Coordinates are always in full screen pixels (1280x800). "
                "Take a screenshot before you click: you cannot see otherwise."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": list(_AKTIONER),
                        "description": "What to do on the desktop.",
                    },
                    "x": _nr("X in full screen pixels."),
                    "y": _nr("Y in full screen pixels."),
                    "width": _nr("Zoom only: crop width in pixels."),
                    "height": _nr("Zoom only: crop height in pixels."),
                    "faktor": _nr("Zoom only: magnification 1-8 (default 2)."),
                    "button": {
                        "type": "string",
                        "enum": ["left", "middle", "right"],
                        "description": "Click button (default left).",
                    },
                    "text": {"type": "string", "description": "Type: text to type into the focused window."},
                    "key": {
                        "type": "string",
                        "description": "Key: a single key such as Return, Tab, Escape, BackSpace, Up, Down.",
                    },
                    "timeout_ms": _nr("Wait: how long to wait for a change, max 10000 (default 1500)."),
                },
                "required": ["action"],
            },
        },
    },
]

DESKTOP_TOOL_HANDLERS = {
    "jarvis_desktop": _exec_jarvis_desktop,
}

#: Navnene ét sted, saa scoping-lister og pruning ikke kan komme ud af trit.
DESKTOP_TOOL_NAMES: tuple[str, ...] = tuple(DESKTOP_TOOL_HANDLERS)
