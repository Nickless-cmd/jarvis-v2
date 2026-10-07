import { useContext, useSyncExternalStore } from 'react'
import { StreamContext, type StreamContextValue } from '../contexts/StreamContext'

function useLager() {
  const l = useContext(StreamContext)
  if (!l) throw new Error('useStream must be used within StreamProvider')
  return l
}

export function useStream(): StreamContextValue {
  const l = useLager()
  // Abonnér på lageret i stedet for at læse en kontekst-værdi: kun DENNE
  // komponent renderes om ved en stream-opdatering (lib/vaerdiLager).
  //
  // Men den giver HELE værdien, så «denne komponent» rendres om ved hver
  // chunk — også når det felt den læser står helt stille. Læser du få felter,
  // brug `useStreamUdsnit`. Målt 4/10-2026, se `useStreamUdsnit`.
  return useSyncExternalStore(l.abonner, l.hent, l.hent)
}

export function useStreamUdsnit<T>(vaelg: (v: StreamContextValue) => T): T {
  /**
   * Abonnér på ÉT felt. Rendrer kun om når netop det felt ændrer sig.
   *
   * Målt 4/10-2026 på Bjørns tal — 566 sessioner i sidepanelet, ét svar er
   * ~405 frames:
   *
   *     useStream()        30,2 ms per chunk · 21 renders per 20 chunks
   *     useStreamUdsnit()   0,0 ms per chunk ·  0 renders per 20 chunks
   *
   * 30 ms er 1,8 × frame-budgettet ved 60 fps, og over ét svar bliver det
   * 12,2 s ren sidebar-render for et felt (`workingSessionId`) der ikke
   * ændrede sig én gang.
   *
   * Lageret fra 19/9 fjernede den ANDEN halvdel af samme problem: dengang lå
   * stream-tilstanden som kontekst-VÆRDI, og React måtte jage ændringen
   * gennem hele træet (6,8 s af et 46 s svar). Konteksten blev konstant, men
   * abonnenterne fik stadig alt. Det her er den halvdel der stod tilbage.
   *
   * KUN til primitiver og stabile referencer. Vælger du et objekt-literal,
   * giver hver læsning en ny identitet, og React advarer om at `getSnapshot`
   * ikke er cachet — og du har byttet for mange renders til en uendelig
   * løkke. Vælg felterne enkeltvis i stedet.
   */
  const l = useLager()
  return useSyncExternalStore(l.abonner, () => vaelg(l.hent()), () => vaelg(l.hent()))
}
