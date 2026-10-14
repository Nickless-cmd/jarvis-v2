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

13/10-2026 — UDVIDET, fordi den foerste version draebte en anden session.
Bjoern: «den der checker om turen er slut foer genstart udvides.. du draebte
lige en anden session.» Den foerste version ventede KUN paa det run der bad om
genstarten. Men en genstart draeber ALLE koersler, ikke kun mit eget: i det
oejeblik mit run doede, faldt vagten — ogsaa selv om en anden session var midt
i en tur. Nu er betingelsen «MIT run er doedt OG ingen ANDRE koersler lever».

Er der stadig nogen i gang naar vinduet lober ud, genstarter vi IKKE. En
udskudt genstart er en gene; en draebt tur er et tab. Se `_afbryd`.

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
# 30 min, ikke 15 (13/10-2026). Loftet rammes nu ogsaa naar en ANDEN session
# koerer — og en session kan sagtens tage tyve minutter. Naar noget andet lever,
# ABBRYDER vi ved loftet (se `_afbryd`); et for kort vindue ville altsaa goere en
# helt normal anden tur til en afbrudt genstart. For mit EGET run betyder loftet
# intet: er det doedt, gaar vi videre med det samme.
MAX_WAIT_S = 1800.0
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


def _andre_lever(egen_run_id: str) -> str:
    """Run-id for et ANDET levende run — "" hvis ingen, "?" hvis vi ikke ved det.

    Bjoern 13/10-2026: «den der checker om turen er slut foer genstart
    udvides.. du draebte lige en anden session.» Den foerste version ventede
    KUN paa det run der bad om genstarten — men genstarten draeber ALLE
    koersler. I det oejeblik mit run doede, faldt vagten, og en anden session
    midt i en tur blev revet med.

    Kilden er den DELTE aktiv-tilstand, den SAMME som `is_visible_run_alive`
    bygger paa — og vi genbruger dens dom i stedet for at skrive en anden.
    Tilstanden baerer ÉT run ad gangen: det der koerer NU. Det er nok, fordi
    genstarten kun skal vide om der er NOGEN at draebe.

    Den daekker baade chat-sessioner og autonome runs: autonome runs rydder
    selv tilstanden naar de er faerdige (`autonomous_stream_run.py:205`), og
    det er beviset for at de ogsaa saetter den.

    "?" betyder «ved det ikke», og kalderen venter. Hellere sent end midt i
    en tur.
    """
    try:
        from core.services.visible_runs import is_visible_run_alive
        from core.services.visible_runs_sections.run_control_state import (
            _get_active_visible_run_state,
        )
    except Exception:
        logger.warning("deferred_restart: kan ikke importere aktiv-tilstanden",
                       exc_info=True)
        return "?"
    try:
        state = _get_active_visible_run_state() or {}
    except Exception:
        logger.warning("deferred_restart: kunne ikke laese aktiv-tilstanden",
                       exc_info=True)
        return "?"
    rid = str(state.get("run_id") or "")
    if not rid or rid == str(egen_run_id or ""):
        return ""
    try:
        return rid if is_visible_run_alive(rid) else ""
    except Exception:
        logger.warning("deferred_restart: kunne ikke doemme run %s", rid[:12],
                       exc_info=True)
        return "?"


def wait_for_idle(run_id: str, *, margin_s: float = DEFAULT_MARGIN_S) -> tuple[float, str]:
    """Vent til MIT run er doedt OG ingen andre koersler lever.

    Returnerer ``(sekunder_ventet, grund)``. ``grund`` er "" naar det er
    sikkert at genstarte; ellers en kort forklaring paa hvad der stadig koerer.
    """
    start = time.monotonic()
    while time.monotonic() - start < MAX_WAIT_S:
        if not _run_is_alive(run_id) and _andre_lever(run_id) == "":
            # Margin: race-vinduet mellem svaret i chat_messages og
            # outcome-raekken i visible_runs er maalt til 1-15 s. 5 s oveni
            # doeds-tidspunktet er nok.
            time.sleep(max(0.0, float(margin_s)))
            return time.monotonic() - start, ""
        time.sleep(POLL_INTERVAL_S)

    # Vinduet lob ud. HVAD staar i vejen? Raekkefoelgen er med vilje: mit eget
    # run foerst, for det er den oprindelige grund til at vente.
    if _run_is_alive(run_id):
        return time.monotonic() - start, f"eget run {run_id[:12]} lever stadig"
    andre = _andre_lever(run_id)
    if andre == "?":
        return time.monotonic() - start, "kunne ikke laese run-tilstanden"
    if andre:
        return time.monotonic() - start, f"run {andre[:12]} koerer stadig"
    # Intet i vejen alligevel (kilden blev laesbar i sidste oejeblik) — koer.
    time.sleep(max(0.0, float(margin_s)))
    return time.monotonic() - start, ""


def _afbryd(waited: float, grund: str, run_id: str) -> None:
    """Genstarten blev UDSKUDT — ikke udfoert. Sig det hoejt, og ryd op.

    To ting skal ske, og begge er noedvendige:

    1. Den ventende bekræftelses-fil SLETTES. `restart_self` skriver den FOER
       scriptet startes, og ved naeste api-opstart sender den «genstart
       gennemfoert». Bliver den liggende, lyver den — der skete ingen genstart.
    2. Det skal kunne SES. Indbakken er den flade Bjoern og jeg begge laeser,
       og samme sted som run-closure-gatens beskeder lander nu.
    """
    try:
        from core.tools.restart_self_tools import PENDING_RESTART_FILE
        PENDING_RESTART_FILE.unlink(missing_ok=True)
    except Exception:
        logger.warning("deferred_restart: kunne ikke slette den ventende fil",
                       exc_info=True)
    try:
        from core.services.inbox_state import _ejer_id, registrer_kilde
        bruger = _ejer_id()
        if bruger:
            registrer_kilde(
                bruger_id=bruger,
                kildetype="genstart",
                kilde_id=f"udskudt-{run_id or 'ukendt'}",
                oprettende_run_id=run_id,
                paastaaet_ejer="huset",
                beskrivelse=(
                    f"Genstart UDSKUDT efter {waited:.0f}s — {grund}. "
                    "Jeg genstarter ikke mens en anden session koerer. "
                    "Sig til, saa proever jeg igen."
                ),
            )
    except Exception:
        logger.warning("deferred_restart: kunne ikke skrive til indbakken",
                       exc_info=True)
    print(f"deferred_restart: UDSKUDT efter {waited:.0f}s — {grund}. Ingen genstart.")



def main(argv: list[str]) -> int:
    run_id = argv[1] if len(argv) > 1 else ""
    services = [s for s in (argv[2].split(",") if len(argv) > 2 else []) if s]
    margin = float(argv[3]) if len(argv) > 3 else DEFAULT_MARGIN_S
    if not services:
        services = ["jarvis-api", "jarvis-runtime"]

    waited, grund = wait_for_idle(run_id, margin_s=margin)
    if grund:
        # Der koerer stadig noget. Vi genstarter IKKE — en draebt tur er
        # dyrere end en udskudt genstart.
        _afbryd(waited, grund, run_id)
        return 2

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
