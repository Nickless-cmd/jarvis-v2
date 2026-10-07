#!/usr/bin/env python3
"""Splitter et prompt-dump fra /tmp/jarvis-prompt-dumps/latest.json i sektioner.

Bjørn (30/9-2026): «jeg vil den fulde prompt præcis når jeg sender og i det
sekund det forlader huset … del den op i sektioner så den er overskuelig.»

Dumpet skrives af core/services/prompt_dump.py og indeholder HELE requesten:
provider, model, lane, messages[], tools[] og params{}. Dette script gør det
læsbart: én markdown-fil med et indholdsfortegnelse-agtigt overblik, hver
message for sig og værktøjskataloget opdelt pr. værktøj.

Brug:
    python3 scripts/prompt_dump_split.py                    # latest.json
    python3 scripts/prompt_dump_split.py --file prev.json   # den forrige
    python3 scripts/prompt_dump_split.py --out /tmp/x.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_DUMP_DIR = Path("/tmp/jarvis-prompt-dumps")


def _chars(obj) -> int:
    try:
        return len(json.dumps(obj, ensure_ascii=False))
    except Exception:  # ikke-serialiserbar → 0 er aerligt "kan ikke maales"
        return 0


def _role_title(m: dict) -> str:
    role = str(m.get("role") or "?")
    name = str(m.get("name") or "")
    return f"{role}/{name}" if name else role


def _msg_body(m: dict) -> str:
    """Indholdet som tekst — håndterer både streng og strukturerede blokke."""
    c = m.get("content")
    if isinstance(c, str):
        return c
    if c is None:
        return ""
    return json.dumps(c, ensure_ascii=False, indent=2)


def build_markdown(dump: dict) -> str:
    msgs = dump.get("messages") or []
    tools = dump.get("tools") or []
    params = dump.get("params") or {}

    out: list[str] = []
    w = out.append

    # ── Header ────────────────────────────────────────────────────────────
    w("# Prompt-dump — den fulde request til udbyderen")
    w("")
    w("| | |")
    w("|---|---|")
    w(f"| provider | `{dump.get('provider')}` |")
    w(f"| model | `{dump.get('model')}` |")
    w(f"| lane | `{dump.get('lane') or '-'}` |")
    w(f"| runde | `{dump.get('round_index')}` |")
    w(f"| messages | **{len(msgs)}** ({sum(_chars(m) for m in msgs):,} tegn) |")
    w(f"| tools | **{len(tools)}** ({_chars(tools):,} tegn) |")
    w(f"| params | {', '.join(f'`{k}`' for k in params) or '—'} |")
    w("")

    # ── Indholdsfortegnelse ───────────────────────────────────────────────
    w("## Indhold")
    w("")
    w(f"- [Params](#params) · {_chars(params):,} tegn")
    w(f"- [Værktøjskatalog](#vaerktoejskatalog) · {len(tools)} værktøjer · {_chars(tools):,} tegn")
    w(f"- [Beskeder](#beskeder) · {len(msgs)} stk · {sum(_chars(m) for m in msgs):,} tegn")
    for i, m in enumerate(msgs):
        n = _chars(m)
        if n < 400:
            continue
        w(f"  - [{i:>2}. {_role_title(m)}](#msg-{i}) · {n:,} tegn")
    w("")

    # ── Params ────────────────────────────────────────────────────────────
    w("## Params")
    w("")
    if params:
        w("```json")
        w(json.dumps(params, ensure_ascii=False, indent=2))
        w("```")
    else:
        w("*(ingen)*")
    w("")

    # ── Værktøjer ─────────────────────────────────────────────────────────
    w("## Værktøjskatalog")
    w("")
    if tools:
        for i, t in enumerate(tools):
            fn = (t or {}).get("function") or {}
            name = fn.get("name") or (t or {}).get("name") or f"tool-{i}"
            desc = str(fn.get("description") or "")
            desc = desc.split("\n")[0][:140]
            w(f"### {i:>2}. `{name}` · {_chars(t):,} tegn")
            w("")
            if desc:
                w(f"> {desc}")
                w("")
            w("<details><summary>definition</summary>")
            w("")
            w("```json")
            w(json.dumps(t, ensure_ascii=False, indent=2))
            w("```")
            w("")
            w("</details>")
            w("")
    else:
        w("*(ingen værktøjer i denne request)*")
        w("")

    # ── Beskeder ──────────────────────────────────────────────────────────
    w("## Beskeder")
    w("")
    for i, m in enumerate(msgs):
        n = _chars(m)
        w(f'<a id="msg-{i}"></a>')
        w(f"### {i}. {_role_title(m)} · {n:,} tegn")
        w("")
        extra = {k: v for k, v in m.items() if k not in ("role", "content", "name")}
        if extra:
            w("```json")
            w(json.dumps(extra, ensure_ascii=False, indent=2)[:2000])
            w("```")
            w("")
        body = _msg_body(m)
        w("````text")
        w(body if body else "(tom)")
        w("````")
        w("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="latest.json", help="filnavn i dump-mappen")
    ap.add_argument("--dir", default=str(_DUMP_DIR))
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    path = Path(a.dir) / a.file
    if not path.exists():
        print(f"FEJL: {path} findes ikke.", file=sys.stderr)
        print("Er sentinel-filen arméret?  touch /tmp/jarvis-prompt-dump", file=sys.stderr)
        return 1

    with open(path, encoding="utf-8") as fh:
        dump = json.load(fh)

    md = build_markdown(dump)
    out = a.out or f"{a.dir}/split-{a.file.replace('.json', '')}.md"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(md)

    msgs = dump.get("messages") or []
    tools = dump.get("tools") or []
    print(f"skrev {out}")
    print(f"  messages={len(msgs)} ({sum(_chars(m) for m in msgs):,} tegn)")
    print(f"  tools={len(tools)} ({_chars(tools):,} tegn)")
    print(f"  params={list((dump.get('params') or {}))}")
    print(f"  filstørrelse={os.path.getsize(out):,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
