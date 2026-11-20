"""Desk render capabilities — fra gæt til måling.

## Hvorfor den findes

MÅLT 20/11-2026: domænet «desk render capabilities» stod på **0.32 i alle
1.000 versioner** af personlighedsvektoren. Tallet var en LLM-formodning.
Intet i Python-koden refererede den browser-måling der FAKTISK findes:
`*.maaling.test.ts` kørt i rigtig Chromium af CI-jobbet `desk-browser`.

Senderen producerede et faktum. Der fandtes ingen læser. Det er samme
fejlklasse som build-id'et (sendt i 26 dage, læst af ingen) og dommerens
400-tegns vindue: en mekanisme hvis indgangsbetingelse ingen opfylder.

Denne modul er læseren. Den kører præcis den kommando huset selv bruger —
`npx vitest run` med `RUN_BROWSER_LAYOUT_MEASUREMENT=1` i `apps/jarvis-desk`,
**hele suiten, ikke en fil-liste**. Fil-listen var selv fejlen 18/11-2026:
den blev skrevet med de to davaerende filer, og da den tredje kom til,
kørte den ikke — jobbet meldte grønt på 2 filer mens den nye stod `3 skipped`.
Uden en liste kan en ny måling ikke glemmes.

## Loftet på 0.85

Et grønt run er bevis for det MÅLTE, ikke for det umålte. Suiten dækker
karakter-figuren, matrix-layoutet, titel-crossfade og ordhalens
layout-stabilitet — ikke markdown, værktøjslinjer eller layout på alle
bredder. Derfor kan en fuld grøn kørsel ikke give 1.0.

## Kadence

Målingen tager ~9 sekunder og kræver node + Chromium, så den kører ikke hvert
tik: `heartbeat_curriculum_cadence.tick_desk_measurement_cadence` starter den i
en baggrundstråd hver `DESK_MEASUREMENT_INTERVAL_SECONDS` (6 t). Uden den kobling
havde `record()` nul produktionskaldesteder, og 0.85 var loftet, ikke en måling.
Manuelt:

    python -c "from core.services.desk_render_capability import record; print(record())"
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

#: Domænenøglen i `confidence_by_domain`. Skal matche curriculum-planens navn,
#: ellers skriver vi til en nøgle ingen læser — samme fejl som build-id'et.
DOMAIN = "desk render capabilities"

#: Hvor suiten ligger. `apps/jarvis-desk` er roden, fordi det er der
#: `package.json` med vitest bor.
DESK_DIR = Path(__file__).resolve().parents[2] / "apps" / "jarvis-desk"

#: Loft, ikke mål: suiten dækker kun figur, matrix, titel-crossfade og ordhale
#: (se modul-docstring «Loftet på 0.85»). Begrundelsen stod i filen fra første
#: commit (git log -S _CAP: kun b2d36b650, merge af 48b6d2f07) — ingen senere
#: ændring; loftet er bevidst og beholdes, og en grøn kørsel måler derfor 0.85.
_CAP = 0.85

#: Vitest' opsummeringslinje. Formen varierer med hvad der skete:
#:   `Tests  9 passed (9)`
#:   `Tests  2 failed | 7 passed (9)`
#:   `Tests  3625 passed | 1 skipped (3626)`
#: MÅLT 20/11-2026: den tredje form knækkede en regex der krævede at «passed»
#: blev efterfulgt af «(». Hele desk-suiten meldte 3625 passed | 1 skipped, og
#: parseren svarede «kunne ikke læse opsummeringen». Målingen var grøn — det var
#: læseren der var blind. Derfor parses DELENE, ikke en fast ordstilling.
_TESTS_LINE_RE = re.compile(r"^\s*Tests\s+(.+?)\((\d+)\)\s*$", re.MULTILINE)
_PART_RE = re.compile(r"(\d+)\s+(failed|passed|skipped|todo)", re.IGNORECASE)
#: `Tests  no tests` — suiten kørte, men målte intet.
_NO_TESTS_RE = re.compile(r"Tests\s+no tests", re.IGNORECASE)


def _standard_runner(timeout_s: int) -> tuple[int, str]:
    """Kør browser-målingerne. Returnerer (exit-kode, samlet output)."""
    env = {"RUN_BROWSER_LAYOUT_MEASUREMENT": "1"}
    proc = subprocess.run(  # noqa: S603 — fast argv, ingen shell
        ["npx", "vitest", "run"],
        cwd=str(DESK_DIR),
        env={**__import__("os").environ, **env},
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def parse_vitest(output: str) -> dict[str, Any]:
    """Læs vitest-opsummeringen. Ren funktion — testbar uden browser."""
    text = str(output or "")
    if _NO_TESTS_RE.search(text):
        return {
            "measured": False,
            "reason": "suiten kørte, men målte intet (no tests)",
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
        }
    linjer = list(_TESTS_LINE_RE.finditer(text))
    if not linjer:
        return {
            "measured": False,
            "reason": "kunne ikke læse vitest-opsummeringen — ingen Tests-linje",
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
        }
    sidste = linjer[-1]  # vitest skriver opsummeringen til sidst
    dele = {
        navn.lower(): int(antal) for antal, navn in _PART_RE.findall(sidste.group(1))
    }
    passed = dele.get("passed", 0)
    failed = dele.get("failed", 0)
    skipped = dele.get("skipped", 0) + dele.get("todo", 0)
    total = int(sidste.group(2))
    if passed + failed <= 0:
        return {
            "measured": False,
            "reason": "opsummeringen indeholdt ingen kørte tests",
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": total,
        }
    return {
        "measured": True,
        "reason": "",
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
    }


def measure(
    *,
    runner: Callable[[int], tuple[int, str]] | None = None,
    timeout_s: int = 300,
) -> dict[str, Any]:
    """Kør målingen og returnér en MÅLT confidence. Skriver intet."""
    run = runner or _standard_runner
    if not DESK_DIR.is_dir():
        return {
            "ok": False,
            "measured": False,
            "reason": f"desk-mappen findes ikke: {DESK_DIR}",
            "domain": DOMAIN,
        }
    try:
        code, output = run(timeout_s)
    except subprocess.TimeoutExpired:  # tidsudloeb ER svaret: intet maalt, ikke en fejl
        return {
            "ok": False,
            "measured": False,
            "reason": f"målingen timede ud efter {timeout_s}s",
            "domain": DOMAIN,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("desk_render_capability: maaling fejlede: %s", exc)
        return {
            "ok": False,
            "measured": False,
            "reason": f"målingen kunne ikke starte: {type(exc).__name__}: {exc}",
            "domain": DOMAIN,
        }

    parsed = parse_vitest(output)
    if not parsed["measured"]:
        return {
            "ok": False,
            "measured": False,
            "reason": parsed["reason"],
            "exit_code": code,
            "output_tail": output[-600:],
            "domain": DOMAIN,
        }

    total = int(parsed["total"])
    passed = int(parsed["passed"])
    failed = int(parsed["failed"])
    # Skippede tests måler intet og må derfor ikke trække raten ned. Målt
    # 20/11-2026: suiten meldte `3625 passed | 1 skipped (3626)`. Regnede man
    # over total, gav en fuldt grøn kørsel 0.9997 i stedet for 1.0 — og et
    # enkelt skip ville ligne en brist i min evne.
    maalt = passed + failed
    pass_rate = round(passed / maalt, 4) if maalt else 0.0
    confidence = round(min(_CAP, pass_rate), 3)
    return {
        "ok": code == 0 and failed == 0,
        "measured": True,
        "domain": DOMAIN,
        "passed": passed,
        "failed": failed,
        "skipped": int(parsed.get("skipped") or 0),
        "total": total,
        "pass_rate": pass_rate,
        "confidence": confidence,
        "cap": _CAP,
        "exit_code": code,
        "output_tail": output[-600:] if code != 0 else "",
    }


def set_domain_confidence(
    domain: str, value: float, *, evidence: str
) -> dict[str, Any]:
    """Sæt domænets confidence til en MÅLT værdi.

    Forskellen fra `task_worker.record_curriculum_outcome` er med vilje:
    den registrering er TRINVIS (+0.05 / −0.03) og bygger på bogholderi —
    «runnet kaldte ét værktøj». Denne sætter den målte værdi direkte, og
    kræver derfor en `evidence`-streng der siger hvad der blev målt.
    """
    from core.runtime.db_cognitive import (
        get_latest_cognitive_personality_vector,
        upsert_cognitive_personality_vector,
    )

    key = " ".join(str(domain or "").lower().split())[:120]
    if not key:
        return {"recorded": False, "reason": "intet domæne"}
    if not str(evidence or "").strip():
        return {"recorded": False, "reason": "målt værdi kræver et bevis"}

    current = get_latest_cognitive_personality_vector() or {}
    try:
        domains = json.loads(str(current.get("confidence_by_domain") or "{}"))
    except ValueError:
        domains = {}
    if not isinstance(domains, dict):
        domains = {}

    existing = next((k for k in domains if str(k).lower().split() == key.split()), None)
    name = existing or key
    before = float(domains.get(name, 0.3))
    after = max(0.0, min(1.0, round(float(value), 3)))
    if existing is not None and after == before:
        return {
            "recorded": False,
            "reason": "uændret",
            "before": before,
            "after": after,
            "evidence": evidence,
        }

    domains[name] = after
    upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps(domains, ensure_ascii=False),
        communication_style=str(current.get("communication_style", "{}")),
        learned_preferences=str(current.get("learned_preferences", "[]")),
        recurring_mistakes=str(current.get("recurring_mistakes", "[]")),
        strengths_discovered=str(current.get("strengths_discovered", "[]")),
        current_bearing=str(current.get("current_bearing", "")),
        emotional_baseline=str(current.get("emotional_baseline", "{}")),
    )
    logger.info(
        "desk_render_capability: %s %s -> %s (%s)", name, before, after, evidence
    )
    return {
        "recorded": True,
        "domain": name,
        "before": before,
        "after": after,
        "evidence": evidence,
    }


def record(
    *,
    runner: Callable[[int], tuple[int, str]] | None = None,
    timeout_s: int = 300,
) -> dict[str, Any]:
    """Mål og skriv resultatet ind i domænet. Ét kald = én målt sandhed."""
    result = measure(runner=runner, timeout_s=timeout_s)
    if not result.get("measured"):
        return result  # intet målt -> intet skrevet. Tavshed er ikke 0.32.
    evidence = (
        f"{result['passed']}/{result['total']} browser-målinger grønne i rigtig "
        f"Chromium (npx vitest run, RUN_BROWSER_LAYOUT_MEASUREMENT=1)"
    )
    result["record"] = set_domain_confidence(
        DOMAIN, float(result["confidence"]), evidence=evidence
    )
    return result
