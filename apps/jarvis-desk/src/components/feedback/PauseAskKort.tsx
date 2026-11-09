import { PauseAndAskCard } from '../rich/PauseAndAskCard'
import { useStream } from '../../hooks/useStream'
import { liveChatBlokke } from '../../lib/streamReducer'
import { pauseAskIn } from '../../lib/pauseAsk'

/** `pause_and_ask`-kortet, vist over composeren — ikke i transcriptet.
 *
 * 9/11-2026. Bjørns symptom: «problemet med pause and ask er det er inline så
 * det ruller med transcriptet». Det er præcis hvad der skete: spørgsmålet blev
 * tegnet af `ToolCard` inde i tråden, så det rullede væk når turen skrev videre
 * — og et spørgsmål der ruller væk er et spørgsmål han ikke kan svare på.
 *
 * `lib/pauseAsk.ts` havde allerede begge funktioner til at løse det:
 * `pauseAskIn` (find spørgsmålet i blokkene) og `withoutPauseAsk` (skjul det i
 * tråden). Ingen af dem blev kaldt fra en view. Det er samme fejlform som
 * resten af dagen: mekanismen findes, koblingen gør ikke.
 *
 * Samme form som `GodkendelsesKort`: tilstanden læses fra den delte
 * StreamContext, og svaret sendes gennem `emitPauseSvar` — den pub/sub som
 * begge views allerede lytter på (`onPauseSvar`), så svaret bliver den næste
 * brugerbesked uden at kortet skal kende viewet.
 */
export function PauseAskKort() {
  const stream = useStream()
  const ask = pauseAskIn(liveChatBlokke(stream))
  if (!ask) return null
  return <PauseAndAskCard ask={ask} />
}
