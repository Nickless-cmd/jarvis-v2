"""Er DEN HER koersel uovervaaget? — run-scopet, ikke gaettet.

K9's anden halvdel: «requested confinement fails before execution when
unavailable». Bjoern 10/9-2026: kun for autonome koersler.

## Hvorfor en ContextVar og ikke et navnepraefiks

Autonome run-id'er begynder med `autonomous-`, og et vaerktoej faar run-id'et
med i `_runtime_turn_id`. Det ville have vaeret nemmere at laese praefikset.
Men et praefiks er en KONVENTION, ikke en sandhed — samme indvending som mod
at udlede en vaerktoejs-placering af `operator_`-navnet i K1. Konventionen
holder indtil den dag nogen doeber et run noget andet, og saa fejler et
SIKKERHEDS-valg stille.

Her sætter koerslen selv flaget, én gang, dér hvor den ved besked.

## Hvorfor fail-closed KUN for autonome

En uovervaaget koersel har ingen til at redde sig hvis sandkassen mangler; den
skal hellere lade vaere. Bjoerns egen sti er fail-open med vilje — en
manglende mekanisme maa ikke goere hans bagdoer ubrugelig, og han er der selv
til at se hvad der sker.
"""
from __future__ import annotations

import contextvars
import time

_autonom: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "jarvis_run_autonom", default=False,
)


def set_autonomous(vaerdi: bool):
    """Markér koerslen. Returnerer token'et saa kalderen kan nulstille."""
    return _autonom.set(bool(vaerdi))


def reset_autonomous(token) -> None:
    try:
        _autonom.reset(token)
    except Exception:
        pass
    # A bounded autonomous run must not leave its counters in a reused
    # context (notably tests and worker pools).  Ordinary runs use zero = no
    # extra ceiling.
    try:
        _max_tool_calls.set(0)
        _tool_calls_used.set(0)
        _deadline_monotonic.set(0.0)
    except Exception:  # context cleanup is best-effort after run completion
        pass


def is_autonomous() -> bool:
    """Kaster aldrig. Ved vi det ikke, er svaret NEJ — og saa opfoerer alt sig
    som foer."""
    try:
        return bool(_autonom.get())
    except Exception:
        return False


# ── Mekanisk budget for uovervågede side-opgaver ──────────────────────────
# Nul betyder «ingen ekstra per-run-grænse» og bevarer alle eksisterende runs.
# Idle-dispatcheren sætter begge værdier eksplicit; promptens ord er dermed en
# forklaring af en runtime-regel, ikke selve håndhævelsen.
_max_tool_calls: contextvars.ContextVar[int] = contextvars.ContextVar(
    "jarvis_autonomous_max_tool_calls", default=0,
)
_tool_calls_used: contextvars.ContextVar[int] = contextvars.ContextVar(
    "jarvis_autonomous_tool_calls_used", default=0,
)
_deadline_monotonic: contextvars.ContextVar[float] = contextvars.ContextVar(
    "jarvis_autonomous_deadline_monotonic", default=0.0,
)


def set_autonomous_budget(*, max_tool_calls: int = 0, max_seconds: float = 0.0) -> None:
    _max_tool_calls.set(max(0, int(max_tool_calls or 0)))
    _tool_calls_used.set(0)
    _deadline_monotonic.set(
        time.monotonic() + max(0.0, float(max_seconds or 0.0))
        if max_seconds else 0.0
    )


def consume_autonomous_tool_budget() -> bool:
    """Reserve one tool call, or refuse it after the deadline/ceiling."""
    if not is_autonomous():
        return True
    deadline = float(_deadline_monotonic.get() or 0.0)
    if deadline and time.monotonic() >= deadline:
        return False
    ceiling = int(_max_tool_calls.get() or 0)
    used = int(_tool_calls_used.get() or 0)
    if ceiling and used >= ceiling:
        return False
    _tool_calls_used.set(used + 1)
    return True


def autonomous_budget_state() -> dict[str, int | float | bool]:
    deadline = float(_deadline_monotonic.get() or 0.0)
    return {
        "max_tool_calls": int(_max_tool_calls.get() or 0),
        "tool_calls_used": int(_tool_calls_used.get() or 0),
        "deadline_set": bool(deadline),
        "seconds_remaining": max(0.0, deadline - time.monotonic()) if deadline else 0.0,
    }


# ── Tilstedeværelse: er der et menneske i den anden ende? (19/10-2026) ──────
#
# Bjørn: «en autonom vækning i en tilstedeværelse-session bør arve den
# igangværende sessions permissions og tool-sæt — det er en vækning, ikke et
# autonomt baggrunds-run».
#
# `is_autonomous` svarer på et ANDET spørgsmål: blev kørslen startet af
# systemet? Det skal blive ved med at være sandt for en vækning — ellers mister
# `bash` sin indespærring (K9). Tilstedeværelse er en separat kendsgerning, og
# den sættes af kørslen selv, samme sted som flaget, udledt af SESSIONEN.

_user_present: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "jarvis_user_present", default=False,
)


def set_user_present(vaerdi: bool):
    """Markér om der er et menneske i den anden ende. Returnerer token'et."""
    return _user_present.set(bool(vaerdi))


def reset_user_present(token) -> None:
    try:
        _user_present.reset(token)
    except Exception:  # token kan tilhøre en anden kontekst — reset er best-effort
        pass


def user_present() -> bool:
    """Er der et menneske i den anden ende af DENNE kørsel? Kaster aldrig.

    Fail-closed: ved vi det ikke, er svaret NEJ, og så gælder den autonome
    politik som før.
    """
    try:
        return bool(_user_present.get())
    except Exception:  # uden for en kontekst: fail-closed, aldrig fail-open
        return False


# ── Koerslens identitet: run-id og origin (15/9-2026) ────────────────────
#
# `skill_invoked` stod med TOMT run_id paa hans synlige tur 16:29, selvom
# telemetrien var bygget samme dag. Kilden var `run_closure_gate`s globale
# «seneste run» — og den saettes KUN af `runtime.autonomous_run_started`. En
# synlig tur publicerer aldrig det event, og i jarvis-api (hvor de synlige ture
# koerer) er gatens lytter ikke engang startet. Feltet kunne altsaa aldrig
# blive udfyldt for netop de ture der betyder noget.
#
# Samme loesning som flaget ovenfor: koerslen saetter det selv, én gang, dér
# hvor den ved besked. En global ville ogsaa kollidere naar to koersler
# overlapper i samme proces; en ContextVar kan ikke.

_run_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "jarvis_run_id", default="",
)
_origin: contextvars.ContextVar[str] = contextvars.ContextVar(
    "jarvis_run_origin", default="",
)


def set_run_identity(run_id: str, origin: str = "") -> None:
    _run_id.set(str(run_id or "").strip())
    _origin.set(str(origin or "").strip())


def current_run_id() -> str:
    """"" naar ingen koersel har sat det. Kaster aldrig."""
    try:
        return _run_id.get()
    except Exception:
        return ""


def current_origin() -> str:
    """"" for en almindelig brugertur, eller naar vi ikke ved det."""
    try:
        return _origin.get()
    except Exception:
        return ""
