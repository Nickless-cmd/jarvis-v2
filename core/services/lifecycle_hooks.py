"""Livscyklus-hooks server-side — paritet med jarvis-code.

jarvis-code har ni hooks omkring en tur (`src/hooks.py`); runtimen har NUL.
Dens `runtime_hooks.py` hedder det samme men er noget andet: eventbus-dispatch
af `heartbeat.tick_completed` og to soeskende. Der var altsaa ingen maade at
haenge sin egen adfaerd paa en tur server-side.

**Hvorfor det kunne bygges NU og ikke foer.** jarvis-codes hooks er klient-side
fordi typen `command` koerer et shell-script LOKALT — og i et server-loop er
"lokalt" containeren, ikke Bjoerns maskine. Det er den begraensning der holdt
hooks paa klienten. Men `operator_bash` staar nu paa 1,2 % fejl over 10.163
kald (mest brugte vaerktoej i systemet), saa en command-hook KAN naa hans
maskine paalideligt. Derfor `where: "operator"`.

**Kontrakten er jarvis-codes, ordret:** en hook svarer
``{action: allow|block|inject, message, context}``. `block` stopper handlingen,
`inject` haefter tekst paa konteksten, `allow` lader den gaa.

**Vi fyrer KUN de haendelser vi kan honorere.** En `PreToolUse` der svarer
"block" og bliver ignoreret er vaerre end ingen hook: den ser ud til at virke.
Se `WIRED_EVENTS` for hvad der faktisk er koblet, og modulets test for hvorfor
resten ikke er det endnu.

Kernen er REN (ingen I/O) saa den kan testes uden en tur; I/O ligger i kanten.
Self-safe hele vejen: en hook maa aldrig braekke et run.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
from pathlib import Path
from typing import Any

# jarvis-codes taxonomi, ordret — saa en hooks.json kan flyttes uden omskrivning.
HOOK_EVENTS: tuple[str, ...] = (
    "SessionStart", "SessionEnd", "UserPromptSubmit",
    "PreToolUse", "PostToolUse", "Stop", "PreCompact",
    "SubagentStop", "Notification",
)

# Hvad der FAKTISK er koblet i det synlige loop lige nu. Alt andet kan
# konfigureres men fyrer ikke — og det skal staa her, ikke i en TODO.
# `UserPromptSubmit` koblet 5/9: begge domme kan honoreres dér — `block`
# afslutter turen, `inject` haefter kontekst paa foer prompt-assembly.
WIRED_EVENTS: frozenset[str] = frozenset({"UserPromptSubmit"})

_ALLOW: dict[str, Any] = {"action": "allow", "message": "", "context": None}


def _allow(context: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"action": "allow", "message": "", "context": context}


# ── Ren kerne ────────────────────────────────────────────────────────────

def matcher_matches(matcher: str, tool_name: str, command: str = "") -> bool:
    """Rammer et matcher-moenster dette tool-kald? Ren.

    Understoetter jarvis-codes fire former:
      ``*``             alt
      ``A|B|C``         OR af tool-navne
      ``Tool(glob)``    tool == Tool OG kommandoen matcher glob
      ``Tool(/regex/)`` tool == Tool OG kommandoen matcher regex
      ``Tool``          eksakt navn

    Fail-OPEN ved uforstaaeligt moenster: hook'en faar lov at koere og svare
    selv. Et moenster man har skrevet forkert skal give stoej, ikke tavshed.
    """
    try:
        m = (matcher or "*").strip()
        if m == "*" or m == tool_name:
            return True
        if "|" in m and "(" not in m:
            return tool_name in {p.strip() for p in m.split("|")}
        got = re.match(r"^([A-Za-z_]\w*)\((.*)\)$", m)
        if got:
            tool, pattern = got.group(1), got.group(2)
            if tool != tool_name:
                return False
            if pattern.startswith("/") and pattern.endswith("/") and len(pattern) > 1:
                return bool(re.search(pattern[1:-1], command or ""))
            return fnmatch.fnmatch(command or "", pattern)
        # Et almindeligt navn er en GENKENDT form — mismatch er et aegte nej.
        if re.fullmatch(r"[A-Za-z_]\w*", m):
            return False
        # Alt andet er et moenster vi ikke forstod. Fail-OPEN: hook'en koerer og
        # svarer selv. Et moenster man har skrevet forkert skal give stoej, ikke
        # tavshed — ellers fejler hook'en lydloest og man tror den virker.
        return True
    except Exception:
        return True


def decide(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Saml flere hook-svar til ét. Ren.

    **Block vinder.** Naar ét vaern siger nej, er svaret nej — ellers ville
    raekkefoelgen i en config afgoere sikkerheden. Injektioner fra alle hooks
    samles, saa to hooks kan bidrage hver sit uden at overskrive hinanden.
    """
    besked: list[str] = []
    ctx: dict[str, Any] | None = None
    blokeret = False
    for r in results or []:
        if not isinstance(r, dict):
            continue
        handling = str(r.get("action") or "allow")
        m = str(r.get("message") or "").strip()
        if r.get("context"):
            ctx = dict(r["context"])
        if handling == "block":
            blokeret = True
            if m:
                besked.append(m)
        elif handling == "inject" and m:
            besked.append(m)
    if blokeret:
        return {"action": "block", "message": "\n".join(besked), "context": ctx}
    if besked:
        return {"action": "inject", "message": "\n".join(besked), "context": ctx}
    return _allow(ctx)


# ── I/O-kant ─────────────────────────────────────────────────────────────

def config_path() -> Path:
    """`~/.jarvis-v2/config/hooks.json` — config er runtimens sandhed for
    governance-indstillinger (se CLAUDE.md's kilde-til-sandhed)."""
    home = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(home) / "config" / "hooks.json"


def load_hooks() -> dict[str, list[dict[str, Any]]]:
    """{haendelse: [hook, ...]}. Self-safe → tomt."""
    try:
        p = config_path()
        if not p.exists():
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        hooks = data.get("hooks", data)
        if not isinstance(hooks, dict):
            return {}
        return {k: v for k, v in hooks.items()
                if k in HOOK_EVENTS and isinstance(v, list)}
    except Exception:
        return {}


def hooks_for(event: str) -> list[dict[str, Any]]:
    """Konfigurerede hooks for én haendelse. Self-safe → tom liste."""
    try:
        return [h for h in (load_hooks().get(event) or []) if isinstance(h, dict)]
    except Exception:
        return []


def _run_command_hook(hook: dict[str, Any], context: dict[str, Any],
                      user_id: str = "") -> dict[str, Any]:
    """Koer et shell-script med kontekst paa stdin. Exit 2 = block (jarvis-codes
    konvention), alt andet = allow; stdout bliver til en injektion.

    `where` afgoer HVOR:
      ``operator``  paa Bjoerns maskine via operator_bash — det var netop den
                    vej der ikke fandtes da jarvis-code blev bygget.
      ``container`` i runtimens egen container (default: ingen bro-afhaengighed).
    """
    cmd = str(hook.get("command") or "").strip()
    if not cmd:
        return _allow()
    hvor = str(hook.get("where") or "container").strip().lower()
    nyttelast = json.dumps(context, ensure_ascii=False)
    timeout = float(hook.get("timeout_s") or 20.0)

    if hvor == "operator":
        try:
            import asyncio

            from core.tools.operator_tools import operator_bash_async
            # Konteksten gaar ind som miljoevariabel frem for stdin: bro-kaldet
            # tager en kommandostreng, ikke en aaben pipe.
            wrapped = f"JARVIS_HOOK_CONTEXT={json.dumps(nyttelast)} {cmd}"
            res = asyncio.run(operator_bash_async(
                command=wrapped, user_id=user_id, timeout_s=timeout))
            kode = int((res or {}).get("exit_code") or 0)
            ud = str((res or {}).get("stdout") or "").strip()
        except Exception as exc:
            # En doed bro maa ikke blokere en tur.
            return {"action": "allow", "message": f"hook-bro fejlede: {exc}"[:200],
                    "context": None}
    else:
        try:
            import subprocess
            p = subprocess.run(["/bin/sh", "-c", cmd], input=nyttelast, text=True,
                               capture_output=True, timeout=timeout)
            kode, ud = p.returncode, (p.stdout or "").strip()
        except Exception as exc:
            return {"action": "allow", "message": f"hook fejlede: {exc}"[:200],
                    "context": None}

    if kode == 2:
        return {"action": "block", "message": ud or "blokeret af hook", "context": None}
    return {"action": "inject", "message": ud, "context": None} if ud else _allow()


def _run_http_hook(hook: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """POST konteksten; svarets `action`/`message` gaelder. Self-safe → allow."""
    url = str(hook.get("url") or "").strip()
    if not url:
        return _allow()
    try:
        import urllib.request
        req = urllib.request.Request(
            url, data=json.dumps(context, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=float(hook.get("timeout_s") or 10.0)) as r:
            svar = json.loads((r.read() or b"{}").decode("utf-8") or "{}")
        if not isinstance(svar, dict):
            return _allow()
        handling = str(svar.get("action") or "allow")
        if handling not in ("allow", "block", "inject"):
            handling = "allow"
        return {"action": handling, "message": str(svar.get("message") or ""),
                "context": svar.get("context")}
    except Exception:
        return _allow()


def run_hook(event: str, hook: dict[str, Any], context: dict[str, Any],
             user_id: str = "") -> dict[str, Any]:
    """Koer ÉN hook. Self-safe → allow."""
    try:
        if event in ("PreToolUse", "PostToolUse"):
            if not matcher_matches(str(hook.get("matcher") or "*"),
                                   str(context.get("tool") or ""),
                                   str(context.get("command") or "")):
                return _allow()
        art = str(hook.get("type") or "command").lower()
        if art == "command":
            return _run_command_hook(hook, context, user_id=user_id)
        if art == "http":
            return _run_http_hook(hook, context)
        return _allow()
    except Exception:
        return _allow()


def fire(event: str, context: dict[str, Any], user_id: str = "") -> dict[str, Any]:
    """Fyr alle hooks for en haendelse og saml dommen. Self-safe → allow.

    Ingen konfigurerede hooks → allow uden at have roert noget. Det er den
    almindelige vej, og den skal vaere gratis.
    """
    try:
        konfigurerede = hooks_for(event)
        if not konfigurerede:
            return _allow()
        return decide([run_hook(event, h, context, user_id=user_id)
                       for h in konfigurerede])
    except Exception:
        return _allow()
