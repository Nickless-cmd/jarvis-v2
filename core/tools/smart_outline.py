"""smart_outline — structural file summary, much cheaper than read_file.

When the model wants to understand "what's in this large file", reading
the whole thing burns tokens unnecessarily. The outline gives:
- classes (with their methods)
- top-level functions (with signatures)
- top-level constants / module-level dataclass blocks

Python uses the stdlib ``ast`` module — no extra dependency. Other
languages (.ts/.js/.go) get a regex fallback that catches the most
common declaration patterns so the model still gets *something*
useful instead of "unsupported".

Designed to complement read_file: outline first, then read_file with
``offset/limit`` on the specific section you actually need.
"""
from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REGEX_LANG_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    ".ts": [
        ("class", re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)", re.M)),
        ("interface", re.compile(r"^\s*(?:export\s+)?interface\s+(\w+)", re.M)),
        ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.M)),
        ("type", re.compile(r"^\s*(?:export\s+)?type\s+(\w+)", re.M)),
    ],
    ".tsx": [
        ("component", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)", re.M)),
        ("class", re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.M)),
    ],
    ".js": [
        ("class", re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.M)),
        ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.M)),
    ],
    ".go": [
        ("func", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(\w+)", re.M)),
        ("type", re.compile(r"^\s*type\s+(\w+)\s+(struct|interface)", re.M)),
    ],
    ".rs": [
        ("fn", re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)", re.M)),
        ("struct", re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)", re.M)),
        ("impl", re.compile(r"^\s*impl(?:<[^>]+>)?\s+(\w+)", re.M)),
    ],
}


def _python_outline(source: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [{"kind": "syntax_error", "name": str(exc), "line": exc.lineno or 0}]
    items: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [
                {
                    "name": m.name,
                    "line": m.lineno,
                    "end_line": getattr(m, "end_lineno", m.lineno),
                }
                for m in node.body
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            items.append({
                "kind": "class",
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "methods": methods,
                "method_count": len(methods),
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            try:
                signature = ast.unparse(
                    ast.FunctionDef(
                        name=node.name,
                        args=node.args,
                        body=[],
                        decorator_list=[],
                        returns=node.returns,
                    )
                ).split("\n", 1)[0].rstrip(":")
            except Exception:
                signature = f"def {node.name}(...)"
            items.append({
                "kind": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "signature": signature[:200],
            })
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    items.append({
                        "kind": "module_const",
                        "name": target.id,
                        "line": node.lineno,
                    })
    return items


def _regex_outline(source: str, suffix: str) -> list[dict[str, Any]]:
    patterns = _REGEX_LANG_PATTERNS.get(suffix, [])
    if not patterns:
        return []
    items: list[dict[str, Any]] = []
    for kind, pat in patterns:
        for m in pat.finditer(source):
            line = source[:m.start()].count("\n") + 1
            items.append({
                "kind": kind,
                "name": m.group(1),
                "line": line,
            })
    items.sort(key=lambda x: x["line"])
    return items


def _exec_smart_outline(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    if not path:
        return {"status": "error", "error": "path is required"}
    p = Path(path).expanduser()
    if not p.exists():
        return {"status": "error", "error": f"file not found: {path}"}
    if not p.is_file():
        return {"status": "error", "error": "path is not a regular file"}
    if p.stat().st_size > 2 * 1024 * 1024:
        return {"status": "error", "error": "file too large for outline (>2 MB)"}
    try:
        source = p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"status": "error", "error": f"read failed: {exc}"}

    suffix = p.suffix.lower()
    if suffix == ".py":
        outline = _python_outline(source)
        language = "python"
    elif suffix in _REGEX_LANG_PATTERNS:
        outline = _regex_outline(source, suffix)
        language = suffix.lstrip(".")
    else:
        return {
            "status": "ok",
            "path": str(p),
            "language": "unsupported",
            "outline": [],
            "note": f"no outline available for {suffix or '(no extension)'}; use read_file",
        }

    return {
        "status": "ok",
        "path": str(p),
        "language": language,
        "total_lines": source.count("\n") + 1,
        "outline": outline,
        "item_count": len(outline),
    }


SMART_OUTLINE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "smart_outline",
            "description": (
                "Get a structural outline of a file (classes, functions, "
                "constants, line numbers) without reading the whole file. "
                "Much cheaper than read_file for large files. Python uses "
                "ast (full signatures); .ts/.tsx/.js/.go/.rs use regex. "
                "Use this first, then read_file with offset/limit on the "
                "specific section you need."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path."},
                },
                "required": ["path"],
            },
        },
    },
]
