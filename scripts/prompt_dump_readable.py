#!/usr/bin/env python3
"""Læsbar version af et prompt-dump (30/9-2026).

Bjørn: «kan du ikk gøre det lidt mere læsbart for mig?»

Den rå splitter (prompt_dump_split.py) viser ALT: 108 værktøjsdefinitioner i
fuld JSON og hver besked råt dumpet. Det er komplet, men ulæseligt — 500 KB.

Denne variant vender det om: oversigten først, så hver besked med en
genkendelig etikette og et kort uddrag. Default er KORT (intet fuldt indhold);
--full klapper det fulde indhold ud bag <details> i stedet.

Den splitter ogsaa user-beskederne i «Bjørns ord» vs «tool-resultater», fordi
de to ligger pakket i SAMME besked — ellers skjuler oversigten hvor vægten er.

Brug:
    python3 scripts/prompt_dump_readable.py                 # latest.json, kort
    python3 scripts/prompt_dump_readable.py --full           # med alt indhold
    python3 scripts/prompt_dump_readable.py --file prev.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_DUMP_DIR = Path("/tmp/jarvis-prompt-dumps")
_TAIL_SENTINEL = "⟦◆DYNAMIC-TAIL-DO-NOT-CACHE◆⟧"
_TOOL_MARK = "⟦værktøjs-resultat⟧"
_PREVIEW_SHORT = 400
_PREVIEW_FULL = 650


def _chars(obj) -> int:
    try:
        return len(json.dumps(obj, ensure_ascii=False))
    except Exception:  # ikke-serialiserbar → 0 er aerligt "kan ikke maales"
        return 0


def _text(m: dict) -> str:
    c = m.get("content")
    if isinstance(c, str):
        return c
    if c is None:
        return ""
    return json.dumps(c, ensure_ascii=False, indent=2)


def _split_user(t: str) -> tuple[int, int, int]:
    """(bjoern-tegn, tool-resultat-tegn, rest) inde i ÉN user-besked.

    Beskederne er pakket som «Bjørn: <hans ord>» efterfulgt af én eller flere
    «⟦værktøjs-resultat⟧ …»-blokke. Uden denne split ser alt ud som «samtale».
    """
    if _TOOL_MARK not in t:
        if t.lstrip().startswith("Bjørn:"):
            return len(t), 0, 0
        return 0, 0, len(t)
    parts = t.split(_TOOL_MARK)
    head = parts[0]
    bjoern = len(head) if head.lstrip().startswith("Bjørn:") else 0
    tool = sum(len(_TOOL_MARK) + len(p) for p in parts[1:])
    return bjoern, tool, len(head) - bjoern


def _kind(i: int, m: dict) -> tuple[str, str]:
    """(kategori-noegle, menneske-etikette) for én besked."""
    role = str(m.get("role") or "?")
    t = _text(m)
    head = t.lstrip()[:80]
    if role == "system":
        if i == 0:
            return "persona", "PERSONA + WORKSPACE-FILER · cachet prefix"
        return "kapsel", "KONTINUITETS-KAPSEL · aendrer sig hver tur"
    if role == "assistant":
        return "svar", "mit svar"
    if role == "tool":
        return "resultat", "vaerktoejssvar (raw)"
    if role == "user":
        if head.startswith("[Komprimeret historik"):
            return "historik", "KOMPRIMERET SAMTALEHISTORIK"
        if head.startswith(_TOOL_MARK) or head.startswith("[tool"):
            return "resultat", "tool-resultat"
        if head.startswith("Bjørn:"):
            return "bjoern", "din besked (+ tool-resultater)"
        return "andet", "user-besked"
    return "andet", role


def _pct(n: int, total: int) -> str:
    return f"{100.0 * n / total:.1f} %" if total else "—"


def build(dump: dict, full: bool = False) -> str:
    msgs = dump.get("messages") or []
    tools = dump.get("tools") or []
    params = dump.get("params") or {}
    preview = _PREVIEW_FULL if full else _PREVIEW_SHORT

    tools_chars = _chars(tools)

    # ── aggregér indholdet ────────────────────────────────────────────────
    agg = {"bjoern": 0, "svar": 0, "resultat": 0, "historik": 0, "persona": 0,
           "kapsel": 0, "andet": 0}
    counts: dict[str, int] = {}
    for i, m in enumerate(msgs):
        k, _ = _kind(i, m)
        counts[k] = counts.get(k, 0) + 1
        if k == "bjoern":
            b, tool, rest = _split_user(_text(m))
            agg["bjoern"] += b
            agg["resultat"] += tool
            agg["andet"] += rest
        elif k in agg:
            agg[k] += _chars(m)

    total = sum(agg.values()) + tools_chars

    out: list[str] = []
    w = out.append

    # ── Header ────────────────────────────────────────────────────────────
    w("# Prompten der forlod huset")
    w("")
    w("| | |")
    w("|---|---|")
    w(f"| provider | `{dump.get('provider')}` |")
    w(f"| model | `{dump.get('model')}` |")
    w(f"| lane | `{dump.get('lane') or '-'}` |")
    w(f"| runde | `{dump.get('round_index')}` |")
    w(f"| beskeder | **{len(msgs)}** |")
    w(f"| vaerktoejer | **{len(tools)}** |")
    w(f"| i alt | **{total:,} tegn** |")
    w("")

    # ── På 10 sekunder ────────────────────────────────────────────────────
    w("## Paa 10 sekunder")
    w("")
    w("| post | tegn | andel | hvad |")
    w("|---|---:|---:|---|")
    rows = [
        ("historik", "Komprimeret samtalehistorik", "ældre samtale komprimeret til én blok"),
        ("bjoern", "Dine ord", "hvad du faktisk skrev"),
        ("svar", "Mine svar", "hvad jeg svarede"),
        ("resultat", "Tool-resultater", "rå output fra værktøjer, pakket i dine beskeder"),
        ("persona", "Persona + workspace-filer", "system-prompten, den cachede prefix"),
        ("kapsel", "Kontinuitets-kapsel", "mood, chronicle — ændrer sig hver tur"),
        ("andet", "Andet", "formatering, markører"),
    ]
    for key, label, hvad in rows:
        n = agg.get(key, 0)
        if not n:
            continue
        c = counts.get(key, 0)
        w(f"| **{label}**" + (f" ({c})" if c else "") + f" | {n:,} | {_pct(n, total)} | {hvad} |")
    w(f"| **Vaerktoejskatalog** ({len(tools)} stk) | {tools_chars:,} | {_pct(tools_chars, total)} | alle vaerktoejers JSON-definitioner |")
    w(f"| | **{total:,}** | **100 %** | |")
    w("")

    # ── Params ────────────────────────────────────────────────────────────
    w("## Parametre")
    w("")
    if params:
        for k in sorted(params):
            w(f"- `{k}` = `{json.dumps(params[k], ensure_ascii=False)}`")
    else:
        w("*(ingen)*")
    w("")

    # ── Beskederne ────────────────────────────────────────────────────────
    w("## Beskederne, én for én")
    w("")
    if full:
        w("Hver besked med rolle, stoerrelse og uddrag. Det fulde indhold ligger")
        w("sammenklappet under **vis hele beskeden**.")
    else:
        w("Hver besked med rolle, stoerrelse og et kort uddrag. Det fulde indhold")
        w("er ikke med her — koer med `--full` for at faa det.")
    w("")
    for i, m in enumerate(msgs):
        t = _text(m)
        n = _chars(m)
        _, lab = _kind(i, m)
        role = str(m.get("role") or "?")
        w(f"### {i}. {lab} · {n:,} tegn")
        w("")
        meta = f"`role={role}`"
        if _TAIL_SENTINEL in t:
            meta += " · **indeholder hale-sentinel**"
        if role == "user" and _TOOL_MARK in t:
            b, tool, rest = _split_user(t)
            meta += f" · din tekst {b:,} · tool-resultater {tool:,}"
        w(meta)
        w("")
        if n <= preview:
            w("```text")
            w(t if t else "(tom)")
            w("```")
        else:
            w("```text")
            w(t[:preview])
            w("…")
            w("```")
            if full:
                w(f"<details><summary>vis hele beskeden ({n:,} tegn)</summary>")
                w("")
                w("```text")
                w(t)
                w("```")
                w("")
                w("</details>")
        w("")

    # ── Værktøjskataloget ─────────────────────────────────────────────────
    w("## Vaerktoejskataloget")
    w("")
    if not tools:
        w("*(ingen vaerktoejer i denne request)*")
        w("")
    else:
        w("| # | navn | tegn | hvad |")
        w("|---:|---|---:|---|")
        for i, t in enumerate(tools):
            fn = (t or {}).get("function") or {}
            name = fn.get("name") or (t or {}).get("name") or f"tool-{i}"
            desc = str(fn.get("description") or "").split("\n")[0].strip()
            if len(desc) > 90:
                desc = desc[:87] + "…"
            desc = desc.replace("|", "\\|")
            w(f"| {i} | `{name}` | {_chars(t):,} | {desc} |")
        w("")
        if full:
            w("<details><summary>vis alle fulde definitioner</summary>")
            w("")
            for i, t in enumerate(tools):
                fn = (t or {}).get("function") or {}
                name = fn.get("name") or (t or {}).get("name") or f"tool-{i}"
                w(f"**{i}. `{name}`**")
                w("")
                w("```json")
                w(json.dumps(t, ensure_ascii=False, indent=2))
                w("```")
                w("")
            w("</details>")
            w("")

    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="latest.json", help="filnavn i dump-mappen")
    ap.add_argument("--dir", default=str(_DUMP_DIR))
    ap.add_argument("--out", default="")
    ap.add_argument("--full", action="store_true", help="med alt fuldt indhold")
    a = ap.parse_args()

    path = Path(a.dir) / a.file
    if not path.exists():
        print(f"FEJL: {path} findes ikke.", file=sys.stderr)
        print("Er sentinel-filen armeret?  touch /tmp/jarvis-prompt-dump", file=sys.stderr)
        return 1

    with open(path, encoding="utf-8") as fh:
        dump = json.load(fh)

    md = build(dump, full=a.full)
    suffix = "full" if a.full else "kort"
    out = a.out or f"{a.dir}/readable-{suffix}.md"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(md)

    print(f"skrev {out}")
    print(f"  beskeder={len(dump.get('messages') or [])}")
    print(f"  vaerktoejer={len(dump.get('tools') or [])}")
    print(f"  filstoerrelse={os.path.getsize(out):,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
