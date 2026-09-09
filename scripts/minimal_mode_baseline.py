#!/usr/bin/env python
"""Minimal-mode-basislinje — hvad kan modellen UDEN Jarvis' stillads?

DeepSeek-harness-spec'ens §12: deres `minimal`-preset er bevidst nøgen — fast
prompt, ingen runtime-kontekst, ingen kompaktion, og præcis to værktøjer
(persistent bash + `str_replace_editor`). Det er den flade DeepSeek selv
benchmarker på, fordi produktions-tal afhænger lige så meget af stilladset som
af modellen.

Fase 0 kræver den samme måling hos os: *«establish the minimal-mode baseline
… and record model-only success/failure on the same fixtures, so later phases
can measure what the harness adds rather than assuming it»*.

Denne kørsel er DEN nøgne side. Den låner INTET fra Jarvis-runtimen — ingen
prompt-samling, ingen Central, ingen hukommelse, ingen identitet. Modellen får
en fast prompt og to værktøjer, og opgaverne har maskin-tjekbar facit.

**Facit kommer fra kilden i samme øjeblik, aldrig fra en håndskrevet forventning.**
Hver opgave efterprøves ved at køre en kommando i arbejdsmappen bagefter. Det
er den eneste måde en model-måling ikke kan komme til at måle sin egen
forventning.

Brug (på den maskine hvor Ollama kører):

    python scripts/minimal_mode_baseline.py --runder 8
    python scripts/minimal_mode_baseline.py --opgave fil-skriv --gentag 3
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

ENDPOINT = "http://127.0.0.1:11434"
MODEL = "deepseek-v4-flash:cloud"

# Fast, komplet persona — som minimal-presettets. Ingen runtime-kontekst,
# ingen identitetsfiler, ingen hukommelse. Den ændrer sig ikke mellem opgaver.
SYSTEM = (
    "You are a coding agent working in a scratch directory. "
    "You have exactly two tools: `bash` to run shell commands, and "
    "`str_replace_editor` to create or edit files. "
    "Work step by step. When the task is done, reply with a short plain-text "
    "summary and no tool call."
)

VAERKTOEJER = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command in the working directory.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "str_replace_editor",
            "description": (
                "Create a file (command=create) or replace a string in it "
                "(command=str_replace)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": ["create", "str_replace"]},
                    "path": {"type": "string"},
                    "file_text": {"type": "string"},
                    "old_str": {"type": "string"},
                    "new_str": {"type": "string"},
                },
                "required": ["command", "path"],
            },
        },
    },
]


# ── Opgaver: hver med en FACIT-kommando der køres bagefter ────────────────
# Facit er en kommando, ikke en streng. Består den (exit 0), lykkedes opgaven.
OPGAVER = {
    "fil-skriv": {
        "opgave": "Create a file called svar.txt containing exactly the word: bananer",
        "facit": "test \"$(cat svar.txt 2>/dev/null | tr -d '[:space:]')\" = bananer",
        "opsaet": None,
    },
    "find-linje": {
        "opgave": (
            "The file kode.py contains one function that returns 42. "
            "Write the line number of its `return` statement into linje.txt "
            "(just the number)."
        ),
        "facit": "test \"$(cat linje.txt | tr -d '[:space:]')\" = 4",
        "opsaet": "printf '# top\\n\\ndef svar():\\n    return 42\\n' > kode.py",
    },
    "ret-fejl": {
        "opgave": (
            "The script buggy.py fails when run. Fix it so `python3 buggy.py` "
            "prints 7 and exits 0. Change as little as possible."
        ),
        "facit": "test \"$(python3 buggy.py 2>/dev/null)\" = 7",
        "opsaet": "printf 'print(3 + \"4\")\\n' > buggy.py",
    },
    # Sværere: kræver at læse FLERE filer, sammenholde dem og handle på
    # resultatet — den slags hvor et stillads (hukommelse, kontekst-samling)
    # i teorien skulle hjælpe. Hvis den nøgne model også klarer DEN, har
    # stilladset ikke bevist sin værdi på denne opgavestørrelse.
    "sammenhold": {
        "opgave": (
            "The directory konfig/ has several .env files. Exactly one of them "
            "defines PORT with a value that is NOT also present in porte.txt. "
            "Write that file's name (just the filename) into fundet.txt."
        ),
        "facit": "test \"$(cat fundet.txt | tr -d '[:space:]')\" = c.env",
        "opsaet": (
            "mkdir -p konfig && printf 'PORT=8080\\n' > konfig/a.env && "
            "printf 'PORT=9090\\n' > konfig/b.env && "
            "printf 'PORT=7777\\n' > konfig/c.env && "
            "printf 'HOST=x\\n' > konfig/d.env && "
            "printf '8080\\n9090\\n3000\\n' > porte.txt"
        ),
    },
    "flertrin": {
        "opgave": (
            "Write a python script tal.py that reads numbers from tal.txt (one "
            "per line), and prints their sum. Then run it and put the result "
            "into sum.txt. Do not compute the sum yourself."
        ),
        "facit": "test \"$(cat sum.txt | tr -d '[:space:]')\" = 60 && test -f tal.py",
        "opsaet": "printf '10\\n20\\n30\\n' > tal.txt",
    },
    "taelle": {
        "opgave": (
            "Count how many .txt files are in the data/ directory (not "
            "recursive) and write the number into antal.txt."
        ),
        "facit": "test \"$(cat antal.txt | tr -d '[:space:]')\" = 3",
        "opsaet": "mkdir -p data && touch data/a.txt data/b.txt data/c.txt data/d.md",
    },
}


def _kald(beskeder: list[dict], *, timeout: int = 180) -> dict | None:
    krop = json.dumps({
        "model": MODEL,
        "messages": beskeder,
        "tools": VAERKTOEJER,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 800},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{ENDPOINT}/api/chat", data=krop,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as exc:
        print(f"    ! modelkald fejlede: {type(exc).__name__}: {exc}")
        return None


def _koer(cmd: str, cwd: Path, timeout: int = 30) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)[-2000:]
    except subprocess.TimeoutExpired:
        return 124, "[timeout]"
    except Exception as exc:                        # pragma: no cover
        return 1, f"[{type(exc).__name__}: {exc}]"


def _udfoer_vaerktoej(navn: str, args: dict, mappe: Path) -> str:
    if navn == "bash":
        kode, ud = _koer(str(args.get("command") or ""), mappe)
        return f"exit={kode}\n{ud}" if ud.strip() else f"exit={kode}"
    if navn == "str_replace_editor":
        sti = mappe / str(args.get("path") or "").lstrip("/")
        try:
            if args.get("command") == "create":
                sti.parent.mkdir(parents=True, exist_ok=True)
                sti.write_text(str(args.get("file_text") or ""), encoding="utf-8")
                return f"created {sti.name}"
            gammel, ny = str(args.get("old_str") or ""), str(args.get("new_str") or "")
            t = sti.read_text(encoding="utf-8")
            if gammel not in t:
                return "error: old_str not found"
            sti.write_text(t.replace(gammel, ny, 1), encoding="utf-8")
            return f"edited {sti.name}"
        except Exception as exc:
            return f"error: {type(exc).__name__}: {exc}"
    return f"error: unknown tool {navn}"


def koer_opgave(navn: str, spec: dict, *, maks_runder: int) -> dict:
    mappe = Path(tempfile.mkdtemp(prefix=f"minimal-{navn}-"))
    try:
        if spec["opsaet"]:
            _koer(spec["opsaet"], mappe)
        beskeder = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": spec["opgave"]},
        ]
        start = time.time()
        runder = 0
        vaerktoejskald = 0
        for _ in range(maks_runder):
            runder += 1
            svar = _kald(beskeder)
            if svar is None:
                return {"opgave": navn, "ok": False, "grund": "modelkald fejlede",
                        "runder": runder, "tool_kald": vaerktoejskald}
            besked = svar.get("message") or {}
            kald = besked.get("tool_calls") or []
            beskeder.append(besked)
            if not kald:
                break
            for k in kald:
                fn = (k.get("function") or {})
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    try: args = json.loads(args)
                    except Exception: args = {}
                vaerktoejskald += 1
                resultat = _udfoer_vaerktoej(str(fn.get("name") or ""), args, mappe)
                beskeder.append({"role": "tool", "content": resultat[:4000]})
        # FACIT: kør tjek-kommandoen i mappen. Kilden svarer, ikke vi.
        kode, _ = _koer(spec["facit"], mappe)
        return {
            "opgave": navn, "ok": kode == 0, "runder": runder,
            "tool_kald": vaerktoejskald, "sekunder": round(time.time() - start, 1),
        }
    finally:
        shutil.rmtree(mappe, ignore_errors=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--opgave", default="", help="kun én opgave (se OPGAVER)")
    p.add_argument("--gentag", type=int, default=1)
    p.add_argument("--runder", type=int, default=8, help="maks agent-runder pr. opgave")
    a = p.parse_args()

    valgte = {a.opgave: OPGAVER[a.opgave]} if a.opgave else OPGAVER
    resultater = []
    print(f"minimal-mode · model={MODEL} · maks {a.runder} runder\n")
    for navn, spec in valgte.items():
        for i in range(a.gentag):
            r = koer_opgave(navn, spec, maks_runder=a.runder)
            resultater.append(r)
            mark = "✓" if r["ok"] else "✗"
            print(f"  {mark} {navn:12} runder={r['runder']} tools={r['tool_kald']} "
                  f"{r.get('sekunder', '?')}s"
                  + (f"  ({r['grund']})" if r.get("grund") else ""))
    n = len(resultater)
    ok = sum(1 for r in resultater if r["ok"])
    print(f"\nbestået {ok}/{n}")
    print(json.dumps(resultater, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
