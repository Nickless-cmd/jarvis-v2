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
    EJER_BRUGER,
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
    # `decision` (4/10-2026): beslutnings-gaten har sin EGEN eskalering i tre
    # bånd, og indbakken må ikke lægge en anden oven på den. I dag gater de
    # alligevel ikke, fordi de registreres uden for et levende run og derfor
    # får ejeren `huset` — men det er en KONSEKVENS af proveniensen, ikke en
    # regel. Registrerede nogen senere en beslutning inde i et run, ville den
    # kunne nægte en mutation, og så ville to gater skubbe til det samme.
    "decision", "agent_result",
    # `scheduled` (10/10-2026): en planlagt opgave er husets, ikke en
    # forpligtelse. Den maa oprette, aldrig naegte en mutation. Uden dette
    # ville hver fyret `schedule_task` laegge en blokerende post i indbakken
    # — og en planlagt efterkontrol ville gate det naeste vaerktoejskald.
    "scheduled",
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


#: Har vi allerede advaret om det ubundne fald i denne proces? Én linje er
#: diagnosen; én per tur er støj der gør loggen ulæselig.
_HAR_ADVARET: list[bool] = [False]


def _ejer_workspace() -> str:
    """Ejerens workspace-navn — `workspace_context`'s EGEN standard.

    Hardkodet «bjorn» ville være en fjerde kopi af samme sandhed. Navnet blev
    omdøbt fra «default» én gang før (Task 5), og en kopi her ville have
    overlevet omdøbningen tavst og lukket ejeren ude.
    """
    try:
        from core.identity.workspace_context import _DEFAULT_STATE
        return str(getattr(_DEFAULT_STATE, "workspace_name", "") or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_state: kunne ikke laese ejer-workspacet: %s", exc)
        return ""


def _ejer_id() -> str:
    """Ejerens rigtige bruger-id, med workspace-navnet som sidste udvej.

    Faldet er med vilje mod at BEVARE hans indbakke. Svarer `owner_user_id()`
    tom — intet ejer-record, en DB der ikke kan læses — er alternativet en
    indbakke der er tom hver tur uden at sige hvorfor, og det er den fejlform
    hele dette spor handler om. Den gamle adfærd er stadig den dårligste af de
    to, så den er sidst og den siger til.
    """
    try:
        from core.identity.owner_resolver import owner_user_id
        uid = str(owner_user_id() or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_state: kunne ikke oploese ejeren: %s", exc)
        uid = ""
    if uid:
        return uid
    ws = _ejer_workspace()
    logger.warning("inbox_state: ingen ejer-identitet kunne oploeses — falder "
                   "tilbage paa workspace-navnet %r. Det er den gamle adfaerd "
                   "der opfandt en ANDEN indbakke til samme person.", ws)
    return ws


def _advar_om_ubundet_fald(rolle: str) -> None:
    """Sig ÉN gang at læsningen kørte uden bundet bruger.

    Tilstanden er lovlig for ejeren og farlig for alle andre, og inde i
    processen kan de to ikke skelnes. Så længe det er sådan, er en linje i
    loggen det eneste der kan gøre tilstanden synlig — uden den sker faldet
    tavst, og tavshed er præcis hvad der lod to indbakker opstå.
    """
    if _HAR_ADVARET[0]:
        return
    _HAR_ADVARET[0] = True
    logger.warning(
        "inbox_state: laeser indbakken UDEN bundet bruger-id (rolle=%r) og "
        "falder tilbage paa ejeren. Lovligt for Bjoern, hvis desk-request "
        "ikke binder noget; en TABT ContextVar i en anden brugers session ser "
        "identisk ud herinde. Lukkes foerst naar ejeren bindes eksplicit.",
        rolle)


def bruger_for_workspace(navn: str) -> str:
    """Oversæt et workspace-NAVN til et bruger-id. Tom streng når det ikke går.

    Den findes fordi nogle kilder kun kender navnet: `self_wakeup` læser
    vækningens egen række, hvor `user_id` kan være tom og `workspace_name`
    udfyldt. Den gamle kode skrev så navnet direkte i `bruger_id` — og det er
    netop sammenblandingen af to navnerum i én kolonne der lavede to
    indbakker til samme person.

    Ejerens workspace oversættes til `owner_user_id()`; alle andre slås op i
    bruger-tabellen. Kan navnet ikke oversættes, svarer den tomt frem for at
    gætte: en post i den forkerte indbakke er værre end ingen post.
    """
    navn = str(navn or "").strip()
    if not navn:
        return ""
    if navn == _ejer_workspace():
        return _ejer_id()
    try:
        from core.identity.users import find_user_by_workspace
        u = find_user_by_workspace(navn)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_state: kunne ikke slaa workspace %r op: %s", navn, exc)
        return ""
    uid = str(getattr(u, "discord_id", "") or "").strip() if u is not None else ""
    if not uid:
        # Et navn uden bruger. Tavshed her ville lade posten forsvinde uden
        # spor, og det er den fejlform hele dette spor handler om.
        logger.warning("inbox_state: workspace %r har ingen bruger — posten "
                       "kan ikke knyttes til en indbakke", navn)
    return uid


def laese_bruger() -> str:
    """HVIS indbakke skal læses? Tom streng når det ikke kan afgøres.

    ## Hullet dette lukker

    Målt 4/10-2026. De tre LÆSE-steder — prompt-sektionen, værktøjerne og
    ruten — faldt tilbage på `current_workspace_name()` når `current_user_id()`
    var tom:

        uid or current_workspace_name()

    Og `_DEFAULT_STATE.workspace_name` er **"bjorn"**. Så i en anden
    husstandsbrugers session, hvis ContextVar'en var tabt — og den fælde er
    målt to gange i dette hus (`tool_scope_ctxvar_lost`,
    `contextvar_async_generator_gap`) — ville `_bruger_id()` svare «bjorn», og
    **Bjørns indbakke stod i den anden brugers prompt.**

    Skrive-vejen gjorde det rigtigt hele tiden
    (`_autentificeret_bruger_matcher` kræver `role == "owner"`). Læse- og
    skrive-vejen var altså uenige om samme spørgsmål, og uenigheden lækkede i
    den farlige retning. Det er tredje gang i dette spor at to definitioner af
    samme regel driver fra hinanden — og den dyreste, for de andres workspaces
    er krypterede netop for at det ikke kan ske.

    ## Hvorfor faldet ikke bare blev FJERNET

    Min første rettelse krævede `current_role() == "owner"` for at falde
    tilbage. Den var fail-closed og den ville have slukket Bjørns egen
    indbakke, hver tur. Målt på CT105 4/10:

      * `users` har to rækker, `lotte` og `rune`, begge `member`. Der er
        **ingen owner-række** — Bjørn er den implicitte ejer.
      * Hans desk-request bærer derfor intet bruger-header, så middlewaren
        tager `not user_id and not project_root`-hurtigvejen og binder
        **ingenting**.
      * Standard-konteksten er `('bjorn', '', '')`.

    Bjørns ægte tilstand er altså BYTE-IDENTISK med en tabt ContextVar. Inde i
    processen findes der intet felt der skiller dem. En rolle-gate her ville
    ikke lukke lækagen; den ville kun flytte skaden fra «en anden ser hans
    indbakke» til «han har ingen». Se `docs/` og spørgsmålet til ham: hullet
    lukkes først når ejeren BINDES eksplicit, og det er en ændring i
    auth-middlewaren, ikke her.

    ## Hvad faldet så peger på

    `owner_user_id()`, ikke `current_workspace_name()`. Det er en rigtig
    identitet frem for et mappenavn, og forskellen var ikke kosmetisk — målt
    samme dag stod der **to indbakker til samme person**:

        1246415163603816499 | 70 raekker | 18 wakeup done, 11 drop, 4 job drop
        bjorn               | 36 raekker | 35 decision aaben, 0 lukket

    De 70 er dem Jarvis faktisk arbejder i; de 36 er dem workspace-faldet
    skrev, og ingen af dem er nogensinde blevet lukket. De samme beslutninger
    stod under BEGGE id'er. Dobbelt-sandhed, opfundet af en fallback — og
    præcis det `Source of Truth` forbyder.

    `current_role()`, ikke `effective_role()`: den sidste kalder `touch(sid)`
    og fornyer override-vinduet. En læsning må ikke forlænge en TOTP-elevering.
    """
    try:
        from core.identity.workspace_context import (
            current_role,
            current_user_id,
            current_workspace_name,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_state: kunne ikke laese bruger-konteksten: %s", exc)
        return ""
    uid = str(current_user_id() or "").strip()
    if uid:
        return uid
    rolle = str(current_role() or "").strip().lower()
    if rolle and rolle != "owner":
        # En BUNDET ikke-ejer. Her er der positivt bevis for at det ikke er
        # ejeren, og saa falder vi ikke tilbage. Det er den ene halvdel af
        # laekagen der KAN lukkes inde i processen.
        return ""
    if str(current_workspace_name() or "").strip() != _ejer_workspace():
        # Et ANDET workspace uden rolle: samme slutning. Og tomt workspace er
        # heller ikke ejerens — en helt ubundet kalder (et script, en daemon,
        # en test der nulstiller alt) skal faa den typede «ingen bruger»-fejl
        # frem for husets indbakke. Standardtilstanden er «bjorn», ikke tom,
        # saa Bjoerns egen vej rammes ikke af det.
        return ""
    _advar_om_ubundet_fald(rolle)
    return _ejer_id()


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


def _kilde_ejer_kan_loefte(kildetype: str, kilde_ejer: str) -> bool:
    """Må KILDENS egen ejer sætte etiketten til `jarvis`?

    Kun når kildetypen ikke kan gate. Den grænse ER sikkerheden: uden den
    kunne et `kilde_ejer="jarvis"` på en `job`-post både mærke OG låse, og så
    var skrive-kontrakten omgået ad en ny vej — «huset kan informere, men ikke
    kræve» ville være uden virkning igen, bare med et andet parameter-navn.

    Med grænsen kan denne vej ændre ETIKETTEN og aldrig magten.
    """
    if str(kilde_ejer or "").strip().lower() != EJER_JARVIS:
        return False
    return str(kildetype or "").strip().lower() in IKKE_GATENDE_KILDETYPER


def registrer_kilde(
    *,
    bruger_id: str,
    kildetype: str,
    kilde_id: str,
    oprettende_run_id: str = "",
    paastaaet_ejer: str = "",
    kilde_ejer: str = "",
    beskrivelse: str = "",
    output_sti: str = "",
    output_bytes: int | None = None,
    expires_at: str = "",
) -> dict[str, Any]:
    """Registrér en kilde i indbakken. Idempotent per (bruger, kildetype, kilde_id).

    `paastaaet_ejer` ignoreres som bevis — den læses KUN for at kunne mærke en
    post `huset` når kalderen selv siger det. Den kan aldrig løfte en post til
    `jarvis`; det afgør den levende kontekst.

    `kilde_ejer` er den ANDEN slags ejerskab, og den er ikke en påstand om
    noget kalderen selv fandt på: den er ejeren som KILDENS EGEN RÆKKE bærer
    den — i dag `behavioral_decisions.created_by`. Den accepteres kun for
    kildetyper der ikke kan gate (`_kilde_ejer_kan_loefte`), så den flytter
    etiketten `[huset]` → `[dig]` og aldrig evnen til at nægte en mutation.

    ## Hvorfor den findes (målt 4/10-2026)

    Beslutnings-posterne blev mærket `huset`, fordi de registreres fra en
    baggrundsvej uden et levende run. Mærket beskriver SKRIVEREN — og blev
    læst som et udsagn om EJERSKABET. Bjørn: «du må aldrig være i tvivl om
    hvad der er til dig.» En beslutning er Jarvis' egen forpligtelse
    (`created_by` står `jarvis` i 79 af 80 rækker), og posten skal sige det.
    """
    kildetype_n = str(kildetype or "").strip().lower()

    ejer = EJER_UKENDT
    if verificeret_jarvis_run(oprettende_run_id, bruger_id):
        ejer = EJER_JARVIS
    elif _kilde_ejer_kan_loefte(kildetype_n, kilde_ejer):
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
        # En kilde der KENDER en frist kan sætte den (5/10-2026). Er den tom,
        # afgør `db_inbox.opret_eller_hent` om posten skal have en: kun en post
        # der kan nægte en mutation får en, og reglen står ét sted.
        expires_at=expires_at,
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
    # En UDSAT post kommer tilbage (målt 5/10-2026). `drop` og `udloebet` er
    # udsættelser, ikke afgørelser — så en kilde der stadig melder posten aktuel
    # må genåbne den. Uden dette var genregistrering en no-op: `opret_eller_hent`
    # returnerer en eksisterende række urørt, `expires_at` blev aldrig sat, og
    # 76 beslutnings-poster stod i `drop` og kom aldrig igen.
    #
    # Grænsen er den samme som for etiketten: kun en kildetype der IKKE kan
    # nægte en mutation må flyttes af sin kilde — ellers kunne en daemon
    # genåbne en blokerende post.
    post = r.get("post") or {}
    if (kildetype_n in IKKE_GATENDE_KILDETYPER
            and str(post.get("status") or "") in db_inbox.GENAABNING_STATUSSER):
        g = db_inbox.genaabn_af_kilde(bruger_id=bruger_id, kilde_id=kilde_id)
        if g.get("status") == "ok":
            r = {**r, "post": g.get("post") or post, "genaabnet": True}
            post = r["post"]
    # ── Teksten følger kilden (målt 5/10-2026) ──────────────────────────────
    #
    # `opret_eller_hent` er `INSERT OR IGNORE`: beskrivelsen blev skrevet ÉN
    # gang og derefter frossen. Målt i drift stod `dec_b596dcde9db7` med
    # «[imperativ 33%]» i indbakken mens gaten viste «Adherence 50% (advisory
    # band)» — den flade Bjørn læser løj om båndet, fordi scoren havde ændret
    # sig siden registreringen.
    #
    # Det er samme fejlform som `expires_at`: en regel der kun gælder ved INSERT
    # dækker ikke de rækker der allerede står der. Kilden er den eneste der
    # KENDER sin tekst, så den må rette den — men kun på en post der ikke er
    # afgjort, og kun når teksten faktisk er en anden. Rækkefølgen er med vilje
    # genåbning FØRst: en post der netop er genåbnet er `aaben`, og får derfor
    # sin friske tekst i samme runde.
    if beskrivelse:
        o = db_inbox.opdater_beskrivelse(
            bruger_id=bruger_id, kilde_id=kilde_id, beskrivelse=beskrivelse)
        if o.get("status") == "ok":
            r = {**r, "post": o.get("post") or post}
            post = r["post"]
    if int(post.get("paamindelser") or 0) == 0 and not post.get("afgjort_at"):
        _spor("inbox.registreret", {
            "bruger_id": bruger_id, "kildetype": kildetype_n, "kilde_id": kilde_id,
            "verificeret_ejer": ejer, "kraever_handling": kraever_handling})
    return r


# ── Bjørns egen vej ind (4/10-2026) ─────────────────────────────────────────

#: Kildetypen for noget et MENNESKE har flagget. Egen type, ikke `job` eller
#: `daemon`, fordi den har en anden proveniens end alle de andre: den er
#: oprettet af en autentificeret handling, ikke udledt af en kilde.
KILDETYPE_FLAG: Final[str] = "bug"


def flag_fra_bruger(
    *,
    bruger_id: str,
    titel: str,
    beskrivelse: str = "",
    bloker: bool = False,
) -> dict[str, Any]:
    """Et menneske flagger noget. Den FJERDE skriver.

    ## Hullet dette lukker

    Indbakken havde tre skrivere: Jarvis gennem verificeret proveniens, huset
    gennem `paastaaet_ejer="huset"`, og `ukendt` når intet kunne bevises. Der
    fandtes **ingen vej hvor en menneskelig handling oprettede en post** —
    `registrer_kilde` blev kun kaldt af kilder.

    `side_tasks` var næsten det, men med en anden sandhed: en JSON-fil uden
    bruger-scoping, uden proveniens, uden terminale tilstande og uden
    retention. Og dens eneste skriver var et VÆRKTØJ, altså kun Jarvis — som
    oven i købet har det skjult fra sit katalog (`tool_hunt_nudge` siger det),
    så det kræver `load_more_tools` og dermed 92 % → 26 % cache-hit. Målt: 8
    poster i alt, alle terminale. Fladen fandtes og var praktisk uopnåelig.

    ## `bloker` er et VALG, ikke en bivirkning

    Bjørns afgørelse 4/10: «synlig men gater ikke som standard».

    Normal gating kræver `verificeret_ejer == "jarvis"` — det du selv har
    lovet kommer tilbage til dig. En post Bjørn flagger har ham som ejer og
    ville derfor aldrig gate under den regel. `bloker` er den eksplicitte
    undtagelse: huset kan informere, Jarvis kan binde sig selv, og Bjørn kan
    **kræve** — men kun når han siger det.

    Faren er konkret og målt i dag: en post der gater kan spærre for netop de
    værktøjer der skulle rette den. Det var dead-locken i
    `mark_wakeup_consumed`. Derfor er `bloker` falsk som standard, og
    `inbox_done`/`inbox_drop` virker uændret på en blokerende post — så
    pressionen er reel uden at kunne låse ham fast.
    """
    bruger_id = str(bruger_id or "").strip()
    titel = str(titel or "").strip()
    if not bruger_id:
        return {"status": "fejl", "error": "bruger_id kraeves"}
    if not titel:
        # En post uden titel kan ikke navngives i visningen, og
        # skrive-kontraktens betingelse 2 siger at en post der ikke kan
        # navngives ikke må gate. Så afvis frem for at oprette en stum post.
        return {"status": "fejl", "error": "titel kraeves"}

    from uuid import uuid4
    kilde_id = f"bug-{uuid4().hex[:10]}"
    tekst = f"{titel} — {beskrivelse}".strip(" —") if beskrivelse else titel
    r = db_inbox.opret_eller_hent(
        bruger_id=bruger_id,
        kildetype=KILDETYPE_FLAG,
        kilde_id=kilde_id,
        # Ejeren ER brugeren. Det er ikke en påstand: ruten kalder kun med den
        # autentificerede principal, og `bruger_id` kommer derfra.
        verificeret_ejer=EJER_BRUGER,
        kraever_handling=bool(bloker),
        beskrivelse=tekst,
        bloker=bool(bloker),
    )
    if r.get("status") != "ok":
        logger.warning("inbox_state: kunne IKKE flagge %r for %s: %s",
                       titel[:60], bruger_id, r.get("error"))
        return r
    _spor("inbox.flagget_af_bruger", {
        "bruger_id": bruger_id, "kilde_id": kilde_id, "bloker": bool(bloker)})
    return {"status": "ok", "id": kilde_id, "bloker": bool(bloker),
            "post": r.get("post")}


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


def _afgoer_sideopgave(bruger_id: str, post_id: str, *, decision: str,
                       reason: str = "") -> dict[str, Any] | None:
    """Route en sideopgave til dens eget lager; skriv aldrig inbox_items.

    Et `side-` præfiks er kun routing. Ejerskab kontrolleres før opslaget,
    og et ukendt id bliver aldrig til en vellykket afgørelse.
    """
    if not str(post_id or "").startswith("side-"):
        return None
    if str(bruger_id or "") != _ejer_id():
        return {"status": "ukendt", "id": post_id}
    from core.services.side_tasks import get, resolve
    task = get(post_id)
    if task is None:
        return {"status": "ukendt", "id": post_id}
    old = str(task.get("status") or "")
    if old in {"completed", "dismissed"}:
        if old == decision:
            return {"status": "ok", "type": "side_task", "id": post_id,
                    "allerede": old}
        return {"status": "fejl", "type": "side_task", "id": post_id,
                "error": f"side task is already {old}"}
    result = resolve(post_id, decision=decision, lukket_af="inbox", reason=reason)
    if result.get("status") != "ok":
        return {"status": "fejl", "type": "side_task", "id": post_id,
                "error": str(result.get("error") or "status update failed")}
    return {"status": "ok", "type": "side_task", "id": post_id}


def done(bruger_id: str, post_id: str) -> dict[str, Any]:
    """Kvittér en ALLEREDE UDFØRT opgave. Typet svar, aldrig prosa."""
    side = _afgoer_sideopgave(bruger_id, post_id, decision="completed")
    if side is not None:
        return side
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
    side = _afgoer_sideopgave(bruger_id, post_id, decision="dismissed", reason=grund)
    if side is not None:
        return side
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
    "KILDETYPE_FLAG", "flag_fra_bruger", "laese_bruger",
    "EJER_BRUGER", "EJER_HUSET", "EJER_JARVIS", "EJER_UKENDT", "STATUS_AABEN",
    "IKKE_GATENDE_KILDETYPER", "done", "drop", "registrer_kilde",
    "verificeret_jarvis_run",
]
