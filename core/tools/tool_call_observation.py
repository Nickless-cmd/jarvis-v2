"""Alt hvad der KUN observerer et vaerktoejskald — efter det er kaldt.

Udskilt fra ``simple_tools.py`` (2.141 linjer) efter Boy Scout-reglen, foer
K2 laegger et skema-tjek ind i ``execute_tool``.

De tre ting her har ét faelles traek: de aendrer aldrig udfaldet. Central-
nerven, den persistente forbrugstaeller og permission-klassificerens skygge
maa alle fejle uden at kaldet maerker det. Derfor er de nemme at laese samlet
og svaere at laese spredt ud i en dispatch-funktion.
"""
from __future__ import annotations

from typing import Any


def observe_tool_call(name: str, arguments: dict[str, Any],
                      result: dict[str, Any]) -> None:
    """Observér et faerdigt vaerktoejskald. Kaster aldrig."""
    try:
        from core.services.central_core import central as _central_tools
        try:
            from core.identity.workspace_context import effective_role as _er
            from core.tools.tool_scoping import current_tool_scope as _cs
            _role_obs = _er() or ""
            _scope_obs = _cs() or ""
        except Exception:
            _role_obs, _scope_obs = "", ""
        _status = str(result.get("status") or "ok") if isinstance(result, dict) else "ok"
        _central_tools().observe({
            "cluster": "tools", "nerve": "tool_call", "tool": name,
            "kind": "operator" if str(name).startswith("operator_") else "native",
            "role": _role_obs, "scope": _scope_obs,
            "session_id": str(arguments.get("_runtime_session_id")
                              or arguments.get("_session_id") or ""),
            "status": _status,
            "error": (str(result.get("error") or "")[:160]
                      if isinstance(result, dict) and _status != "ok" else ""),
        })
    except Exception:
        pass
    # Tools-cluster Phase 2: persistent forbrugs-tæller (DB, cross-proces api↔runtime) →
    # Centralen kan ordne kataloget (mest-brugt først, døde sidst) + flagge døde tools.
    try:
        from core.services.tool_usage_store import record_use
        _ok = isinstance(result, dict) and str(result.get("status") or "ok") == "ok"
        record_use(name, kind="operator" if str(name).startswith("operator_") else "native",
                   ok=_ok)
    except Exception:
        pass
    # ── Permission-classifier shadow observe (harness Part E) ──────────────
    # Non-blocking: predict owner-approval for mutating tools + record the outcome
    # (bootstrap: ok→approve, blocked→deny; approval_needed→stash for gold at resolve).
    # Fail-open, never changes the returned status. Default mode shadow.
    try:
        from core.services import permission_classifier as _pc
        if (isinstance(result, dict) and _pc.permission_classifier_mode() != "off"
                and _pc.is_mutating(name)):
            _pc_status = str(result.get("status") or "")
            _pc_approval_id = str(result.get("approval_id") or "")
            _pc_args = dict(arguments)

            def _pc_shadow() -> None:
                try:
                    pred = _pc.classify_action(name, _pc_args, {"status": _pc_status})
                    if _pc_status == "approval_needed" and _pc_approval_id:
                        _pc.stash_prediction(_pc_approval_id, name, pred.verdict)
                    else:
                        _actual = ("approve" if _pc_status == "ok"
                                   else ("deny" if _pc_status in ("blocked", "gate_blocked") else ""))
                        if _actual:
                            _pc.record_prediction_outcome(name, predicted=pred.verdict,
                                                          actual=_actual, is_owner_gold=False)
                except Exception:
                    pass
            import threading as _pc_th
            _pc_th.Thread(target=_pc_shadow, daemon=True).start()
    except Exception:
        pass
