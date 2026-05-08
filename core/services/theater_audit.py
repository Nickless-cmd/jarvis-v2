"""Theater Audit -- find narrative-first inner-life patterns.

The audit does not decide whether Jarvis should speak poetically. It flags
places where prompts may create inner-state prose before runtime evidence,
appraisal, and causal consequences exist.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAX_FINDINGS = 80

_SCAN_ROOTS = (
    "core/services",
    "workspace/default",
)

_PATTERNS: tuple[dict[str, Any], ...] = (
    {
        "id": "second_person_state_command",
        "label": "Second-person state command",
        "regex": re.compile(
            r"\bdu\s+(føler|mærker|tænker)\b|"
            r"\bdu\s+er\s+Jarvis\b|"
            r"\bdu\s+er\b.{0,60}\b(presset|træt|glad|bange|frustreret|rolig|nysgerrig|levende|alene|her)\b",
            re.IGNORECASE,
        ),
        "risk": "high",
        "score": 35,
        "summary": "Prompt language tells Jarvis what he is or feels instead of deriving it.",
    },
    {
        "id": "first_person_state_claim",
        "label": "First-person state claim",
        "regex": re.compile(r"\b(jeg\s+(føler|mærker|tænker)|det\s+føles)\b", re.IGNORECASE),
        "risk": "medium",
        "score": 22,
        "summary": "First-person prose can become self-looping memory if persisted as truth.",
    },
    {
        "id": "sentence_generation_command",
        "label": "Sentence generation command",
        "regex": re.compile(
            r"skriv\s+(én|en|1|2-4|præcis|kort).*sætning|skriv\s+som",
            re.IGNORECASE,
        ),
        "risk": "high",
        "score": 32,
        "summary": "The system asks for a feeling-like sentence rather than a structured appraisal.",
    },
    {
        "id": "living_persona_prompt",
        "label": "Living persona prompt",
        "regex": re.compile(r"person\s+der\s+lever\s+et\s+liv|tal\s+som\s+dig\s+selv", re.IGNORECASE),
        "risk": "high",
        "score": 38,
        "summary": "Persona instructions risk simulating life instead of exposing causal state.",
    },
    {
        "id": "identity_preamble_pressure",
        "label": "Identity preamble pressure",
        "regex": re.compile(r"build_identity_preamble|identity_preamble", re.IGNORECASE),
        "risk": "medium",
        "score": 18,
        "summary": "Identity context may prime daemon prose if not bounded by evidence contracts.",
    },
    {
        "id": "private_inner_voice_prompt",
        "label": "Private inner voice prompt",
        "regex": re.compile(
            r"\bindre\s+stemme\b|\binner\s+voice\b|privat[e]?\s+sætning|private\s+thought",
            re.IGNORECASE,
        ),
        "risk": "medium",
        "score": 24,
        "summary": "Private voice should render state, not create durable self-belief by itself.",
    },
)


def build_theater_audit_surface() -> dict[str, Any]:
    findings = _scan_findings()
    files = _rank_files(findings)
    recommended = _recommended_task(files)
    counts = _counts(findings)
    return {
        "fetchedAt": datetime.now(UTC).isoformat(),
        "mode": "theater-audit-v1",
        "summary": {
            "findings": len(findings),
            "high_risk": counts["high"],
            "medium_risk": counts["medium"],
            "low_risk": counts["low"],
            "files": len(files),
            "top_risk_score": files[0]["risk_score"] if files else 0,
        },
        "findings": findings[:_MAX_FINDINGS],
        "files": files[:25],
        "recommendedTheaterTask": recommended,
        "criteria": [
            "Inner state should be derived from runtime signals, not commanded as prose.",
            "First-person rendering should be labeled as rendering, not stored as source truth.",
            "State claims should expose evidence, confidence, expiry, and allowed effects.",
            "A claimed inner layer should have causal consequences or be marked narrative-only.",
        ],
    }


def _scan_findings() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in _scan_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(path.relative_to(_REPO_ROOT))
        is_python = path.suffix.lower() == ".py"
        in_docstring = False  # Tracks multi-line docstring state for .py files
        for line_no, line in enumerate(text.splitlines(), start=1):
            if is_python:
                in_docstring, skip = _python_line_state(line, in_docstring)
                if skip:
                    continue
                # Strip trailing inline comments before pattern-matching so
                # comment-text inside descriptive comments doesn't trigger
                # (e.g. `_X = 5  # min minutes between inner voice runs`).
                # Only strip when there's a `  #` or `\t#` separator so we
                # don't break URL-fragments or strings containing `#`.
                scan_line = _strip_trailing_inline_comment(line)
            else:
                scan_line = line
            for pattern in _PATTERNS:
                if pattern["regex"].search(scan_line):
                    findings.append({
                        "id": f"{rel}:{line_no}:{pattern['id']}",
                        "path": rel,
                        "line": line_no,
                        "kind": pattern["id"],
                        "label": pattern["label"],
                        "risk": pattern["risk"],
                        "risk_score": int(pattern["score"]),
                        "summary": pattern["summary"],
                        "excerpt": _excerpt(line),
                    })
    findings.sort(
        key=lambda item: (
            -int(item["risk_score"]),
            str(item["path"]),
            int(item["line"]),
            str(item["kind"]),
        )
    )
    return findings


def _scan_files() -> list[Path]:
    files: list[Path] = []
    for root_name in _SCAN_ROOTS:
        root = _REPO_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".py", ".md", ".txt"}:
                continue
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    files.sort()
    return files


def _python_line_state(line: str, in_docstring: bool) -> tuple[bool, bool]:
    """Track multi-line docstring state and decide whether to skip this line.

    Returns (new_in_docstring_state, skip_this_line).

    Replaces the older single-line-only _skip_python_line which couldn't
    skip docstring CONTENT (only the opening line). That meant module
    docstrings, function docstrings, and any prose embedded in triple-
    quoted strings would still get scanned and produce false positives
    for self-referential daemons (e.g. inner_voice_daemon mentioning
    "inner voice" in its own docstring).
    """
    stripped = line.strip()

    if in_docstring:
        # Closing triple-quote ends the docstring section; skip the line itself.
        if '"""' in line or "'''" in line:
            return False, True
        return True, True

    # Detect docstring open. A line that starts with """ AND has another """
    # later means it's a one-line docstring → skip but stay closed.
    if stripped.startswith(('"""', "'''")):
        opener = '"""' if stripped.startswith('"""') else "'''"
        rest = stripped[3:]
        if opener in rest:
            return False, True  # one-liner docstring
        return True, True  # multi-line docstring opens

    if not stripped:
        return False, True
    if stripped.startswith("#"):
        return False, True
    if stripped.startswith(("def ", "class ", "import ", "from ")):
        return False, True
    # Inline comment after code: drop the comment portion before scanning.
    # If after stripping the inline comment there's nothing significant
    # left (just a constant assignment etc.), skip the line.
    # Conservative: only skip if the line is ONLY a comment-bearing
    # constant/variable assignment with `# ...` trailing.
    if "  #" in line or "\t#" in line:
        # Don't fully skip — let the scanner check the code part. The
        # comment text itself can still trigger, but inline comments are
        # rare false-positive sources compared to docstrings.
        pass
    return False, False


def _skip_python_line(line: str) -> bool:
    """Backwards-compatible wrapper. Use _python_line_state for new code."""
    _, skip = _python_line_state(line, False)
    return skip


def _strip_trailing_inline_comment(line: str) -> str:
    """Drop trailing `  # ...` or `\\t# ...` comment so its prose isn't scanned.

    Conservative: only triggers when the `#` is preceded by whitespace
    (so URL fragments and `#` inside string literals stay intact). Won't
    handle every edge case but covers the common ``CONST = 5  # comment``
    pattern that produces false positives in self-referential modules.
    """
    for sep in ("  #", "\t#"):
        idx = line.find(sep)
        if idx >= 0:
            return line[:idx]
    return line


def _rank_files(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for item in findings:
        path = str(item["path"])
        bucket = by_path.setdefault(
            path,
            {
                "path": path,
                "risk_score": 0,
                "findings": 0,
                "high_risk": 0,
                "medium_risk": 0,
                "top_kinds": {},
            },
        )
        bucket["risk_score"] += int(item["risk_score"])
        bucket["findings"] += 1
        if item["risk"] == "high":
            bucket["high_risk"] += 1
        elif item["risk"] == "medium":
            bucket["medium_risk"] += 1
        kinds = bucket["top_kinds"]
        kinds[item["kind"]] = int(kinds.get(item["kind"], 0)) + 1

    ranked = []
    for bucket in by_path.values():
        kinds = bucket.pop("top_kinds")
        bucket["top_kinds"] = [
            {"kind": kind, "count": count}
            for kind, count in sorted(kinds.items(), key=lambda pair: (-pair[1], pair[0]))[:4]
        ]
        bucket["priority"] = _priority_label(int(bucket["risk_score"]))
        ranked.append(bucket)
    ranked.sort(key=lambda item: (-int(item["risk_score"]), str(item["path"])))
    return ranked


def _recommended_task(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not files:
        return None
    top = files[0]
    path = str(top["path"])
    return {
        "id": f"theater-refactor-{Path(path).stem}",
        "title": f"Convert {Path(path).name} from prompt-theater to appraisal state",
        "goal": (
            "Replace narrative-first inner-state prompts with structured state records "
            "containing evidence, confidence, expiry, and allowed runtime effects. "
            "Keep first-person language only as optional rendering."
        ),
        "scope": path,
        "task_kind": "theater_refactor",
        "priority": str(top["priority"]),
        "priority_score": int(top["risk_score"]),
        "reason": (
            f"{top['findings']} theater-risk finding(s), "
            f"{top['high_risk']} high-risk, {top['medium_risk']} medium-risk."
        ),
        "source": "theater-audit",
    }


def _counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for item in findings:
        risk = str(item.get("risk") or "low")
        counts[risk if risk in counts else "low"] += 1
    return counts


def _priority_label(score: int) -> str:
    if score >= 160:
        return "high"
    if score >= 70:
        return "medium"
    return "low"


def _excerpt(line: str) -> str:
    clean = " ".join(str(line).strip().split())
    if len(clean) <= 180:
        return clean
    return f"{clean[:177]}..."
