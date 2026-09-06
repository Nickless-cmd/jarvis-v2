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
        # 2026-09-05: var haardkodet til $HOME/.jarvis-v2/shared og ignorerede
        # dermed JARVIS_HOME, som alt andet i workspace_paths respekterer. Det
        # gjorde laese- og skrivevejen uenige saa snart JARVIS_HOME var sat.
        from core.runtime.workspace_paths import shared_dir as _shared_dir
        shared_dir = _shared_dir()
        shared_path = shared_dir / filename
        if shared_path.exists() and shared_path.stat().st_size > own:
            return shared_path
    except Exception:
        pass
    return path


_CORE_HEADINGS = frozenset({"kerne", "core", "kerne (altid i prompten)"})
# Den ene sektion i SOUL.md/IDENTITY.md som Jarvis selv må skrive i (blok D).
DEVELOPMENT_HEADINGS = frozenset({"udvikling", "development"})


def _development_section_text(text: str) -> str:
    """Body of a `## Udvikling` section, or "" when absent."""
    out: list[str] = []
    inside = False
    level = 0
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip().lower()
            if inside and hashes <= level:
                break
            if title in DEVELOPMENT_HEADINGS:
                inside, level = True, hashes
                continue
        if inside:
            out.append(raw)
    return "\n".join(out).strip()


def _core_section_text(text: str) -> str:
    """Body of a `## Kerne` (or `## Core`) section, or "" when absent."""
    out: list[str] = []
    inside = False
    level = 0
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip().lower()
            if inside and hashes <= level:
                break
            if title in _CORE_HEADINGS:
                inside, level = True, hashes
                continue
        if inside:
            out.append(raw)
    return "\n".join(out).strip()


def _workspace_file_section(
    path: Path,
    *,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    # Prompt-siden (6/9-2026): hemmeligheder maskeres paa vej ind i konteksten.
    # En noegle indsat i USER.md eller MEMORY.md ville ellers ligge i HVER
    # prompt og gaa til en ekstern udbyder hver eneste tur.
    # Stoerrelses-tjekket ovenfor bruger fortsat read_text_for_path: masken
    # ville aendre laengden, og det tal skal beskrive filen som den ER.
    from core.services.secret_redaction import read_for_prompt
    path = _resolve_with_shared_fallback(path)
    text = read_for_prompt(path)
    if text is None:
        return None
    # 2026-09-04 (memory repair, R7): USER.md var 23 KB uden protokol for hvad
    # der er kerne og hvad der er historik — prompten fik de første ~3 KB. Hvis
    # filen har en "## Kerne"-sektion, er DET indholdet der læses ind.
    full_text = text
    core_text = _core_section_text(text)
    if core_text:
        text = core_text
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
    # 2026-09-04 (lærings-sløjfe, blok D): «## Udvikling» i SOUL.md/IDENTITY.md
    # er den ENE sektion han selv må skrive i. Den ligger nederst i filen og
    # ville derfor altid falde uden for line-loftet. Reservér plads til den, så
    # hans egen udvikling ikke er det første der skæres væk.
    dev_text = _development_section_text(full_text)
    if dev_text:
        dev_lines = [
            f"- {' '.join(raw.split())}"
            for raw in dev_text.splitlines()
            if raw.strip() and not raw.strip().startswith("#")
        ][:3]
        dev_lines = [ln if len(ln) <= max_chars else ln[: max_chars - 1].rstrip() + "…"
                     for ln in dev_lines]
        fresh = [ln for ln in dev_lines if ln not in lines]
        if fresh:
            keep = max(0, max_lines - len(fresh))
            lines = lines[:keep] + fresh
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
