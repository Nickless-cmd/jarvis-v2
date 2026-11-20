"""Kortlivet opslag af strukturerede tool-resultater til DIL-binding.

Nøglen er altid ``(run_id, tool_use_id)``. Dermed kan en reference kun læse
et resultat fra samme tur, selv hvis en model genbruger et tool-id senere.
Storen er proceslokal og begrænset; den er ikke en ny vedvarende sandhedskilde.
"""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from threading import Lock

_MAX_RUNS = 128
_laas = Lock()
_resultater: OrderedDict[str, dict[str, object]] = OrderedDict()


def registrer(run_id: str, tool_use_id: str, resultat: object) -> None:
    tur = str(run_id or "").strip()
    kald = str(tool_use_id or "").strip()
    if not tur or not kald:
        return
    with _laas:
        _resultater.setdefault(tur, {})[kald] = deepcopy(resultat)
        _resultater.move_to_end(tur)
        while len(_resultater) > _MAX_RUNS:
            _resultater.popitem(last=False)


def hent(run_id: str, tool_use_id: str) -> object | None:
    tur = str(run_id or "").strip()
    kald = str(tool_use_id or "").strip()
    if not tur or not kald:
        return None
    with _laas:
        resultat = _resultater.get(tur, {}).get(kald)
        return deepcopy(resultat) if resultat is not None else None
