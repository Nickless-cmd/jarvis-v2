"""Memory probe: does recall find what Bjørn knows is there? (memory repair 2026-09-04, Task 7)

Runs a fixed set of questions (tests/fixtures/memory_probes.json) through
``recall()`` (one fused path) and the prompt-side MEMORY.md section selector,
and reports hit@3 per probe and per source. Read-only: no writes, no service
restart. Run on CT105 with the owner context:

    PYTHONPATH=/media/projects/jarvis-v2 python scripts/memory_probe.py [--json] [--limit 3]

A probe hits when any ``expect`` substring appears (case-insensitive) in any of
the top-N result texts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "memory_probes.json"


def load_probes(path: Path = FIXTURE) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("probes") or [])


def score_probe(texts: list[str], expect: list[str]) -> bool:
    blob = "\n".join(str(t or "").lower() for t in texts)
    return any(str(e).lower() in blob for e in expect if str(e).strip())


def run_probes(
    probes: list[dict[str, Any]],
    *,
    sources: dict[str, Callable[[str, int], list[str]]],
    limit: int = 3,
) -> dict[str, Any]:
    """``sources`` maps a name to a callable(query, limit) -> list[str] of result texts."""
    rows: list[dict[str, Any]] = []
    totals: dict[str, int] = {name: 0 for name in sources}
    for probe in probes:
        query = str(probe.get("query") or "")
        expect = list(probe.get("expect") or [])
        row: dict[str, Any] = {"id": probe.get("id"), "query": query, "hits": {}}
        for name, fn in sources.items():
            try:
                texts = list(fn(query, limit) or [])
            except Exception as exc:  # a broken source must not abort the probe run
                row["hits"][name] = False
                row.setdefault("errors", {})[name] = str(exc)[:120]
                continue
            hit = score_probe(texts, expect)
            row["hits"][name] = hit
            totals[name] += int(hit)
        rows.append(row)
    n = max(1, len(probes))
    return {
        "probes": len(probes),
        "limit": limit,
        "rows": rows,
        "hit_at_n": {name: {"hits": c, "rate": round(c / n, 3)} for name, c in totals.items()},
    }


def _owner_context() -> None:
    from core.identity.users import get_owner
    from core.identity.workspace_context import set_context

    owner = get_owner()
    uid = str(getattr(owner, "discord_id", "") or "").strip() if owner else ""
    if uid:
        set_context(workspace_name="default", role="owner", user_id=uid)


def _live_sources() -> dict[str, Callable[[str, int], list[str]]]:
    def _recall(query: str, limit: int) -> list[str]:
        from core.services.recall import recall
        return [str(r.get("text") or "") for r in recall(query, limit=limit).get("results") or []]

    def _memory_md(query: str, limit: int) -> list[str]:
        from core.services.prompt_sections.memory_md_selection import select_memory_md_sections
        return select_memory_md_sections(query, workspace_dir=_ws(), max_sections=limit, max_chars=4000)

    def _brain(query: str, limit: int) -> list[str]:
        from core.services import jarvis_brain
        out = []
        for _score, eid in jarvis_brain.search_brain_scored(query_text=query, limit=limit, min_cosine=0.5):
            e = jarvis_brain.read_entry(eid)
            out.append(f"{e.title}: {e.content}")
        return out

    return {"recall": _recall, "memory_md": _memory_md, "brain": _brain}


def _ws() -> Path:
    try:
        from core.runtime.workspace_paths import workspace_dir_or_owner
        return workspace_dir_or_owner()
    except ImportError:  # main-tree (pre-repair) has no owner fallback; context is set
        from core.runtime.workspace_paths import workspace_dir
        return workspace_dir()


def _legacy_sources() -> dict[str, Callable[[str, int], list[str]]]:
    """Main-compatible sources (pre-repair code paths) so before/after can be compared."""

    def _workspace(query: str, limit: int) -> list[str]:
        from core.services.memory_search import search_memory
        return [f"§ {r.get('section', '')}: {r.get('text', '')}" for r in search_memory(query, limit=limit) or []]

    def _memory_md_lines(query: str, limit: int) -> list[str]:
        from core.services import prompt_contract as pc
        ws = _ws()
        entries = pc._workspace_memory_entries(ws / "MEMORY.md")
        sel = pc._select_relevant_memory_entries(
            entries, user_message=query, max_lines=limit, max_chars=280, workspace_dir=ws,
        )
        return list(sel.lines)

    def _brain_uncapped(query: str, limit: int) -> list[str]:
        from core.services import jarvis_brain
        out = []
        for e in jarvis_brain.search_brain(query_text=query, limit=limit):
            out.append(f"{e.title}: {e.content}")
        return out

    return {"workspace": _workspace, "memory_md_lines": _memory_md_lines, "brain_uncapped": _brain_uncapped}


def format_report(result: dict[str, Any]) -> str:
    names = list(result["hit_at_n"].keys())
    lines = [f"Memory probe — {result['probes']} probes, hit@{result['limit']}", ""]
    header = f"{'probe':<22}" + "".join(f"{n:>14}" for n in names)
    lines.append(header)
    for row in result["rows"]:
        cells = "".join(f"{('HIT' if row['hits'].get(n) else '-'):>14}" for n in names)
        lines.append(f"{str(row['id'])[:21]:<22}{cells}")
    lines.append("")
    for n in names:
        h = result["hit_at_n"][n]
        lines.append(f"{n:<14} {h['hits']}/{result['probes']}  ({h['rate']:.0%})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--legacy", action="store_true", help="main-compatible sources (before-measurement)")
    parser.add_argument("--readonly", action="store_true", help="never create FTS tables in the DB")
    args = parser.parse_args(argv)
    if args.readonly:
        import os
        os.environ["JARVIS_FTS_READONLY"] = "1"
    try:
        _owner_context()
    except Exception as exc:
        print(f"warning: owner context not set: {exc}", file=sys.stderr)
    sources = _legacy_sources() if args.legacy else _live_sources()
    result = run_probes(load_probes(args.fixture), sources=sources, limit=args.limit)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
