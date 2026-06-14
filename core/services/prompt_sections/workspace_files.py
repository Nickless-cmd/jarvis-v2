"""Workspace file section helpers — udskilt fra prompt_contract.py (Boy Scout).

Tre tightly coupled funktioner til at læse markdown-filer fra workspace/
og bygge prompt-sektioner ud af dem:
  - _workspace_file_section: kerne, læser og normaliserer linjer
  - _workspace_guidance_section: tynd wrapper med samme signatur
  - _workspace_optional_file_section: med fallback-path

Re-eksporteres fra prompt_contract.py så eksisterende imports + monkeypatches
i tests ikke knækker.

2026-06-09: tilføjet `_resolve_with_shared_fallback` — hvis workspace-
versionen er stub-tynd (<500 bytes), prøv ~/.jarvis-v2/shared/<navn>
som fallback. Multi-user spec'en gør shared/ til owner-state og
workspaces/<user>/ til per-user overrides, men hvis owner-workspace
indeholder en bootstrap-stub (typisk fra workspace_bootstrap) skulle
shared-versionen vinde. Uden denne fallback læste vi tynde stubs for
SOUL/IDENTITY/MILESTONES selvom rige versioner lå i shared/.
"""
from __future__ import annotations
import os
from pathlib import Path

# Filer hvor stub-fallback giver mening — identitets-filer som forventes
# at være "rige" (5KB+). Hvis workspace-versionen er <STUB_THRESHOLD bytes
# og shared har en større version, foretrækker vi shared.
_FALLBACK_FILENAMES = frozenset({
    "SOUL.md", "IDENTITY.md", "MILESTONES.md", "USER.md", "MEMORY.md",
})
_STUB_THRESHOLD_BYTES = 500


def _effective_size(path: Path) -> int:
    """Byte-størrelse af workspace-fil, encryption-aware.

    For en krypteret member-fil eksisterer kun `<path>.enc`; her tæller den
    dekrypterede indholds-længde. Plaintext-filer tæller deres st_size som før,
    så adfærden er byte-for-byte identisk mens kryptering er slået fra.
    """
    from core.services.workspace_crypto import member_user_id_for_path, read_text_for_path
    enc = Path(str(path) + ".enc")
    if member_user_id_for_path(path) and enc.exists() and not path.exists():
        try:
            txt = read_text_for_path(path)
            return len(txt.encode("utf-8")) if txt else 0
        except Exception:
            return enc.stat().st_size  # konservativt: behandl som "har indhold"
    return path.stat().st_size if path.exists() else 0


def _resolve_with_shared_fallback(path: Path) -> Path:
    """Hvis `path` peger på en stub-tynd identitets-fil og shared/<navn>
    har en større version, returner shared-versionen i stedet.

    Garanteret aldrig at returnere en sti der ikke eksisterer hvis den
    oprindelige eksisterede — fallback bruges KUN når shared har mere
    indhold end workspace. Encryption-aware via _effective_size.
    """
    filename = path.name
    if filename not in _FALLBACK_FILENAMES:
        return path
    try:
        own = _effective_size(path)
        if own >= _STUB_THRESHOLD_BYTES:
            return path  # workspace har rigt indhold — brug det
        shared_dir = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2" / "shared"
        shared_path = shared_dir / filename
        if shared_path.exists() and shared_path.stat().st_size > own:
            return shared_path
    except Exception:
        pass
    return path


def _workspace_file_section(
    path: Path,
    *,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    from core.services.workspace_crypto import read_text_for_path
    path = _resolve_with_shared_fallback(path)
    text = read_text_for_path(path)
    if text is None:
        return None
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        normalized = " ".join(line.split())
        if len(normalized) > max_chars:
            normalized = normalized[: max_chars - 1].rstrip() + "…"
        lines.append(f"- {normalized}")
        if len(lines) >= max_lines:
            break
    if not lines:
        return None
    return "\n".join([f"{label}:", *lines])


def _workspace_guidance_section(
    path: Path,
    *,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    section = _workspace_file_section(
        path,
        label=label,
        max_lines=max_lines,
        max_chars=max_chars,
    )
    return section


def _ws_exists(path: Path) -> bool:
    """Eksistens-tjek encryption-aware (.enc tæller for member-filer)."""
    if path.exists():
        return True
    from core.services.workspace_crypto import member_user_id_for_path
    return bool(member_user_id_for_path(path)) and Path(str(path) + ".enc").exists()


def _workspace_optional_file_section(
    path: Path,
    *,
    fallback_path: Path | None,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    source = path if _ws_exists(path) else fallback_path
    if source is None or not _ws_exists(source):
        return None
    return _workspace_file_section(
        source,
        label=label,
        max_lines=max_lines,
        max_chars=max_chars,
    )
