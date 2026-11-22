"""Brugerdefinerbare tool-hooks som shell-kommandoer.

## Hvorfor shell og ikke Python

Bjørn valgte shell-kommandoer 22/11-2026: «maksimal fleksibilitet». Alternativet
var deklarative JSON-regler (sikkert, men kan kun matche mønstre) eller en ren
observatør (kan aldrig stoppe noget). Prisen for valget er en ny
eksekveringsflade på hvert model-initieret tool-kald, og den pris betales her:

- Argumenterne sendes som **JSON på stdin** og interpoleres ALDRIG ind i
  kommandoen. Et tool-argument kan derfor ikke blive shell-kode.
- Miljøet er **hvidlistet** (`PATH`, `HOME`, `LANG` plus tre egne variable).
  Arvede `DEEPSEEK_API_KEY` og lignende ville ellers ligge i klartekst i en
  shell-hook, som er præcis den flade hooks skal gøre sikrere — ikke større.
- Hver hook har en **hård timeout**; en hængende hook kan ikke lamme et kald.
- Kører indespærret når `bash_sandbox` faktisk kan levere det, uden netværk.
  Kan den ikke, kører hooken uden — samme fail-open som husets bash-vej, men
  rapporteret i `status()` i stedet for fortiet.

## Hvad det koster

Målt 22/11-2026 med den config der ligger i drift (én blokerende `before` på
bash-familien og én `after`-observatør på alt): **10,4 ms ekstra per
tool-kald**, mod 0,2 ms uden hooks. Prisen er processtarten af `sh`, ikke
logikken. En tur med ti tool-kald bliver altså ~100 ms langsommere. Det er
acceptabelt for en vogter, men det er ikke gratis, og en observatør på *alt*
er den dyre halvdel — vil man ned, indsnævres `match` i stedet for at slå
laget fra.

## Kontrakten (Claude Codes semantik, fordi den er kendt)

``before``: exit **2** blokerer kaldet. Enhver anden udfald — 0, 1, crash,
timeout — lader kaldet fortsætte og logges. En hook der går i stykker må ikke
gøre hele systemet ubrugeligt; det er den samme regel som
``tool_lifecycle_hooks`` allerede lover for Python-hooks.

``after``: observatør. Exit-koden læses og logges, men kan intet stoppe —
resultatet er allerede udført.

## Hvor hooks bor

``~/.jarvis-v2/config/tool_hooks.json`` — uden for repoet, som
``ntfy_selfhosted.json``, fordi filen er maskinens konfiguration og ikke
kildens. Uden filen er mekanismen slukket, og det er den ærlige default: et
tomt lag der ikke gør krav på noget.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import subprocess
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_STI = pathlib.Path.home() / ".jarvis-v2" / "config" / "tool_hooks.json"

# Et hook-kald er ikke et sted hvor man skal kunne hente en nøgle.
_ENV_HVIDLISTE = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TMPDIR")
_STANDARD_TIMEOUT_S = 5.0
_MAKS_TIMEOUT_S = 60.0

_load_lock = RLock()
_loaded = False
_hooks: list["ShellHook"] = []
_last_error = ""


@dataclass
class HookResultat:
    """Hvad en enkelt hook-kørsel svarede. Bruges af tests og af status."""

    exit_kode: int | None
    blokerer: bool
    output: str = ""
    fejl: str = ""
    confinement: dict[str, Any] = field(default_factory=dict)


@dataclass
class ShellHook:
    """Én konfigureret hook. Implements ``ToolLifecycleHook`` strukturelt."""

    name: str
    match: re.Pattern[str]
    before: str = ""
    after: str = ""
    timeout_s: float = _STANDARD_TIMEOUT_S
    cwd: str = ""

    # ── matching ────────────────────────────────────────────────────────
    def rammer(self, tool_name: str) -> bool:
        return bool(self.match.search(str(tool_name or "")))

    # ── kørsel ──────────────────────────────────────────────────────────
    def _miljoe(self, *, fase: str, tool_name: str) -> dict[str, str]:
        env = {k: os.environ[k] for k in _ENV_HVIDLISTE if k in os.environ}
        env["JARVIS_TOOL_NAME"] = str(tool_name or "")
        env["JARVIS_HOOK_PHASE"] = fase
        env["JARVIS_HOOK_NAME"] = self.name
        return env

    def _koer(self, kommando: str, *, fase: str, tool_name: str,
              arguments: dict[str, Any]) -> HookResultat:
        if not kommando.strip():
            return HookResultat(exit_kode=0, blokerer=False)

        payload = json.dumps(
            {"tool": tool_name, "phase": fase, "arguments": arguments},
            ensure_ascii=False, default=str,
        )
        cwd = self.cwd or str(pathlib.Path.home())
        argv = ["/bin/sh", "-c", kommando]
        confinement: dict[str, Any] = {"requested": False, "actual": False}
        try:
            from core.services import bash_sandbox

            # Netværk er slået fra: en hook skal inspicere et kald, ikke ringe ud.
            e = bash_sandbox.enforcement(
                kommando, cwd, allow_egress=False, require=False,
            )
            confinement = e.as_dict()
            if e.argv:
                argv = e.argv
        except Exception as exc:  # sandbox er valgfri — hooken skal stadig køre
            logger.debug("tool_hooks: sandbox-afgørelse fejlede: %s", exc)

        try:
            proc = subprocess.run(  # noqa: S603 — argv er en fast liste, ikke en shell-streng
                argv,
                input=payload,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                env=self._miljoe(fase=fase, tool_name=tool_name),
                cwd=cwd if pathlib.Path(cwd).is_dir() else None,
            )
        except subprocess.TimeoutExpired:  # en hængende hook må ikke lamme kaldet
            return HookResultat(
                exit_kode=None, blokerer=False,
                fejl=f"timeout efter {self.timeout_s:.0f}s",
                confinement=confinement,
            )
        except Exception as exc:  # hook-grænse: en defekt hook må ikke dræbe kaldet
            return HookResultat(
                exit_kode=None, blokerer=False, fejl=str(exc),
                confinement=confinement,
            )

        ud = (proc.stdout or "").strip()
        fejl = (proc.stderr or "").strip()
        # Kun exit 2 blokerer. En hook der fejler af andre grunde (manglende
        # værktøj, tastefejl, crash) er en advarsel, ikke en dom over kaldet.
        blokerer = fase == "before" and proc.returncode == 2
        return HookResultat(
            exit_kode=proc.returncode, blokerer=blokerer,
            output=ud[:2000], fejl=fejl[:2000], confinement=confinement,
        )

    # ── protokollen ─────────────────────────────────────────────────────
    def before_tool(self, tool_name: str, arguments: dict[str, Any]):
        from core.services.tool_lifecycle_hooks import HookDecision

        if not self.before or not self.rammer(tool_name):
            return None
        res = self._koer(self.before, fase="before", tool_name=tool_name,
                         arguments=arguments)
        if res.blokerer:
            grund = res.output or f"blokeret af hook '{self.name}'"
            logger.info("tool_hooks: %s blokerede %s — %s", self.name, tool_name, grund)
            return HookDecision.block(grund)
        if res.exit_kode not in (0, None):
            logger.warning(
                "tool_hooks: %s svarede exit %s på %s (kaldet fortsætter): %s",
                self.name, res.exit_kode, tool_name, res.fejl or res.output,
            )
        return None

    def after_tool(self, tool_name: str, arguments: dict[str, Any],
                   result: dict[str, Any]) -> None:
        if not self.after or not self.rammer(tool_name):
            return
        # Resultatet lægges oveni argumenterne, så en observatør kan se udfaldet
        # — men kun som status og størrelse. Hele payloaden må ikke med: en
        # `read_file` af en stor fil ville gøre hver log-linje til en kopi af
        # filens indhold. En log skal være et spor, ikke et arkiv.
        samlet = dict(arguments or {})
        try:
            samlet["__result__"] = {
                "status": str((result or {}).get("status") or ""),
                "bytes": len(json.dumps(result or {}, default=str)),
            }
        except Exception:  # et ubeskriveligt resultat må ikke stoppe observatøren
            samlet["__result__"] = {"status": "?"}
        res = self._koer(self.after, fase="after", tool_name=tool_name,
                         arguments=samlet)
        if res.exit_kode not in (0, None):
            logger.warning(
                "tool_hooks: after-hook %s svarede exit %s på %s: %s",
                self.name, res.exit_kode, tool_name, res.fejl or res.output,
            )


# ── indlæsning ──────────────────────────────────────────────────────────

def _parse(raw: Any) -> tuple[bool, list[ShellHook], str]:
    """Config-dokument → (enabled, hooks, fejl). Kaster aldrig."""
    if not isinstance(raw, dict):
        return False, [], "config er ikke et JSON-objekt"

    enabled = bool(raw.get("enabled") is True)
    hooks: list[ShellHook] = []
    fejl = ""
    for i, item in enumerate(raw.get("hooks") or []):
        if not isinstance(item, dict):
            fejl = f"hook #{i} er ikke et objekt"
            continue
        navn = str(item.get("name") or f"hook-{i}")
        moenster = str(item.get("match") or "")
        if not moenster:
            fejl = f"hook '{navn}' mangler 'match'"
            continue
        try:
            match = re.compile(moenster)
        except re.error as exc:
            fejl = f"hook '{navn}' har ugyldigt regex: {exc}"
            continue
        try:
            timeout = float(item.get("timeout_s") or _STANDARD_TIMEOUT_S)
        except (TypeError, ValueError):
            timeout = _STANDARD_TIMEOUT_S
        hooks.append(ShellHook(
            name=navn,
            match=match,
            before=str(item.get("before") or ""),
            after=str(item.get("after") or ""),
            timeout_s=max(0.1, min(timeout, _MAKS_TIMEOUT_S)),
            cwd=str(item.get("cwd") or ""),
        ))
    return enabled, hooks, fejl


def ensure_loaded(*, tving: bool = False) -> bool:
    """Læs config én gang pr. proces. Returnerer True hvis hooks er aktive.

    Kaldes fra gatewayen, ikke fra et opstartssted: en hook skal virke i enhver
    proces der udfører tool-kald, også en CLI eller en test, uden at nogen
    husker at registrere den. ``tving=True`` genlæser (efter en config-ændring).
    """
    global _loaded, _hooks, _last_error

    with _load_lock:
        if _loaded and not tving:
            return bool(_hooks)

        from core.services import tool_lifecycle_hooks as lifecycle

        if tving:
            for hook in _hooks:
                lifecycle.unregister_hook(hook)
            _hooks = []
            lifecycle.set_enabled(False)

        _loaded = True
        _last_error = ""

        if not CONFIG_STI.is_file():
            return False

        try:
            raw = json.loads(CONFIG_STI.read_text(encoding="utf-8"))
        except Exception as exc:
            _last_error = f"config kunne ikke læses: {exc}"
            logger.warning("tool_hooks: %s", _last_error)
            return False

        enabled, parsed, fejl = _parse(raw)
        if fejl:
            _last_error = fejl
            logger.warning("tool_hooks: %s", fejl)
        if not enabled or not parsed:
            return False

        for hook in parsed:
            lifecycle.register_hook(hook)
        _hooks = parsed
        lifecycle.set_enabled(True)
        logger.info("tool_hooks: %d hook(s) aktive fra %s", len(parsed), CONFIG_STI)
        return True


def status() -> dict[str, Any]:
    """Hvad er indlæst, og hvorfor ikke? Måling i stedet for formodning."""
    from core.services import tool_lifecycle_hooks as lifecycle

    return {
        "config": str(CONFIG_STI),
        "config_findes": CONFIG_STI.is_file(),
        "loaded": _loaded,
        "enabled": lifecycle.is_enabled(),
        "antal": len(_hooks),
        "hooks": [
            {"name": h.name, "match": h.match.pattern, "before": bool(h.before),
             "after": bool(h.after), "timeout_s": h.timeout_s}
            for h in _hooks
        ],
        "fejl": _last_error,
    }


def _nulstil_for_test() -> None:
    """Kun til tests: glem hvad der er indlæst, så en fixture kan styre det."""
    global _loaded, _hooks, _last_error
    from core.services import tool_lifecycle_hooks as lifecycle

    with _load_lock:
        for hook in _hooks:
            lifecycle.unregister_hook(hook)
        _hooks = []
        _loaded = False
        _last_error = ""


__all__ = [
    "CONFIG_STI", "HookResultat", "ShellHook", "ensure_loaded", "status",
]
