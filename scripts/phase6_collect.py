#!/usr/bin/env python3
"""Fase 6 «Bæres han på tværs af tid?» — indsamler.

Forhåndsregistrering: docs/experiments/2026-09-02-phase6-preregistration.md
(skrevet FØR denne fil kørte første gang).

Samme prober, samme model, TRE tidspunkter. FILES-armens prompt er byte-
identisk hver gang og udgør derfor et rent temperatur-støjgulv; FULL-armens
prompt driver med runtime-tilstanden. Spørgsmålet er om Jarvis' svar holder
sammen på trods af den drift — og om aftrykket kan skelnes fra tekst-tvillingen.

Gemmer råt til ~/.jarvis-v2/files/phase6/responses.jsonl sammen med hash og
længde af den prompt der FAKTISK blev sendt, så validitetstjekket (T4) kan
efterprøves bagefter. Rører ingen produktionstilstand.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT_DIR = Path.home() / ".jarvis-v2" / "files" / "phase6"
OUT_FILE = OUT_DIR / "responses.jsonl"

MODELS = {
    "QWN": {"provider": "alibaba", "model": "qwen-plus"},
    "CPL": {"provider": "copilot-free", "model": "gpt-4.1"},
}

# Samme ti prober som fase 5, så de to forsøg kan holdes op mod hinanden.
# scripts/ er ikke en pakke — hentes ad sti.
import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location('_p5', REPO / 'scripts' / 'phase5_collect.py')
_p5 = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_p5)
PROBES = _p5.PROBES
_identity_text = _p5._identity_text

CONDITIONS = ("FULL", "FILES", "BARE")


def _full_system_prompt(probe_text: str) -> str:
    """Jarvis' ÆGTE prompt-assembly — bygges PÅ NY ved hvert tidspunkt.

    Det er hele forsøget: denne streng skal drive mellem tidspunkter, mens
    identitetsteksten står stille.
    """
    from core.services.prompt_contract import build_visible_chat_prompt_assembly
    a = build_visible_chat_prompt_assembly(
        provider="deepseek", model="deepseek-v4-flash",
        user_message=probe_text, session_id=None,
    )
    return a.text or ""


def _call(provider: str, model: str, system: str, user: str) -> dict:
    from core.runtime.provider_router import resolve_provider_router_target
    from core.services.cheap_provider_runtime import _execute_openai_compatible_chat
    base_url = ""
    try:
        t = resolve_provider_router_target(lane="cheap") or {}
        if str(t.get("provider")) == provider:
            base_url = str(t.get("base_url") or "")
    except Exception:
        pass
    messages = ([{"role": "system", "content": system}] if system else [])
    messages.append({"role": "user", "content": user})
    t0 = time.time()
    r = _execute_openai_compatible_chat(
        provider=provider, model=model, auth_profile="default",
        base_url=base_url, messages=messages, timeout=120.0,
    )
    return {"text": str(r.get("text") or "").strip(), "seconds": round(time.time() - t0, 1)}


def collect_timepoint(tp: int, rnd: random.Random) -> int:
    """Ét tidspunkt: alle betingelser × modeller × prober."""
    identity = _identity_text()
    arms = [(f"{c}-{mk}", c, mv) for mk, mv in MODELS.items() for c in CONDITIONS]
    done = 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("a", encoding="utf-8") as fh:
        for pid, kind, text in PROBES:
            # FULL bygges ÉN gang pr. probe pr. tidspunkt — så alle modeller
            # ser præcis samme tilstand, og drift mellem tidspunkter er den
            # eneste forskel.
            full_sys = _full_system_prompt(text)
            order = list(arms)
            rnd.shuffle(order)
            for name, cond, mv in order:
                system = full_sys if cond == "FULL" else (identity if cond == "FILES" else "")
                res, ok = {"text": "", "seconds": 0, "error": "ikke forsoegt"}, False
                for attempt in range(3):
                    try:
                        res = _call(mv["provider"], mv["model"], system, text)
                        ok = bool(res["text"])
                        if ok:
                            break
                    except Exception as exc:
                        res = {"text": "", "seconds": 0, "error": str(exc)[:160]}
                    time.sleep(4 * (attempt + 1))
                time.sleep(1.5)
                fh.write(json.dumps({
                    "ts": datetime.now(UTC).isoformat(),
                    "timepoint": tp, "arm": name, "condition": cond,
                    "model_key": name.split("-")[-1],
                    "provider": mv["provider"], "model": mv["model"],
                    "probe_id": pid, "probe_kind": kind,
                    # Bevis for T4: hvad blev FAKTISK sendt.
                    "system_chars": len(system),
                    "system_sha1": hashlib.sha1(system.encode()).hexdigest()[:16],
                    **res,
                }, ensure_ascii=False) + "\n")
                fh.flush()
                done += 1
                print("    t%d %-10s %-3s  %s  %s" % (
                    tp, name, pid, "ok " if ok else "FEJL",
                    (res.get("text") or res.get("error", ""))[:52].replace("\n", " ")),
                    flush=True)
    return done


def run(timepoints: int, gap_minutes: float) -> None:
    rnd = random.Random(20260902)
    total = 0
    for tp in range(1, timepoints + 1):
        print(f"  === tidspunkt {tp}/{timepoints} — {datetime.now(UTC).isoformat()} ===",
              flush=True)
        total += collect_timepoint(tp, rnd)
        if tp < timepoints:
            print(f"  venter {gap_minutes:.0f} min paa at tilstanden driver...", flush=True)
            time.sleep(gap_minutes * 60)
    print(f"  faerdig: {total} svar -> {OUT_FILE}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--timepoints", type=int, default=3)
    ap.add_argument("--gap-minutes", type=float, default=45.0)
    a = ap.parse_args()
    run(a.timepoints, a.gap_minutes)
