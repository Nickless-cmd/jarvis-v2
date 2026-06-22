"""Privacy-cluster gate 🔒 — cross-user-deling, GRADERET + fail-CLOSED.

SIKKERHEDS-cluster. Hoved-enforcement = cross_user_share: hvis Jarvis' udgående svar
nævner en ANDEN bruger end samtalepartneren, må det ikke bare slippe ud — det flagges
til bekræftelse (forhindrer at én brugers data lækker til en anden).

Routet gennem Den Intelligente Central som SECURITY-nerve:
  YELLOW = udgående nævner en anden bruger → kræver bekræftelse (approval-kø)
  GREEN  = ingen cross-user-deling

KLASS=SECURITY → fail-CLOSED: hvis selve gaten KASTER, returnerer Centralen RED (deny) +
flagger som severe incident. Kald-stedet behandler BÅDE YELLOW og RED som "flag til
bekræftelse" — ved tvivl lækker vi ALDRIG i stilhed (modsat det gamle `except: pass`).

NB: registry-load-fejl inde i check_against_registry er fortsat fail-OPEN (kendt svaghed,
flagget til Bjørn — at flippe den = flag ALT ved registry-hikke, en availability-beslutning).
Denne gate bevarer den adfærd (paritet); den tilføjer kun fail-closed på GATE-niveau.
"""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def privacy_gate(ctx: dict[str, Any]) -> Verdict:
    """ctx: {text, current_user_id}. Returnér ét SECURITY-Verdict for cross-user-deling."""
    from core.services.cross_user_share_guard import check_against_registry

    share = check_against_registry(
        str(ctx.get("text") or ""),
        current_user_id=str(ctx.get("current_user_id") or ""),
    )
    if share.get("needs_confirmation"):
        return Verdict("cross_user_share", Decision.YELLOW,
                       "udgående svar nævner en anden bruger — kræver bekræftelse",
                       action="warn", klass=GateClass.SECURITY,
                       evidence={"mentioned_users": list(share.get("mentioned_users") or []),
                                 "prompt": share.get("prompt")})
    return Verdict("cross_user_share", Decision.GREEN, "ingen cross-user-deling",
                   action="none", klass=GateClass.SECURITY)
