"""Workspace file section helpers — udskilt fra prompt_contract.py (Boy Scout).

Tre tightly coupled funktioner til at læse markdown-filer fra workspace/
og bygge prompt-sektioner ud af dem:
  - _workspace_file_section: kerne, læser og normaliserer linjer
  - _workspace_guidance_section: tynd wrapper med samme signatur
  - _workspace_optional_file_section: med fallback-path

Re-eksporteres fra prompt_contract.py så eksisterende imports + monkeypatches
i tests ikke knækker.
"""
from __future__ import annotations
from pathlib import Path


def _workspace_file_section(
    path: Path,
    *,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    if not path.exists():
        return None
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
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


def _workspace_optional_file_section(
    path: Path,
    *,
    fallback_path: Path | None,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    source = path if path.exists() else fallback_path
    if source is None or not source.exists():
        return None
    return _workspace_file_section(
        source,
        label=label,
        max_lines=max_lines,
        max_chars=max_chars,
    )
