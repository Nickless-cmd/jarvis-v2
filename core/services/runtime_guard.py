"""Vagt: rejs `jarvis-runtime` når den er død.

## Hullet, målt 18/10-2026

Runtime lå død i **55 minutter** (19:32:47 → 20:28:05) uden at nogen rejste
den. Bjørn opdagede det, ikke systemet. Tre ting gjorde det muligt, alle målt:

1. **Begge units har `Restart=on-failure`.** En pæn SIGTERM giver exit 0, og
   systemd genstarter derfor *aldrig* en frivilligt stoppet service. Det var
   ikke et crash — journalen viser `Deactivated successfully`, 31/31
   nedlukningstrin, 2,07 s.
2. **`/health` på 8080 svarede `ok` hele tiden.** API og runtime er to
   services på to porte, og API'ets svar er ikke bevis på at hjertet slår.
   Derfor kunne hele samtalen køre videre oven på en død runtime.
3. **Der fandtes ingen vagt.** Fem `jarvis-*`-timers kørte (memtrack,
   cutoff-detector, mem-guard, model-sweep, account2-v6) — ingen af dem
   spurgte om runtime levede.

## Hvorfor vagten ikke bor i runtime

Det er den vigtigste arkitektur-beslutning her. En vagt inde i runtime's eget
heartbeat kan pr. definition ikke rejse runtime når runtime er død. Den skal
køre **udenfor**, som en systemd-timer. Alt nedenfor er derfor ren logik der
kan kaldes fra en oneshot-service, ikke fra et heartbeat-tick.

## Fire tilstande, ikke to

`aktiv` og `sund` er ikke det samme, og forskellen er farlig:

| systemd | port 8011 | betydning | handling |
|---|---|---|---|
| active | svarer | sund | intet |
| inactive | intet svar | død | **start** |
| active | intet svar | hængt proces | **restart** |
| inactive | svarer | nogen ANDEN holder porten | **blind** — ingen handling |

Den sidste række er den vigtige. Svarer porten men systemd siger «ikke aktiv»,
så er det ikke vores runtime der svarer — og at starte en ny ville enten fejle
på portkollision eller give to processer der kæmper om samme port. Vi ved det
ikke, og så gætter vi ikke: vi melder blindhed. Samme kontrakt som
`ci_status_watch` (rate-limit er blindhed, ikke sundhed).

## Rate-limit: en vagt der selv bliver problemet

Rejser den tre gange inden for 30 minutter uden at tilstanden holder, stopper
den og melder det i stedet. En vagt der genstarter i ring er værre end ingen
vagt — den skjuler årsagen og brænder CPU. Grænsen er målt mod den konkrete
fejl: en enkelt genstart tog 6 sekunder (20:28:00 → 20:28:06), så tre forsøg
inden for 30 minutter er rigelig luft til en ægte hikke og alt for lidt til en
genstarts-loop.

## Loggen har altid en STARTLINJE

Hver kørsel skriver én linje, også når alt er i orden. En 0-byte log kan ikke
skelne «aldrig kørt» fra «dræbt undervejs» fra «venter stadig» — den skelnen
er hele pointen med en vagt, så loggen må ikke være tavs når den er rask.
"""
from __future__ import annotations

import json
import logging
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Runtime'ens port. API'et er 8080 og siger intet om denne.
PORT = 8011
SERVICE = "jarvis-runtime"

#: Hvor længe vi venter på at en rejst service svarer, før vi kalder det fejl.
START_VENT_SEKUNDER = 25

#: Hvor mange rejs-forsøg der må ske inden for vinduet før vagten giver op.
MAKS_FORSOEG = 3
FORSOEG_VINDUE = timedelta(minutes=30)

#: Én notifikation pr. tilstand pr. dette interval. Uden den ville en vedvarende
#: fejl ringe på Bjørns telefon hvert minut.
VARSEL_COOLDOWN = timedelta(minutes=15)

#: Loggen ligger under `~/.jarvis-v2/logs/` og ikke i `/var/log`, fordi vagten
#: kører som `bs` — og det SKAL den: `ntfy_gateway._load_config()` og
#: `Path.home()` peger på Bjørns config, så en root-proces ville lede efter
#: `/root/.jarvis-v2/config/runtime.json`, ikke finde den, og tie stille om
#: at den ikke kunne varsle. Målt 18/10-2026: første udgave skrev til
#: `/var/log` og fik `Permission denied` — vagten kørte, men efterlod ingen
#: spor, hvilket er præcis den tavshed en vagt ikke må have.
_LOG_STI = Path.home() / ".jarvis-v2" / "logs" / "runtime-guard.log"
_STATE_STI = Path.home() / ".jarvis-v2" / "state" / "runtime_guard.json"


def _nu() -> datetime:
    return datetime.now(UTC)


def probe_health(port: int = PORT, timeout: float = 3.0) -> bool:
    """Svarer runtime'ens `/health`? Netværksfejl betyder NEJ, ikke «ved det ikke».

    Vi spørger bevidst det samme endpoint som `restart_self`'s smoke-test gør.
    En proces der kører men ikke svarer er præcis den tilstand en
    `Restart=on-failure` aldrig fanger.
    """
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/health", timeout=timeout
        ) as svar:
            return svar.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):  # porten er LUKKET — det er et svar, ikke en fejl der må kaste
        return False


def systemd_tilstand(service: str = SERVICE) -> str:
    """`active`, `inactive`, `activating`, `deactivating` eller `unknown`.

    `activating`/`deactivating` er ikke «død» — det er en planlagt overgang, og
    vagten må ikke blande sig. Målt 18/10-2026: en genstart af runtime tager
    ~6 sekunder, så et minut-interval rammer det vindue jævnligt.
    """
    try:
        svar = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True, timeout=10, check=False,
        )
        tekst = (svar.stdout or "").strip()
        return tekst or "unknown"
    except (OSError, subprocess.SubprocessError):  # kan vi ikke SPØRGE systemd, er svaret ukendt — ikke «død», så vagten venter
        return "unknown"


def beslut(aktiv: str, sund: bool) -> str:
    """Ren beslutningsfunktion — ingen I/O, så den kan testes uden systemd.

    Returnerer en af: ``ok``, ``start``, ``restart``, ``blind``, ``vent``.
    """
    aktiv_norm = (aktiv or "unknown").strip().lower()

    # En planlagt overgang er ikke en fejl. Vent til næste tick.
    if aktiv_norm in {"activating", "deactivating", "reloading"}:
        return "vent"

    if aktiv_norm == "active":
        return "ok" if sund else "restart"

    if aktiv_norm == "inactive":
        # Porten svarer, men systemd siger at vores service ikke kører. Så er
        # det en ANDEN proces der holder porten. Vi gætter ikke.
        return "blind" if sund else "start"

    # failed / unknown: vi kan ikke læse tilstanden. Behandl som død, men
    # `unknown` fra en manglende systemctl er blindhed, ikke et svar.
    if aktiv_norm == "failed":
        return "start"
    return "blind"


def _laes_state() -> dict[str, Any]:
    try:
        return json.loads(_STATE_STI.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # manglende eller korrupt state er en FØRSTE kørsel — tomt bogholderi, ikke en fejl
        return {}


def _skriv_state(state: dict[str, Any]) -> None:
    try:
        _STATE_STI.parent.mkdir(parents=True, exist_ok=True)
        _STATE_STI.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError as exc:
        # Bevidst ikke fatal: en vagt der ikke kan gemme sin bogholderi skal
        # stadig kunne rejse runtime. Men den skal sige det.
        logger.warning("runtime_guard: kunne ikke skrive state: %s", exc)


def _log(linje: str) -> None:
    """Skriv ALTID en linje — også ved «alt er fint»."""
    tekst = f"{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')} {linje}\n"
    try:
        _LOG_STI.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_STI.open("a", encoding="utf-8") as fh:
            fh.write(tekst)
    except OSError as exc:
        # Kan loggen ikke skrives, er det stadig ikke en grund til at lade
        # runtime ligge død. Men fejlen skal ud i journalen, ikke forsvinde.
        logger.warning("runtime_guard: kunne ikke skrive log (%s): %s", _LOG_STI, exc)
    logger.info("runtime-guard: %s", linje.rstrip())


def _varsl(besked: str, titel: str, *, state: dict[str, Any], noegle: str) -> bool:
    """Send til Bjørns telefon — men ikke oftere end cooldown tillader.

    Går gennem `ntfy_gateway.send_notification`, som er den ægte port: den
    læser server/topic/token fra runtime.json og sætter User-Agent (uden den
    afviser Cloudflare med error 1010 — målt to gange, ntfy og mcp.exa.ai).
    """
    nu = _nu()
    sidst_tekst = str(state.get(f"varsel_{noegle}") or "")
    if sidst_tekst:
        try:
            sidst = datetime.fromisoformat(sidst_tekst)
            if nu - sidst < VARSEL_COOLDOWN:
                return False
        except ValueError:  # et utæt tidsstempel betyder «vi ved ikke hvornår» — så varsler vi frem for at tie
            pass
    try:
        from core.services.ntfy_gateway import send_notification

        send_notification(besked, title=titel, priority="high", tags=["wrench"])
        state[f"varsel_{noegle}"] = nu.isoformat()
        return True
    except Exception as exc:  # porten må ikke kunne vælte vagten
        logger.warning("runtime_guard: kunne ikke varsle: %s", exc)
        return False


def _rejs(handling: str, service: str = SERVICE) -> tuple[bool, str]:
    """Kør systemctl. `sudo -n` fordi oneshot-servicen ikke må hænge på en prompt."""
    verb = "start" if handling == "start" else "restart"
    try:
        svar = subprocess.run(
            ["sudo", "-n", "systemctl", verb, service],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if svar.returncode != 0:
            fejl = (svar.stderr or svar.stdout or "").strip()[:300]
            return False, f"systemctl {verb} rc={svar.returncode}: {fejl}"
        return True, f"systemctl {verb} ok"
    except (OSError, subprocess.SubprocessError) as exc:  # kastede systemctl, bærer vi fejlen ORDRET videre — en vagt der ikke kan rejse skal sige hvorfor
        return False, f"systemctl {verb} kastede: {exc}"


def tjek_og_rejs(*, tør_handle: bool = True) -> dict[str, Any]:
    """Én kørsel af vagten. Returnerer hvad den så og hvad den gjorde.

    ``tør_handle=False`` gør den til en ren observatør — brugt af tests og af
    et manuelt «vis mig hvad du ville gøre».
    """
    aktiv = systemd_tilstand()
    sund = probe_health()
    handling = beslut(aktiv, sund)

    state = _laes_state()
    resultat: dict[str, Any] = {
        "tid": _nu().isoformat(),
        "aktiv": aktiv,
        "sund": sund,
        "handling": handling,
        "udfoert": False,
        "detalje": "",
        "varslet": False,
    }

    if handling == "ok":
        _log(f"aktiv={aktiv} sund=True -> ok")
        # En rask tilstand skal rydde rate-limit, ellers bærer en gammel
        # hændelse straffen ind i en fremtidig, urelateret fejl.
        if state.get("forsøg"):
            state["forsøg"] = []
            _skriv_state(state)
        return resultat

    if handling == "vent":
        _log(f"aktiv={aktiv} sund={sund} -> vent (planlagt overgang)")
        return resultat

    if handling == "blind":
        _log(f"aktiv={aktiv} sund={sund} -> blind (porten svarer, men ikke vores service)")
        resultat["detalje"] = "porten svarer uden at systemd kender servicen"
        if tør_handle:
            resultat["varslet"] = _varsl(
                f"Runtime-vagten kan ikke afgøre tilstanden: systemd siger "
                f"'{aktiv}', men port {PORT} svarer. Jeg har ikke genstartet "
                f"noget — det kan være en anden proces på porten.",
                "Jarvis runtime-vagt: blind", state=state, noegle="blind",
            )
            _skriv_state(state)
        return resultat

    # handling er 'start' eller 'restart' — nu gælder rate-limit.
    nu = _nu()
    forsoeg = [
        t for t in (state.get("forsøg") or [])
        if isinstance(t, str) and _nu() - datetime.fromisoformat(t) < FORSOEG_VINDUE
    ]
    if len(forsoeg) >= MAKS_FORSOEG:
        _log(f"aktiv={aktiv} sund={sund} -> GIVER OP ({len(forsoeg)} forsøg i vinduet)")
        resultat["detalje"] = f"rate-limit: {len(forsoeg)} forsøg uden virkning"
        if tør_handle:
            resultat["varslet"] = _varsl(
                f"Runtime er nede, og jeg har forsøgt at rejse den "
                f"{len(forsoeg)} gange inden for 30 minutter uden at det holdt. "
                f"Jeg stopper med at genstarte i ring — der er noget galt, som "
                f"en genstart ikke løser.",
                "Jarvis runtime-vagt: giver op", state=state, noegle="opgivet",
            )
            _skriv_state(state)
        return resultat

    resultat["detalje"] = f"{handling}: aktiv={aktiv} sund={sund}"
    if not tør_handle:
        _log(f"aktiv={aktiv} sund={sund} -> {handling} (tør-kørsel, intet udført)")
        return resultat

    ok, detalje = _rejs(handling)
    forsoeg.append(nu.isoformat())
    state["forsøg"] = forsoeg
    resultat["udfoert"] = ok
    resultat["detalje"] = detalje

    if not ok:
        _log(f"aktiv={aktiv} sund={sund} -> {handling} MISLYKKEDES: {detalje}")
        resultat["varslet"] = _varsl(
            f"Runtime er nede og jeg kunne ikke rejse den: {detalje}",
            "Jarvis runtime-vagt: kunne ikke rejse runtime",
            state=state, noegle="mislykket",
        )
        _skriv_state(state)
        return resultat

    # Vent og se om den faktisk kom op — «systemctl start returnerede 0» er
    # ikke det samme som «runtime lever». Det er hele dagens lære.
    import time

    svarer = False
    for _ in range(START_VENT_SEKUNDER):
        time.sleep(1)
        if probe_health():
            svarer = True
            break

    resultat["sund_efter"] = svarer
    if svarer:
        _log(f"aktiv={aktiv} sund={sund} -> {handling} UDFØRT, port {PORT} svarer")
        resultat["varslet"] = _varsl(
            f"Runtime var {'nede' if handling == 'start' else 'hængt'} "
            f"(systemd: {aktiv}). Jeg rejste den, og port {PORT} svarer igen. "
            f"API'et kørte hele tiden, så du ville ikke have mærket det.",
            "Jarvis runtime-vagt: rejst", state=state, noegle="rejst",
        )
    else:
        _log(
            f"aktiv={aktiv} sund={sund} -> {handling} UDFØRT, men port {PORT} "
            f"svarer IKKE efter {START_VENT_SEKUNDER}s"
        )
        resultat["varslet"] = _varsl(
            f"Jeg rejste runtime, men port {PORT} svarer stadig ikke efter "
            f"{START_VENT_SEKUNDER} sekunder. Processen kører, men hjertet slår ikke.",
            "Jarvis runtime-vagt: rejst men død", state=state, noegle="dod",
        )
    _skriv_state(state)
    return resultat


def main() -> int:
    """Entry point for oneshot-servicen. Exit 0 uanset — en vagt må ikke crashe."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        resultat = tjek_og_rejs()
        logger.info("runtime-guard resultat: %s", json.dumps(resultat, ensure_ascii=False))
    except Exception as exc:  # vagten selv må aldrig efterlade os blinde
        _log(f"KRASH: {type(exc).__name__}: {exc}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
