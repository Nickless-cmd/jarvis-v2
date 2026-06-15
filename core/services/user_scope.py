"""Per-bruger data-scope (SECURITY #154, streng GDPR).

`scope_uid()` giver den identitet en DB-læsning/skrivning skal scopes til:
  - en autentificeret brugers kontekst (current_user_id) → den bruger.
  - ingen kontekst (daemon/system/autonomt) → owner som default-identitet, så
    Jarvis' eget autonome arbejde ikke knækker, mens medlemmer forbliver strengt
    isolerede til deres egne rækker.

Nordstjerne: hverken owner eller et medlem kan læse en ANDENS private data.
Eksisterende NULL-rækker (enbruger-æraen) backfilles til owner i migrationen.
"""
from __future__ import annotations


def scope_uid() -> str:
    """Den bruger-id en privat DB-operation skal scopes til. "" hvis intet kan
    resolves (pre-multiuser fallback: kalderen scoper da ikke = uændret adfærd)."""
    try:
        from core.identity.workspace_context import current_user_id
        uid = (current_user_id() or "").strip()
        if uid:
            return uid
    except Exception:
        pass
    # Ingen bruger-kontekst → owner som default (daemon/autonomt Jarvis-arbejde).
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        return (get_owner_discord_id() or "").strip()
    except Exception:
        return ""
