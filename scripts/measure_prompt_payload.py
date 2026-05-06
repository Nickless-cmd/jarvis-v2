"""Measure where Jarvis's visible-chat prompt tokens come from.

Builds a real prompt assembly for a sample user message, collects the
tool definitions that would be sent alongside, and reports total tokens
broken down by source:

  - system instruction (subdivided by [SECTION] headers when possible)
  - transcript history (per message, with role)
  - tool definitions (per tool)
  - the new user turn

No state mutation. Read-only. Run anytime.

Usage:
    conda activate ai
    python scripts/measure_prompt_payload.py
    python scripts/measure_prompt_payload.py --user-message "vis mig din runtime"
    python scripts/measure_prompt_payload.py --session-id <uuid>
    python scripts/measure_prompt_payload.py --json > payload.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Add repo root to sys.path so imports work when run as a script
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def count_tokens(text: str) -> int:
    """Count tokens with tiktoken if available; else chars/4 estimate."""
    if not text:
        return 0
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


# Section headers as they appear in the assembled system prompt.
# These come from prompt_contract.py; the order is arbitrary, we just
# match them anywhere in the text.
_SECTION_HEADER_RE = re.compile(
    r"^(\[[A-Z][A-Z0-9 _\-/]+\])\s*$",
    re.MULTILINE,
)


def split_system_by_sections(text: str) -> list[tuple[str, int, int]]:
    """Split a system prompt into (header, char_count, token_count) tuples.

    A "section" starts at a `[SECTION_NAME]` line and runs until the next
    such header. Anything before the first header is reported as
    `[<preamble>]`. Returns the list in the order sections appear.
    """
    if not text:
        return []
    matches = list(_SECTION_HEADER_RE.finditer(text))
    out: list[tuple[str, int, int]] = []
    if not matches:
        return [("[<entire system prompt>]", len(text), count_tokens(text))]
    if matches[0].start() > 0:
        chunk = text[: matches[0].start()]
        out.append(("[<preamble>]", len(chunk), count_tokens(chunk)))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.start() : end]
        out.append((m.group(1), len(chunk), count_tokens(chunk)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user-message", default="hej, hvordan har du det?")
    ap.add_argument("--session-id", default=None)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of table")
    ap.add_argument(
        "--top-tools",
        type=int,
        default=20,
        help="show this many largest tool definitions in table mode",
    )
    args = ap.parse_args()

    # Resolve provider/model from router if not supplied
    if not args.provider or not args.model:
        from core.services.visible_model import resolve_provider_router_target

        target = resolve_provider_router_target(lane="visible")
        args.provider = args.provider or str(target.get("provider", "") or "")
        args.model = args.model or str(target.get("model", "") or "")

    from core.services.visible_model import _build_visible_prompt_assembly

    assembly = _build_visible_prompt_assembly(
        provider=args.provider,
        model=args.model,
        user_message=args.user_message,
        session_id=args.session_id,
    )

    sys_text = assembly.text or ""
    sys_tokens = count_tokens(sys_text)
    sys_chars = len(sys_text)
    sections = split_system_by_sections(sys_text)

    transcript_msgs = list(assembly.transcript_messages or [])
    transcript_breakdown = [
        {
            "index": i,
            "role": str(m.get("role", "?")),
            "chars": len(str(m.get("content", "") or "")),
            "tokens": count_tokens(str(m.get("content", "") or "")),
        }
        for i, m in enumerate(transcript_msgs)
    ]
    transcript_tokens_total = sum(int(b["tokens"]) for b in transcript_breakdown)

    # Tool definitions — same path the agentic loop uses
    tool_defs: list = []
    try:
        from core.tools.simple_tools import get_tool_definitions

        tool_defs = list(get_tool_definitions() or [])
    except Exception as exc:
        tool_defs = []
        tool_defs_error = str(exc)
    else:
        tool_defs_error = None

    tool_breakdown = []
    for td in tool_defs:
        td_text = json.dumps(td, ensure_ascii=False)
        name = (
            (td.get("function") or {}).get("name")
            or td.get("name")
            or "?"
        )
        tool_breakdown.append(
            {
                "name": str(name),
                "chars": len(td_text),
                "tokens": count_tokens(td_text),
            }
        )
    tool_breakdown.sort(key=lambda r: r["tokens"], reverse=True)
    tool_tokens_total = sum(int(r["tokens"]) for r in tool_breakdown)

    user_tokens = count_tokens(args.user_message)

    grand_total = sys_tokens + transcript_tokens_total + tool_tokens_total + user_tokens

    payload = {
        "provider": args.provider,
        "model": args.model,
        "user_message": args.user_message,
        "session_id": args.session_id,
        "totals": {
            "system_tokens": sys_tokens,
            "system_chars": sys_chars,
            "transcript_tokens": transcript_tokens_total,
            "transcript_messages": len(transcript_msgs),
            "tool_def_tokens": tool_tokens_total,
            "tool_def_count": len(tool_breakdown),
            "user_message_tokens": user_tokens,
            "grand_total_tokens": grand_total,
        },
        "system_sections": [
            {"header": h, "chars": c, "tokens": t} for h, c, t in sections
        ],
        "transcript_messages": transcript_breakdown,
        "tool_definitions": tool_breakdown,
        "tool_defs_error": tool_defs_error,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    # Pretty table output
    def pct(n: int) -> str:
        return f"{(100.0 * n / grand_total):5.1f}%" if grand_total else "  -  "

    print("=" * 78)
    print(f"  Jarvis visible-chat prompt payload measurement")
    print(f"  provider={args.provider}  model={args.model}")
    print(f"  user_message={args.user_message!r}")
    print(f"  session_id={args.session_id}")
    print("=" * 78)
    print()
    print(f"  GRAND TOTAL: {grand_total:>7,} tokens")
    print()
    print(f"  System prompt        {sys_tokens:>7,} tok  {pct(sys_tokens)}   ({sys_chars:,} chars)")
    print(f"  Transcript history   {transcript_tokens_total:>7,} tok  {pct(transcript_tokens_total)}   ({len(transcript_msgs)} messages)")
    print(f"  Tool definitions     {tool_tokens_total:>7,} tok  {pct(tool_tokens_total)}   ({len(tool_breakdown)} tools)")
    print(f"  User message         {user_tokens:>7,} tok  {pct(user_tokens)}")
    if tool_defs_error:
        print(f"  (tool def error: {tool_defs_error})")
    print()

    print("-" * 78)
    print("  System prompt — by [SECTION]")
    print("-" * 78)
    if sections:
        for header, chars, toks in sorted(sections, key=lambda r: r[2], reverse=True):
            print(f"  {toks:>5,} tok  {chars:>6,} ch   {header}")
    else:
        print("  (no [SECTION] markers found)")
    print()

    if transcript_breakdown:
        print("-" * 78)
        print("  Transcript history — per message")
        print("-" * 78)
        for b in transcript_breakdown:
            print(
                f"  #{b['index']:>3}  {b['role']:>10}  {b['tokens']:>5,} tok  {b['chars']:>6,} ch"
            )
        print()

    if tool_breakdown:
        print("-" * 78)
        print(f"  Tool definitions — top {min(args.top_tools, len(tool_breakdown))} by token cost")
        print("-" * 78)
        for r in tool_breakdown[: args.top_tools]:
            print(f"  {r['tokens']:>5,} tok  {r['chars']:>6,} ch   {r['name']}")
        if len(tool_breakdown) > args.top_tools:
            rest_tok = sum(int(r["tokens"]) for r in tool_breakdown[args.top_tools :])
            print(f"  ...        + {len(tool_breakdown) - args.top_tools} more = {rest_tok:,} tok")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
