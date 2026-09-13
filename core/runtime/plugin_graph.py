"""Afhængighedsgrafen — Fase 9: «plugin boot rejects missing/cyclic dependencies».

## Hvorfor det her ikke er teori

Målt 13/9-2026 på den levende kadence-graf: 119 producenter, 14 erklærede
afhængigheder, 0 manglende og 0 cykler. Grafen er rask *i dag*.

Men det er ikke pointen. Pointen er hvad der sker når den ikke er det:

    _evaluate_producer(tastefejl)  ->  ('blocked', 'dependency-not-met:findes_slet_ikke')
    _evaluate_producer(cyk_a)      ->  ('blocked', 'dependency-not-met:cyk_b')
    _evaluate_producer(cyk_b)      ->  ('blocked', 'dependency-not-met:cyk_a')

En tastefejl i ét navn blokerer producenten **for evigt**, og en cyklus låser
begge sider. Værre: `blocked` er ikke til at skelne fra det helt lovlige
«forælderen har bare ikke kørt endnu». En død producent ser altså nøjagtig ud
som en der venter.

Samme familie som de andre tavse nedbrud i huset — en prune der aldrig sletter
en række, en kronik der altid siger `success` og aldrig udfører noget. Koden er
rigtig, tælleren står på nul, og ingen kigger.

## Hvad validatoren gør anderledes

Den svarer på spørgsmålet én gang, ved opstart, hvor nogen kan nå at reagere —
i stedet for at lade svaret sive ud som en `reason`-streng i et tick-resultat
ingen læser.

Og den navngiver **hele cyklussen**, ikke bare at der er én. «Der er en cyklus»
sender folk på jagt i 119 knuder; `a -> b -> c -> a` er til at rette.

## Streng eller rapporterende

Spec'en siger «fail at boot». Det er rigtigt for nye sømme, hvor en afvist
opstart er billig. Den levende kadence-graf er en anden sag: dér ville et kast
tage hele runtime ned fordi én producent havde en tastefejl, og det er værre end
sygdommen. Spec'en siger selv at eksisterende tjenester migrerer gradvist.

Derfor to tilstande, og `streng` er et VALG kalderen træffer — ikke en default
der afgør skæbnen for kode der ikke er skrevet med den i tankerne.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping


class GrafFejl(Exception):
    """Grafen kan ikke bære arbejde. Rejses kun i streng tilstand."""


@dataclass(frozen=True)
class Rapport:
    """Hvad grafen fejler — og hvad den kan, hvis noget."""

    #: knude -> de afhængigheder ingen udbyder
    manglende: dict[str, tuple[str, ...]] = field(default_factory=dict)
    #: hver cyklus som den sti den udgør, fx ("a", "b", "c", "a")
    cykler: tuple[tuple[str, ...], ...] = ()
    #: knuderne i en rækkefølge hvor enhver afhængighed kommer først.
    #: Tom hvis grafen har cykler — en cyklisk graf HAR ingen rækkefølge, og
    #: en delvis ville se brugbar ud.
    raekkefoelge: tuple[str, ...] = ()

    @property
    def rask(self) -> bool:
        return not self.manglende and not self.cykler

    def forklar(self) -> list[str]:
        """Menneskelæsbart. Hver linje skal kunne handles på uden opslag."""
        ud: list[str] = []
        for knude, savnede in sorted(self.manglende.items()):
            ud.append(f"{knude} afhaenger af {', '.join(savnede)} — ingen udbyder")
        for cyklus in self.cykler:
            ud.append("cyklus: " + " -> ".join(cyklus))
        return ud


def valider(
    graf: Mapping[str, Iterable[str]],
    *,
    streng: bool = False,
) -> Rapport:
    """Find manglende udbydere og cykler, og læg knuderne i en gyldig orden.

    `graf` er `knude -> afhængigheder`. En knude der kun optræder som
    afhængighed og ikke som nøgle er en MANGLENDE udbyder — det er hele
    forskellen på en graf og en ønskeseddel.

    `streng=True` rejser `GrafFejl` i stedet for at rapportere. Brug den for
    nye sømme, hvor en afvist opstart er billig; brug rapporten for levende
    kode der ikke er skrevet med et kast i tankerne.
    """
    knuder = {str(k): tuple(str(d) for d in (v or ())) for k, v in graf.items()}

    manglende: dict[str, tuple[str, ...]] = {}
    for knude, afh in knuder.items():
        savnede = tuple(d for d in afh if d not in knuder)
        if savnede:
            manglende[knude] = savnede

    cykler = _find_cykler(knuder)

    # Rækkefølgen udregnes KUN på en acyklisk graf. En delvis orden fra en
    # cyklisk graf ville se brugbar ud og starte halvdelen af systemet i en
    # orden der ikke holder.
    raekkefoelge: tuple[str, ...] = () if cykler else _toposorter(knuder)

    rapport = Rapport(manglende=manglende, cykler=cykler, raekkefoelge=raekkefoelge)
    if streng and not rapport.rask:
        raise GrafFejl("; ".join(rapport.forklar()))
    return rapport


def _find_cykler(knuder: Mapping[str, tuple[str, ...]]) -> tuple[tuple[str, ...], ...]:
    """Dybde-først med tre farver. Hver fundet cyklus returneres som sin sti.

    Hvid = ikke besøgt, graa = paa stakken lige nu, sort = faerdig. En kant
    ind i en GRAA knude er en cyklus, og stakken fra den knude og frem ER
    cyklussen — det er derfor stien bæres med rundt i stedet for kun en
    besøgt-mængde.
    """
    HVID, GRAA, SORT = 0, 1, 2
    farve: dict[str, int] = {}
    fundne: list[tuple[str, ...]] = []
    set_af_fundne: set[frozenset[str]] = set()

    def gaa(knude: str, sti: list[str]) -> None:
        farve[knude] = GRAA
        for naeste in knuder.get(knude, ()):
            if naeste not in knuder:
                continue                      # manglende udbyder — rapporteres separat
            f = farve.get(naeste, HVID)
            if f == GRAA:
                # Cyklussen er stien fra `naeste` og frem, lukket om sig selv.
                start = sti.index(naeste)
                cyklus = tuple(sti[start:]) + (naeste,)
                # Samme cyklus kan naas fra flere indgange. Vi vil have den ÉN
                # gang — ellers drukner en rapport med tre indgange til samme
                # ring i tre linjer der siger det samme.
                noegle = frozenset(cyklus)
                if noegle not in set_af_fundne:
                    set_af_fundne.add(noegle)
                    fundne.append(cyklus)
            elif f == HVID:
                gaa(naeste, sti + [naeste])
        farve[knude] = SORT

    for knude in sorted(knuder):
        if farve.get(knude, HVID) == HVID:
            gaa(knude, [knude])
    return tuple(fundne)


def _toposorter(knuder: Mapping[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Kahn. Afhængigheder først, og navne-sorteret inden for hvert lag.

    Sorteringen er ikke pynt: uden den afhænger opstartsordenen af dict-orden,
    og to kørsler af samme graf kunne give forskellig orden. En rækkefølge man
    ikke kan reproducere er ikke til at fejlsøge.
    """
    resterende = {k: {d for d in v if d in knuder} for k, v in knuder.items()}
    ud: list[str] = []
    while resterende:
        klar = sorted(k for k, afh in resterende.items() if not afh)
        if not klar:
            break                              # cyklisk rest — kalderen ved det
        for k in klar:
            ud.append(k)
            del resterende[k]
        for afh in resterende.values():
            afh.difference_update(klar)
    return tuple(ud)
