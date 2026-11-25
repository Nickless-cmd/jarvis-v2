"""Encrypt durable previews for visible member runs."""
from __future__ import annotations

from core.services import chat_crypto


def member_for_run(run) -> str | None:
    member = chat_crypto.medlem_for_raekke(user_id=str(getattr(run, "user_id", "") or ""))
    if member:
        return member
    member = chat_crypto.medlem_for_session(str(getattr(run, "session_id", "") or ""))
    if not member:
        from core.identity.workspace_context import current_role
        if current_role() in {"member", "partner", "guest"}:
            raise RuntimeError("authenticated member key could not be resolved")
    return member


def protect_preview(text: str | None, member: str | None) -> str | None:
    return chat_crypto.krypter(text, member) if text and member else text


#: Staar i stedet for chiffertekst naar et preview ikke kan bevises laesbart.
#: Siger EKSPLICIT at svaret ikke kan bevises — en dommer eller prompt maa
#: ikke tro at base64 er svaret, og heller ikke at svaret var tomt.
PLADSHOLDER_KRYPTERET = "[krypteret svar — indholdet kan ikke bevises her]"


def laesbaar_preview(
    text_preview: str | None,
    session_id: str | None = None,
    user_id: str | None = None,
) -> str | None:
    """Preview som en dommer/prompt/LLM trygt kan laese. ALDRIG chiffertekst.

    Klartekst (og tom) returneres uaendret. `enc:`-tekst dekrypteres med
    medlemmet udledt af `user_id` (foerst) eller `session_id`; kan noeglen ikke
    bevises, eller dekrypteringen fejler, returneres `PLADSHOLDER_KRYPTERET`.
    """
    if not text_preview or not chat_crypto.er_krypteret(text_preview):
        return text_preview
    member = None
    if user_id:
        member = chat_crypto.medlem_for_raekke(user_id=str(user_id))
    if not member and session_id:
        member = chat_crypto.medlem_for_session(str(session_id))
    if member:
        klar = chat_crypto.dekrypter(text_preview, member)
        if not chat_crypto.er_krypteret(klar):
            return klar
    return PLADSHOLDER_KRYPTERET


def reveal_preview(text: str | None, user_id: str | None) -> str | None:
    """Som `laesbaar_preview` med kun `user_id` — aldrig chiffertekst ud."""
    return laesbaar_preview(text, user_id=user_id)


def er_laesbar(text_preview: str | None) -> bool:
    """Er dette preview et SVAR en dommer/prompt maa citere?

    Nej for tom tekst, for `PLADSHOLDER_KRYPTERET` og for raa chiffertekst.
    Reglen bor her og ikke hos den enkelte forbruger: otte steder laeste
    previewet som om det var svaret, og hver af dem skulle have opdaget det
    samme. Chiffertekst er ikke et svar, og «kan ikke bevises» er ikke et svar.
    """
    tekst = str(text_preview or "").strip()
    if not tekst:
        return False
    if tekst == PLADSHOLDER_KRYPTERET:
        return False
    return not chat_crypto.er_krypteret(tekst)
