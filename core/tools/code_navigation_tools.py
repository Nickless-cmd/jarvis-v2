"""Symbol find / find usages — regex-based v1.

Tree-sitter would give precise AST-aware results but pulls a heavy dep
tree and per-language parsers. For v1 we use ripgrep with
language-aware patterns derived from the file extension. Less precise
than AST (we'd miss `foo()` invoked via `getattr(obj, 'foo')()`) but
fast, dependency-free, and good enough for the 80% case Jarvis hits
when refactoring.

Returned hits include {file, line, kind, snippet} so the model can
quickly orient. Capped at MAX_HITS to keep responses bounded.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from core.identity.project_context import current_project_root

MAX_HITS = 200

# Language → regex for definition lines. Each pattern uses a
# placeholder %S% replaced with the symbol (rg's -e supports per-call
# substitution, simpler to do it ourselves).
_DEFINITION_PATTERNS: dict[str, list[str]] = {
    "py": [
        r"^\s*(?:async\s+)?def\s+%S%\s*\(",
        r"^\s*class\s+%S%\b",
        r"^\s*%S%\s*=\s*",
    ],
    "js": [
        r"\bfunction\s+%S%\s*\(",
        r"\b(?:const|let|var)\s+%S%\s*=",
        r"\bclass\s+%S%\b",
        r"^export\s+(?:default\s+)?(?:async\s+)?function\s+%S%\b",
    ],
    "jsx": [],  # falls back to js
    "ts": [
        r"\bfunction\s+%S%\s*\(",
        r"\b(?:const|let|var)\s+%S%\s*[:=]",
        r"\bclass\s+%S%\b",
        r"\binterface\s+%S%\b",
        r"\btype\s+%S%\s*=",
        r"\benum\s+%S%\b",
    ],
    "tsx": [],  # falls back to ts
    "go": [
        r"\bfunc\s+%S%\s*\(",
        r"\bfunc\s+\(\w+\s+\*?\w+\)\s+%S%\s*\(",  # method
        r"\btype\s+%S%\s+(?:struct|interface)",
    ],
    "rs": [
        r"\bfn\s+%S%\s*[<(]",
        r"\bstruct\s+%S%\b",
        r"\benum\s+%S%\b",
        r"\btrait\s+%S%\b",
    ],
    "java": [
        r"\b(?:public|private|protected|static|\s)*\s+\w+\s+%S%\s*\(",
        r"\bclass\s+%S%\b",
        r"\binterface\s+%S%\b",
    ],
}

# Cross-language fallback if ext is unknown — generic identifier
_GENERIC_DEFINITION = [r"\b%S%\b"]


def _ext_patterns(extensions: list[str] | None) -> tuple[list[str], list[str]]:
    """Return (patterns, ripgrep --type-add args, ripgrep -t args).

    Actually returns (patterns, type-args) — we don't try to be clever
    about per-extension typing; just provide all extension patterns and
    let the regex match guide.
    """
    keys = extensions or list(_DEFINITION_PATTERNS.keys())
    seen: set[str] = set()
    patterns: list[str] = []
    for k in keys:
        # tsx/jsx fall back to ts/js
        fallback = {"tsx": "ts", "jsx": "js"}.get(k, k)
        for p in _DEFINITION_PATTERNS.get(fallback, []):
            if p not in seen:
                seen.add(p)
                patterns.append(p)
    if not patterns:
        patterns = list(_GENERIC_DEFINITION)
    return patterns, keys


def _scope_dir() -> Path | None:
    root = current_project_root().strip()
    if not root:
        return None
    p = Path(root).expanduser().resolve()
    return p if p.is_dir() else None


def _ripgrep_available() -> bool:
    return shutil.which("rg") is not None


def _run_rg(patterns: list[str], symbol: str, scope: Path, extra_args: list[str]) -> list[dict[str, Any]]:
    if not _ripgrep_available():
        return []
    sym_escaped = re.escape(symbol)
    hits: list[dict[str, Any]] = []
    for raw in patterns:
        pat = raw.replace("%S%", sym_escaped)
        try:
            res = subprocess.run(
                [
                    "rg", "--no-heading", "-n", "--color=never",
                    "-g", "!.git", "-g", "!node_modules", "-g", "!__pycache__",
                    "-g", "!dist", "-g", "!build", "-g", "!.venv",
                    "-m", "30",  # cap per pattern
                    *extra_args,
                    pat,
                    str(scope),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            continue
        for line in res.stdout.splitlines():
            # Format: path:line:content
            m = re.match(r"^([^:]+):(\d+):(.*)$", line)
            if not m:
                continue
            hits.append({
                "file": m.group(1),
                "line": int(m.group(2)),
                "snippet": m.group(3).strip()[:200],
                "matched_pattern": pat,
            })
            if len(hits) >= MAX_HITS:
                return hits
    return hits


def _exec_find_symbol(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    scope = _scope_dir()
    if scope is None:
        return {
            "status": "error",
            "error": "no project anchored — set X-JarvisX-Project (anchor in JarvisX) before find_symbol",
        }
    raw_exts = args.get("extensions")
    extensions = None
    if isinstance(raw_exts, list):
        extensions = [str(x).strip().lstrip(".") for x in raw_exts if x]
    patterns, _ = _ext_patterns(extensions)
    if not _ripgrep_available():
        return {
            "status": "error",
            "error": "ripgrep not available on host — please install `rg`",
        }
    hits = _run_rg(patterns, name, scope, extra_args=[])
    # Dedupe by (file,line)
    seen: set[tuple[str, int]] = set()
    deduped: list[dict[str, Any]] = []
    for h in hits:
        key = (h["file"], h["line"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(h)
    # Heuristic: classify the kind by looking at the snippet
    for h in deduped:
        h["kind"] = _classify(h["snippet"])
    return {
        "status": "ok",
        "name": name,
        "scope": str(scope),
        "count": len(deduped),
        "hits": deduped,
        "truncated": len(hits) >= MAX_HITS,
    }


def _exec_find_usages(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    scope = _scope_dir()
    if scope is None:
        return {
            "status": "error",
            "error": "no project anchored — set X-JarvisX-Project before find_usages",
        }
    if not _ripgrep_available():
        return {"status": "error", "error": "ripgrep not available"}
    sym_escaped = re.escape(name)
    # Word-boundary match — skip declarations with a follow-up filter
    pattern = rf"\b{sym_escaped}\b"
    try:
        res = subprocess.run(
            [
                "rg", "--no-heading", "-n", "--color=never",
                "-g", "!.git", "-g", "!node_modules", "-g", "!__pycache__",
                "-g", "!dist", "-g", "!build", "-g", "!.venv",
                "-m", "20",
                pattern,
                str(scope),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "ripgrep timed out"}
    hits: list[dict[str, Any]] = []
    for line in res.stdout.splitlines():
        m = re.match(r"^([^:]+):(\d+):(.*)$", line)
        if not m:
            continue
        snippet = m.group(3).strip()
        kind = _classify(snippet)
        # find_usages excludes the declaration site
        if kind in ("def", "class", "type", "interface"):
            kind = "definition"
        hits.append({
            "file": m.group(1),
            "line": int(m.group(2)),
            "snippet": snippet[:200],
            "kind": kind,
        })
        if len(hits) >= MAX_HITS:
            break
    return {
        "status": "ok",
        "name": name,
        "scope": str(scope),
        "count": len(hits),
        "hits": hits,
        "truncated": len(hits) >= MAX_HITS,
    }


def _classify(snippet: str) -> str:
    s = snippet.lstrip()
    if re.match(r"(?:async\s+)?def\s+\w+\s*\(", s):
        return "def"
    if re.match(r"class\s+\w+", s):
        return "class"
    if re.match(r"function\s+\w+\s*\(", s):
        return "def"
    if re.match(r"(?:const|let|var)\s+\w+", s):
        return "var"
    if re.match(r"interface\s+\w+", s):
        return "interface"
    if re.match(r"type\s+\w+\s*=", s):
        return "type"
    if re.match(r"enum\s+\w+", s):
        return "enum"
    if re.match(r"struct\s+\w+", s):
        return "struct"
    if re.match(r"trait\s+\w+", s):
        return "trait"
    if re.match(r"fn\s+\w+", s):
        return "def"
    if re.match(r"func\s+", s):
        return "def"
    return "use"


CODE_NAVIGATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "find_symbol",
            "description": (
                "Find where a symbol (function, class, variable, type) is "
                "DEFINED inside the currently anchored project. Returns hits "
                "with file, line, kind (def/class/var/interface/type/etc), "
                "and source snippet. Uses regex patterns matched per language "
                "from file extension. Faster and more reliable than blind "
                "search for code-navigation use cases."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Symbol name"},
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Limit to file extensions (e.g. ['py','ts']). Default: all known.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_usages",
            "description": (
                "Find all uses of a symbol inside the anchored project — "
                "callers, references, imports. Returns hits with kind="
                "'definition' for the declaration sites and kind='use' "
                "everywhere else, so you can quickly see callers separately "
                "from the def. Cap 200 hits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Symbol name"},
                },
                "required": ["name"],
            },
        },
    },
]


CODE_NAVIGATION_TOOL_HANDLERS: dict[str, Any] = {
    "find_symbol": _exec_find_symbol,
    "find_usages": _exec_find_usages,
}
