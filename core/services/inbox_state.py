"""Proveniens og bogføring for indbakken.

Opgave 1 og 3 i `docs/superpowers/specs/2026-10-03-indbakke-som-kontrolflade-design.md`.

## Hele pointen: ejer er BEVIS, ikke et flag

Spec'ens skrive-kontrakt siger det kort: *det du selv har lovet kommer tilbage
til dig; huset kan informere, men ikke kræve.* Kun en post Jarvis selv har
startet må nægte en mutation. En daemon, et heartbeat eller et recurring-job må
gerne OPRETTE en post — den må blot aldrig gate.

Derfor må `kilde_ejer="jarvis"` fra en vilkårlig kalder ikke være nok. Et flag
kalderen selv vælger er ikke proveniens; det er en påstand.

## Hvad der faktisk KAN bevise det (målt 3/10-2026 på CT105)

Spec'ens Opgave 1 beder om at knytte registreringen til «et faktisk tool-/run-id
og autentificeret bruger». Jeg målte hvor det står, før jeg valgte kilde:

* `visible_runs.user_id` er **tom på alle 1037 runs** i de sidste syv dage
  (843 synlige, 194 autonome, én distinkt værdi: tom streng). Kolonnen findes,
  men intet skriver den. Den kan altså ikke bevise noget — havde jeg bygget
  verifikationen på den, ville den have svaret «ukendt» hver gang, og hele
  gaten var født død. Det er `built_but_not_connected` i den retning der er
  sværest at se: koden ville være korrekt, og tabellen tom.
* `costs.user_id` er tom i alle 16.695 rækker på to døgn. Samme historie.
* `chat_messages.user_id` ER udfyldt: 3.579 af 4.462 beskeder på to døgn bærer
  et rigtigt bruger-id. Brugeren kendes altså på BESKED-niveau.
* Den autentificerede principal findes i `workspace_context`'s ContextVar,
  sat fra bearer-tokenet. Det er den ÆGTE autentificering, og den er levende i
  det øjeblik et tool-kald kører.

Beviset er derfor **den levende kontekst ved oprettelsen**, ikke en kolonne:
run-id'et skal være det run der kører NU, og den autentificerede bruger skal
være den post'en skrives for. En kalder der sender et run-id der ikke er i gang
har ikke bevist noget.

## Fald-retningen

Ukendt proveniens ⇒ `verificeret_ejer = "ukendt"` og `kraever_handling = False`.
Posten er stadig SYNLIG. En post der ikke kan bevise sit ejerskab må aldrig
blokere — men den må heller ikke forsvinde, for så ville gaten kunne omgås ved
at gøre proveniensen utydelig.

`current_role()` bruges, ikke `effective_role()`: den sidste kalder `touch(sid)`
og **fornyer override-vinduet**. En registrering må ikke forlænge en TOTP-
elevering som skjult sideeffekt.
"""
from __future__ import annotations

import logging
from typing import Any, Final

from core.runtime import db_inbox
from core.runtime.db_inbox import (
    EJER_HUSET,
    EJER_JARVIS,
    EJER_UKENDT,
    STATUS_AABEN,
    STATUS_DONE,
    STATUS_DROP,
)

logger = logging.getLogger(__name__)


def _spor(kind: str, payload: dict[str, Any]) -> None:
    """Publicér til eventbussen. Kaster aldrig — se `inbox_gate._spor`."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(kind, payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_state: kunne ikke spore %s: %s", kind, exc)

#: Kildetyper der ALDRIG gater, uanset hvor kaldet kom fra. Spec'ens tabel:
#: recurring/heartbeat/daemoner må oprette, ikke kræve. Godkendelser har sin
#: egen klasse («venter på Bjørn») og gater ikke, fordi hans svartid ikke må
#: blive Jarvis' blokering.
IKKE_GATENDE_KILDETYPER: Final[frozenset[str]] = frozenset({
    "daemon", "heartbeat", "recurring", "approval", "digest", "proposal",
})


def _autentificeret_bruger_matcher(bruger_id: str) -> bool:
    """Er den autentificerede principal netop `bruger_id`?

    To veje, og KUN to:

    1. Tokenet bærer et bruger-id, og det er det samme. Den normale multi-bruger-vej.
    2. Tokenet bærer intet bruger-id, men rollen er `owner`, og posten skrives
       for det workspace konteksten peger på. Det er ejerens egen vej — og
       `_DEFAULT_STATE` har `role=""`, så en ubundet standardkontekst (scripts,
       daemoner, tests) falder IKKE igennem her. Det er netop meningen: huset
       må ikke kunne gate.
    """
    try:
        from core.identity.workspace_context import (
            current_role,
            current_user_id,
            current_workspace_name,
        )
    except Exception as exc:  # noqa: BLE001
        # Kan vi ikke læse konteksten, kan vi ikke bevise noget. Log det —
        # sker det hver gang, gater intet, og uden linjen ville det aldrig
        # stå nogen steder.
        logger.warning("inbox_state: kunne ikke laese bruger-konteksten: %s", exc)
        return False
    bruger_id = str(bruger_id or "").strip()
    if not bruger_id:
        return False
    uid = str(current_user_id() or "").strip()
    if uid:
        return uid == bruger_id
    return str(current_role() or "").strip().lower() == "owner" and \
        str(current_workspace_name() or "").strip() == bruger_id


def verificeret_jarvis_run(oprettende_run_id: str, bruger_id: str) -> bool:
    """Er dette Jarvis' EGET arbejde, i et run der kører nu, for denne bruger?

    Begge led skal holde. Et run-id alene beviser ikke hvem det var for, og en
    autentificeret bruger alene beviser ikke at det var Jarvis der startede
    posten — det kunne være huset der skrev i hendes navn.
    """
    run = str(oprettende_run_id or "").strip()
    if not run:
        return False
    try:
        from core.services.session_context_resolve import aktivt_run_id
        levende = str(aktivt_run_id("") or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_state: kunne ikke laese aktivt run: %s", exc)
        return False
    # Et kalder-leveret run-id der IKKE er det kørende run er en påstand.
    # Netop den form — «jeg siger det kom fra dette run» — er den spoofing
    # spec'ens Trin 1 tester imod.
    if not levende or levende != run:
        return False
    return _autentificeret_bruger_matcher(bruger_id)


def registrer_kilde(
    *,
    bruger_id: str,
    kildetype: str,
    kilde_id: str,
    oprettende_run_id: str = "",
    paastaaet_ejer: str = "",
    beskrivelse: str = "",
    output_sti: str = "",
    output_bytes: int | None = None,
) -> dict[str, Any]:
    """Registrér en kilde i indbakken. Idempotent per (bruger, kildetype, kilde_id).

    `paastaaet_ejer` ignoreres som bevis — den læses KUN for at kunne mærke en
    post `huset` når kalderen selv siger det. Den kan aldrig løfte en post til
    `jarvis`; det afgør den levende kontekst.
    """
    kildetype_n = str(kildetype or "").strip().lower()

    ejer = EJER_UKENDT
    if verificeret_jarvis_run(oprettende_run_id, bruger_id):
        ejer = EJER_JARVIS
    elif str(paastaaet_ejer or "").strip().lower() == EJER_HUSET:
        ejer = EJER_HUSET

    # Skrive-kontraktens betingelse 1: ejeren er verificeret som Jarvis. Plus
    # kildetypen — en recurring-post er husets, uanset hvem der kaldte.
    kraever_handling = ejer == EJER_JARVIS and kildetype_n not in IKKE_GATENDE_KILDETYPER

    r = db_inbox.opret_eller_hent(
        bruger_id=bruger_id,
        kildetype=kildetype_n,
        kilde_id=kilde_id,
        oprettende_run_id=str(oprettende_run_id or ""),
        verificeret_ejer=ejer,
        kraever_handling=kraever_handling,
        beskrivelse=beskrivelse,
        output_sti=output_sti,
        output_bytes=output_bytes,
    )
    if r.get("status") != "ok":
        # Spec'ens Global Constraint: en handlingskrævende post der ikke blev
        # skrevet SKAL logges på WARNING. En fejlet skrivning må ikke blive en
        # værdi der ser ud som succes.
        logger.warning(
            "inbox_state: kunne IKKE registrere %s/%s for %s (kraever_handling=%s): %s",
            kildetype_n, kilde_id, bruger_id, kraever_handling, r.get("error"))
        _spor("inbox.registrering_fejlede", {
            "bruger_id": bruger_id, "kildetype": kildetype_n, "kilde_id": kilde_id,
            "kraever_handling": kraever_handling, "error": str(r.get("error") or "")})
        return r
    # Kun NYE poster spores. En genregistrering er idempotent og maa ikke
    # taelle igen — ellers ville Opgave 7's «hvor mange blev
    # handlingskraevende» vokse hver gang en notifikation blev genleveret.
    post = r.get("post") or {}
    if int(post.get("paamindelser") or 0) == 0 and not post.get("afgjort_at"):
        _spor("inbox.registreret", {
            "bruger_id": bruger_id, "kildetype": kildetype_n, "kilde_id": kilde_id,
            "verificeret_ejer": ejer, "kraever_handling": kraever_handling})
    return r


# ── Opgave 3: bogføringen ───────────────────────────────────────────────────

#: Hvilken kilde-mekanisme lukker hvilken kildetype. `done` på en vækning skal
#: ramme `mark_wakeup_consumed`; et job stoppes IKKE af `done` — det er en
#: selvstændig, kilde-specifik mutation med egne tilladelser.
_DONE_HANDLERE: Final[dict[str, str]] = {
    "wakeup": "self_wakeup.mark_wakeup_consumed",
}


def _luk_kilden(post: dict[str, Any]) -> dict[str, Any]:
    """Kør kildens egen kvitterings-mekanisme, hvis den har én.

    Returnerer `{"status": "ok"|"ingen"|"fejl", ...}`. «ingen» er et gyldigt
    svar: de fleste kildetyper har ingen kvittering at give, og så er den
    durable afgørelse hele lukningen.
    """
    kildetype = str(post.get("kildetype") or "")
    if kildetype != "wakeup":
        return {"status": "ingen"}
    kilde_id = str(post.get("kilde_id") or "")
    try:
        from core.services import self_wakeup
        # `wake-` ER en del af det rigtige wakeup-id (målt: `wake-` + 10 hex),
        # og `mark_wakeup_consumed` slår op på `record["wakeup_id"] ==
        # wakeup_id`. Strippes præfikset, fejler opslaget og returnerer
        # «wakeup not found». Præfikset vælger mekanisme; det klippes ikke af.
        svar = self_wakeup.mark_wakeup_consumed(kilde_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_state: mark_wakeup_consumed(%s) kastede: %s", kilde_id, exc)
        return {"status": "fejl", "error": str(exc)}
    if isinstance(svar, dict) and str(svar.get("status") or "") not in ("ok", "already"):
        # Kilden selv FANGER sine fejl og returnerer dem som en værdi. Et
        # `except` omkring kaldet rammes derfor aldrig — fejlen skal læses af
        # svaret, ellers bliver den en værdi vi ikke kan skelne fra succes.
        return {"status": "fejl", "error": str(svar.get("error") or svar)}
    return {"status": "ok"}


def _find_i_kilderne(bruger_id: str, post_id: str) -> tuple[str, str] | None:
    """(kildetype, beskrivelse) for et id visningen VISER men tabellen ikke har.

    ## Hullet dette lukker

    Målt 4/10-2026 kl. 07:16, Jarvis' FØRSTE brug af værktøjerne: `inbox` →
    ok, derefter `inbox_done(wake-cf0577f5bb)` → fejl, `inbox_drop(
    phase3-final-classifier)` → fejl, `inbox_drop(jarvis_bare)` → fejl. Tre af
    seks kald. Han skrev det selv: «kunne ikke lukke dem (id'erne matcher
    ikke)».

    Årsagen: `byg_indbakke` læser FIRE kilder — `inbox_items`, vækninger, jobs
    og godkendelser — mens `done`/`drop` kun kendte `inbox_items`. De tre
    poster var ældre end skriveren i `schedule_self_wakeup`, så de havde ingen
    række. Visningen viste altså poster der ikke kunne lukkes: en blindgyde,
    og samme form som da skriveren manglede helt.

    ## Hvorfor den spørger VISNINGENS egne adaptere

    Ikke id-præfikset. Spec'ens Opgave 3 trin 3 siger det: «vælg kildehandler
    fra postens typede `kildetype`, ikke alene fra et brugerleveret
    id-præfiks.» Og ved at bruge `Kilder()` — de samme funktioner visningen
    bruger — kan de to ikke blive uenige om hvad der findes. Det er en garanti
    ved konstruktion frem for to lister der skal holdes i sync.
    """
    try:
        from core.services.inbox_view import Kilder
        k = Kilder()
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_state: kunne ikke laese kilderne: %s", exc)
        return None
    for hent, kildetype, id_felt, tekst_felter in (
            (k.vaekninger, "wakeup", "wakeup_id", ("prompt", "reason")),
            (k.jobs, "job", "id", ("navn", "beskrivelse", "kommando")),
    ):
        try:
            for r in hent(bruger_id) or []:
                if str(r.get(id_felt) or "").strip() != post_id:
                    continue
                for felt in tekst_felter:
                    if str(r.get(felt) or "").strip():
                        return kildetype, str(r[felt])[:200]
                return kildetype, ""
        except Exception as exc:  # noqa: BLE001
            # Én kilde der fejler maa ikke skjule de andre — men den skal ses,
            # ellers bliver et id tavst «ukendt» fordi en laesning braekkede.
            logger.warning("inbox_state: kilde %s fejlede ved opslag af %r: %s",
                           kildetype, post_id[:40], exc)
    return None


def _hent_eller_optag(bruger_id: str, post_id: str) -> dict[str, Any] | None:
    """Postens række — og opret den hvis KILDEN findes men rækken ikke gør.

    Posten optages som `ukendt` og dermed ikke-gatende, og det er ærligt: vi
    kunne ikke bevise proveniensen da den blev oprettet, for den blev oprettet
    før registreringen fandtes. Men den skal kunne LUKKES — en afgørelse er
    hele pointen, og en post man ikke kan afgøre er værre end ingen post.
    """
    post = db_inbox.hent(bruger_id=bruger_id, kilde_id=post_id)
    if post is not None:
        return post
    fundet = _find_i_kilderne(bruger_id, post_id)
    if fundet is None:
        return None
    kildetype, beskrivelse = fundet
    r = db_inbox.opret_eller_hent(
        bruger_id=bruger_id, kildetype=kildetype, kilde_id=post_id,
        verificeret_ejer=EJER_UKENDT, kraever_handling=False,
        beskrivelse=beskrivelse)
    if r.get("status") != "ok":
        logger.warning("inbox_state: kunne ikke optage %s/%s for %s: %s",
                       kildetype, post_id, bruger_id, r.get("error"))
        return None
    _spor("inbox.optaget_ved_lukning", {
        "bruger_id": bruger_id, "kildetype": kildetype, "kilde_id": post_id,
        "grund": "kilden fandtes, raekken gjorde ikke"})
    return r.get("post")


def done(bruger_id: str, post_id: str) -> dict[str, Any]:
    """Kvittér en ALLEREDE UDFØRT opgave. Typet svar, aldrig prosa."""
    post = _hent_eller_optag(bruger_id, post_id)
    if post is None:
        # Et ukendt id må ALDRIG melde succes. Det er husets hyppigste
        # fejlform, og her er den særlig grim: et «ok» på et id der ikke
        # findes ville frigive gaten uden at lukke noget.
        return {"status": "ukendt", "id": post_id}
    kilde = _luk_kilden(post)
    if kilde.get("status") == "fejl":
        return {"status": "fejl", "type": str(post.get("kildetype") or ""),
                "id": post_id, "error": str(kilde.get("error") or "")}
    # Kildens ændring FØRST, derefter den durable afgørelse. Rækkefølgen er
    # valgt: fejler afgørelsen efter en lykket kilde-ændring, står posten åben
    # og et nyt `done` er idempotent (kilden svarer «already»). Omvendt
    # rækkefølge ville efterlade en kvitteret post hvis kilde aldrig blev lukket.
    r = db_inbox.afgoer(bruger_id=bruger_id, kilde_id=post_id,
                        ny_status=STATUS_DONE, grund="kvitteret")
    if r.get("status") == "allerede":
        return {"status": "ok", "type": str(post.get("kildetype") or ""),
                "id": post_id, "allerede": str(r.get("havde") or "")}
    if r.get("status") != "ok":
        return {"status": "fejl", "type": str(post.get("kildetype") or ""),
                "id": post_id, "error": str(r.get("error") or r.get("status"))}
    _spor("inbox.afgjort", {"bruger_id": bruger_id, "kilde_id": post_id,
                            "udfald": "done", "kildetype": str(post.get("kildetype") or "")})
    return {"status": "ok", "type": str(post.get("kildetype") or ""), "id": post_id}


def drop(bruger_id: str, post_id: str, reason: str) -> dict[str, Any]:
    """Afvis en åben post med begrundelse.

    Den stopper **ikke** et kørende job eller en agent. Annullering er en
    selvstændig mutation med egne tilladelser, og at skjule den bag `drop`
    ville gøre en afvisning til et stop uden at nogen bad om det.
    """
    grund = str(reason or "").strip()
    if not grund:
        return {"status": "fejl", "id": post_id, "error": "reason kraeves"}
    post = _hent_eller_optag(bruger_id, post_id)
    if post is None:
        return {"status": "ukendt", "id": post_id}
    r = db_inbox.afgoer(bruger_id=bruger_id, kilde_id=post_id,
                        ny_status=STATUS_DROP, grund=grund)
    if r.get("status") == "allerede":
        return {"status": "ok", "type": str(post.get("kildetype") or ""),
                "id": post_id, "allerede": str(r.get("havde") or "")}
    if r.get("status") != "ok":
        return {"status": "fejl", "type": str(post.get("kildetype") or ""),
                "id": post_id, "error": str(r.get("error") or r.get("status"))}
    _spor("inbox.afgjort", {"bruger_id": bruger_id, "kilde_id": post_id,
                            "udfald": "drop", "grund": grund,
                            "kildetype": str(post.get("kildetype") or "")})
    return {"status": "ok", "type": str(post.get("kildetype") or ""), "id": post_id}


__all__ = [
    "EJER_HUSET", "EJER_JARVIS", "EJER_UKENDT", "STATUS_AABEN",
    "IKKE_GATENDE_KILDETYPER", "done", "drop", "registrer_kilde",
    "verificeret_jarvis_run",
]
