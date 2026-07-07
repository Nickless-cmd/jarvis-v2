"""Mission Control routes — aggregator.

Denne fil var tidligere en god-fil (4605 linjer, 207 ruter). Den er splittet i
feature-moduler (behavior-preserving, ren kode-flytning):

- ``mission_control_imports``      — fuld import-flade fra core.services m.fl.
- ``mission_control_common``       — konstanter, cache-primitiver, _mc_runtime*-
                                     aggregatoren og alle _surface/-tool/-skill/
                                     -hardening/-lab hjælpere.
- ``mission_control_runs_ops``     — runs, overview, events, costs, approvals,
                                     memory-pipeline, autonomy, initiatives, operations.
- ``mission_control_jarvis_state`` — jarvis-introspektion (cognitive-frame, self-*,
                                     dream-*, embodied, ...).
- ``mission_control_agents``       — agenter, lineage, council/swarm.
- ``mission_control_runtime_config``— adaptive/tool-intent, runtime-contract,
                                     heartbeat, visible-execution, capability-approval.
- ``mission_control_introspection``— kognitiv/relationel introspektion.
- ``mission_control_skills_hardening_lab`` — skills, memory, hardening, lab.

Hvert route-modul har sin egen prefix-frie ``APIRouter``. Her samles de under det
originale ``/mc``-prefix + ``mission-control``-tag via ``include_router``, så alle
paths er uændrede.

For at bevare bagudkompatibilitet re-eksporteres HELE den samlede flade (hjælpere,
konstanter OG alle route-funktioner) i dette moduls navnerum. Eksisterende imports
som ``from ...mission_control import mc_memory_pipeline`` og test-patch-mål som
``patch("...mission_control.mc_memory_pipeline")`` virker derfor uændret.
"""
from __future__ import annotations

from fastapi import APIRouter

# Delt flade + hjælpere (re-eksporteres i dette navnerum for bagudkompatibilitet).
from .mission_control_common import *  # noqa: F401,F403

# Route-moduler (importér undermodulerne så deres route-funktioner kan re-eksporteres).
from . import mission_control_runs_ops as _runs_ops
from . import mission_control_jarvis_state as _jarvis_state
from . import mission_control_agents as _agents
from . import mission_control_runtime_config as _runtime_config
from . import mission_control_introspection as _introspection
from . import mission_control_skills_hardening_lab as _skills_hardening_lab

# Route-payload-cachen bor i mission_control_common (delt af alle undermoduler og
# aldrig reloadet). Den lå tidligere i DENNE fil, som isolated_runtime-fixturen
# reloader pr. test — reload ryddede altså cachen mellem tests. For at bevare den
# adfærd (frisk cache pr. reload, ingen state-læk på tværs af tests) rydder vi den
# eksplicit her, så den nulstilles hver gang mission_control (gen)importeres.
try:  # pragma: no cover - defensivt ved partial import
    _MC_ROUTE_CACHE.clear()  # noqa: F405 (fra mission_control_common via *)
except Exception:
    pass

# Aggregér: original prefix/tags, samler alle undermodulers ruter uændret.
router = APIRouter(prefix="/mc", tags=["mission-control"])

_ROUTE_SUBMODULES = (
    _runs_ops,
    _jarvis_state,
    _agents,
    _runtime_config,
    _introspection,
    _skills_hardening_lab,
)

for _submodule in _ROUTE_SUBMODULES:
    router.include_router(_submodule.router)

# Re-eksportér alle route-funktioner i dette navnerum (bagudkompatibilitet +
# test-patch-mål). Kopiér hvert undermoduls route-callables ind i globals().
for _submodule in _ROUTE_SUBMODULES:
    for _name, _obj in vars(_submodule).items():
        if _name.startswith("_"):
            continue
        if callable(_obj) and getattr(_obj, "__module__", "").startswith(
            "apps.api.jarvis_api.routes.mission_control_"
        ):
            globals().setdefault(_name, _obj)

del _submodule, _name, _obj
