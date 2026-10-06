"""Et faerdigt baggrundsjob melder sig selv — i inboxen, eller med en vaekning.

Bjoern 6/10-2026: «han boer ikk skulle saette et wakeup ved baggrundsopgaver …
hvis han saetter et build til at koere i baggrunden boer den selv melde tilbage
enten i inbox hvis han er i et aktivt run, og vaekke ham naar processen er
faerdig hvis han ikk er i et aktivt run».

Alle delene fandtes; ingen kaldte dem i den raekkefoelge:

* `operator_background` er TILSTANDSLOES med vilje — hele tilstanden er filer
  paa operatoerens maskine (`<id>.log/.pid/.rc`), og `.rc` skrives naar
  processen er faerdig. Det er signalet, og det kraever ingen aendring af
  `bash_session` eller `operator_background` (som begge er Bjoerns gate-frie
  vej udenom og ikke maa roeres).
* `background_jobs.liste()` laeser praecis de filer gennem broen og giver
  `status` ("running"/"exited"/"paused"), `exit_code`, `sekunder` og
  `kommando` — plus `bridge_ok`.
* `notification_bridge.send_session_notification()` afgoer SELV hvilket af de
  to tilfaelde vi er i, og siger det i sit svar: `"queued"` = sessionen var
  aktiv, beskeden ligger i `session_inbox` og flushes efter hans tur.
  `"ok"` = der var ingen aktiv tur, beskeden blev skrevet direkte.
* `self_wakeup.schedule_self_wakeup()` er det der faktisk VAEKKER.

Derfor behoever vagten ikke sin egen «er han aktiv»-logik: svaret fra broen
fortaeller det. Ét sted at tage fejl i stedet for to.

**Hvad den IKKE goer, og hvorfor.**

* `bridge_ok=False` → den melder INTET og markerer intet. En doed bro betyder
  at vi ikke VED hvad der koerer paa hans maskine; det er stik modsat «der
  koerer ingenting». `background_jobs` har samme regel, med samme ord.
* Mislykket levering → jobbet markeres IKKE som meldt. Saa proever naeste tick
  igen, i stedet for at tabe beskeden i tavshed.
* **Koldstart melder ikke.** Det foerste tick efter deploy (eller efter en
  nulstillet state) skriver alle allerede-faerdige jobs ind som «meldt» UDEN
  at sende noget. Uden den regel ville featuren levere en byge af gamle jobs
  i samme oejeblik den gik live — praecis moenstret fra
  notifikations-stoejen 2/10, hvor fire uafhaengige kanaler fyrede paa én
  gang.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

#: UDEN «.json» — `state_store._path()` tilfoejer endelsen selv, saa navnet med
#: endelse ville give «baggrundsjob_vagt.json.json». Persistens-gaten fangede det.
_STATE = "baggrundsjob_vagt"
#: Bound staten. Jobfiler forsvinder fra operatoerens /tmp ved genstart, saa en
#: ubegraenset liste ville vokse uden at tjene noget.
_MAX_MELDTE = 200
#: Vaekningen er ikke hastende — jobbet er allerede faerdigt. 60 s er ogsaa
#: `self_wakeup._MIN_DELAY_SECONDS`, saa et lavere tal ville alligevel blive
#: rundet op i tavshed.
_VAEKNING_DELAY_S = 60


def _nu_iso() -> str:
    return datetime.now(UTC).isoformat()


def _hent_state() -> dict[str, Any]:
    from core.runtime.state_store import load_json
    raw = load_json(_STATE, {}) or {}
    if not isinstance(raw, dict):
        return {"initialiseret": False, "meldt": {}}
    meldt = raw.get("meldt")
    return {
        "initialiseret": bool(raw.get("initialiseret")),
        "meldt": dict(meldt) if isinstance(meldt, dict) else {},
    }


def _gem_state(state: dict[str, Any]) -> None:
    from core.runtime.state_store import save_json
    meldt = dict(state.get("meldt") or {})
    if len(meldt) > _MAX_MELDTE:
        # Nyeste beholdes: ældste meldinger er dem hvis jobfiler laengst er vaek.
        beholdt = sorted(meldt.items(), key=lambda kv: str(kv[1]), reverse=True)[:_MAX_MELDTE]
        meldt = dict(beholdt)
    save_json(_STATE, {"initialiseret": True, "meldt": meldt})


def _bro(navn: str, args: dict[str, Any]) -> dict[str, Any]:
    """Bro-kald til operatoerens maskine. Egen funktion, saa testen har en soem."""
    from core.tools.simple_tools import execute_tool
    return execute_tool(navn, args) or {}


def _ejer_uid() -> str:
    try:
        from core.identity.owner_resolver import owner_user_id
        return (owner_user_id() or "").strip()
    except Exception:  # intet ejer-opslag → ingen bro-rute
        return ""


def _varighed(sekunder: Any) -> str:
    try:
        s = int(sekunder or 0)
    except Exception:  # ukendt varighed er ikke en fejl, bare ukendt
        return ""
    if s <= 0:
        return ""
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    return f"{s // 3600}t {(s % 3600) // 60}m"


def beskedtekst(job: dict[str, Any]) -> str:
    """Én linje der kan staa alene i en inbox. Udfaldet FOERST — det er det der
    afgoer om han skal gribe ind."""
    kode = job.get("exit_code")
    # `navn` er Jarvis egen etiket naar han gav jobbet en («Bygger APK 280
    # (kun arm64)»), ellers kommandoen. Begge var TOMME indtil 6/10-2026, hvor
    # listen holdt op med at laese dem fra en forkert sti.
    kommando = (str(job.get("navn") or "").strip()
                or str(job.get("kommando") or "").strip()
                or "(baggrunds-shell)")
    tid = _varighed(job.get("sekunder"))
    halen = f" efter {tid}" if tid else ""
    if kode is None:
        # Processen er vaek uden en .rc-fil. Det er ikke «lykkedes» — det er
        # ukendt, og at skrive 0 ville vaere en loegn.
        return (f"⏹ Baggrundsjobbet `{kommando}` er ikke laengere i gang{halen}, "
                f"men efterlod ingen exit-kode.")
    if int(kode) == 0:
        return f"✅ Baggrundsjobbet `{kommando}` er faerdigt{halen} (exit 0)."
    return f"❌ Baggrundsjobbet `{kommando}` fejlede{halen} — exit {int(kode)}."


def _meld(job: dict[str, Any]) -> tuple[bool, str]:
    """Levér meldingen. Returnerer (leveret, hvordan)."""
    tekst = beskedtekst(job)
    try:
        from core.services.notification_bridge import (
            delivery_succeeded,
            send_session_notification,
        )
        svar = send_session_notification(tekst, source="baggrundsjob-vagt")
    except Exception:
        logger.warning("baggrundsjob_vagt: kunne ikke levere melding", exc_info=True)
        return False, "fejl"
    if not delivery_succeeded(svar):
        return False, str(svar.get("status") or "fejl")

    status = str(svar.get("status") or "")
    if status == "queued":
        # Han arbejder. Inboxen flusher efter hans tur — ingen vaekning, for
        # han er allerede vaagen, og en vaekning midt i en tur er praecis det
        # «raab ind ad doeren» inboxen blev bygget for at undgaa.
        return True, "inbox"

    # Ingen aktiv tur: beskeden staar i sessionen, men der er ingen der laeser
    # den af sig selv. Derfor en vaekning — det er den han ellers skulle have
    # booket i haanden.
    try:
        from core.services.self_wakeup import schedule_self_wakeup
        res = schedule_self_wakeup(
            delay_seconds=_VAEKNING_DELAY_S,
            prompt=(f"{tekst}\n\nSe resultatet, og rapportér KUN til Bjørn hvis der er "
                    f"noget han skal vide eller gøre."),
            reason="baggrundsjob faerdigt",
        )
        if str(res.get("status") or "") == "error":
            # Vaekningen fejlede (typisk loftet paa pending). Beskeden ER
            # leveret, saa jobbet taeller som meldt — men det skal staa i
            # svaret, ikke forsvinde.
            return True, f"skrevet_uden_vaekning:{res.get('error')}"
    except Exception:
        logger.warning("baggrundsjob_vagt: kunne ikke booke vaekning", exc_info=True)
        return True, "skrevet_uden_vaekning"
    return True, "vaekning"


def tick_baggrundsjob_vagt(*, trigger: str = "", last_visible_at: str = "") -> dict[str, Any]:
    """Kadence-producer: meld hvert nyligt afsluttet baggrundsjob ÉN gang."""
    uid = _ejer_uid()
    if not uid:
        return {"status": "ingen_ejer"}
    # `_operator_jobs`, IKKE `background_jobs.liste()`. Panelets `liste()`
    # samler fire kilder, og én af dem er `_lokale_shell_sessioner()`, hvis egen
    # docstring siger at ENHVER forespoergsel — ogsaa `list` — nulstiller
    # bash_session-daemonens nedluknings-ur. Panelet holder kun det ur varmt
    # mens det er aabent; en producer der poller hvert andet minut ville holde
    # en session-loes daemon i live for evigt. Vagten skal kun have
    # operator-siden (det er dér `.rc` skrives), saa den spoerger kun dér — ét
    # bro-kald i stedet for fire kilder.
    from core.services.background_jobs import BroTier, _operator_jobs
    try:
        jobs = _operator_jobs(uid, _bro)
    except BroTier:  # broen tier → vi VED ikke; markér intet, meld intet
        return {"status": "bro_tier"}
    except Exception:  # alt andet er en aegte fejl og skal kunne ses i loggen
        logger.warning("baggrundsjob_vagt: kunne ikke hente joblisten", exc_info=True)
        return {"status": "liste_fejl"}

    faerdige = [j for j in (jobs or [])
                if str(j.get("status") or "") == "exited" and str(j.get("id") or "")]
    state = _hent_state()
    meldt: dict[str, Any] = state["meldt"]

    if not state["initialiseret"]:
        for j in faerdige:
            meldt[str(j["id"])] = _nu_iso()
        _gem_state({"meldt": meldt})
        return {"status": "koldstart", "tavse": len(faerdige)}

    nye, maader, fejlede = 0, [], 0
    for job in faerdige:
        jid = str(job["id"])
        if jid in meldt:
            continue
        leveret, hvordan = _meld(job)
        if not leveret:
            fejlede += 1
            continue
        meldt[jid] = _nu_iso()
        nye += 1
        maader.append(hvordan)
    if nye:
        _gem_state({"meldt": meldt})
    return {"status": "ok", "meldt": nye, "maader": maader,
            "fejlede": fejlede, "faerdige_i_alt": len(faerdige)}
