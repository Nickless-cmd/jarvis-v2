"""Hvem koerer denne agent — og lever den proces stadig?

BAGGRUND (maalt 10/9-2026). `jarvis-api` og `jarvis-runtime` koerer SAMME
app (`uvicorn apps.api.jarvis_api.app:app`), saa BEGGE processer eksekverer
opstarts-hooken — inklusive `recover_crashed_agents()`, som markerer enhver
agent i `starting/active/blocked` som styrtet.

Registret havde intet ejerskabs-maerke. En genstart af den ene proces kunne
derfor doemme en agent der levede i den ANDEN. Kun én agent er nogensinde
blevet fejet (af 198), fordi agenter er kortlivede — men mekanismen er der,
og et deploy genstarter begge.

VALGET NAAR VI IKKE KAN AFGOERE DET: lad vaere at feje. En aegte
forældreloes bliver samlet op af TTL-udloebet (verificeret levende, senest
5/9), mens en fejet LEVENDE agent mister sit arbejde uden spor. Af de to
fejl er den sidste vaerst, saa tvivl falder ud til agentens fordel.

MEN «TOMT MAERKE» ER IKKE TVIVL. Det betyder «raekke fra foer migreringen»,
og den fejes som hidtil. Jarvis fandt at dokumentet her lovede det modsatte:
under «tom» gemte der sig TO situationer — en gammel raekke, hvor fejning er
rigtig, og en LEVENDE agent hvis proces ikke kunne danne et maerke, hvor
fejning er praecis den skade vaernet er bygget mod. Derfor degraderer
`denne_proces()` hellere til starttid `0` end til tomt: en levende proces maa
aldrig komme til at ligne en gammel raekke. Fejningen har desuden et
friskheds-vaern for tomme maerker.

Maerket er `<host>:<pid>:<starttid>`. Starttiden goer det immunt over for
pid-genbrug: en ny proces med samme pid har en anden starttid.
"""
from __future__ import annotations

import logging
import os
import socket
import subprocess
import threading

logger = logging.getLogger(__name__)


def _starttid(pid: int) -> str:
    """Procesens starttid i clock ticks (felt 22 i /proc/<pid>/stat).

    Kommandonavnet i felt 2 kan indeholde mellemrum og parenteser, saa der
    splittes EFTER den sidste `)` — ellers forskubbes felterne.
    """
    try:
        with open(f"/proc/{pid}/stat", "rb") as fh:
            raw = fh.read().decode("utf-8", "replace")
        hale = raw[raw.rindex(")") + 1:].split()
        return hale[19]                       # felt 22, 0-indekseret efter comm
    except Exception:
        return ""


def denne_proces() -> str:
    """Maerket for den proces der kalder.

    DEGRADERER, den fejler ikke til tomt. Kan starttiden ikke laeses, bruges
    `0` — saa kan `lever()` stadig se om pid'en findes, bare uden vaernet mod
    pid-genbrug. TOMT maerke betyder nemlig noget ANDET: en raekke fra foer
    migreringen, som skal fejes. Faldt en levende proces tilbage til tomt,
    ville dens agenter blive fejet af netop det vaern der er bygget for at
    undgaa det. (Jarvis fandt tvetydigheden.)

    Tom streng kun hvis selv vaertsnavn eller pid er utilgaengelige.
    """
    try:
        pid = os.getpid()
        return f"{socket.gethostname()}:{pid}:{_starttid(pid) or '0'}"
    except Exception:
        return ""


def lever(maerke: str) -> bool | None:
    """Lever processen bag maerket?

    `True`  — samme host, pid findes, starttid matcher.
    `False` — samme host, og processen er beviseligt vaek.
    `None`  — kan ikke afgoeres: ANDEN host, eller ulaesbar form.
              Kalderen skal behandle `None` som «roer den ikke».

    TOMT maerke giver ogsaa `None`, men betyder noget andet: raekken er fra
    foer migreringen. Kalderen skelner — se `recover_crashed_agents`, hvor
    tomme maerker fejes som hidtil, men med et friskheds-vaern saa en LEVENDE
    agent uden maerke ikke rammes.
    """
    if not maerke:
        return None
    dele = maerke.rsplit(":", 2)
    if len(dele) != 3:
        return None
    host, pid_s, start = dele
    try:
        if host != socket.gethostname():
            return None                       # en anden maskine — ikke vores kald
        pid = int(pid_s)
    except Exception:
        return None
    if not os.path.exists(f"/proc/{pid}"):
        return False
    nu = _starttid(pid)
    if not nu:
        return None
    # `0` = maerket blev dannet uden laesbar starttid. Pid'en findes, saa
    # processen lever — bare uden vaernet mod pid-genbrug.
    return True if start == "0" else nu == start


# ─────────────────────────────────────────────────────────────────────────────
# Efterladte API-processer
#
# BAGGRUND (maalt 18/10-2026). En genstart efterlod den gamle API-proces i live
# med 172 traade og 261 aabne DB-forbindelser, `PPID=1`, 18,6 % CPU — og den
# skrev videre til den SAMME `jarvis.db` som den nye proces. Den lyttede ikke
# paa porten, saa den fik ingen requests; den var en KONKURRERENDE SKRIVER.
# Det er praecis den slags der giver «database is locked» og WAL-vaekst.
#
# Aarsagen er `KillMode=process` i systemd-uniten: systemd draeber kun MainPID,
# ikke hele cgroup'en. En proces der er startet uden om systemd (eller hvis
# foraelder er doed) overlever derfor en `systemctl restart` uden at nogen
# opdager det.
#
# HVORFOR DET IKKE KAN AFGOERES PAA CMDLINE ALENE
# `jarvis-api` og `jarvis-runtime` koerer SAMME app — se modul-docstringen
# ovenfor. To processer med identisk cmdline er derfor det NORMALE, og en vagt
# der taeller dem ville alarmere hver gang huset er sundt. Skellet gaar et
# andet sted: systemd kender sine MainPID'er. Alt andet med API-cmdline er
# efterladt. Det spoergsmaal kan kun besvares af kalderen, som derfor giver
# `main_pids` ind — funktionen her læser ikke systemd selv.

_API_CMDLINE_MARKOER = "apps.api.jarvis_api"


def _cmdline(pid: int) -> str:
    """Procesens kommandolinje med NUL-bytes erstattet af mellemrum."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            return fh.read().replace(b"\x00", b" ").decode("utf-8", "replace")
    except Exception:                    # processen kan do mellem listdir og her
        return ""


def _foraeldre(pid: int) -> int:
    """PPID for `pid` (felt 4 i /proc/<pid>/stat), 0 hvis ulaesbar."""
    try:
        with open(f"/proc/{pid}/stat", "rb") as fh:
            raw = fh.read().decode("utf-8", "replace")
        return int(raw[raw.rindex(")") + 1:].split()[1])
    except Exception:                    # samme kaploeb: processen kan vaere vaek
        return 0


def er_efterladt_api_proces(
    *,
    pid: int,
    cmdline: str,
    main_pids: set[int],
    eget_pid: int,
    foraeldre_kæde: set[int],
) -> bool:
    """Er denne proces en API-proces som systemd ikke ejer?

    Ren funktion — ingen /proc-laesning — saa den kan testes uden at spoerge
    den maskine den selv koerer paa. Det er med vilje: en vagt der kun kan
    testes ved at efterlade en aegte proces er en vagt ingen tør teste.

    Seks betingelser, alle noedvendige:

    1. Cmdline peger paa API-app'en (ellers er det en helt anden proces).
    2. Pid'en er ikke en af systemds MainPID'er (saa er den legitim).
    3. Pid'en er ikke min egen (jeg er per definition i live).
    4. Pid'en er ikke en FORFADER til mig. Under en genstart kan min nye
       proces vaere startet af den gamle, og den skal ikke doemmes for det.
    5. Pid'en er ikke 1 (init).
    6. Pid'en er positiv.

    `foraeldre_kæde` er de pid'er der ligger over mig i traeet. Kalderen
    bygger den; her tjekkes kun medlemskab.
    """
    if pid <= 1:
        return False
    if _API_CMDLINE_MARKOER not in (cmdline or ""):
        return False
    if pid in main_pids:
        return False
    if pid == eget_pid:
        return False
    if pid in foraeldre_kæde:
        return False
    return True


def foraeldre_kæde(pid: int | None = None) -> set[int]:
    """Pid'erne over `pid` (default: mig selv) op til init."""
    naeste = os.getpid() if pid is None else pid
    kaede: set[int] = set()
    set_pid = set()
    while naeste and naeste > 1 and naeste not in set_pid:
        set_pid.add(naeste)
        naeste = _foraeldre(naeste)
        if naeste > 1:
            kaede.add(naeste)
    return kaede


def efterladte_api_processer(*, main_pids: set[int]) -> list[dict[str, object]]:
    """Find API-processer som systemd ikke ejer.

    `main_pids` kommer fra kalderen (`systemctl show -p MainPID` for hver
    unit). Funktionen spoerger ALDRIG systemd selv — den skal kunne kaldes fra
    en test og fra en proces uden systemd-adgang.

    Returnerer `[{pid, cmdline, starttid, alder_s}]`, nyeste sidst. Tom liste
    er det normale svar; en ikke-tom liste betyder at nogen skal rydde op.
    """
    eget = os.getpid()
    kaede = foraeldre_kæde(eget)
    fund: list[dict[str, object]] = []
    try:
        pid_navne = [n for n in os.listdir("/proc") if n.isdigit()]
    except Exception:                    # /proc ulaesbar — tomt svar er aerligt
        return fund
    for navn in pid_navne:
        pid = int(navn)
        cmd = _cmdline(pid)
        if not er_efterladt_api_proces(
            pid=pid,
            cmdline=cmd,
            main_pids=main_pids,
            eget_pid=eget,
            foraeldre_kæde=kaede,
        ):
            continue
        fund.append(
            {
                "pid": pid,
                "cmdline": cmd.strip(),
                "starttid": _starttid(pid),
                "ppid": _foraeldre(pid),
            }
        )
    fund.sort(key=lambda r: int(r["pid"]))
    return fund


#: De to units der koerer API-app'en. Begge skal spoerges — se modul-docstringen.
API_UNITS: tuple[str, ...] = ("jarvis-api", "jarvis-runtime")


def systemd_main_pids(units: tuple[str, ...] = API_UNITS) -> set[int]:
    """MainPID for hver unit, som systemd kender den lige nu.

    En unit der ikke findes eller ikke koerer giver 0 og filtreres væk — en
    standset unit ejer ingen proces, og dens gamle pid maa ikke taelles med.

    Fejler ALDRIG: kan systemctl ikke kaldes (ingen systemd, ingen rettigheder,
    timeout), returneres det tomme sæt. Kalderen skal behandle det som «jeg ved
    ikke hvem der ejer hvad» — og saa hellere lade vaere at doemme nogen. En
    vagt der gaetter forkert er vaerre end ingen vagt.
    """
    pids: set[int] = set()
    for unit in units:
        try:
            ud = subprocess.run(
                ["systemctl", "show", "-p", "MainPID", "--value", unit],
                capture_output=True,
                text=True,
                timeout=5,
            )
            tal = int((ud.stdout or "0").strip() or "0")
        except Exception:                # unit findes ikke el. ingen systemd
            continue
        if tal > 1:
            pids.add(tal)
    return pids


#: Hvor laenge vagten venter foer den doemmer. En legitim nedlukning tager op
#: til 30 s (5 s graceful + SIGKILL), og ved opstart kan den gamle proces derfor
#: stadig vaere i live UDEN at vaere efterladt. 90 s er rigeligt til at den er
#: vaek, og en aegte efterladt proces bliver ikke mindre efterladt af at vente.
EFTERLADT_FORSINKELSE_S = 90.0


def start_efterladt_vagt(forsinkelse_s: float = EFTERLADT_FORSINKELSE_S) -> threading.Thread:
    """Start vagten i en daemon-traad. Opdager og RAPPORTERER — draeber ikke.

    HVORFOR DEN IKKE DRAEBER
    En vagt der draeber forkert er vaerre end ingen vagt. Ved opstart kan den
    gamle proces vaere midt i en legitim, langsom nedlukning; draebte vi den,
    ville vi kappe arbejde praecis som `drain_before_restart` findes for at
    undgaa. Vagten skriver derfor den praecise kommando i loggen og lader et
    menneske (eller mig) tage beslutningen. Det er den samme afvejning som
    `recover_crashed_agents` goer: tvivl falder ud til den levende proces.

    Traaden er daemon, saa den holder ikke processen i live ved nedlukning.
    """
    def _koer() -> None:
        import time as _tid

        try:
            _tid.sleep(max(0.0, float(forsinkelse_s)))
            fund = efterladte_api_processer(main_pids=systemd_main_pids())
        except Exception as exc:                     # pragma: no cover - miljoe
            logger.warning("efterladt-proces-vagt kunne ikke maale: %s", exc)
            return
        if not fund:
            return
        for post in fund:
            logger.warning(
                "EFTERLADT API-PROCES pid=%s ppid=%s — skriver til samme DB uden "
                "at eje porten. Draeb den: kill -TERM %s",
                post["pid"],
                post["ppid"],
                post["pid"],
            )
        logger.warning(
            "efterladt-proces-vagt: %d efterladt(e) API-proces(ser). "
            "Aarsag er KillMode=process i systemd-uniten — kun MainPID draebes.",
            len(fund),
        )

    traad = threading.Thread(target=_koer, name="efterladt-proces-vagt", daemon=True)
    traad.start()
    return traad
