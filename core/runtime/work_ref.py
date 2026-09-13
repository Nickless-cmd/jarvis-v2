"""Én præfikset reference til et stykke arbejde — og ét sted at opløse den.

## Hvorfor ikke ét fælles id

Målt 13/9-2026: **elleve** lagre repræsenterer «et stykke arbejde», og næsten
ingen er koblet. Det nærliggende svar er at give dem alle det samme `work_id`.
Det ville være forkert, og målingen viser hvorfor.

`runtime_tasks` har allerede en `run_id`-kolonne. Den fyldes med
`heartbeat-tick:036bd93e-…` — et **tidspunkt**, ikke en kørsel. Og ingen af de
andre opgave-skabere (`runtime_action_executor`, `system_cartographer`,
`agency_cartographer`) sender en kørsel med; de sætter `origin` som en
tekst-etiket. Der findes altså ikke en kørsel at pege på for det meste arbejde.

Så et fælles id ville kræve at opfinde en relation hvor der ikke er nogen. En
opfundet relation er værre end ingen, fordi den ser ud som viden.

## To felter, to spørgsmål

- **rod** — *hvilket* stykke arbejde er det her? For en opgave er det opgaven
  selv; for en samtale-tur er det kørslen.
- **ophav** — *hvorfor* findes det? Et tick, en kørsel, en kartograf.

De to smelter kun sammen når arbejdet er født af noget der selv er arbejde.

## Formen

`art:id` — fx `run:visible-abc`, `task:a1b2c3`, `tick:036bd93e`.

Præfikset er ikke pynt. To id-rum der ligner hinanden kan forveksles uden det,
og en reference man ikke kan opløse er en streng, ikke en nøgle. Huset havde
allerede taget konventionen i netop `runtime_tasks.run_id`
(`heartbeat-tick:…`) — den blev bare aldrig brugt som opslag.

En ukendt art **afvises**. Et gæt ville pege på det forkerte lager.
"""
from __future__ import annotations

from typing import Final

#: Art → hvilket lager referencen peger ind i. Listen er bevidst kort: en art
#: der ikke kan opløses tilbage til en række er ikke en reference.
ARTER: Final[dict[str, str]] = {
    "run": "visible_runs.run_id",
    "task": "runtime_tasks.task_id",
    "flow": "runtime_flows.flow_id",
    "dispatch": "claude_dispatch_audit.task_id",
    # Arten hedder `heartbeat-tick` fordi det er hvad producenten FAKTISK
    # udsender — `payload["tick_id"]` er allerede `heartbeat-tick:036bd93e-…`,
    # og 984 raekker baerer den form.
    #
    # Foerste udgave af dette modul kaldte arten `tick` og praefiksede oveni.
    # Resultatet var at `lav()` afviste vaerdien (id med skilletegn) og feltet
    # blev TOMT — en regression en eksisterende test fangede. Dataen havde
    # konventionen foerst; opgaven var at foelge den, ikke at opfinde en ny.
    "heartbeat-tick": "hjerteslagets tick (intet lager — et tidspunkt)",
}

_SKILLETEGN: Final[str] = ":"


class UgyldigReference(ValueError):
    """Referencen kan ikke opløses. Rejses hellere end at gætte en art."""


def lav(art: str, id_: str) -> str:
    """Byg en reference. Afviser ukendte arter og tomme id'er.

    En reference til «ingenting» er værre end intet felt: den ser ud som en
    forbindelse og fører ingen steder hen.
    """
    a = str(art or "").strip().lower()
    i = str(id_ or "").strip()
    if a not in ARTER:
        raise UgyldigReference(
            f"ukendt art {a!r} — kendte: {', '.join(sorted(ARTER))}")
    if not i:
        raise UgyldigReference(f"tomt id for art {a!r}")
    if _SKILLETEGN in i:
        # Id'et maa ikke selv baere et skilletegn — saa kan opløsningen ikke
        # afgoere hvor arten slutter. `heartbeat-tick:uuid` er praecis den form
        # der ville braekke det, og den findes allerede i data.
        raise UgyldigReference(
            f"id maa ikke indeholde {_SKILLETEGN!r}: {i!r}")
    return f"{a}{_SKILLETEGN}{i}"


def opløs(reference: str) -> tuple[str, str]:
    """`art:id` → `(art, id)`. Afviser alt den ikke kan opløse.

    Returnerer ALDRIG et gæt. En reference uden præfiks kunne være et run-id
    eller et task-id, og de to peger i hvert sit lager.
    """
    r = str(reference or "").strip()
    if not r:
        raise UgyldigReference("tom reference")
    art, sep, id_ = r.partition(_SKILLETEGN)
    if not sep:
        raise UgyldigReference(
            f"reference uden art: {r!r} — forventede «art{_SKILLETEGN}id»")
    a = art.strip().lower()
    if a not in ARTER:
        raise UgyldigReference(f"ukendt art {a!r} i {r!r}")
    if not id_.strip():
        raise UgyldigReference(f"tomt id i {r!r}")
    return a, id_.strip()


def er_gyldig(reference: str) -> bool:
    """Kan referencen opløses? Til steder der skal filtrere, ikke fejle."""
    try:
        opløs(reference)
        return True
    except UgyldigReference:
        return False


def lager_for(reference: str) -> str:
    """Hvilket lager peger referencen ind i? Til fejlbeskeder og flader."""
    art, _ = opløs(reference)
    return ARTER[art]


def fra_run(run_id: str) -> str:
    """Genvej for den hyppigste rod: en synlig eller autonom kørsel."""
    return lav("run", run_id)


def fra_task(task_id: str) -> str:
    return lav("task", task_id)
