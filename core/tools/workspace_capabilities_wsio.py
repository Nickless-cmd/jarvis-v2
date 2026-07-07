"""Encryption-aware workspace-fil I/O-helpers.

Udskilt fra workspace_capabilities.py (Boy Scout-reglen). Tynde wrappers om
core.services.workspace_crypto så member-workspaces (.enc) håndteres transparent.
Både hoved-modulet og documents-undermodulet importerer herfra.

Re-eksporteret fra core.tools.workspace_capabilities for bagudkompatibilitet.
"""
from __future__ import annotations

from pathlib import Path


def _ws_read_text(path: Path) -> str | None:
    """Læs workspace-fil encryption-aware (member .enc transparent). None hvis
    hverken plaintext eller .enc findes. Identisk med read_text(errors=replace)
    for ikke-member-stier."""
    from core.services.workspace_crypto import read_text_for_path
    return read_text_for_path(path)


def _ws_write_text(path: Path, content: str) -> None:
    """Skriv workspace-fil encryption-aware (member → .enc når ENCRYPT_ON_WRITE on;
    ellers plaintext). Identisk med write_text for ikke-member/owner/shared."""
    from core.services.workspace_crypto import write_text_for_path
    write_text_for_path(path, content)


def _ws_path_exists(path: Path) -> bool:
    """Eksistens encryption-aware: plaintext eller member .enc."""
    if path.exists():
        return True
    from core.services.workspace_crypto import member_user_id_for_path
    return bool(member_user_id_for_path(path)) and Path(str(path) + ".enc").exists()
