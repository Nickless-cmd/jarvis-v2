/**
 * En værdi der kan læses med useSyncExternalStore — uden en React-kontekst
 * der ændrer sig.
 *
 * Profileret 19/9-2026: stream-tilstanden lå som VÆRDIEN af en kontekst om
 * hele appen og skiftede ved hver stream-opdatering (og hvert 500. ms via
 * elapsedMs). Når en memoiseret række så sprang sin render over, måtte React
 * 19 gennemgå hele dens undertræ for at se om noget dér læste den ændrede
 * kontekst (propagateParentContextChanges fra updateSimpleMemoComponent):
 * 6,8 s af et 46 s svar, jævnt fordelt — hele træet igen ved hver opdatering.
 *
 * Med et lager er konteksten konstant. Kun de komponenter der abonnerer,
 * renderes om — og React har ingen kontekst-ændring at jage gennem træet.
 */
export interface VaerdiLager<T> {
  hent: () => T
  saet: (v: T) => void
  abonner: (lytter: () => void) => () => void
}

export function lavVaerdiLager<T>(start: T): VaerdiLager<T> {
  let vaerdi = start
  const lyttere = new Set<() => void>()
  return {
    hent: () => vaerdi,
    saet: (v) => {
      if (Object.is(v, vaerdi)) return
      vaerdi = v
      lyttere.forEach((l) => l())
    },
    abonner: (l) => { lyttere.add(l); return () => { lyttere.delete(l) } },
  }
}
