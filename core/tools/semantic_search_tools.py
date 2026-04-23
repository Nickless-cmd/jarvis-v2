"""Semantic code search — natural language queries over the Jarvis codebase."""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import Any

_REPO_ROOT = Path("/media/projects/jarvis-v2")
_SEARCH_DIRS = ["core", "apps/api", "scripts"]
_MAX_CANDIDATES = 200
_CONTEXT_LINES = 25


def _extract_definitions(repo_root: Path, dirs: list[str]) -> list[dict]:
    """Extract function/class definitions with file:line and docstring snippet."""
    definitions = []
    for d in dirs:
        for py_file in (repo_root / d).rglob("*.py"):
            rel_path = str(py_file.relative_to(repo_root))
            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                name = node.name
                lineno = node.lineno
                docstring = ast.get_docstring(node) or ""
                # Build a rich candidate string for scoring
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                candidate = f"{kind} {name}: {docstring[:120]}" if docstring else f"{kind} {name}"
                definitions.append({
                    "name": name,
                    "kind": kind,
                    "file": rel_path,
                    "line": lineno,
                    "candidate": candidate,
                    "docstring": docstring[:200],
                })
    return definitions


def _keyword_prefilter(definitions: list[dict], query: str, limit: int = _MAX_CANDIDATES) -> list[dict]:
    """Quick keyword pre-filter to reduce candidates before expensive scoring."""
    query_words = set(query.lower().split())
    scored = []
    for d in definitions:
        text = (d["name"] + " " + d["docstring"]).lower()
        hits = sum(1 for w in query_words if w in text)
        scored.append((hits, d))
    # Sort: keyword hits first, then all remaining
    scored.sort(key=lambda x: x[0], reverse=True)
    # Take top `limit`: those with any keyword hit first, then fill with rest
    with_hits = [d for hits, d in scored if hits > 0]
    without_hits = [d for hits, d in scored if hits == 0]
    return (with_hits + without_hits)[:limit]


def _score_with_llm(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """Use LLM to rank candidates by semantic relevance to query."""
    # Build a compact list for the LLM to rank
    candidate_lines = "\n".join(
        f"{i+1}. [{d['file']}:{d['line']}] {d['candidate']}"
        for i, d in enumerate(candidates[:50])  # LLM can handle ~50
    )
    prompt = (
        f"Jeg søger i Jarvis' kodebase efter: \"{query}\"\n\n"
        f"Her er kandidater (fil:linje, navn/docstring):\n{candidate_lines}\n\n"
        f"Svar KUN med en kommasepareret liste af de {min(top_k, 10)} mest relevante numre, "
        f"f.eks.: 3,7,12,1,5\nSvar:"
    )
    try:
        from core.context.compact_llm import call_compact_llm
        response = call_compact_llm(prompt, max_tokens=60).strip()
        # Parse comma-separated numbers
        indices = []
        for part in response.replace(";", ",").split(","):
            try:
                n = int(part.strip()) - 1  # convert to 0-indexed
                if 0 <= n < len(candidates):
                    indices.append(n)
            except ValueError:
                pass
        return [candidates[i] for i in indices[:top_k]]
    except Exception:
        return candidates[:top_k]


def _read_context(file: str, line: int, context: int = _CONTEXT_LINES) -> str:
    try:
        path = _REPO_ROOT / file
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        start = max(0, line - 1)
        end = min(len(lines), start + context)
        return "\n".join(lines[start:end])
    except Exception:
        return ""


def _exec_semantic_search_code(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    top_k = min(int(args.get("top_k") or 5), 10)
    dirs = args.get("dirs") or _SEARCH_DIRS

    if not query:
        return {"status": "error", "error": "query is required"}

    # 1. Extract all definitions
    try:
        definitions = _extract_definitions(_REPO_ROOT, dirs)
    except Exception as e:
        return {"status": "error", "error": f"Failed to index codebase: {e}"}

    if not definitions:
        return {"status": "error", "error": "No Python definitions found in search dirs."}

    # 2. Keyword pre-filter
    candidates = _keyword_prefilter(definitions, query)

    # 3. LLM semantic ranking
    top = _score_with_llm(query, candidates, top_k)

    # 4. Build results with code context
    results = []
    for d in top:
        code = _read_context(d["file"], d["line"])
        results.append({
            "file": d["file"],
            "line": d["line"],
            "name": d["name"],
            "kind": d["kind"],
            "docstring": d["docstring"],
            "code_preview": code,
            "location": f"{d['file']}:{d['line']}",
        })

    return {
        "status": "ok",
        "query": query,
        "results": results,
        "count": len(results),
        "indexed": len(definitions),
        "text": "\n\n".join(
            f"**{r['location']}** — {r['kind']} `{r['name']}`\n"
            + (f"_{r['docstring']}_\n" if r["docstring"] else "")
            + f"```python\n{r['code_preview'][:400]}\n```"
            for r in results
        ),
    }


SEMANTIC_SEARCH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "semantic_search_code",
            "description": (
                "Search the Jarvis codebase using natural language. "
                "Returns function/class definitions relevant to the query, with file:line location and code preview. "
                "Better than search/grep for questions like 'where is the heartbeat scheduler?' or 'how does cost tracking work?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of what you're looking for.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 10).",
                    },
                    "dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Directories to search (default: ['core', 'apps/api', 'scripts']).",
                    },
                },
                "required": ["query"],
            },
        },
    },
]
