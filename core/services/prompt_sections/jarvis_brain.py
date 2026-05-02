"""Always-on Jarvis Brain summary injection for prompt_contract.

Reads state/jarvis_brain_summary.md (written by jarvis_brain_daemon's
summary_loop) and renders it as a prompt section. Silent skip if file
missing or empty (recall must never block prompt-byggeri).

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md sektion 5.1.
"""
from __future__ import annotations


def _approx_tokens(text: str) -> int:
    """Crude estimate: ~4 chars per token. Good enough for budget trim."""
    return max(1, len(text) // 4)


def build_jarvis_brain_section(*, token_budget: int = 350) -> str:
    """Returnerer summary som markdown-sektion, eller "" hvis intet at vise."""
    from core.services import jarvis_brain

    p = jarvis_brain._state_root() / "jarvis_brain_summary.md"
    if not p.exists():
        return ""
    try:
        raw = p.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
    if not raw:
        return ""

    # Trim på sektions-grænser hvis over budget. Sektioner identificeres ved
    # **bold:** linjer (matcher summary-daemonens output-format).
    if _approx_tokens(raw) > token_budget:
        parts: list[str] = []
        current = ""
        for line in raw.split("\n"):
            if line.startswith("**") and current:
                parts.append(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            parts.append(current)
        # Drop sektioner bagud indtil under budget
        while parts and _approx_tokens("\n".join(parts)) > token_budget:
            parts.pop()
        if parts:
            raw = "\n".join(parts)
        else:
            # Nothing fits — hard cut on chars
            raw = raw[: token_budget * 4]

    return f"## Hvad jeg ved nu (min egen hjerne)\n\n{raw}\n"
