"""Per-provider circuit-breaker adaptere for OllamaFreeAPI og Arko.

Udskilt fra ``cheap_provider_runtime_adapters`` 2026-09-01 efter Boy Scout-reglen
(filen var 2.046 linjer). Funktionerne hører sammen: de er tynde adaptere der
oversætter to providere med hver sin historiske breaker-adfærd til den delte
``provider_circuit_breaker``-store, keyed på ``provider_id``.

Spec §11.2: de tidligere ofa/arko-specifikke breakers blev løftet til den delte
store. Adapterne bevarer hver providers oprindelige tærskler via ``pp_configure``
— ofa: 3 fejl i træk → åben 5 min; arko: 3 fejl i træk → åben 3 min.

Alle symboler re-eksporteres fra ``cheap_provider_runtime_adapters``, så
eksisterende imports ikke brækker.
"""

from __future__ import annotations

# ── OllamaFreeAPI ───────────────────────────────────────────────────────────
_OFA_CB_THRESHOLD = 3            # open after 3 consecutive fails (bevaret)
_OFA_CB_OPEN_DURATION_S = 300.0  # stay open 5 minutes (bevaret)
_OFA_PROVIDER_ID = "ollamafreeapi"


def _ofa_circuit_open() -> bool:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_configure(_OFA_PROVIDER_ID, threshold=_OFA_CB_THRESHOLD,
                     cooldown_s=_OFA_CB_OPEN_DURATION_S)
    return _cb.pp_is_open(_OFA_PROVIDER_ID)


def _ofa_circuit_record_failure() -> None:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_configure(_OFA_PROVIDER_ID, threshold=_OFA_CB_THRESHOLD,
                     cooldown_s=_OFA_CB_OPEN_DURATION_S)
    _cb.pp_record_failure(_OFA_PROVIDER_ID)


def _ofa_circuit_record_success() -> None:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_record_success(_OFA_PROVIDER_ID)


# ── Arko ────────────────────────────────────────────────────────────────────
_ARKO_CB_THRESHOLD = 3          # consecutive failures before opening (bevaret)
_ARKO_CB_OPEN_DURATION_S = 180  # stay open for 3 minutes (bevaret)
_ARKO_PROVIDER_ID = "arko"


def _arko_circuit_open() -> bool:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_configure(_ARKO_PROVIDER_ID, threshold=_ARKO_CB_THRESHOLD,
                     cooldown_s=float(_ARKO_CB_OPEN_DURATION_S))
    return _cb.pp_is_open(_ARKO_PROVIDER_ID)


def _arko_circuit_record_failure() -> None:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_configure(_ARKO_PROVIDER_ID, threshold=_ARKO_CB_THRESHOLD,
                     cooldown_s=float(_ARKO_CB_OPEN_DURATION_S))
    _cb.pp_record_failure(_ARKO_PROVIDER_ID)


def _arko_circuit_record_success() -> None:
    from core.services import provider_circuit_breaker as _cb
    _cb.pp_record_success(_ARKO_PROVIDER_ID)
