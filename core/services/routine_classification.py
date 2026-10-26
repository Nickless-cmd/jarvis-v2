"""Klassifikation af en rutine ved oprettelsen — valget, ikke gættet.

Baggrund (Bjørn 19/10-2026)
---------------------------
«Meningen med routiner er det er noget du og bruger opretter sammen. Rutine
holder opgaven -> sender til inbox -> inbox vurdere klassifikation af indhold
-> inbox aktiv/idle … når en rutine oprettes skal man vælge om den skal udføre
i baggrunden og rapportere til inbox eller om rutines udføres af dig hvor
brugeren sidst var aktiv … derfor skal vi osse være sikker på inbox fremhæver
vigtige beskeder.»

To ting følger af det, og de er begge designvalg her:

1. **Klassifikationen sættes ved oprettelsen.** Den der opretter ved allerede
   hvad opgaven er: en medicinpåmindelse er *til brugeren, skal ses*, en
   natlig inspektion er *til mig, kan vente*. En dommer der læser teksten ved
   hver poll ville være dyr, nondeterministisk — og det er præcis sådan en
   gammel opgave starter midt i en kørende samtale.

2. **`kraever_handling` er en konsekvens, ikke et løsrevet flag.** I dag
   skriver den oprettende part en boolean i hånden, og derfor kunne 16
   inspektions-poster alle have `kraever_handling=0` mens 9 af dem stadig stod
   som «VENTER PÅ DIG». Klassen udleder flaget; den enkelte post kan ikke
   længere modsige sig selv.

Fail-closed
-----------
En ukendt `execution_mode` eller `importance` kaster `ValueError` frem for at
falde tilbage på en standard. En tastefejl der stille bliver «normal» er en
opgave der aldrig bliver fremhævet — og ingen opdager det, fordi intet fejler.
Tom streng er derimod et bevidst «brug standarden»: det er den vej alle
eksisterende kaldesteder går, så tilføjelsen ændrer ingen adfærd.
"""
from __future__ import annotations

from core.services.routine_types import (
    RoutineClassification,
    RoutineExecutionMode,
    RoutineImportance,
)

#: Cool-down for `session`-udførsel. Bjørn 19/10-2026: en rutine må ikke
#: forurene en kørende session. Fem minutter er samme vindue som
#: `wakeup_dispatcher._active_turn_blocks` bruger efter brugerens seneste
#: besked — den symmetriske side af samme regel.
_SESSION_COOL_DOWN_MINUTES = 5

#: Vigtigheder der kræver at brugeren ser posten.
_HANDLING = frozenset({RoutineImportance.HIGH, RoutineImportance.CRITICAL})

#: Kun `critical` må blokere en mutation (inbox_gate). `high` fremhæves, men
#: stopper ikke arbejde: en påmindelse der ikke er akut skal ikke kunne låse
#: en fil-skrivning.
_BLOCKING = frozenset({RoutineImportance.CRITICAL})


def _parse_execution_mode(raw: str | None) -> RoutineExecutionMode:
    token = str(raw or "").strip().lower()
    if not token:
        # Bagudkompatibel standard: den adfærd alle eksisterende rutiner har
        # haft — et isoleret run. Intet skifter for dem.
        return RoutineExecutionMode.BACKGROUND
    try:
        return RoutineExecutionMode(token)
    except ValueError:
        gyldige = ", ".join(m.value for m in RoutineExecutionMode)
        raise ValueError(
            f"ukendt execution_mode {raw!r} — gyldige værdier: {gyldige}"
        ) from None


def _parse_importance(raw: str | None) -> RoutineImportance:
    token = str(raw or "").strip().lower()
    if not token:
        return RoutineImportance.NORMAL
    try:
        return RoutineImportance(token)
    except ValueError:
        gyldige = ", ".join(i.value for i in RoutineImportance)
        raise ValueError(
            f"ukendt importance {raw!r} — gyldige værdier: {gyldige}"
        ) from None


def classify_routine(
    *, execution_mode: str | None = "", importance: str | None = "",
) -> RoutineClassification:
    """Validér valget og udled de felter indbakken og runneren læser.

    Rene funktioner, ingen DB, ingen side-effekter — så reglen kan testes
    uden en rutine og læses ét sted.
    """
    mode = _parse_execution_mode(execution_mode)
    weight = _parse_importance(importance)
    return RoutineClassification(
        execution_mode=mode,
        importance=weight,
        requires_handling=weight in _HANDLING,
        blocks_mutations=weight in _BLOCKING,
        highlights=weight in _HANDLING,
        cool_down_minutes=(
            _SESSION_COOL_DOWN_MINUTES
            if mode in {RoutineExecutionMode.SESSION, RoutineExecutionMode.ADAPTIVE}
            else 0
        ),
    )
