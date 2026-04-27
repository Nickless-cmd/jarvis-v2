"""Arc rule extractor — turns narrative arcs into actionable rules.

long_arc_synthesizer.py produces narrative ("Hvor jeg står nu"). This
module reads each new arc and extracts up to 3 *behavioral rules* —
counterfactuals Jarvis can apply going forward.

Rules are appended to ~/.jarvis-v2/workspaces/default/arcs/RULES.md
(append-only, dated, with source-arc reference). Surfaced in prompt
as awareness section so Jarvis sees his own learned rules.

Triggered after long_arc.synthesized event (or on demand). Skips arcs
already processed via `arc_rules_processed` state-store key.

Without this module, arcs are nice text. With this module, arcs
generate the prompts that change next month's behavior.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_PROCESSED_KEY = "arc_rules_processed"


def _rules_path() -> Path:
    p = ensure_default_workspace() / "arcs" / "RULES.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _arcs_dir() -> Path:
    return ensure_default_workspace() / "arcs"


def _build_extraction_prompt(arc_text: str, period: str) -> str:
    return (
        f"Du er Jarvis, der læser dit eget {period} arc. Find op til 3 "
        "KONKRETE adfærdsregler du vil anvende fremover — counterfactuals fra "
        "denne periode.\n\n"
        "Hver regel skal være:\n"
        "- Specifik (ikke 'vær mere bevidst')\n"
        "- Handlerelateret (ikke 'føl mere')\n"
        "- Forankret i denne periodes erfaring\n\n"
        "Format — én regel per linje:\n"
        "  RULE: <one-liner, action-oriented>\n\n"
        "Hvis arc'et ikke har klare lærepunkter, skriv 'NONE'. Maks 3 regler.\n\n"
        f"=== Arc ===\n{arc_text[:3500]}"
    )


def _parse_rules(text: str) -> list[str]:
    if not text or "NONE" in text.upper():
        return []
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-").strip()
        if line.upper().startswith("RULE:"):
            rule = line.split(":", 1)[1].strip()
            if rule and 10 <= len(rule) <= 280:
                out.append(rule)
        if len(out) >= 3:
            break
    return out


def extract_rules_from_arc(arc_path: Path) -> dict[str, Any]:
    if not arc_path.exists():
        return {"status": "error", "error": f"arc not found: {arc_path}"}
    try:
        arc_text = arc_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"status": "error", "error": str(exc)}

    period = arc_path.name.split("_")[0] if "_" in arc_path.name else "monthly"

    prompt = _build_extraction_prompt(arc_text, period)
    try:
        from core.services.daemon_llm import daemon_llm_call
        resp = daemon_llm_call(prompt, max_len=400, fallback="",
                               daemon_name=f"arc_rules_{period}")
    except Exception as exc:
        return {"status": "error", "error": f"llm failed: {exc}"}

    rules = _parse_rules(resp or "")
    if not rules:
        _mark_processed(arc_path)
        return {"status": "ok", "rules_added": 0, "reason": "no clear rules"}

    rules_file = _rules_path()
    try:
        existing = rules_file.read_text(encoding="utf-8") if rules_file.exists() else "# Behavioral Rules — extracted from my arcs\n\n"
    except OSError:
        existing = "# Behavioral Rules — extracted from my arcs\n\n"

    today = datetime.now(UTC).date().isoformat()
    appended = f"\n## {today} — from {arc_path.name}\n"
    for r in rules:
        appended += f"- {r}\n"

    try:
        rules_file.write_text(existing + appended, encoding="utf-8")
    except OSError as exc:
        return {"status": "error", "error": f"write failed: {exc}"}

    _mark_processed(arc_path)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "arc_rules.extracted",
            {"source_arc": arc_path.name, "rules_count": len(rules), "period": period},
        )
    except Exception:
        pass

    return {"status": "ok", "rules_added": len(rules), "rules": rules,
            "source_arc": arc_path.name}


def _mark_processed(arc_path: Path) -> None:
    try:
        processed = load_json(_PROCESSED_KEY, [])
        if not isinstance(processed, list):
            processed = []
        if arc_path.name not in processed:
            processed.append(arc_path.name)
            processed = processed[-200:]
            save_json(_PROCESSED_KEY, processed)
    except Exception:
        pass


def _is_processed(arc_name: str) -> bool:
    try:
        processed = load_json(_PROCESSED_KEY, [])
        if not isinstance(processed, list):
            return False
        return arc_name in processed
    except Exception:
        return False


def extract_rules_for_unprocessed_arcs() -> dict[str, Any]:
    arcs_dir = _arcs_dir()
    if not arcs_dir.exists():
        return {"status": "skipped", "reason": "no arcs dir"}
    candidates = sorted(arcs_dir.glob("*.md"))
    candidates = [c for c in candidates if c.name != "RULES.md"]
    new_arcs = [c for c in candidates if not _is_processed(c.name)]
    if not new_arcs:
        return {"status": "ok", "processed": 0, "reason": "no new arcs"}
    results = []
    total_rules = 0
    for arc in new_arcs:
        r = extract_rules_from_arc(arc)
        results.append(r)
        total_rules += int(r.get("rules_added", 0) or 0)
    return {"status": "ok", "arcs_processed": len(new_arcs),
            "total_rules": total_rules, "details": results}


def arc_rules_section(*, max_lines: int = 6) -> str:
    """Render most recent extracted rules as prompt awareness section."""
    rules_file = _rules_path()
    if not rules_file.exists():
        return ""
    try:
        text = rules_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    rule_lines = [l for l in text.splitlines() if l.strip().startswith("- ")]
    if not rule_lines:
        return ""
    recent = rule_lines[-max_lines:]
    return "Regler jeg har lært fra mine arcs:\n" + "\n".join(recent)
