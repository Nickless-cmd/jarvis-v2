"""Auth-cluster gate 🔒 — tool-access (rolle-håndhævelse), SECURITY fail-CLOSED.

SIKKERHEDS-cluster. Hoved-enforcement = tool-access: må DENNE rolle køre DETTE værktøj?
Den serverside-backstop i execute_tool (hvis model-tool-filteret omgås via prompt-
injection/bug) routes nu gennem Den Intelligente Central som SECURITY-nerve.

Grader:
  RED   = ikke tilladt for rollen → DENY (tool_not_permitted)
  GREEN = tilladt (eller owner/unbound — betroede interne/daemon-kald)

KRITISKE invarianter:
- **Owner/daemon ("" eller "owner") låses ALDRIG ude** → altid GREEN (gaten kaldes kun
  for ægte member/guest-roller; kald-stedet sender ikke owner gennem RED-stien).
- **klass=SECURITY → fail-CLOSED**: hvis is_tool_allowed KASTER, returnerer Centralen RED
  (deny) — en member hvis permission-check fejler bliver NÆGTET, ikke tilladt (modsat det
  gamle except:pass der tillod stille). Sikkerheds-nerve: kan ikke slås fra, kun isoleres.
"""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def auth_gate(ctx: dict[str, Any]) -> Verdict:
    """ctx: {role, scope, name}. Returnér ét SECURITY-Verdict for tool-access."""
    role = str(ctx.get("role") or "")
    # Owner/unbound (betroede interne/daemon-kald) → aldrig nægtet.
    if role in ("", "owner"):
        return Verdict("tool_access", Decision.GREEN, "owner/unbound — tilladt",
                       action="none", klass=GateClass.SECURITY)
    scope = str(ctx.get("scope") or "")
    name = str(ctx.get("name") or "")
    from core.tools.tool_scoping import is_tool_allowed
    if not is_tool_allowed(role=role, scope=scope, name=name):
        return Verdict("tool_access", Decision.RED,
                       f"værktøj '{name}' ikke tilladt for rollen '{role}'",
                       action="block", klass=GateClass.SECURITY,
                       evidence={"role": role, "tool": name})
    return Verdict("tool_access", Decision.GREEN, "tilladt", action="none",
                   klass=GateClass.SECURITY)
