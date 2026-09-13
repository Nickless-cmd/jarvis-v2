"""Ejerskab over registreringer — Fase 9, `RuntimePluginLifecycle`.

Exit-kriterierne der bæres her:

    «scoped registration is identity-based, exact-entry disposal is idempotent,
     empty layers are reclaimed, and disposal reaches quiescence»
    «disposal reports unresolved ownership»

## Hvorfor huset har brug for det

Kortlagt 13/9-2026. Der findes **elleve** registre i `core/` af formen
`dict[navn] = spec`, og af dem har præcis nul en afhændings-vej der returneres
til den der registrerede:

    internal_cadence.register_producer     -> None
    central_layer_contract.register_layer  -> None
    nerve_registry.register                -> dict, ingen live-kalder til unregister
    gate_kernel.register                   -> None, listen tømmes aldrig
    skill_contract_registry.register_skill -> None
    error_healers.register_healer          -> None
    jobs_engine.register_handler           -> None
    projection_runtime.register            -> kun _unregister_all_for_tests
    central_injection_registry.register    -> None
    autonomy_proposal_queue.register_*     -> None
    base_plugin.register_plugin            -> kun clear_registry (test-hjælper)

Den eneste ægte handle/afhænd-parring i huset er eventbussens
`subscribe()`/`unsubscribe()`.

Konsekvensen står i `apps/api/jarvis_api/app.py`: ~30 håndholdte `stop_*()`-kald
i en fast rækkefølge, hver pakket i sit eget `try/except: pass`, uden frist og
uden nogen garanti for at nedlukningen sker i modsat orden af opstarten. Og
48 `start_*` mod 42 `stop_*` — parringen er manuel og ufuldstændig.

## Hvad et omfang (`Omfang`) er

Et sted at lægge sine registreringer, så de kan **forsvinde sammen**. Ikke et
nyt register — en ejer oven på de registre der findes.

Reglerne, og hvorfor hver af dem:

- **Identitet, ikke navn.** To registreringer med samme navn er to
  registreringer. Nøglen er postens egen identitet, så en afhændelse rammer
  præcis den post der blev lagt — ikke en senere med samme navn.
- **Afhændelse er idempotent.** Kaldes den to gange, sker der noget én gang.
  Uden det bliver «afhænd for en sikkerheds skyld» til en fejlkilde, og så
  holder folk op med at gøre det.
- **Tomme lag ryddes.** Et omfang uden poster efterlader ikke en tom bøtte.
  Ellers vokser registret med lig af omfang der er væk.
- **Modsat orden.** Sidst registreret afhændes først, ligesom man ruller en
  stak tilbage. Et lag der blev bygget oven på et andet skal væk først.
- **Uafklaret ejerskab RAPPORTERES.** Fejler en afhændelse, forsvinder den
  ikke i et `except: pass`. Den står i rapporten med navn og grund. Det er hele
  forskellen på en nedlukning man kan stole på og en der ser stille ud.

## Frist og ro (`quiescence`)

`afhaend(frist)` stopper først tilgang, tømmer så det ejede arbejde indtil
fristen, og afregistrerer til sidst i modsat orden. Når den er færdig, er
omfanget **roligt**: ingen nye poster kan komme ind, og ingen gamle er tilbage.

Nås fristen ikke, er det ikke en fejl der kastes — det er en rapport med det der
stod tilbage. En nedluknings-rutine der kaster gør nedlukningen værre.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

#: Standard-frist for en afhændelse. Samme størrelsesorden som eventbussens
#: `_WRITER_SHUTDOWN_TIMEOUT` (5,0 s) — den eneste eksisterende drain-til-frist
#: i huset, og der er ingen grund til at opfinde et andet tal.
STANDARD_FRIST_S = 5.0


@dataclass
class Post:
    """Én registrering og vejen tilbage.

    `identitet` er postens egen — ikke `navn`. To poster kan hedde det samme,
    og en afhændelse skal ramme den rigtige.
    """

    identitet: int
    navn: str
    afhaend: Callable[[], Any]
    afhaendt: bool = False


@dataclass
class Rapport:
    """Hvad en afhændelse efterlod. Det er den her der gør nedlukningen ærlig."""

    omfang: str = ""
    afhaendte: tuple[str, ...] = ()
    #: (navn, grund) for hver post der IKKE kunne afhændes. Spec'ens
    #: «unresolved ownership» — det der ellers ville forsvinde i `except: pass`.
    uafklarede: tuple[tuple[str, str], ...] = ()
    #: Naaede vi ro inden fristen?
    rolig: bool = True
    #: Arbejde der stadig koerte da fristen loeb ud.
    udestaaende_arbejde: int = 0
    varighed_s: float = 0.0

    @property
    def ren(self) -> bool:
        return not self.uafklarede and self.rolig

    def forklar(self) -> list[str]:
        ud: list[str] = []
        for navn, grund in self.uafklarede:
            ud.append(f"{self.omfang}: {navn} kunne ikke afhaendes — {grund}")
        if not self.rolig:
            ud.append(f"{self.omfang}: fristen loeb ud med "
                      f"{self.udestaaende_arbejde} stykke(r) arbejde i gang")
        return ud


class Omfang:
    """Ejer af et sæt registreringer. Alt lagt heri forsvinder sammen."""

    def __init__(self, navn: str) -> None:
        self.navn = str(navn)
        self._poster: list[Post] = []
        self._laas = threading.RLock()
        self._lukket = False
        self._arbejde = 0

    # ------------------------------------------------------------- registrering

    def registrer(self, navn: str, afhaend: Callable[[], Any]) -> Callable[[], bool]:
        """Læg en post i omfanget. Returnerer dens EGEN afhændelses-vej.

        Den returnerede funktion afhænder præcis denne post — ikke den næste
        med samme navn — og er idempotent: den svarer `True` første gang og
        `False` derefter, uden at gøre noget igen.

        Registrering på et lukket omfang afvises. Det er halvdelen af «stop
        admission»: er nedlukningen begyndt, må der ikke komme nyt ind bagfra,
        for så bliver rækkefølgen ved afhændelsen en løgn.
        """
        with self._laas:
            if self._lukket:
                raise RuntimeError(
                    f"omfanget «{self.navn}» er lukket — kan ikke registrere «{navn}»")
            post = Post(identitet=id(afhaend) ^ len(self._poster),
                        navn=str(navn), afhaend=afhaend)
            # Identiteten skal vaere unik INDEN FOR omfanget. `id()` alene kan
            # genbruges naar et objekt er samlet op, saa den blandes med
            # positionen — to poster i samme omfang kan derfor ikke kollidere.
            while any(p.identitet == post.identitet for p in self._poster):
                post.identitet += 1
            self._poster.append(post)
        return lambda: self._afhaend_en(post)

    def _afhaend_en(self, post: Post) -> bool:
        with self._laas:
            if post.afhaendt:
                return False                 # idempotent — anden gang er en no-op
            post.afhaendt = True
            try:
                self._poster.remove(post)
            except ValueError:
                pass
        try:
            post.afhaend()
            return True
        except Exception:
            logger.warning("afhaendelse af «%s» i omfanget «%s» fejlede",
                           post.navn, self.navn, exc_info=True)
            return False

    # ----------------------------------------------------------------- arbejde

    def arbejde_startet(self) -> None:
        """Meld at omfanget har arbejde i gang. Afhændelsen venter på det."""
        with self._laas:
            self._arbejde += 1

    def arbejde_slut(self) -> None:
        with self._laas:
            # Aldrig under nul. En utaellelig taeller ville gøre `rolig`
            # meningsloes, og en afhaendelse ville tro den var faerdig.
            self._arbejde = max(0, self._arbejde - 1)

    @property
    def arbejde_i_gang(self) -> int:
        with self._laas:
            return self._arbejde

    @property
    def antal(self) -> int:
        with self._laas:
            return len(self._poster)

    @property
    def tom(self) -> bool:
        return self.antal == 0

    # --------------------------------------------------------------- afhændelse

    def afhaend(self, frist_s: float = STANDARD_FRIST_S) -> Rapport:
        """Stop tilgang, tøm til fristen, afregistrér i modsat orden.

        Kaster aldrig. En nedlukning der kaster gør nedlukningen værre — og en
        afhændelse er netop det sted hvor man IKKE har råd til at miste
        kontrollen over resten af listen.
        """
        start = time.monotonic()
        with self._laas:
            self._lukket = True              # 1. stop tilgang
            poster = list(self._poster)

        # 2. toem ejet arbejde til fristen
        rolig = True
        while True:
            if self.arbejde_i_gang <= 0:
                break
            if time.monotonic() - start >= max(0.0, frist_s):
                rolig = False
                break
            time.sleep(0.005)
        udestaaende = self.arbejde_i_gang

        # 3. afregistrér i MODSAT orden
        afhaendte: list[str] = []
        uafklarede: list[tuple[str, str]] = []
        # En afbrydelse maa ikke efterlade resten af listen ukoert — det er
        # netop den «unresolved ownership» filen findes for. Men den maa
        # heller ikke sluges: Ctrl-C skal stadig virke. Derfor gemmes den, og
        # kastes FOERST naar hele listen er koert og rapporten er skrevet.
        afbrydelse: BaseException | None = None
        for post in reversed(poster):
            with self._laas:
                if post.afhaendt:
                    continue
                post.afhaendt = True
                try:
                    self._poster.remove(post)
                except ValueError:
                    pass
            try:
                post.afhaend()
                afhaendte.append(post.navn)
            except BaseException as fejl:
                # IKKE `except: pass`. Det er praecis den tavshed spec'en
                # kalder «unresolved ownership», og den er grunden til at en
                # nedlukning kan se stille ud mens den efterlader liv.
                #
                # BaseException og ikke Exception: en afhaender der rejser
                # SystemExit ville ellers forlade resten af listen ukoert, og
                # de poster ville vaere uafklarede UDEN at staa i rapporten —
                # den vaerste af de to slags tavshed.
                uafklarede.append((post.navn, f"{type(fejl).__name__}: {fejl}"))
                logger.warning("uafklaret ejerskab: «%s» i omfanget «%s»",
                               post.navn, self.navn, exc_info=True)
                if isinstance(fejl, (KeyboardInterrupt, SystemExit)) and afbrydelse is None:
                    afbrydelse = fejl

        rapport = Rapport(
            omfang=self.navn,
            afhaendte=tuple(afhaendte),
            uafklarede=tuple(uafklarede),
            rolig=rolig,
            udestaaende_arbejde=udestaaende,
            varighed_s=round(time.monotonic() - start, 4),
        )
        if not rapport.ren:
            for linje in rapport.forklar():
                logger.error("afhaendelse: %s", linje)
        if afbrydelse is not None:
            # Listen er koert faerdig og rapporten er skrevet. Nu maa
            # afbrydelsen naa sin kalder — et Ctrl-C der forsvandt ville
            # vaere en anden slags loegn.
            raise afbrydelse
        return rapport


class Registret:
    """De levende omfang. Tomme lag ryddes, så registret ikke samler lig."""

    def __init__(self) -> None:
        self._omfang: dict[str, Omfang] = {}
        self._laas = threading.RLock()

    def aabn(self, navn: str) -> Omfang:
        with self._laas:
            o = self._omfang.get(navn)
            if o is None or o._lukket:
                o = Omfang(navn)
                self._omfang[navn] = o
            return o

    def afhaend(self, navn: str, frist_s: float = STANDARD_FRIST_S) -> Rapport:
        with self._laas:
            o = self._omfang.get(navn)
        if o is None:
            return Rapport(omfang=navn)      # allerede væk — ikke en fejl
        rapport = o.afhaend(frist_s)
        with self._laas:
            # Tomme lag ryddes. Et omfang uden poster der bliver staaende, er
            # en bøtte registret skal baere rundt paa uden at nogen ejer den.
            if self._omfang.get(navn) is o and o.tom:
                del self._omfang[navn]
        return rapport

    def afhaend_alle(self, frist_s: float = STANDARD_FRIST_S) -> list[Rapport]:
        """Luk alt. Nyeste omfang først — samme modsatte orden som inden i ét."""
        with self._laas:
            navne = list(self._omfang)
        return [self.afhaend(n, frist_s) for n in reversed(navne)]

    def ryd_tomme(self) -> int:
        """Fjern omfang uden poster. Returnerer antallet der blev ryddet."""
        with self._laas:
            tomme = [n for n, o in self._omfang.items() if o.tom]
            for n in tomme:
                del self._omfang[n]
            return len(tomme)

    @property
    def navne(self) -> tuple[str, ...]:
        with self._laas:
            return tuple(sorted(self._omfang))

    def status(self) -> dict[str, Any]:
        """Hvad Centralen skal kunne vise."""
        with self._laas:
            return {
                "omfang": {n: {"poster": o.antal, "arbejde": o.arbejde_i_gang}
                           for n, o in self._omfang.items()},
                "antal": len(self._omfang),
            }


#: Processens register. Ét sted, så en nedlukning kan finde alt.
REGISTRET = Registret()


def koer_nedlukning(trin: list[tuple[str, Callable[[], Any]]],
                    *, navn: str = "nedlukning") -> Rapport:
    """Kør en håndholdt nedluknings-liste i DEN GIVNE orden, og rapportér.

    ## Hvorfor ikke bare et omfang

    Et `Omfang` afhænder i modsat orden, fordi registreringer er en stak. Den
    her liste er ikke en stak — den er en håndskrevet rækkefølge nogen har
    tænkt over. At vende den ville være en adfærdsændring forklædt som en
    oprydning, så ordenen holdes præcis som den er.

    ## Hvad der faktisk var galt

    Målt 13/9-2026 på `apps/api/jarvis_api/app.py`: nedlukningen havde TO
    modsatte fejl i samme blok.

      * **15 kald uden værn.** Fejlede `stop_heartbeat_scheduler()`, blev alle
        14 efterfølgende aldrig kørt — og ingen ville vide det.
      * **14 kald i `except: pass`.** De fejler tavst. Nedlukningen ser stille
        ud, og noget lever videre.

    Den ene halvdel mister resten af listen, den anden mister sandheden. Her
    får man begge dele: hvert trin køres, og det der ikke lykkedes står i
    rapporten med navn og grund.
    """
    start = time.monotonic()
    kørte: list[str] = []
    uafklarede: list[tuple[str, str]] = []
    afbrydelse: BaseException | None = None
    for trin_navn, fn in trin:
        try:
            fn()
            kørte.append(trin_navn)
        except BaseException as fejl:
            uafklarede.append((trin_navn, f"{type(fejl).__name__}: {fejl}"))
            logger.warning("nedlukning: «%s» fejlede", trin_navn, exc_info=True)
            if isinstance(fejl, (KeyboardInterrupt, SystemExit)) and afbrydelse is None:
                afbrydelse = fejl
    rapport = Rapport(
        omfang=navn,
        afhaendte=tuple(kørte),
        uafklarede=tuple(uafklarede),
        varighed_s=round(time.monotonic() - start, 4),
    )
    if uafklarede:
        logger.error("nedlukning: %d af %d trin fejlede — %s",
                     len(uafklarede), len(trin),
                     ", ".join(n for n, _ in uafklarede))
    if afbrydelse is not None:
        raise afbrydelse
    return rapport
