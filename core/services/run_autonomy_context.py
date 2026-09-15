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


def is_autonomous() -> bool:
    """Kaster aldrig. Ved vi det ikke, er svaret NEJ — og saa opfoerer alt sig
    som foer."""
    try:
        return bool(_autonom.get())
    except Exception:
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
