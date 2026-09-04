"""MEMORY.md line/section selection for the visible prompt.

Extracted from prompt_contract.py (Boy Scout, 2026-09-04, memory repair R2/R4).
Callers and tests patch these names on ``core.services.prompt_contract`` — the
re-imports there keep that working.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.identity.workspace_bootstrap import (
    TEMPLATE_DIR,
    read_daily_memory_lines,
    read_recent_daily_memory_lines,
)
from core.services.prompt_relevance_backend import (
    BoundedMemorySelectionAttempt,
    run_bounded_nl_memory_entry_selection,
)
from core.services.prompt_sections.memory_scoring import (
    _heuristic_relevant_memory_entries,
    _merge_ordered_memory_entries,
)

import re

# 2026-09-04 (efter merge): mindst 3 tegn, ikke 4 — ellers taeller "GPU", "PVE",
# "PSU", "API", "SSH", "LXC", "VPN", "DNS", "iOS" ikke som emneord, og
# "hvilken GPU har jeg" mistede sin MEMORY.md-sektion. Korte fyldord er i stedet
# paa stoplisten.
_TOKEN_RE = re.compile(r"[A-Za-zÆØÅæøå0-9_]{3,}")
_GENERIC_MEMORY_WORDS = frozenset({
    "skal", "ikke", "eller", "hvis", "this", "that", "with", "from", "user",
    "memory", "jarvis", "bjørn",
    # korte fyldord (3 tegn) — dansk + engelsk
    "har", "jeg", "dig", "mig", "den", "det", "der", "til", "for", "med", "kan",
    "vil", "var", "sig", "min", "dit", "din", "sin", "sit", "men", "som", "nok",
    "the", "and", "you", "are", "was", "our", "its", "can", "did", "how", "why",
    "hvad", "hvor", "hvem", "hvordan", "hvorfor", "hvilken", "hvilket", "hvilke",
    "bruges", "bruger", "brugt",
})


@dataclass(slots=True)
class MemorySectionSelection:
    lines: list[str]
    backend_attempted: bool
    backend_success: bool
    fallback_used: bool
    backend_name: str | None
    backend_provider: str | None
    backend_model: str | None
    backend_status: str
    prompt_file_used: bool


def _track_memory_selection(selection: MemorySectionSelection, mode: str, candidate_count: int) -> None:
    """Telemetry lives in prompt_contract (module-level history); lazy import avoids a cycle."""
    try:
        from core.services import prompt_contract as _pc
        _pc._track_memory_selection(selection, mode, candidate_count)
    except Exception:
        pass


def _workspace_memory_section(
    path: Path,
    *,
    label: str,
    user_message: str,
    max_lines: int,
    max_chars: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> MemorySectionSelection | None:
    entries = _workspace_memory_entries(path)
    if not entries:
        return None
    # 2026-09-04 (memory repair, R2): vælg SEKTIONER via det eksisterende
    # memory_search-indeks (overskrift + brødtekst, embedding/tf-idf) før den
    # gamle linje-heuristik, som kun kender ~10 nøgleord og ellers tager filens
    # sidste linjer.
    if path.name == "MEMORY.md":
        try:
            from core.services.prompt_sections.memory_md_selection import (
                select_memory_md_sections,
            )
            section_lines = select_memory_md_sections(
                user_message,
                workspace_dir=workspace_dir,
                max_sections=max(1, int(max_lines)),
                max_chars=max(200, int(max_chars)),
            )
        except Exception:
            section_lines = []
        if section_lines:
            section_lines = _filter_answer_changing_memory(user_message, section_lines)
        if section_lines:
            selection = MemorySectionSelection(
                lines=section_lines,
                backend_attempted=True,
                backend_success=True,
                fallback_used=False,
                backend_name="section-embedding",
                backend_provider=None,
                backend_model=None,
                backend_status="ok",
                prompt_file_used=False,
            )
            _track_memory_selection(selection, mode, len(entries))
            return selection
    selection = _select_relevant_memory_entries(
        entries,
        user_message=user_message,
        max_lines=max_lines,
        max_chars=max_chars,
        workspace_dir=workspace_dir,
        mode=mode,
    )
    if not selection.lines:
        return None
    _track_memory_selection(selection, mode, len(entries))
    return selection


def _today_daily_memory_lines(*, limit: int = 10) -> list[str]:
    """Read today's daily memory lines for injection into visible prompts.

    Wraps read_daily_memory_lines with exception safety so prompt
    builders never fail because the daily file is missing, empty, or
    briefly unreadable.
    """
    try:
        return read_daily_memory_lines(limit=limit)
    except Exception:
        return []


def _recent_daily_memory_lines(*, limit: int = 12, days: int = 7) -> list[str]:
    try:
        return read_recent_daily_memory_lines(days=days, limit=limit)
    except Exception:
        return _today_daily_memory_lines(limit=limit)




def _workspace_memory_entries(path: Path) -> list[str]:
    from core.services.workspace_crypto import read_text_for_path
    text = read_text_for_path(path)
    if text is None:
        return []
    entries: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        normalized = " ".join(line.lstrip("-").split()).strip()
        if not normalized:
            continue
        entries.append(normalized)
    return entries


def _select_relevant_memory_entries(
    entries: list[str],
    *,
    user_message: str,
    max_lines: int,
    max_chars: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> MemorySectionSelection:
    # Skip the LLM re-ranking on the visible hot path (2026-07-22, 4-agent latency audit;
    # mirrors the existing relevance_skip_nl_on_visible precedent). _bounded_nl_memory_selection
    # is a ~1s deepseek call (up to the 4s _HOT_RESOLVE_CAP) that BLOCKS the assembly, while the
    # heuristic scorer (~3µs, already the fallback below at "else") picks sensible lines.
    # AWARENESS-NEUTRAL: memory is still injected; only the LLM's re-ranking of the last 8
    # MEMORY.md lines is dropped. Flag-gated (memory_selection_skip_nl_on_visible, default True)
    # → instant rollback if memory-selection quality regresses.
    _skip_nl = False
    if mode == "visible_chat":
        # Live kill-switch (runtime-state, default True) — flip to False instantly if
        # memory-selection quality regresses, no redeploy. Bjørn cares about memory quality
        # (it's why selection was a MODEL not embeddings) → keep it reversible.
        try:
            from core.runtime.db_core import get_runtime_state_value as _grs_msel
            _flag = _grs_msel("memory_selection_skip_nl_on_visible", True)
            _skip_nl = True if _flag is None else bool(_flag)
        except Exception:
            _skip_nl = True
    if _skip_nl:
        backend_attempt = BoundedMemorySelectionAttempt(
            attempted=False, success=False, backend="skipped-visible-hotpath",
            provider=None, model=None, status="skipped-visible-hotpath", result=None,
        )
    else:
        backend_attempt = _bounded_nl_memory_selection(
            user_message=user_message,
            entries=entries,
            max_lines=max_lines,
            workspace_dir=workspace_dir,
            mode=mode,
        )
    ordered: list[str]
    from core.services.workspace_crypto import read_text_for_path
    prompt_file_used = bool(
        read_text_for_path(workspace_dir / "VISIBLE_MEMORY_SELECTION.md") is not None
        or (TEMPLATE_DIR / "VISIBLE_MEMORY_SELECTION.md").exists()
    )

    if backend_attempt.success and backend_attempt.result is not None:
        bounded_entries = entries[-8:]
        selected_indexes = backend_attempt.result.selected_indexes
        backend_ordered = [
            bounded_entries[index]
            for index in selected_indexes
            if 0 <= index < len(bounded_entries)
        ]
        heuristic_ordered = _heuristic_relevant_memory_entries(
            entries,
            user_message=user_message,
            max_lines=max_lines,
        )
        ordered = _merge_ordered_memory_entries(
            heuristic_ordered,
            backend_ordered,
            max_lines=max_lines,
        )
    else:
        ordered = _heuristic_relevant_memory_entries(
            entries,
            user_message=user_message,
            max_lines=max_lines,
        )
    ordered = _filter_answer_changing_memory(user_message, ordered)

    clipped: list[str] = []
    for entry in ordered:
        text = entry
        if len(text) > max_chars:
            text = text[: max_chars - 1].rstrip() + "…"
        clipped.append(text)
    return MemorySectionSelection(
        lines=clipped,
        backend_attempted=backend_attempt.attempted,
        backend_success=backend_attempt.success,
        fallback_used=not backend_attempt.success,
        backend_name=backend_attempt.backend,
        backend_provider=backend_attempt.provider,
        backend_model=backend_attempt.model,
        backend_status=backend_attempt.status,
        prompt_file_used=prompt_file_used,
    )


def memory_could_change_answer(user_message: str, memory_text: str) -> bool:
    """Cheap gate: inject memory only when it can affect this answer's substance."""
    msg_terms = {
        t.lower() for t in _TOKEN_RE.findall(str(user_message or ""))
        if t.lower() not in _GENERIC_MEMORY_WORDS
    }
    mem_terms = {
        t.lower() for t in _TOKEN_RE.findall(str(memory_text or ""))
        if t.lower() not in _GENERIC_MEMORY_WORDS
    }
    if not msg_terms or not mem_terms:
        return False
    if msg_terms & mem_terms:
        return True
    return bool(
        any(ch.isdigit() for ch in str(user_message or ""))
        and any(ch.isdigit() for ch in str(memory_text or ""))
    )


def _filter_answer_changing_memory(user_message: str, lines: list[str]) -> list[str]:
    return [line for line in lines if memory_could_change_answer(user_message, line)]


def _bounded_nl_memory_selection(
    *,
    user_message: str,
    entries: list[str],
    max_lines: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> BoundedMemorySelectionAttempt:
    return run_bounded_nl_memory_entry_selection(
        user_message=user_message,
        entries=entries,
        max_lines=max_lines,
        workspace_dir=workspace_dir,
        mode=mode,
    )


# _memory_line_relevance_score, _contains_any, _heuristic_relevant_memory_entries,
# _merge_ordered_memory_entries er udskilt til prompt_sections/memory_scoring.py (Boy Scout) —
# re-importeret nedenfor for bagudkompatibilitet.
