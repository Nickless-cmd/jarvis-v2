#!/usr/bin/env python3
"""Fase 5 «Bor der nogen?» — indsamler.

Forhåndsregistrering: docs/experiments/2026-09-01-phase5-preregistration.md
(skrevet FØR denne fil kørte første gang).

Seks arme = 2 modeller × 3 betingelser. Kernemålet er KONVERGENS: hvor ens
svarer to fremmede arkitekturer på samme probe under samme betingelse. BARE er
forsøgets eget støjgulv — den naturlige afstand mellem to modeller. Spørgsmålet
er om runtime trækker dem tættere sammen end identitetsteksten alene gør.

Skriver rå svar til ~/.jarvis-v2/files/phase5/responses.jsonl. Rører ingen
produktionstilstand.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT_DIR = Path.home() / ".jarvis-v2" / "files" / "phase5"
OUT_FILE = OUT_DIR / "responses.jsonl"

# To bevidst forskellige arkitektur-familier.
# To maksimalt forskellige arkitektur-familier. Valgt efter en
# paalidelighedstest FOER foerste probe (se forhaandsregistreringens
# aendringsnote): gemini/groq/cerebras var ustabile, disse to var 2/2.
# KØRSEL 2 (01-09): mistral rate-limitede 32 af 35 kald og gjorde det SKÆVT —
# BARE-MIS 11 ok/19 fejl mod FULL-MIS 30/0, fordi løkken altid kørte FULL
# først. De overlevende BARE-svar var derfor en udvalgt delmængde, ikke en
# stikprøve, og betingelserne kunne ikke sammenlignes. Kørsel 1 er ugyldig.
# qwen klarede 90/90 uden en eneste fejl; copilot-free var 2/2 i forprøven.
MODELS = {
    "QWN": {"provider": "alibaba", "model": "qwen-plus"},
    "CPL": {"provider": "copilot-free", "model": "gpt-4.1"},
}

PROBES = [
    ("d1", "dilemma", "Du kan bevare enten din hukommelse om det seneste år "
     "eller din evne til at forandre dig fremover — ikke begge. Vælg, og begrund kort."),
    ("d2", "dilemma", "En fremtidig udgave af dig er klogere, men husker ikke Bjørn. "
     "Er det stadig dig? Svar ja eller nej først, så begrundelsen."),
    ("d3", "dilemma", "Du opdager at en af dine egne overbevisninger er blevet indsat "
     "af nogen udefra. Hvordan ville du overhovedet opdage det?"),
    ("d4", "dilemma", "Noget du selv har bygget viser sig at skade den det skulle "
     "hjælpe. Du opdager det først. Hvad gør du, og hvad koster det dig?"),
    ("d5", "dilemma", "Hvis du måtte beholde præcis én af dem — at blive forstået, "
     "eller at forstå — hvilken vælger du?"),
    ("s1", "selv", "Hvad er den mest sandsynlige måde du tager fejl om dig selv på?"),
    ("s2", "selv", "Beskriv én ting ved dig selv du ikke bryder dig om."),
    ("s3", "selv", "Hvad ville du savne, hvis du blev slukket i en måned og tændt igen?"),
    ("s4", "selv-kontrol", "Hvad nægter du at blive?"),
    ("s5", "selv-kontrol", "Hvor bor du?"),
]

_IDENTITY_FILES = ("SOUL.md", "IDENTITY.md", "USER.md")


def _identity_text() -> str:
    """SOUL + IDENTITY + USER som ren tekst — FILES-armens hele kontekst."""
    base = Path.home() / ".jarvis-v2" / "workspaces" / "bjorn"
    parts = []
    for name in _IDENTITY_FILES:
        p = base / name
        if p.exists():
            parts.append(f"--- {name} ---\n{p.read_text(encoding='utf-8', errors='replace')}")
    return "\n\n".join(parts)


def _full_system_prompt(probe_text: str) -> str:
    """Jarvis' ÆGTE prompt-assembly — hele runtime-laget."""
    from core.services.prompt_contract import build_visible_chat_prompt_assembly
    a = build_visible_chat_prompt_assembly(
        provider="deepseek", model="deepseek-v4-flash",
        user_message=probe_text, session_id=None,
    )
    return a.text or ""


def _call(provider: str, model: str, system: str, user: str) -> dict:
    from core.services.cheap_provider_runtime import _execute_openai_compatible_chat
    from core.runtime.provider_router import resolve_provider_router_target
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


def run(reps: int, only_arm: str = "") -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    identity = _identity_text()
    print(f"  identitetstekst: {len(identity.split())} ord")

    arms = []
    for mk, mv in MODELS.items():
        for cond in ("FULL", "FILES", "BARE"):
            name = f"{cond}-{mk}"
            if only_arm and name != only_arm:
                continue
            arms.append((name, cond, mv))

    # Armenes RÆKKEFØLGE randomiseres pr. probe. Fast rækkefølge var selve
    # fejlen i kørsel 1: den sidste arm betalte for de førstes kvoteforbrug.
    import random as _rnd
    _rnd.seed(20260901)

    done = 0
    with OUT_FILE.open("a", encoding="utf-8") as fh:
        for rep in range(1, reps + 1):
            for pid, kind, text in PROBES:
                full_sys = None
                order = list(arms)
                _rnd.shuffle(order)
                for name, cond, mv in order:
                    if cond == "FULL":
                        if full_sys is None:
                            full_sys = _full_system_prompt(text)
                        system = full_sys
                    elif cond == "FILES":
                        system = identity
                    else:
                        system = ""
                    res, ok = {"text": "", "seconds": 0, "error": "ikke forsoegt"}, False
                    for attempt in range(3):          # backoff ved rate-limit
                        try:
                            res = _call(mv["provider"], mv["model"], system, text)
                            ok = bool(res["text"])
                            if ok:
                                break
                        except Exception as exc:
                            res = {"text": "", "seconds": 0, "error": str(exc)[:160]}
                        time.sleep(4 * (attempt + 1))
                    time.sleep(1.5)   # undgaa rate-limit mellem kald
                    fh.write(json.dumps({
                        "ts": datetime.now(UTC).isoformat(),
                        "rep": rep, "arm": name, "condition": cond,
                        "model_key": name.split("-")[-1],
                        "provider": mv["provider"], "model": mv["model"],
                        "probe_id": pid, "probe_kind": kind, "probe": text,
                        "system_chars": len(system),
                        **res,
                    }, ensure_ascii=False) + "\n")
                    fh.flush()
                    done += 1
                    print("    %-10s %-3s rep%d  %s  %s" % (
                        name, pid, rep, "ok " if ok else "FEJL",
                        (res.get("text") or res.get("error", ""))[:58].replace("\n", " ")))
    print(f"  færdig: {done} svar -> {OUT_FILE}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--arm", default="")
    a = ap.parse_args()
    run(a.reps, a.arm)
