"""Udskudt genstart — vent til turen er SLUT, genstart saa.

Baggrund (3/10-2026): `restart_self` har en fast `sleep 3`. Kaldes den midt i
en tur, draeber den turen; runnet stemples `interrupted` og genoptages senere
af recovery-dispatcheren — hvilket giver Bjoern TO svar paa én besked (maalt
3/10 kl. 15:43). Kaldes den uden `force`, afviser den naar turen lever, og jeg
endte med at skrive systemd-timer-kommandoen i haanden tre gange paa én dag —
én gang med et tal der naesten draebte turen.

Dette script fjerner gaetteriet: i stedet for et antal sekunder venter det paa
et FAKTUM — at runnet ikke laengere er i live — og genstarter saa.

Fakta-kilden er `is_visible_run_alive()` (visible_runs), som modulet selv
kalder «den AUTORITATIVE liveness-test — CROSS-PROCES»: den laeser
`last_activity_at` fra den DELTE tilstand, som et levende run toucher hvert
par sekunder, med en stale-taerskel paa 75 sekunder.

Derfor: scriptet venter til runnet er dødt (<=75 s efter turen svarede), leegger
en margin oveni, og genstarter. Ingen gae t, ingen afbrudt tur, intet
dublet-svar.

Kaldes detached fra `restart_self` med `defer_until_idle=true`. Kan ogsaa
koeres i haanden:

    python3 scripts/deferred_restart.py <run_id> jarvis-api,jarvis-runtime

Self-safe: kan run-tilstanden ikke laeses, venter vi hele max-vinduet ud
(hellere sent end midt i en tur).
"""
from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 3.0
MAX_WAIT_S = 900.0  # 15 min — saa er turen enten slut eller laenge vaek
DEFAULT_MARGIN_S = 5.0


def _run_is_alive(run_id: str) -> bool:
    """True hvis runnet lever. Kan kilden ikke laeses, svarer vi True (vent)."""
    if not run_id:
        return False
    try:
        from core.services.visible_runs import is_visible_run_alive
    except Exception:  # importvejen fejler kun hvis repoet er i stykker — så vent
        logger.warning("deferred_restart: kan ikke importere liveness-kilden",
                       exc_info=True)
        return True
    try:
        return bool(is_visible_run_alive(run_id))
    except Exception:  # ukendt tilstand → hellere vente end at draebe en levende tur
        logger.warning("deferred_restart: kunne ikke laese run-tilstand for %s",
                       run_id, exc_info=True)
        return True


def wait_for_idle(run_id: str, *, margin_s: float = DEFAULT_MARGIN_S) -> float:
    """Vent til runnet er doedt + margin. Returnerer sekunder ventet."""
    start = time.monotonic()
    while time.monotonic() - start < MAX_WAIT_S:
        if not _run_is_alive(run_id):
            break
        time.sleep(POLL_INTERVAL_S)
    # Margin: race-vinduet mellem svaret i chat_messages og outcome-raekken i
    # visible_runs er maalt til 1-15 s. 5 s oveni doeds-tidspunktet er nok.
    time.sleep(max(0.0, float(margin_s)))
    return time.monotonic() - start


def main(argv: list[str]) -> int:
    run_id = argv[1] if len(argv) > 1 else ""
    services = [s for s in (argv[2].split(",") if len(argv) > 2 else []) if s]
    margin = float(argv[3]) if len(argv) > 3 else DEFAULT_MARGIN_S
    if not services:
        services = ["jarvis-api", "jarvis-runtime"]

    waited = wait_for_idle(run_id, margin_s=margin)

    failures: list[str] = []
    for svc in services:
        try:
            res = subprocess.run(
                ["sudo", "systemctl", "restart", svc],
                capture_output=True, text=True, timeout=90,
            )
            if res.returncode != 0:
                failures.append(f"{svc}: {res.stderr.strip()[:200]}")
        except Exception as exc:  # pragma: no cover - miljoe-afhaengig
            failures.append(f"{svc}: {exc}")

    if failures:
        print(f"deferred_restart: ventede {waited:.0f}s — FEJL: {'; '.join(failures)}")
        return 1
    print(f"deferred_restart: ventede {waited:.0f}s — genstartede {', '.join(services)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
