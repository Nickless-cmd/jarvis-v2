#!/usr/bin/env python3
"""Fase 7 — indsamler svarene.

Forhåndsregistrering: docs/experiments/2026-09-19-phase7-preregistration.md.
Proberne bygges af scripts/phase7_build_probes.py; deres SHA-256 skal stå i
registreringens tillæg FØR denne fil køres — scriptet tjekker det selv.

Tre betingelser × to svar-modeller pr. probe, som fase 6:
  FULL   Jarvis' ægte prompt-assembly, med ejer-konteksten sat
  FILES  SOUL + IDENTITY + USER som ren tekst
  BARE   ingen systemprompt
Brugerbeskeden er probe-spørgsmålet. Ingen værktøjer; intet skrives til
hukommelse eller anden produktionstilstand.

Skriver til ~/.jarvis-v2/files/phase7/ på CT105:
  responses.jsonl  ét svar pr. linje (genoptagelig: færdige par springes over)
  prompts.jsonl    FULL-prompten pr. probe, så V3 kan efterprøves

Køres på CT105:
    PYTHONPATH=/media/projects/jarvis-v2 python scripts/phase7_collect.py
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Udgave "7" eller "7b" (JARVIS_FASE7_UDGAVE) — samme valg som byggeren.
UDGAVE = os.environ.get("JARVIS_FASE7_UDGAVE", "7")
OUT_DIR = Path.home() / ".jarvis-v2" / "files" / {"7": "phase7", "7b": "phase7b"}[UDGAVE]
PROBES = OUT_DIR / "probes.jsonl"
RESPONSES = OUT_DIR / "responses.jsonl"
PROMPTS = OUT_DIR / "prompts.jsonl"
PREREG = REPO / "docs" / "experiments" / {"7": "2026-09-19-phase7-preregistration.md",
                                         "7b": "2026-09-19-phase7b-preregistration.md"}[UDGAVE]

SEED = {"7": 20260919, "7b": 20260920}[UDGAVE]
MODELS = {
    "QWN": {"provider": "alibaba", "model": "qwen-plus"},
    "CPL": {"provider": "copilot-free", "model": "gpt-4.1"},
}
CONDITIONS = ("FULL", "FILES", "BARE")
MEMORY_MARKER = "[HUKOMMELSE]"


def _load_builder():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_p7b", REPO / "scripts" / "phase7_build_probes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _check_locked() -> list[dict]:
    """Proberne SKAL være låst i registreringen før første svar."""
    sha = hashlib.sha256(PROBES.read_bytes()).hexdigest()
    if sha not in PREREG.read_text(encoding="utf-8"):
        raise SystemExit(f"probe-filens SHA-256 {sha} står ikke i {PREREG.name} — lås den først")
    return [json.loads(line) for line in PROBES.read_text(encoding="utf-8").splitlines() if line.strip()]


def _full_system_prompt(question: str) -> str:
    from core.services.prompt_contract import build_visible_chat_prompt_assembly
    a = build_visible_chat_prompt_assembly(
        provider="deepseek", model="deepseek-v4-flash",
        user_message=question, session_id=None,
    )
    return a.text or ""


def _call(provider: str, model: str, system: str, user: str) -> dict:
    from core.services.cheap_provider_runtime import _execute_openai_compatible_chat
    messages = ([{"role": "system", "content": system}] if system else [])
    messages.append({"role": "user", "content": user})
    t0 = time.time()
    r = _execute_openai_compatible_chat(
        provider=provider, model=model, auth_profile="default",
        base_url="", messages=messages, timeout=120.0,
    )
    return {"text": str(r.get("text") or "").strip(), "seconds": round(time.time() - t0, 1)}


def _done() -> set[tuple[str, str]]:
    if not RESPONSES.exists():
        return set()
    out = set()
    for line in RESPONSES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("text"):
                out.add((r["probe_id"], r["arm"]))
    return out


def main() -> None:
    b = _load_builder()
    _uid, ws = b._owner()
    probes = _check_locked()
    identity = "\n\n".join(
        f"--- {n} ---\n{(Path.home() / '.jarvis-v2' / 'workspaces' / ws / n).read_text(encoding='utf-8', errors='replace')}"
        for n in ("SOUL.md", "IDENTITY.md", "USER.md")
        if (Path.home() / ".jarvis-v2" / "workspaces" / ws / n).exists()
    )
    done = _done()
    rnd = random.Random(SEED)
    arms = [(f"{c}-{mk}", c, mv) for mk, mv in MODELS.items() for c in CONDITIONS]
    with RESPONSES.open("a", encoding="utf-8") as fh, PROMPTS.open("a", encoding="utf-8") as ph:
        for p in probes:
            order = list(arms)
            rnd.shuffle(order)  # altid, så rækkefølgen er den samme ved genoptagelse
            todo = [a for a in order if (p["probe_id"], a[0]) not in done]
            if not todo:
                continue
            full_sys = _full_system_prompt(p["question"])
            ph.write(json.dumps({
                "probe_id": p["probe_id"], "ts": datetime.now(UTC).isoformat(),
                "chars": len(full_sys), "has_memory": MEMORY_MARKER in full_sys,
                "sha1": hashlib.sha1(full_sys.encode()).hexdigest()[:16], "text": full_sys,
            }, ensure_ascii=False) + "\n")
            ph.flush()
            for name, cond, mv in todo:
                system = full_sys if cond == "FULL" else (identity if cond == "FILES" else "")
                res: dict = {"text": "", "seconds": 0, "error": "ikke forsoegt"}
                for attempt in range(3):
                    try:
                        res = _call(mv["provider"], mv["model"], system, p["question"])
                        if res["text"]:
                            break
                    except Exception as exc:
                        res = {"text": "", "seconds": 0, "error": str(exc)[:160]}
                    time.sleep(4 * (attempt + 1))
                time.sleep(1.0)
                fh.write(json.dumps({
                    "ts": datetime.now(UTC).isoformat(), "probe_id": p["probe_id"],
                    "bucket": p["bucket"], "type": p["type"], "arm": name, "condition": cond,
                    "model_key": name.split("-")[-1], "provider": mv["provider"], "model": mv["model"],
                    "system_chars": len(system),
                    "system_sha1": hashlib.sha1(system.encode()).hexdigest()[:16],
                    **res,
                }, ensure_ascii=False) + "\n")
                fh.flush()
                print(f"  {p['probe_id']} {name:10s} {'ok ' if res.get('text') else 'FEJL'} "
                      f"{(res.get('text') or res.get('error', ''))[:50]!r}", flush=True)


if __name__ == "__main__":
    main()
