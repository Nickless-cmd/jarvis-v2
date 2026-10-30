"""Live kill switch for daemon-lanens public-safe-rute.

MÅLT 30/10-2026 (7 dage, ``daemon_output_log``):

    alle daemon-kald .............. 13.495
    ramte betalt Ollama Cloud .....  3.171  (23,5 %)

Synderen var ikke daemon-laget som helhed, men ÉN af dets tre indgange:
``_public_safe_candidates()`` byggede sin pulje af ``ollamafreeapi`` +
``ollama`` — og i praksis indeholdt puljen KUN ollama ``:cloud``-modeller.
Der fandtes ingen gratis gren. ``select_public_safe_cheap_lane_target()``
sorterede endda ``ollama`` bevidst først ("better uptime"), så hver eneste
public-safe-daemon gik på den betalte cloud-model hver gang.

Til sammenligning: ``thought_stream``, som bruger den almindelige
cheap-lane-balancer, ramte betalt i 4 % af sine kald.

``experiential_memory`` alene stod for 2.063 af de 3.171 kald — en
JSON-score-opgave, der kørte på en betalt cloud-model ~295 gange i døgnet.

## Hvad denne switch gør

Den lader public-safe-lanen falde tilbage på den gratis balancer — og lader
os flippe tilbage til Ollama-ruten på under et sekund hvis balanceren ikke
kan holde til presset.

Flaget læses ved HVERT kald (5 sekunders TTL-cache), så en ændring i
``runtime.json`` eller en env-var virker uden genstart. En kill switch der
kræver genstart er ikke en kill switch — den er en beslutning.

    public_safe_free_first() == True   → gratis balancer først (ny adfærd)
    public_safe_free_first() == False  → Ollama-ruten først (gammel adfærd)

Kilder i prioriteret rækkefølge:
  1. env ``JARVIS_PUBLIC_SAFE_FREE_FIRST`` (0/false/off/no → slået fra)
  2. ``runtime.json`` → ``daemon_public_safe_free_first``
  3. default: True

## Sådan flipper du

    python3 -m core.services.daemon_lane_switch off     # tilbage til Ollama
    python3 -m core.services.daemon_lane_switch on      # gratis balancer
    python3 -m core.services.daemon_lane_switch status  # hvad gælder nu

Effekten er øjeblikkelig for nye kald — ingen genstart, ingen deploy.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time

logger = logging.getLogger(__name__)

#: Env-override. Sættes den, vinder den over runtime.json.
KILL_SWITCH_ENV = "JARVIS_PUBLIC_SAFE_FREE_FIRST"

#: Nøglen i ``~/.jarvis-v2/config/runtime.json``.
RUNTIME_KEY = "daemon_public_safe_free_first"

#: Hvor længe en læsning må genbruges. Kort nok til at et flip føles live,
#: langt nok til at 2.500 daglige kald ikke læser filen 2.500 gange.
TTL_SECONDS = 5.0

#: (monotonic_timestamp, value)
_cache: tuple[float, bool] = (0.0, True)

_TRUE = {"1", "true", "yes", "on", "ja"}
_FALSE = {"0", "false", "no", "off", "nej"}


def _som_bool(value: object, *, default: bool) -> bool:
    """Tolk en JSON/env-værdi som bool.

    ``bool("false")`` er ``True`` — og det er præcis den fælde der gør at et
    flag skrevet som streng i runtime.json gør det MODSATTE af hvad der står.
    Derfor parses strenge eksplicit; alt ukendt falder tilbage på default.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
    return default


def _read_live() -> bool:
    """Læs flaget fra env → runtime.json → default. Kaster aldrig."""
    raw = os.getenv(KILL_SWITCH_ENV)
    if raw is not None and str(raw).strip() != "":
        return _som_bool(raw, default=True)
    try:
        from core.runtime.config import SETTINGS_FILE

        if not SETTINGS_FILE.exists():
            return True
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return True
        return _som_bool(data.get(RUNTIME_KEY), default=True)
    except Exception:  # utæt/manglende runtime.json => default (gratis); en kill switch må ikke selv kunne vælte kaldet
        return True


def public_safe_free_first() -> bool:
    """True = public-safe-daemons må bruge den gratis balancer.

    False = kill switch er slået til: de går på Ollama-ruten som før.

    Læses ved hvert kald bag en 5-sekunders cache, så et flip i runtime.json
    eller en env-var rammer nye kald næsten øjeblikkeligt.
    """
    global _cache
    now = time.monotonic()
    stamp, value = _cache
    if now - stamp < TTL_SECONDS:
        return value
    value = _read_live()
    _cache = (now, value)
    return value


def set_public_safe_free_first(enabled: bool) -> dict:
    """Flip flaget i runtime.json (atomisk, med backup) og invalider cachen.

    Returnerer den skrevne værdi så kalderen kan verificere at det landede —
    et flip der ikke kan læses tilbage er ikke et flip.
    """
    global _cache
    from core.runtime.runtime_json_io import write_runtime_merged

    value = bool(enabled)
    merged = write_runtime_merged({RUNTIME_KEY: value})
    _cache = (0.0, value)  # tving næste kald til at læse frisk
    written = merged.get(RUNTIME_KEY)
    logger.warning(
        "daemon-lane kill switch: %s (runtime.json %s=%r)",
        "SLAAET FRA — tilbage paa Ollama-ruten" if not value else "SLAAET TIL — gratis balancer",
        RUNTIME_KEY,
        written,
    )
    return {"runtime_key": RUNTIME_KEY, "written": written, "enabled": value}


def invalidate_cache() -> None:
    """Tving næste ``public_safe_free_first()`` til at læse filen igen."""
    global _cache
    _cache = (0.0, True)


def _main(argv: list[str]) -> int:
    command = (argv[1] if len(argv) > 1 else "status").strip().lower()
    if command in {"off", "0", "false", "disable", "tilbage"}:
        result = set_public_safe_free_first(False)
        print(f"kill switch ENGAGERET — public-safe-daemons gaar paa Ollama-ruten")
        print(f"  {result['runtime_key']} = {result['written']}")
        return 0
    if command in {"on", "1", "true", "enable", "gratis"}:
        result = set_public_safe_free_first(True)
        print(f"kill switch SLIPPET — public-safe-daemons bruger den gratis balancer")
        print(f"  {result['runtime_key']} = {result['written']}")
        return 0
    if command in {"status", "vis"}:
        from core.runtime.config import SETTINGS_FILE

        value = public_safe_free_first()
        print(f"public_safe_free_first = {value}")
        print(f"  betydning : {'gratis balancer foerst' if value else 'OLLAMA foerst (kill switch aktiv)'}")
        print(f"  kilde     : env {KILL_SWITCH_ENV}={os.getenv(KILL_SWITCH_ENV) or '(ikke sat)'}")
        print(f"  fil       : {SETTINGS_FILE}")
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            print(f"  noegle    : {RUNTIME_KEY}={data.get(RUNTIME_KEY, '(ikke sat -> default True)')}")
        except Exception as exc:
            print(f"  noegle    : kunne ikke laeses ({exc})")
        return 0
    print(f"ukendt kommando: {command!r} — brug on | off | status", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
