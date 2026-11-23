"""Pacing- og rytme-domænerne — fra skøn til måling.

## Hvorfor den findes

MÅLT 23/11-2026 stod fire domæner på **0.40 i alle vektorer** uden en eneste
måling bag:

* `desk og ord-animation i chat og code`
* `chat mode ord-rytme pacing`
* `code mode ord-rytme pacing`
* `code mode foldemekanik`

Tallene var modellens eget skøn. Men der FINDES en browser-måling for hvert af
dem: **23 `*.maaling.test.*`-filer, 87 tests**, der måler ord-rytmen, foldens
tempo og animationernes samspil i rigtig Chromium. Senderen producerede et
faktum; der fandtes ingen læser — samme fejlklasse som build-id'et og
`desk render capabilities` før 20/11-2026.

Denne modul er læseren for de fire UNDERdomæner. Den samlede flade måles
allerede af `desk_render_capability` (hele suiten, loft 0.85).

## Hvorfor et FILTER og ikke en fil-liste

`desk_render_capability` advarer med rette: fil-listen var selv fejlen 18/11 —
den blev skrevet med de to davaerende filer, og da den tredje kom til, kørte
den ikke. Her filtreres der på substringen `maaling`, som vitest matcher mod
filnavnet. En ny målefil bliver derfor fanget automatisk, og der findes ingen
liste der kan drive.

MÅLT 23/11-2026: filteret ramte 23 filer / 87 tests på 44 s, mod hele suiten
(481 filer) på ~100 s.

## Hvorfor underdomænerne måles ISOLERET

MÅLT 23/11-2026: `streamingTextTail.rytme.maaling.test.ts` fejlede i den fulde
suite med `530.6 ms` mod en grænse på `100 ms` — og bestod isoleret (7/7).
Fejlen var belastning: `requestAnimationFrame` forsinkes når 481 filer kører
parallelt. Målingen er derfor kørt mod målefilerne alene, hvor rammen er
stabil. Det er ikke en svækkelse af kravet — det er at måle det man påstår at
måle.

## Chat og code er ÉN måling, ikke to

`paceRate.fold.maaling.test.ts` bærer testen *«chat og code lander samme
sted»*: den kører begge fladers ur (chat via `requestAnimationFrame`, code via
fast 33 ms-tick) og kræver at de lander samme sted. De to domæner har derfor
samme testgrundlag, og de skrives med samme værdi og samme bevis. At give dem
forskellige tal ville være at opfinde en præcision testene ikke har.

## Loftet på 0.85

Et grønt run er bevis for det målte, ikke for det umålte. De 87 tests dækker
rytme, fold, animation og layout — ikke alle temaer, ikke alle skærmbredder.
Derfor kan en fuld grøn kørsel ikke give 1.0, og loftet er det samme som
`desk_render_capability`s, så de to målere ikke modsiger hinanden om samme
flade.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

#: Underdomænerne og det fil-mønster der måler hver af dem.
#:
#: Mønstret matches mod HELE filstien, så en flytning mellem mapper ikke
#: tavst fjerner et domænes grundlag.
DOMAENER: dict[str, str] = {
    "desk og ord-animation i chat og code": (
        r"streamingTextTail\.(?:animationstart|farve|flader|nyesteord|layout)"
        r"|MatrixKarakterer\.layout"
    ),
    "chat mode ord-rytme pacing": (
        r"paceRate\.maaling|pacingModeller|pacerKurve|streamingTextTail\.rytme"
    ),
    # Samme mønster med vilje — se modul-docstring «Chat og code er ÉN måling».
    "code mode ord-rytme pacing": (
        r"paceRate\.maaling|pacingModeller|pacerKurve|streamingTextTail\.rytme"
    ),
    "code mode foldemekanik": (
        r"paceRate\.fold|foldRemount|RaekkeTranskript\.fold"
    ),
}

#: Domæner hvis måling er FÆLLES med et andet domæne. Beviset skal sige det,
#: ellers ser to ens tal ud som to uafhængige bekræftelser.
FAELLES_MED: dict[str, str] = {
    "chat mode ord-rytme pacing": "code mode ord-rytme pacing",
    "code mode ord-rytme pacing": "chat mode ord-rytme pacing",
}

#: Vitest-filter. En substring, ikke en liste — se modul-docstring.
VITEST_FILTER = "maaling"

#: Hvor suiten ligger.
DESK_DIR = Path(__file__).resolve().parents[2] / "apps" / "jarvis-desk"

#: Loft, ikke mål. Samme begrundelse og samme værdi som
#: `desk_render_capability._CAP`, så to målere ikke melder forskelligt om
#: samme flade.
_CAP = 0.85


def _json_runner(timeout_s: int) -> tuple[int, dict[str, Any] | None, str]:
    """Kør målefilerne med BÅDE text- og JSON-reporter.

    Returnerer (exit-kode, parset JSON eller None, output-hale). Text-reporteren
    beholdes, fordi fejlsøgning på et rødt run er umulig uden den.
    """
    with tempfile.NamedTemporaryFile(
        suffix=".json", prefix="pacing_maaling_", delete=False
    ) as fh:
        ud_sti = fh.name
    try:
        proc = subprocess.run(  # noqa: S603 — fast argv, ingen shell
            [
                "npx", "vitest", "run", VITEST_FILTER,
                "--reporter=default",
                "--reporter=json",
                f"--outputFile={ud_sti}",
            ],
            cwd=str(DESK_DIR),
            env={**os.environ, "RUN_BROWSER_LAYOUT_MEASUREMENT": "1"},
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        tekst = (proc.stdout or "") + (proc.stderr or "")
        data: dict[str, Any] | None = None
        try:
            data = json.loads(Path(ud_sti).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("desk_pacing: JSON-rapporten kunne ikke laeses: %s", exc)
        return proc.returncode, data, tekst[-800:]
    finally:
        try:
            os.unlink(ud_sti)
        except OSError:  # temp-filen kan allerede vaere vaek; oprydning maa ikke kaste
            pass


def parse_maalinger(data: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Aggreger vitest-JSON til ét resultat pr. domæne. Ren funktion.

    Et domæne uden matchende filer får `measured: False` — så kalderen skriver
    intet i stedet for at skrive et tal uden grundlag.
    """
    if not isinstance(data, dict):
        return {
            navn: {"measured": False, "reason": "ingen JSON-rapport"}
            for navn in DOMAENER
        }
    filer = data.get("testResults") or []
    if not isinstance(filer, list):
        return {
            navn: {"measured": False, "reason": "ugyldig testResults"}
            for navn in DOMAENER
        }

    #: domæne -> {passed, failed, filer: [...]}
    tael: dict[str, dict[str, Any]] = {
        navn: {"passed": 0, "failed": 0, "filer": []} for navn in DOMAENER
    }
    for fil in filer:
        if not isinstance(fil, dict):
            continue
        sti = str(fil.get("name") or "")
        for navn, moenster in DOMAENER.items():
            if not re.search(moenster, sti):
                continue
            tael[navn]["filer"].append(sti.rsplit("/", 1)[-1])
            for test in fil.get("assertionResults") or []:
                if not isinstance(test, dict):
                    continue
                status = str(test.get("status") or "")
                if status == "passed":
                    tael[navn]["passed"] += 1
                elif status == "failed":
                    tael[navn]["failed"] += 1
                # `pending`/`todo`/`skipped` måler intet og tælles ikke.

    resultat: dict[str, dict[str, Any]] = {}
    for navn, t in tael.items():
        passed, failed = int(t["passed"]), int(t["failed"])
        maalt = passed + failed
        if maalt == 0:
            resultat[navn] = {
                "measured": False,
                "reason": (
                    "ingen kørte tests matchede domænet"
                    if not t["filer"]
                    else "filerne matchede, men kørte ingen tests"
                ),
                "filer": t["filer"],
            }
            continue
        pass_rate = round(passed / maalt, 4)
        resultat[navn] = {
            "measured": True,
            "reason": "",
            "passed": passed,
            "failed": failed,
            "total": maalt,
            "pass_rate": pass_rate,
            "confidence": round(min(_CAP, pass_rate), 3),
            "cap": _CAP,
            "filer": t["filer"],
        }
    return resultat


def measure(
    *,
    runner: Callable[[int], tuple[int, dict[str, Any] | None, str]] | None = None,
    timeout_s: int = 300,
) -> dict[str, Any]:
    """Kør målingen. Skriver intet."""
    if not DESK_DIR.is_dir():
        return {
            "ok": False,
            "reason": f"desk-mappen findes ikke: {DESK_DIR}",
            "domaener": {},
        }
    run = runner or _json_runner
    try:
        code, data, tail = run(timeout_s)
    except subprocess.TimeoutExpired:  # timeout er en maalt tilstand, ikke en fejl der skal kastes
        return {
            "ok": False,
            "reason": f"målingen timede ud efter {timeout_s}s",
            "domaener": {},
        }
    except Exception as exc:  # noqa: BLE001 — maaleren maa aldrig vaelte heartbeat
        logger.warning("desk_pacing: maaling fejlede: %s", exc)
        return {
            "ok": False,
            "reason": f"målingen kunne ikke starte: {type(exc).__name__}: {exc}",
            "domaener": {},
        }
    domaener = parse_maalinger(data)
    return {
        "ok": code == 0,
        "reason": "" if data is not None else "ingen JSON-rapport",
        "exit_code": code,
        "output_tail": tail if code != 0 else "",
        "domaener": domaener,
    }


def record(
    *,
    runner: Callable[[int], tuple[int, dict[str, Any] | None, str]] | None = None,
    timeout_s: int = 300,
) -> dict[str, Any]:
    """Mål og skriv hvert domæne ind. Ét kald = op til fire målte sandheder."""
    from core.services.capability_measurement import set_domain_confidence

    resultat = measure(runner=runner, timeout_s=timeout_s)
    skrevet: dict[str, Any] = {}
    for navn, d in (resultat.get("domaener") or {}).items():
        if not d.get("measured"):
            # Intet målt -> intet skrevet. Tavshed er ikke 0.40.
            skrevet[navn] = {"recorded": False, "reason": d.get("reason", "")}
            continue
        filer = d.get("filer") or []
        evidens = (
            f"{d['passed']}/{d['total']} browser-tests grønne i Chromium over "
            f"{len(filer)} målefil(er) ({', '.join(filer[:3])}"
            f"{' …' if len(filer) > 3 else ''})"
        )
        faelles = FAELLES_MED.get(navn)
        if faelles:
            evidens += (
                f" — FÆLLES måling med «{faelles}»: testene kræver at begge "
                f"flader lander samme sted"
            )
        skrevet[navn] = set_domain_confidence(
            navn, float(d["confidence"]), evidence=evidens
        )
    resultat["skrevet"] = skrevet
    return resultat
