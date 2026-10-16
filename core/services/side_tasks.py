"""Side-task flag — keep the main thread focused.

When working on task A, Jarvis often notices something tangential that
should be done — but derailing into it costs context and momentum. The
side-task flag lets him capture it without acting: "noted, flagged for
later", and the user (or a future session) can pick it up.

Mirrors my own ``mcp__ccd_session__spawn_task``: short title, longer
self-contained prompt, optional plain-English tldr. Surfaces in the
visible prompt as a small list so the user sees what's queued and can
dismiss anything that's not actually wanted.

Per-session for context, but visible across the workspace so a side
task flagged in Discord is visible in webchat too. Persisted via
state_store.

Status: ``pending``, ``queued`` og ``activated`` er ÅBNE — de står i inboxen
og over chatten i Desk til nogen afslutter dem.
``completed`` og ``dismissed`` er terminale og kan ikke genåbnes. Før fandtes
kun ``dismissed`` som slutpunkt, så en opgave der BLEV lavet, forsvandt som
om den var droppet — og en ``activated`` forsvandt fra prompten i samme
øjeblik den blev taget op.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Final
from uuid import uuid4

from core.runtime.state_store import load_json, med_laas, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "side_tasks"
_VALID_STATUSES = ("pending", "queued", "activated", "completed", "dismissed")
_AABNE = frozenset({"pending", "queued", "activated"})
_TERMINALE = frozenset({"completed", "dismissed"})
_MAX_SHOWN = 6

#: Et bevis skal sige HVAD der blev gjort — ikke blot at noget blev gjort.
#: Grænsen er lav (et par ord), men ikke nul: «ok» og «done» er påstande uden
#: indhold, og det er præcis dem der lod en sideopgave stå åben i MEMORY længe
#: efter at arbejdet var gjort. Formen er husets egen — `inbox_drop` har krævet
#: en grund siden 4/10 af samme årsag: «en afvisning uden grund kan ikke
#: efterprøves».
_MIN_BEVIS: Final[int] = 10


def _kort(tekst: str, maks: int) -> str:
    """Afkort ved en ORD-grænse, så en halv sætning ikke læses som en hel.

    Den gamle `tldr[:240]` skar midt i «send_session_notificati», og en
    afkortet instruks er værre end ingen: den ser ud som et fuldt svar.
    """
    t = " ".join(str(tekst or "").split())
    if len(t) <= maks:
        return t
    skaaret = t[:maks].rsplit(" ", 1)[0].rstrip(",.;:-—")
    return (skaaret or t[:maks]) + "…"


def _load_all() -> list[dict[str, Any]]:
    raw = load_json(_STATE_KEY, [])
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict)]


def _save_all(items: list[dict[str, Any]]) -> None:
    save_json(_STATE_KEY, items)
    # state_store.save_json is deliberately best-effort for optional daemons.
    # Side tasks are user-visible obligations: never return "ok" after a
    # swallowed write error. Mutations hold med_laas, so read-back is stable.
    if _load_all() != items:
        raise OSError("side tasks could not persist")


def _age_label(created_at: Any) -> str | None:
    """Kort alders-tag, fx ``3 dage`` eller ``5t`` — eller None hvis ukendt.

    Uden det ser en opgave der har ligget åben i ti dage lige så frisk ud som
    en fra i morges. En glemt opgave er ikke en ventende opgave, og forskellen
    skal kunne ses på prompten — der er ingen automatik der lukker dem
    (målt 3/10-2026: ``resolve()`` kaldes kun eksplicit).
    """
    if not created_at:
        return None
    try:
        ts = datetime.fromisoformat(str(created_at))
    except (TypeError, ValueError):  # ugyldig dato er ikke en fejl — vi udelader bare alderen
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    seconds = (datetime.now(UTC) - ts).total_seconds()
    if seconds < 0:
        return None
    if seconds < 3600:
        return f"{int(seconds // 60)}min"
    if seconds < 86400:
        return f"{int(seconds // 3600)}t"
    dage = int(seconds // 86400)
    return "1 dag" if dage == 1 else f"{dage} dage"


# ── Timeren: `not_before` (16/10-2026) ─────────────────────────────────────
#
# Bjørn: «Mulighed for en timer funktionalitet, der lader en sætte en tid eller
# dato for opgaven som inboxs gate holder».
#
# Indbakken havde kun ÉN tidsretning: `expires_at` — en FRIST, hvor gaten giver
# OP. Der fandtes ingen `not_before`, hvor den HOLDER IGEN. En opgave kunne
# altså udløbe, men ikke udskydes.
#
# To ting er værd at vide om formen:
#
# 1. `not_before` er SANDHEDEN; vækningen er kun en måde at blive mindet på.
#    Fejeren rydder feltet når tiden er inde, så en vækning der aldrig fyrer
#    ikke efterlader opgaven sovende for evigt.
# 2. En sovende opgave GATER ikke. Det er allerede sandt for hele klassen —
#    `inbox_view` sætter `kraever_handling = False` på hver sideopgave — og den
#    regel bliver ikke kopieret her. En gate uden udgang er præcis den deadlock
#    `bloker` gav os.


def _fremtid(tidsstempel: Any) -> datetime | None:
    """Et ISO-tidsstempel som tz-bevidst datetime — ``None`` hvis ulaeseligt."""
    if not tidsstempel:
        return None
    try:
        ts = datetime.fromisoformat(str(tidsstempel).replace("Z", "+00:00"))
    except (TypeError, ValueError):  # ulaeseligt er «ved ikke», ikke «nu» —
        # fald-retningen ligger i `sovende`, hvor den betyder VAAGEN. Skal den
        # en dag betyde det modsatte, skal den rettes DER, ikke her.
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts


def _vaek_loft_sekunder() -> float:
    """Vækningens eget loft — HENTET fra `self_wakeup`, ikke kopieret.

    `schedule_self_wakeup` klemmer delay til [60, 86400]. En udskydelse længere
    ude kan derfor ikke være ÉN vækning, og det skal ikke ties ihjel: fejeren
    booker i stedet når der er mindre tilbage. To tal for «hvor langt rækker en
    vækning» ville drive fra hinanden — og den ene ville stille booke en vækning
    der fyrede på det forkerte tidspunkt.
    """
    try:
        from core.services.self_wakeup import _MAX_DELAY_SECONDS
        return float(_MAX_DELAY_SECONDS)
    except Exception:  # noqa: BLE001
        logger.warning("side-opgaver: kunne ikke laese vaekningens loft — "
                       "falder tilbage til 86400")
        return 86400.0


def _kort_tid(tidsstempel: Any) -> str:
    """Kort LOKAL tid, fx ``17/10 09:00``. Tom streng hvis ulaeselig."""
    ts = _fremtid(tidsstempel)
    if ts is None:
        return ""
    return ts.astimezone().strftime("%d/%m %H:%M")


def sovende(record: dict[str, Any], *, nu: datetime | None = None) -> bool:
    """SOVER denne opgave — ligger dens `not_before` stadig i fremtiden?

    ÉN definition, brugt af prompt-afsnittet, indbakke-visningen og fejeren. To
    definitioner af «venter til senere» ville drive fra hinanden, og så ville én
    flade sige «sover» mens en anden begyndte at minde om den.

    Fald-retningen er VÆK fra «sover»: tomt eller ulaeseligt `not_before` betyder
    VÅGEN. Et i stykker tidsstempel må ikke kunne skjule en opgave for evigt.
    """
    ts = _fremtid(record.get("not_before"))
    if ts is None:
        return False
    return ts > (nu or datetime.now(UTC))


def sove_tekst(record: dict[str, Any], *, nu: datetime | None = None) -> str:
    """``sover til 17/10 09:00`` — eller ``""`` hvis opgaven ikke sover.

    ÉN formatering, delt af prompt-afsnittet og indbakke-visningen. To
    formateringer ville drive fra hinanden, og den ene ville stille vise et
    tidspunkt der ikke er det opgaven vågner på.
    """
    if not sovende(record, nu=nu):
        return ""
    hvornaar = _kort_tid(record.get("not_before"))
    return f"sover til {hvornaar}" if hvornaar else "sover"


def _annuller_vaekning_id(vaekning_id: str) -> bool:
    """Annullér én booket vækning. Kaster aldrig.

    En vækning der allerede har fyret kan ikke annulleres — det er ikke en fejl,
    der er bare intet at annullere.
    """
    vid = str(vaekning_id or "").strip()
    if not vid:
        return False
    try:
        from core.services.self_wakeup import cancel_wakeup
        return str(cancel_wakeup(vid).get("status") or "") == "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("side-opgaver: kunne ikke annullere vaekning %s: %s", vid, exc)
        return False


def _annuller_vaekning(record: dict[str, Any]) -> bool:
    return _annuller_vaekning_id(str(record.get("vaekning_id") or ""))


def _book_vaekning(record: dict[str, Any], *, nu: datetime | None = None) -> str:
    """Book ÉN vækning til opgavens `not_before`. Id, eller ``""``.

    Kaster aldrig. En opgave der sover er stadig korrekt selv om vækningen ikke
    kunne bookes: `not_before` er sandheden, og fejeren prøver igen.

    Er tidspunktet uden for vækningens rækkevidde (over 24 t), bookes INTET her.
    Det er ikke et fejlet forsøg — fejeren booker når der er mindre tilbage.
    """
    ts = _fremtid(record.get("not_before"))
    if ts is None:
        return ""
    nu = nu or datetime.now(UTC)
    sekunder = (ts - nu).total_seconds()
    if sekunder <= 0 or sekunder > _vaek_loft_sekunder():
        return ""
    tid = str(record.get("side_task_id") or "")
    titel = _kort(str(record.get("title") or ""), 70)
    try:
        from core.services.self_wakeup import schedule_self_wakeup
        sid = str(record.get("arbejds_session") or record.get("session_id") or "").strip()
        svar = schedule_self_wakeup(
            delay_seconds=int(sekunder),
            prompt=(
                f"Side-opgaven [{tid}] «{titel}» sover ikke laengere — dens tid er "
                "inde. Tag den op nu, eller udskyd den igen med "
                "`snooze_side_task`. Er den ikke laengere relevant, saa afvis den "
                f"med en grund: dismiss_side_task(side_task_id=\"{tid}\", "
                "decision=\"dismissed\", reason=\"...\")."),
            reason=f"side-opgave udskudt til {_kort_tid(record.get('not_before'))}",
            # `_default` er IKKE en samtale — den er `flag`s pladsholder. Blev
            # den sendt med, pegede vækningen på en session der ikke findes.
            # Tom ⇒ `pick_wakeup_run_target` resolver ejerens app-samtale.
            session_id=sid if sid and sid != "_default" else None,
            task_id=tid,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("side-opgaver: kunne ikke booke vaekning for %s: %s", tid, exc)
        return ""
    if str(svar.get("status") or "") != "ok":
        logger.warning("side-opgaver: vaekning for %s blev afvist: %s",
                       tid, svar.get("error"))
        return ""
    return str((svar.get("wakeup") or {}).get("wakeup_id") or "")


def _ventende_vaekning_ids() -> set[str] | None:
    """Id'er på vækninger der stadig venter. ``None`` = kunne IKKE læses.

    `None` og `set()` må ikke mappes sammen — samme skel som `_gatende_poster` i
    `inbox_gate`. Kunne vi ikke læse, må vi ikke booke en ny: vi ville ikke
    kunne se at der allerede står én, og hver fejning ville lægge et led til.
    """
    try:
        from core.services.self_wakeup import list_wakeups
        return {str(r.get("wakeup_id") or "")
                for r in list_wakeups(status="pending", limit=200)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("side-opgaver: kunne ikke laese ventende vaekninger: %s", exc)
        return None


def flag(*, title: str, prompt: str, tldr: str = "", session_id: str | None = None,
         finding_key: str = "", source_run_id: str = "", evidence: str = "",
         not_before: str = "") -> dict[str, Any]:
    """Rejs et flag. `not_before` (16/10-2026) gør det til en TIDSINDSTILLET
    opgave: den står åben og synlig, men må ikke tages op før tidspunktet."""
    title = (title or "").strip()
    prompt = (prompt or "").strip()
    if not title or not prompt:
        return {"status": "error", "error": "title and prompt are required"}
    nb = ""
    if str(not_before or "").strip():
        ts = _fremtid(not_before)
        if ts is None:
            return {"status": "error",
                    "error": ("not_before skal vaere et ISO-tidsstempel, fx "
                              "2026-10-20T09:00:00+02:00")}
        # En tid der allerede er passeret udskyder ingenting. Vi gemmer den
        # ikke som en sovende opgave — det ville se ud som en indstilling der
        # virkede, uden at gøre noget.
        if ts > datetime.now(UTC):
            nb = ts.astimezone(UTC).isoformat()
    key = str(finding_key or "").strip()[:240]
    with med_laas(_STATE_KEY):
        items = _load_all()
        if key:
            existing = next((r for r in items if r.get("finding_key") == key), None)
            if existing:
                return {"status": "ok", "side_task_id": existing["side_task_id"],
                        "title": existing.get("title", ""), "deduplicated": True}
        record = {
            "side_task_id": f"side-{uuid4().hex[:10]}",
            "title": title[:200],
            "prompt": prompt[:12000],
            "tldr": tldr[:600] if tldr else "",
            "status": "pending",
            "session_id": str(session_id or "_default"),
            "created_at": datetime.now(UTC).isoformat(),
        }
        if key:
            record["finding_key"] = key
        if source_run_id:
            record["source_run_id"] = str(source_run_id)[:120]
        if evidence:
            record["evidence"] = str(evidence)[:1000]
        if nb:
            record["not_before"] = nb
            record["snoozed_at"] = datetime.now(UTC).isoformat()
        items.append(record)
        _save_all(items)
    if nb:
        # Vækningen bookes EFTER låsen, med vilje: `schedule_self_wakeup`
        # skriver en anden fil og kalder videre i huset, og `med_laas` bruger
        # `flock`, som IKKE er genindtagelig i samme proces. Et book-kald inde
        # i låsen kunne hænge hele API-processen — og en lås der hænger er
        # værre end en lås der holdes kort.
        vid = _book_vaekning(record)
        if vid:
            with med_laas(_STATE_KEY):
                items = _load_all()
                f = next((x for x in items
                          if x.get("side_task_id") == record["side_task_id"]), None)
                if f is not None and str(f.get("not_before") or "") == nb:
                    f["vaekning_id"] = vid
                    _save_all(items)
    return {"status": "ok", "side_task_id": record["side_task_id"], "title": title}


def snooze(side_task_id: str, *, until: str, reason: str = "") -> dict[str, Any]:
    """Udskyd en sideopgave: den må ikke tages op før `until`.

    Bjørn 16/10-2026: «en timer funktionalitet, der lader en sætte en tid eller
    dato for opgaven». Opgaven forbliver ÅBEN og synlig — den markeres som
    sovende, og der bookes en vækning til tidspunktet. Udskydelse er ikke en
    afvisning; `dismissed` er stadig den eneste vej ud af en opgave man ikke vil
    løse, og `completed` den eneste vej ud af en man HAR løst.

    En `activated` opgave afvises: en samtale ER i gang med den, og et
    `not_before` oveni ville være to svar om samme opgave. Sæt den i kø først.
    """
    ts = _fremtid(until)
    if ts is None:
        return {"status": "error",
                "error": ("until skal vaere et ISO-tidsstempel, fx "
                          "2026-10-20T09:00:00+02:00")}
    nu = datetime.now(UTC)
    if ts <= nu:
        return {"status": "error",
                "error": ("until skal ligge i FREMTIDEN — en passeret tid "
                          "udskyder ingenting")}
    iso = ts.astimezone(UTC).isoformat()

    # Læs og afvis FØR noget bookes. En opgave der ikke kan udskydes skal ikke
    # efterlade en vækning vi bagefter skal rydde op i.
    forud = get(side_task_id)
    if forud is None:
        return {"status": "error", "error": f"unknown side_task_id {side_task_id}"}
    if str(forud.get("status") or "") in _TERMINALE:
        return {"status": "error",
                "error": (f"side task {side_task_id} is already {forud.get('status')} "
                          "and cannot be snoozed")}
    if str(forud.get("status") or "") == "activated":
        return {"status": "error",
                "error": ("en igangvaerende opgave kan ikke udskydes — saet den i koe "
                          "foerst (activate_side_task status=queued)")}

    vid = _book_vaekning({**forud, "not_before": iso}, nu=nu)

    with med_laas(_STATE_KEY):
        items = _load_all()
        found = next((r for r in items if r.get("side_task_id") == side_task_id), None)
        old = str((found or {}).get("status") or "")
        fejl = ""
        if found is None:
            fejl = f"unknown side_task_id {side_task_id}"
        elif old in _TERMINALE or old == "activated":
            fejl = f"side task {side_task_id} er nu {old} og kan ikke udskydes"
        if fejl:
            # Tilstanden naaede at skifte mellem laesningen og laasen. Den
            # netop bookede vækning skal ikke staa tilbage og ringe paa doeren
            # for en opgave der er lukket.
            gammel = vid
            vid = ""
        else:
            gammel = str(found.get("vaekning_id") or "")
            found["not_before"] = iso
            found["snoozed_at"] = nu.isoformat()
            found["snooze_reason"] = str(reason).strip()[:500]
            found["updated_at"] = nu.isoformat()
            if vid:
                found["vaekning_id"] = vid
            else:
                found.pop("vaekning_id", None)
            _save_all(items)
    # Annulleringen ligger UDEN for låsen — samme grund som bookingen ovenfor.
    if gammel and gammel != vid:
        _annuller_vaekning_id(gammel)
    if fejl:
        return {"status": "error", "error": fejl}
    return {"status": "ok", "side_task_id": side_task_id,
            "not_before": iso, "vaekning_id": vid}


def vaagn(side_task_id: str, *, reason: str = "") -> dict[str, Any]:
    """Væk en sovende opgave FØR tid: ryd `not_before`, annullér vækningen.

    Modstykket til `snooze`. Uden den ville en udskydelse være en envejsdør
    indtil tiden selv løb ud — og «jeg ombestemte mig» er en helt almindelig
    handling i et opgavesystem. Fejeren gør det samme, men først når tiden ER
    inde; denne gør det med det samme.
    """
    with med_laas(_STATE_KEY):
        items = _load_all()
        found = next((r for r in items if r.get("side_task_id") == side_task_id), None)
        if found is None:
            return {"status": "error", "error": f"unknown side_task_id {side_task_id}"}
        if not sovende(found):
            return {"status": "error",
                    "error": f"side task {side_task_id} is not snoozed"}
        gammel = str(found.get("vaekning_id") or "")
        found.pop("not_before", None)
        found.pop("vaekning_id", None)
        found["vaagnet_at"] = datetime.now(UTC).isoformat()
        if reason:
            found["vaagnet_reason"] = str(reason)[:500]
        found["updated_at"] = datetime.now(UTC).isoformat()
        _save_all(items)
    annulleret = _annuller_vaekning_id(gammel) if gammel else False
    return {"status": "ok", "side_task_id": side_task_id,
            "vaekning_annulleret": annulleret}


def list_pending() -> list[dict[str, Any]]:
    return [r for r in _load_all() if r.get("status") == "pending"]


def list_open() -> list[dict[str, Any]]:
    """Alle åbne — ventende, køede og igangværende."""
    return [r for r in _load_all() if r.get("status") in _AABNE]


def list_open_synlige() -> list[dict[str, Any]]:
    """De åbne der IKKE er skjult i chatten — præcis dem kortet viser.

    Bjørn 8/10-2026: «sørg for X'et ikk sletter dem men bare fjerner dem fra
    chatview». Krydset lavede før en TERMINAL ``dismissed``: opgaven var væk
    for altid, og der fandtes ingen vej tilbage (``resolve`` nægter at
    genåbne). Det er for hårdt et tryk til et kryds i et hjørne.

    Skellet er med vilje: ``list_open()`` er sandheden om hvad der ER åbent og
    styrer Jarvis' prompt som huskeliste; denne funktion er hvad der skal VISES
    over samtalen. En skjult opgave er stadig et åbent løfte — den er bare
    ikke i vejen.
    """
    return [r for r in list_open() if not r.get("skjult_i_chat")]


def get(side_task_id: str) -> dict[str, Any] | None:
    return next((r for r in _load_all() if r.get("side_task_id") == side_task_id), None)


def list_alle(*, maks: int = 50) -> list[dict[str, Any]]:
    """ALLE opgaver, nyeste først — også de lukkede.

    Bjørn 3/10-2026: «desk har ikk noget panel der viser opgaver der er
    flagged selv om jeg har trykket dem væk». `/cowork/side-tasks` svarer kun
    med de ÅBNE, så en opgave der blev lukket forsvandt sporløst — og dermed
    kunne man ikke se forskel på «lukket» og «blev den nogensinde gemt?».

    Målt samme dag: alle seks poster i hans fil var terminale, så kortet var
    korrekt tomt — men umuligt at skelne fra tabt data. Det var selve
    symptomet: persistensen VIRKEDE (bevist med to processer), men der var
    ingen visning der kunne vise det.
    """
    poster = sorted(_load_all(), key=lambda r: str(r.get("created_at", "")),
                    reverse=True)
    return poster[:max(1, int(maks))]


def resolve(side_task_id: str, *, decision: str,
            arbejds_session: str | None = None,
            arbejds_run_id: str | None = None,
            lukket_af: str = "", reason: str = "", bevis: str = "") -> dict[str, Any]:
    """Flyt en opgaves status. `arbejds_session` knytter den til den samtale
    der løser den — se `arbejds_session_for` for hvorfor det er nødvendigt.

    ## En lukning skal bære sin egen begrundelse (16/10-2026)

    Bjørn: «Krav ved completed — men dismissed med begrundelse er altid en vej
    ud». Indtil da krævede `completed` INTET. Det er derfor en sideopgave
    kunne lukkes uden belæg, mens en MEMORY-sektion blev stående og sagde
    «STADIG ÅBEN» om arbejde der for længst var gjort: lukningen og påstanden
    var to poster om samme faktum, og intet bandt dem sammen.

    Nu bærer hver terminal beslutning sin grund:

    * ``completed`` kræver ``bevis`` — hvad der FAKTISK blev gjort.
    * ``dismissed`` kræver ``reason`` — hvorfor den ikke skal løses.

    Begge gemmes på posten, så lukningen kan efterprøves bagefter. Vejen ud
    findes altid: en opgave der ikke kan løses afvises med en grund.
    """
    decision = (decision or "").strip().lower()
    if decision not in {"queued", "dismissed", "activated", "completed"}:
        return {"status": "error", "error": "unknown side-task decision"}
    if decision == "completed" and len(str(bevis or "").strip()) < _MIN_BEVIS:
        return {"status": "error",
                "error": ("completed kræver et bevis: hvad blev der faktisk gjort "
                          f"(mindst {_MIN_BEVIS} tegn). Uden det er lukningen en "
                          "påstand ingen kan efterprøve — kan opgaven ikke løses, "
                          "afvis den i stedet med en grund.")}
    if decision == "dismissed" and not str(reason or "").strip():
        return {"status": "error",
                "error": ("dismissed kræver en grund — en afvisning uden grund "
                          "kan ikke efterprøves")}
    with med_laas(_STATE_KEY):
        items = _load_all()
        found = next((r for r in items if r.get("side_task_id") == side_task_id), None)
        if found is None:
            return {"status": "error", "error": f"unknown side_task_id {side_task_id}"}
        old = str(found.get("status") or "")
        if old in _TERMINALE:
            return {"status": "error",
                    "error": f"side task {side_task_id} is already {old} and cannot be reopened"}
        if decision == "queued" and old == "activated":
            return {"status": "error", "error": "active side task cannot be queued"}
        now = datetime.now(UTC).isoformat()
        found["status"] = decision
        found["updated_at"] = now
        if decision == "queued":
            found["queued_at"] = now
        elif decision == "activated":
            found["activated_at"] = now
        else:
            found["resolved_at"] = now
        if arbejds_session:
            found["arbejds_session"] = str(arbejds_session)
        if arbejds_run_id:
            found["arbejds_run_id"] = str(arbejds_run_id)
        if lukket_af:
            found["lukket_af"] = str(lukket_af)[:60]
        if decision == "dismissed":
            found["dismiss_reason"] = str(reason).strip()[:500]
        if decision == "completed":
            found["bevis"] = str(bevis).strip()[:1000]
        gammel_vaekning = ""
        if decision in _TERMINALE:
            # En lukket opgave må ikke vække nogen (16/10-2026). Uden dette led
            # ville en udskudt opgave ringe på døren efter den var afvist — og
            # svaret ville være «den er lukket», altså støj uden en opgave.
            # Det er samme kobling som `bevis`-kravet: en lukning skal efterlade
            # systemet i en tilstand hvor ingenting peger på den længere.
            gammel_vaekning = str(found.get("vaekning_id") or "")
            found.pop("not_before", None)
            found.pop("vaekning_id", None)
        _save_all(items)
    if gammel_vaekning:
        _annuller_vaekning_id(gammel_vaekning)
    return {"status": "ok", "side_task_id": side_task_id, "new_status": decision}


def saet_skjult(side_task_id: str, *, skjult: bool = True) -> dict[str, Any]:
    """Vis eller skjul en ÅBEN opgave i chatkortet. Rører ikke dens status.

    Det er den bløde modsætning til ``resolve(..., 'dismissed')``: skjult er
    reversibelt, dismissed er det ikke. Bjørn 8/10-2026 bad om netop den
    forskel — krydset skal fjerne opgaven fra chatten, ikke afskrive den.

    En TERMINAL opgave afvises. Den vises ikke i kortet i forvejen, så et flag
    på den ville være en løgn om hvorfor den er væk: den er lukket, ikke skjult.
    """
    with med_laas(_STATE_KEY):
        items = _load_all()
        found = next((r for r in items if r.get("side_task_id") == side_task_id), None)
        if found is None:
            return {"status": "error", "error": f"unknown side_task_id {side_task_id}"}
        old = str(found.get("status") or "")
        if old in _TERMINALE:
            return {"status": "error",
                    "error": f"side task {side_task_id} is already {old} and cannot be hidden"}
        if skjult:
            found["skjult_i_chat"] = True
        else:
            found.pop("skjult_i_chat", None)
        found["updated_at"] = datetime.now(UTC).isoformat()
        _save_all(items)
    return {"status": "ok", "side_task_id": side_task_id, "skjult_i_chat": bool(skjult)}


def arbejds_session_for(session_id: str) -> dict[str, Any] | None:
    """Den ÅBNE side-opgave denne samtale blev startet for — eller ``None``.

    ## Hvorfor den findes

    Bjørn 3/10-2026: «op til trods løste han opgave og så måtte jeg minde ham
    om at markere den flaggede opgave færdig».

    Målt: desk starter opgaven i en NY samtale (`startSideOpgave` → ny session
    → `sendLoesrevet`) og sætter status til `activated`. Men den nye sessions
    id blev aldrig gemt på opgaven, så INTET kunne bagefter vide at den samtale
    hørte til opgave X. Dermed kunne hverken runtimen eller Jarvis selv lukke
    den — den stod som «(i gang)» i prompten indtil et menneske greb ind.

    Det er samme blokerede ligevægt som indbakke-spec'ens §2: en tilstand uden
    nogen der lukker den. Linket her er leddet der manglede.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return None
    for r in _load_all():
        if (r.get("status") in _AABNE
                # En SOVENDE opgave er ikke denne samtales arbejde (16/10-2026).
                # Uden leddet ville lukke-instruksen stå i en samtale der ikke
                # må tage opgaven op endnu — og bede om en lukning af arbejde
                # der ikke er begyndt.
                and not sovende(r)
                and str(r.get("arbejds_session") or "") == sid):
            return r
    return None


def side_tasks_prompt_section(session_id: str | None = None) -> str | None:
    """Listen over åbne side-opgaver — og en eksplicit lukke-instruks når
    DENNE samtale er den der løser én af dem.

    Bjørn 3/10-2026: «måtte jeg minde ham om at markere den flaggede opgave
    færdig». Listen viste opgaven som «(i gang)», men intet sagde hvis ansvar
    det var at lukke den, eller at netop denne samtale VAR arbejdet. En liste
    uden et ansvar bliver stående.

    `session_id` er valgfri, så gamle kaldere ikke brækker — men uden den kan
    afsnittet ikke sige hvilken opgave turen hører til.
    """
    aabne = list_open()
    if not aabne:
        return None
    mit = arbejds_session_for(str(session_id or "")) if session_id else None
    aabne.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    bullets = []
    for r in aabne[:_MAX_SHOWN]:
        # HELE id'et: Jarvis skal kunne afslutte opgaven med præcis det id han
        # ser. Et afkortet id (før: de sidste 10 tegn) kan han ikke bruge.
        sid = str(r.get("side_task_id", ""))
        title = _kort(str(r.get("title", "")), 70)
        # Kun et STIKORD af tldr'en (3/10-2026). Bjørn: «noget forurener
        # side-opgave sessionen … det er samme opgave han laver i en anden
        # session med mig». Målt samme dag stod der 240 tegn med
        # fremgangsmåden i — «Fixet er tre dele: stop aesthetic-daemonens
        # spam, flyt udgangen til send_session_notificati» — afkortet
        # midt i et ord. Det er ikke et flag, det er en arbejdsordre, og den
        # stod i HVER sessions prompt. Opgavens fulde tekst hører i den
        # samtale der løser den, ikke i alle de andre.
        tldr = _kort(str(r.get("tldr", "")).strip(), 70)
        suffix = f" — {tldr}" if tldr else ""
        # Timeren (16/10-2026): en sovende opgave er stadig ÅBEN — den skal ses,
        # men den må ikke læses som noget der skal tages nu. Tiden kommer fra
        # `sove_tekst`, så formateringen ikke findes i to kopier.
        sove = sove_tekst(r)
        tag = (f" ({sove})" if sove
               else " (i gang)" if r.get("status") == "activated"
               else " (i kø)" if r.get("status") == "queued" else "")
        alder = _age_label(r.get("created_at"))
        alder_tag = f" ({alder})" if alder else ""
        bullets.append(f"  [{sid}]{tag} {title}{suffix}{alder_tag}")
    extra = f"  (+{len(aabne) - _MAX_SHOWN} mere)" if len(aabne) > _MAX_SHOWN else ""
    # Mærkningen. Tre egenskaber, som i `visible_run_guard_notices`: hvad
    # listen ER, hvad den IKKE er, og et eksplicit forbud mod den forkerte
    # læsning. Uden det sidste blev en flagget opgave læst som en opgave at
    # gå i gang med — i enhver samtale den stod i.
    afsnit = (
        "Flaggede side-tasks (deferred) — en HUSKELISTE, ikke opgaver du er "
        "sat til. Ingen af dem er bedt om i denne samtale, og du må IKKE "
        "begynde paa en af dem her. Er en af dem arbejdet i netop denne "
        "samtale, staar det udtrykkeligt nedenfor.\n"
        + "\n".join(bullets) + extra
    )
    if mit is not None:
        # Lukke-instruksen. Den staar KUN i den samtale opgaven blev startet
        # for, saa den ikke bliver stoej i alle andre ture.
        afsnit += (
            f"\n\nDENNE samtale er arbejdet paa [{mit.get('side_task_id')}] "
            f"«{mit.get('title')}». Naar den er loest, skal DU lukke den:\n"
            "  dismiss_side_task(side_task_id=\"" + str(mit.get("side_task_id")) + "\", "
            "decision=\"completed\", bevis=\"<hvad du faktisk gjorde>\")\n"
            "Uden et bevis AFVISES lukningen: «completed» er en paastand, og den "
            "skal kunne efterproeves bagefter. Kan den ikke loeses, saa AFVIS den "
            "med en grund (decision=\"dismissed\", reason=\"...\") i stedet for at "
            "lade den staa aaben. "
            "Ingen anden lukker den for dig."
        )
    return afsnit


def _exec_flag_side_task(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.session_context_resolve import aktiv_session_id, aktivt_run_id
    session_id = str(args.get("session_id") or aktiv_session_id("") or "")
    if args.get("finding_kind"):
        from core.services.run_finding_accounting import record_finding
        run_id = str(aktivt_run_id("") or "")
        return record_finding(
            kind=str(args.get("finding_kind") or ""),
            disposition=str(args.get("disposition") or "side_task"),
            path=str(args.get("path") or ""),
            behavior=str(args.get("behavior") or ""),
            evidence=str(args.get("evidence") or ""),
            title=str(args.get("title") or ""),
            next_step=str(args.get("prompt") or ""),
            reason=str(args.get("reason") or ""),
            run_id=run_id, session_id=session_id,
            finding_key=str(args.get("finding_key") or ""),
            existing_side_task_id=str(args.get("existing_side_task_id") or ""),
        )
    return flag(
        title=str(args.get("title") or ""),
        prompt=str(args.get("prompt") or ""),
        tldr=str(args.get("tldr") or ""),
        session_id=session_id,
        finding_key=str(args.get("finding_key") or ""),
        evidence=str(args.get("evidence") or ""),
        not_before=str(args.get("not_before") or ""),
    )


def _exec_list_side_tasks(_args: dict[str, Any]) -> dict[str, Any]:
    items = list_open()
    return {"status": "ok", "side_tasks": items, "count": len(items)}


def _exec_dismiss_side_task(args: dict[str, Any]) -> dict[str, Any]:
    # `decision` er valgfri, så gamle kald uden den stadig betyder «drop den».
    # Med decision=completed kan Jarvis afslutte en opgave han har LAVET, uden
    # et nyt værktøj i det store register (simple_tools.py er over grænsen).
    decision = str(args.get("decision") or "dismissed").strip().lower()
    if decision not in _TERMINALE:
        return {"status": "error", "error": "decision must be 'completed' or 'dismissed'"}
    return resolve(str(args.get("side_task_id") or ""), decision=decision,
                   bevis=str(args.get("bevis") or ""),
                   reason=str(args.get("reason") or ""))


def _exec_activate_side_task(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.session_context_resolve import aktiv_session_id, aktivt_run_id
    decision = str(args.get("status") or "activated").strip().lower()
    if decision not in {"queued", "activated"}:
        return {"status": "error", "error": "status must be queued or activated"}
    return resolve(str(args.get("side_task_id") or ""), decision=decision,
                   arbejds_session=(str(args.get("session_id") or aktiv_session_id("") or "") or None)
                   if decision == "activated" else None,
                   arbejds_run_id=(str(args.get("run_id") or aktivt_run_id("") or "") or None)
                   if decision == "activated" else None)


def _exec_snooze_side_task(args: dict[str, Any]) -> dict[str, Any]:
    """Udskyd en sideopgave til et tidspunkt (16/10-2026).

    Adskilt fra `activate_side_task` med vilje: en udskydelse er ikke en status.
    Opgaven er stadig `pending`/`queued` — den har bare en tid før den må tages
    op, og den tid er et FELT, ikke en tilstand.
    """
    return snooze(
        str(args.get("side_task_id") or ""),
        until=str(args.get("until") or ""),
        reason=str(args.get("reason") or ""),
    )


def _exec_wake_side_task(args: dict[str, Any]) -> dict[str, Any]:
    """Væk en sovende opgave før tid — modstykket til `snooze`."""
    return vaagn(
        str(args.get("side_task_id") or ""),
        reason=str(args.get("reason") or ""),
    )


SIDE_TASK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "flag_side_task",
            "description": (
                "Capture a tangential thing-to-do without derailing the current "
                "task. Use this when you notice something during your main work "
                "that should be addressed later. For an unresolved test gap, "
                "set finding_kind='coverage_gap', disposition, path, behavior, "
                "evidence, and a concrete next step in prompt. Record fixed or "
                "declined findings with the same fields and a reason. A new "
                "relevant failing test must be fixed in current work, never "
                "deferred through a side task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short imperative phrase, e.g. 'Fix stale README badge'."},
                    "prompt": {"type": "string", "description": "Self-contained instructions; the picker won't have your context."},
                    "tldr": {"type": "string", "description": "Plain-English 1-2 sentence summary for the user."},
                    "session_id": {"type": "string"},
                    "finding_kind": {"type": "string", "enum": ["coverage_gap", "new_test_failure", "preexisting_test_failure", "other"]},
                    "disposition": {"type": "string", "enum": ["side_task", "fixed_now", "existing_side_task", "declined", "blocked"]},
                    "path": {"type": "string"},
                    "behavior": {"type": "string"},
                    "evidence": {"type": "string"},
                    "reason": {"type": "string"},
                    "finding_key": {"type": "string"},
                    "existing_side_task_id": {"type": "string"},
                    "not_before": {"type": "string",
                                   "description": "Optional ISO 8601 timestamp: the task sleeps until then and a self-wakeup is booked for that moment."},
                },
                "required": ["title", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_side_tasks",
            "description": "List open side-tasks — pending, queued and active — across all sessions.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dismiss_side_task",
            "description": (
                "Close a flagged side-task. decision='completed' when it has been done "
                "and you can say WHAT was done; decision='dismissed' (default) when the "
                "user said no or it's no longer relevant. Both are REFUSED without their "
                "reason: completed needs `bevis`, dismissed needs `reason`. A closure that "
                "carries no justification is what let a MEMORY section keep claiming "
                "'still open' about work that was already finished. Closed tasks "
                "disappear from the prompt and from Desk and cannot be reopened."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "side_task_id": {"type": "string"},
                    "decision": {"type": "string", "enum": ["completed", "dismissed"],
                                 "description": "completed = done; dismissed = dropped (default)."},
                    "bevis": {"type": "string",
                              "description": "REQUIRED for decision='completed': what was actually done, concretely — commit, file, or measured result."},
                    "reason": {"type": "string",
                               "description": "REQUIRED for decision='dismissed': why the task will not be solved."},
                },
                "required": ["side_task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "activate_side_task",
            "description": "Move a flagged side-task to queue or active work. Active work should include its session_id and run_id when known; this does not dispatch work.",
            "parameters": {
                "type": "object",
                "properties": {"side_task_id": {"type": "string"},
                               "status": {"type": "string", "enum": ["queued", "activated"]},
                               "session_id": {"type": "string"}, "run_id": {"type": "string"}},
                "required": ["side_task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "snooze_side_task",
            "description": (
                "Postpone a flagged side-task until a future time: it stays OPEN "
                "and visible, is marked as sleeping, and a self-wakeup is booked "
                "for `until` so you are actually reminded. Use for 'not before "
                "Tuesday', 'after the deploy'. An `activated` task cannot be "
                "snoozed — queue it first. `until` must be an ISO timestamp in the "
                "FUTURE. Snoozing is NOT a dismissal: use dismiss_side_task when "
                "the task will not be solved at all."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "side_task_id": {"type": "string"},
                    "until": {"type": "string",
                              "description": "ISO 8601 timestamp in the future, e.g. 2026-10-20T09:00:00+02:00."},
                    "reason": {"type": "string",
                               "description": "Optional: why it is postponed."},
                },
                "required": ["side_task_id", "until"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wake_side_task",
            "description": (
                "Wake a sleeping side-task BEFORE its time — clears `not_before` "
                "and cancels the booked wakeup. Use when the reason for the "
                "postponement no longer holds."
            ),
            "parameters": {
                "type": "object",
                "properties": {"side_task_id": {"type": "string"},
                               "reason": {"type": "string"}},
                "required": ["side_task_id"],
            },
        },
    },
]




#: Efter så lang stilstand flyttes en `activated` opgave tilbage til ventende.
#: Stilstand kan aldrig markere `completed`; den status kræver en eksplicit
#: verificering. Tærsklen er et målbart udgangspunkt, ikke bevis på succes.
STILSTAND_MINUTTER: Final[float] = 30.0


def _minutter_siden(tidsstempel: Any) -> float | None:
    """Minutter siden et ISO-tidsstempel — ``None`` hvis det ikke kan læses.

    Fail mod `None`, altså «ved ikke», frem for 0 eller uendeligt: et
    ulæseligt tidsstempel må hverken udløse en lukning eller blokere en.
    """
    if not tidsstempel:
        return None
    try:
        ts = datetime.fromisoformat(str(tidsstempel))
    except (TypeError, ValueError):  # et ulaeseligt tidsstempel er «ved ikke»,
        # ikke «for laenge siden»: fail-retningen staar i docstringen, og en
        # lukning paa et gaet er uigenkaldelig (`completed` er terminal).
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    sekunder = (datetime.now(UTC) - ts).total_seconds()
    if sekunder < 0:
        return None
    return sekunder / 60.0


def _sidst_aktiv(session_id: str) -> str | None:
    """Hvornår samtalen sidst sagde noget (`chat_sessions.updated_at`).

    Verificeret live 3/10-2026: kolonnen følger den seneste besked præcist i
    alle tre aktive samtaler. Én kolonne, ingen besked-gennemløb — samme stil
    som `session_permission` og `session_view`, og modsat det udfaste
    `get_chat_session` der henter hele historikken for ét metadata-felt.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return None
    try:
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute(
                "SELECT updated_at FROM chat_sessions WHERE session_id = ?", (sid,),
            ).fetchone()
        return str(r[0]) if r and r[0] else None
    except Exception:
        logger.warning("side-opgaver: kunne ikke laese aktivitet for %s",
                       sid, exc_info=True)
        return None


def _arbejds_run_aktiv(session_id: str) -> bool:
    """Et langt run må ikke omklassificeres på grund af stille chat-historik."""
    try:
        from core.services.visible_runs import get_active_visible_run
        active = get_active_visible_run() or {}
        return str(active.get("session_id") or "") == session_id
    except Exception:
        logger.warning("side-opgaver: kunne ikke laese aktivt run", exc_info=True)
        return True  # usikkerhed må ikke flytte en aktiv opgave tilbage


def fej_faerdige(*, stilstand_minutter: float | None = None) -> dict[str, Any]:
    """Flyt forladte `activated` opgaver tilbage til `pending`.

    ## Hvorfor en fejer og ikke en overgang ved runnets slutning

    En opgave kan tage flere runs. Det første afsluttede run er ikke bevis
    for at hele sideopgaven er færdig.

    Stilstand er ikke bevis for at arbejdet er udført eller verificeret.
    `completed` er terminal og sættes kun eksplicit. Når en arbejdssamtale
    har ligget stille, gør vi opgaven ventende igen uden at tabe historikken.

    ## Hvorfor ingen ny daemon

    Huset har 40 daemoner der kun tikker når han har travlt. Fejeren kaldes i
    stedet fra to steder der allerede sker: opstart (som husets andre fejere i
    `app.py`) og hver runs efterbehandling. Den sidste betyder at fejningen
    sker netop når der ER aktivitet, uden at nogen poller.

    `tilbage_til_venter` tæller flyttede opgaver; `lukket` bevares som nul for
    gamle kaldere. `venter` tæller opgaver under tærsklen eller med aktivt run.

    Kaster aldrig: en fejer må ikke kunne vælte en opstart eller et run.
    """
    graense = float(stilstand_minutter if stilstand_minutter is not None
                    else STILSTAND_MINUTTER)
    svar: dict[str, Any] = {"lukket": 0, "venter": 0, "uden_link": 0, "ids": [],
                            "vaagnet": 0, "booket": 0, "vaagnede_ids": []}
    try:
        # `list_open()` ligger INDE i try med vilje: fejeren kaldes fra
        # opstarten OG fra hver runs efterbehandling, og en fejer der kaster
        # vaelter begge. Kontrakten er «kaster aldrig», ogsaa naar laesningen
        # selv fejler — `test_fejningen_kaster_ALDRIG` pinner det.
        aabne = list_open()
        for r in aabne:
            if r.get("status") != "activated":
                continue
            sid = str(r.get("arbejds_session") or "").strip()
            if not sid:
                svar["uden_link"] += 1
                continue
            stille = _minutter_siden(_sidst_aktiv(sid))
            if stille is None:
                # Ved ikke → lad den staa. En opgave maa ikke flyttes paa et gaet.
                svar["venter"] += 1
                continue
            if stille < graense:
                svar["venter"] += 1
                continue
            if _arbejds_run_aktiv(sid):
                svar["venter"] += 1
                continue
            tid = str(r.get("side_task_id") or "")
            with med_laas(_STATE_KEY):
                items = _load_all()
                found = next((x for x in items if x.get("side_task_id") == tid), None)
                if found is None or found.get("status") != "activated":
                    continue
                found["status"] = "pending"
                found["stale_at"] = datetime.now(UTC).isoformat()
                found["stale_reason"] = f"arbejdssession stille i {int(stille)}min"
                found.pop("arbejds_session", None)
                found.pop("arbejds_run_id", None)
                _save_all(items)
            svar["ids"].append(tid)
            svar["tilbage_til_venter"] = int(svar.get("tilbage_til_venter") or 0) + 1
            logger.info("side-opgave %s tilbage til ventende — %s stille i %d min",
                        tid, sid, int(stille))

        # ── Timeren (16/10-2026) ──────────────────────────────────────────
        #
        # Samme fejer, fordi det er samme spørgsmål: hvad skal der ske med en
        # opgave hvis tid er inde? `not_before` er SANDHEDEN — vækningen er kun
        # måden at blive mindet på. Derfor to led, og det FØRSTE virker selv om
        # vækningen aldrig fyrer.
        nu = datetime.now(UTC)
        ventende: set[str] | None = None
        for r in aabne:
            nb = _fremtid(r.get("not_before"))
            if nb is None:
                continue
            tid = str(r.get("side_task_id") or "")
            if nb <= nu:
                # Tiden er inde. Vækningen kan være fyret, sprunget over eller
                # aldrig booket — feltet ryddes her, så opgaven står vågen i
                # næste prompt uanset hvad der skete med vækningen. Uden dette
                # led ville ÉN tabt vækning efterlade opgaven sovende for evigt.
                with med_laas(_STATE_KEY):
                    items = _load_all()
                    f = next((x for x in items if x.get("side_task_id") == tid), None)
                    if f is None:
                        continue
                    f_nb = _fremtid(f.get("not_before"))
                    if f_nb is None or f_nb > nu:
                        continue  # ryddet eller udskudt igen imens
                    f.pop("not_before", None)
                    f.pop("vaekning_id", None)
                    f["vaagnet_at"] = nu.isoformat()
                    f["updated_at"] = nu.isoformat()
                    _save_all(items)
                svar["vaagnede_ids"].append(tid)
                svar["vaagnet"] = int(svar.get("vaagnet") or 0) + 1
                logger.info("side-opgave %s vaagnet — not_before passeret", tid)
                continue
            # Sover stadig. Står der en vækning på den? Gør der ikke, og er
            # tiden inden for vækningens rækkevidde, bookes den her — det er
            # sådan en udskydelse længere end 24 timer alligevel bliver mindet
            # om. `_ventende_vaekning_ids` svarer None når den IKKE kunne læses;
            # så booker vi ikke, for vi ville ikke kunne se at der allerede står
            # én, og hver fejning ville lægge et led til.
            if str(r.get("vaekning_id") or ""):
                if ventende is None:
                    ventende = _ventende_vaekning_ids()
                if ventende is None or str(r.get("vaekning_id")) in ventende:
                    svar["venter"] += 1
                    continue
            vid = _book_vaekning(r, nu=nu)
            if not vid:
                svar["venter"] += 1
                continue
            with med_laas(_STATE_KEY):
                items = _load_all()
                f = next((x for x in items if x.get("side_task_id") == tid), None)
                if f is None or not f.get("not_before"):
                    continue
                f["vaekning_id"] = vid
                _save_all(items)
            svar["booket"] = int(svar.get("booket") or 0) + 1
    except Exception:
        logger.warning("side-opgave-fejning fejlede", exc_info=True)
    return svar
