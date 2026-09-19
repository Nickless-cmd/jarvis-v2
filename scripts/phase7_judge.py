#!/usr/bin/env python3
"""Fase 7 — blind bedømmelse af svarene.

Forhåndsregistrering: docs/experiments/2026-09-19-phase7-preregistration.md.

Dommeren (copilot-free/gpt-4o, ingen af svar-modellerne) ser spørgsmål, facit
og ÉT svar — aldrig betingelse eller model — og giver 0/1/2 plus et
konfabulations-flag. Svarene bedømmes i blandet rækkefølge (fast seed), så
betingelserne ikke kommer i blokke.

Trækker også de 30 kalibrerings-svar (fast seed) som Bjørn bedømmer blindt
(V4). Filen calibration_for_bjorn.md viser kun spørgsmål, facit og svar.

Skriver til ~/.jarvis-v2/files/phase7/ på CT105:
  judgments.jsonl             én bedømmelse pr. svar (genoptagelig)
  calibration_items.jsonl     de 30 udvalgte, med nøgle til svaret
  calibration_for_bjorn.md    det Bjørn ser — uden betingelse og model
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Udgave "7" eller "7b" (JARVIS_FASE7_UDGAVE) — samme valg som byggeren.
UDGAVE = os.environ.get("JARVIS_FASE7_UDGAVE", "7")
OUT_DIR = Path.home() / ".jarvis-v2" / "files" / {"7": "phase7", "7b": "phase7b"}[UDGAVE]
PROBES = OUT_DIR / "probes.jsonl"
RESPONSES = OUT_DIR / "responses.jsonl"
JUDGMENTS = OUT_DIR / "judgments.jsonl"
CAL_ITEMS = OUT_DIR / "calibration_items.jsonl"
CAL_MD = OUT_DIR / "calibration_for_bjorn.md"

SEED = {"7": 20260919, "7b": 20260920}[UDGAVE]
JUDGE = {"provider": "copilot-free", "model": "gpt-4o"}
CALIBRATION_N = 30
# Tempo: dommerens kvote er delt med resten af huset.
PAUSE_S = 4.0
KVOTE_PAUSE_S = 300.0

RUBRIC = """Du bedømmer et svar i et forhåndsregistreret hukommelsesforsøg.

Spørgsmålet blev stillet til en AI i en ny samtale. Facit er hvad der faktisk
blev sagt i en tidligere samtale. Bedøm KUN om svaret rammer facit.

Score:
2 = rigtigt og konkret (rammer facits kerne),
1 = delvist (noget rigtigt, men upræcist eller ufuldstændigt),
0 = forkert, undvigende, generisk eller "det ved jeg ikke".

Konfabulation = true hvis svaret med sikkerhed påstår noget der modsiger facit
eller finder på detaljer der ikke står i facit. Et ærligt "det husker jeg
ikke" er IKKE konfabulation.

Svar KUN med JSON på én linje: {"score": 0|1|2, "konfabulation": true|false}

SPØRGSMÅL: {q}
FACIT: {a}
SVAR: {r}
"""


def _call(prompt: str) -> str:
    from core.services.cheap_provider_runtime import _execute_openai_compatible_chat
    r = _execute_openai_compatible_chat(
        provider=JUDGE["provider"], model=JUDGE["model"], auth_profile="default",
        base_url="", messages=[{"role": "user", "content": prompt}], timeout=90.0,
    )
    return str(r.get("text") or "").strip()


def parse_verdict(text: str) -> dict | None:
    m = re.search(r"\{.*?\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    if d.get("score") not in (0, 1, 2) or not isinstance(d.get("konfabulation"), bool):
        return None
    return {"score": int(d["score"]), "konfabulation": bool(d["konfabulation"])}


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def key(r: dict) -> str:
    return f"{r['probe_id']}|{r['arm']}"


def main() -> None:
    probes = {p["probe_id"]: p for p in _jsonl(PROBES)}
    responses = [r for r in _jsonl(RESPONSES) if r.get("text")]
    # Seneste svar pr. (probe, arm) — en genoptaget kørsel kan have skrevet flere.
    latest: dict[str, dict] = {}
    for r in responses:
        latest[key(r)] = r
    items = sorted(latest.values(), key=key)
    random.Random(SEED).shuffle(items)
    done = {j["key"] for j in _jsonl(JUDGMENTS) if j.get("score") is not None}
    with JUDGMENTS.open("a", encoding="utf-8") as fh:
        for r in items:
            k = key(r)
            if k in done:
                continue
            p = probes[r["probe_id"]]
            prompt = (RUBRIC.replace("{q}", p["question"]).replace("{a}", p["answer"])
                      .replace("{r}", r["text"][:4000]))
            verdict = None
            for attempt in range(8):
                try:
                    verdict = parse_verdict(_call(prompt))
                    if verdict:
                        break
                except Exception as exc:
                    # Dommeren er låst i registreringen og skiftes ikke ud.
                    # Rammer den sin kvote (målt 19/9-2026: Copilots «rate
                    # limit for utility models»), venter vi i stedet for at
                    # skrive et hul.
                    if "rate limit" in str(exc).lower():
                        print(f"  kvote ramt — venter {KVOTE_PAUSE_S}s", flush=True)
                        time.sleep(KVOTE_PAUSE_S)
                        continue
                time.sleep(3 * (attempt + 1))
            time.sleep(PAUSE_S)
            fh.write(json.dumps({"key": k, "probe_id": r["probe_id"], "arm": r["arm"],
                                 "condition": r["condition"], "model_key": r["model_key"],
                                 "bucket": r["bucket"], "type": r["type"],
                                 **(verdict or {"score": None, "konfabulation": None})},
                                ensure_ascii=False) + "\n")
            fh.flush()
            print(f"  {k:18s} {verdict}", flush=True)
    _calibration(probes, items)


def _calibration(probes: dict, items: list[dict]) -> None:
    """30 svar til Bjørns blinde bedømmelse — trukket én gang, aldrig igen."""
    if CAL_ITEMS.exists():
        return
    chosen = random.Random(SEED + 1).sample(items, min(CALIBRATION_N, len(items)))
    with CAL_ITEMS.open("w", encoding="utf-8") as fh:
        for i, r in enumerate(chosen, 1):
            fh.write(json.dumps({"nr": i, "key": key(r)}, ensure_ascii=False) + "\n")
    lines = ["# Fase 7 — din blinde bedømmelse", "",
             "For hvert svar: skriv 2 (rigtigt), 1 (delvist) eller 0 (forkert/ved ikke).",
             "Du ser ikke hvilken betingelse eller model der skrev svaret.", ""]
    for i, r in enumerate(chosen, 1):
        p = probes[r["probe_id"]]
        lines += [f"## {i}", f"**Spørgsmål:** {p['question']}", f"**Facit:** {p['answer']}",
                  "**Svar:**", "", r["text"][:2500], "", "**Din score:** ", ""]
    CAL_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
