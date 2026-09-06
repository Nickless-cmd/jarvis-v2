"""Hvor står jeg, og hvordan ser træet ud? — miljø-blok pr. tur.

Porteret fra jarvis-code (`jc_env.py`) 2026-09-06. Runtime havde ingen
modpart: prompten kendte tid, kanal, enheds-tilstedeværelse og rum, men
ingen af de tyve awareness-pladser vidste hvilken mappe han arbejdede i,
hvilken gren han stod på, eller om træet var beskidt.

Det er blevet mere værd i dag. Med checkpoint pr. redigeringsrunde og
operator-kanalen betyder det noget om han står på main, om hans sidste
redigering landede, og om han overhovedet er i et repo.

## Hvorfor den ligger i HALEN

Git-status ændrer sig ved hver eneste redigering. Lå blokken i det stabile
præfiks, ville prefix-cachen brydes på hver tur — og cache-arbejdet er
netop det der har holdt hans svartid nede. Derfor hører den hjemme efter
DYNAMIC-TAIL-markøren, hvor indholdet er volatilt i forvejen.

Den er kort med vilje: gren, renhed, mappe og OS. Ikke en fil-liste. En
`git status` med tredive stier ville koste mere kontekst end den giver
indsigt, og han kan altid selv spørge.

## Kontakt

Bjørn 6/9: «ja, med mulighed for at deaktivere». Tændt som standard, slukkes
med `central_switches.set_enabled("prompt", "env_block", False)`. Modsat
sandboxen, hvor fraværet af et flag skulle betyde slukket, er defaulten her
tændt — og `is_enabled` gør præcis det.

Hvert git-kald er tidsbegrænset og fejler tavst: mangler `git`, er mappen
ikke et repo, eller hænger kaldet, kommer feltet bare tomt tilbage. En
miljø-blok må aldrig kunne forsinke eller vælte en tur.
"""
from __future__ import annotations

import logging
import os
import platform
import subprocess

logger = logging.getLogger(__name__)

_GIT_TIMEOUT_S = 3
_SWITCH = ("prompt", "env_block")


def is_enabled() -> bool:
    try:
        from core.services import central_switches
        return central_switches.is_enabled(*_SWITCH)
    except Exception:
        return True  # default tændt; en cache-fejl må ikke slukke den


def _git(cwd: str, *args: str) -> str | None:
    """Tidsbegrænset git-kald. None ved ENHVER fejl."""
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True,
                           text=True, timeout=_GIT_TIMEOUT_S, check=False)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or "").strip()


def collect_env(cwd: str | None = None) -> dict[str, str]:
    """Saml miljøet. Alle felter er strenge; tomme når de ikke kunne læses."""
    sti = str(cwd or os.getcwd())
    ud: dict[str, str] = {"cwd": sti, "os": f"{platform.system()} {platform.release()}"}
    gren = _git(sti, "rev-parse", "--abbrev-ref", "HEAD")
    if gren is None:
        return ud  # ikke et repo — resten giver ingen mening
    ud["gren"] = gren
    status = _git(sti, "status", "--porcelain")
    if status is not None:
        linjer = [linje for linje in status.splitlines() if linje.strip()]
        ud["renhed"] = "rent" if not linjer else f"{len(linjer)} ændrede filer"
    sidste = _git(sti, "log", "-1", "--format=%h %s")
    if sidste:
        ud["seneste_commit"] = sidste[:100]
    return ud


def render_env_block(cwd: str | None = None) -> str:
    """Én kort blok til halen. Tom streng når slukket eller intet kunne læses."""
    if not is_enabled():
        return ""
    try:
        env = collect_env(cwd)
    except Exception:
        logger.debug("env_block: kunne ikke samle miljø", exc_info=True)
        return ""
    dele = [f"mappe={env.get('cwd', '?')}"]
    if env.get("gren"):
        dele.append(f"gren={env['gren']}")
    if env.get("renhed"):
        dele.append(f"træ={env['renhed']}")
    if env.get("seneste_commit"):
        dele.append(f"seneste={env['seneste_commit']}")
    dele.append(f"os={env.get('os', '?')}")
    return "🖥 HER STÅR DU (serveren, ikke Bjørns maskine): " + " · ".join(dele)
