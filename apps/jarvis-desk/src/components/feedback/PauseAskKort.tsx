import { useEffect, useSyncExternalStore } from 'react'
import { PauseAndAskCard } from '../rich/PauseAndAskCard'
import { useStream } from '../../hooks/useStream'
import { liveChatBlokke } from '../../lib/streamReducer'
import {
  abonnérPauseLukket, emitPauseLuk, erPauseLukket, lukPause, onPauseSvar,
  pauseAskIn, pauseIdentitet, pauseLukketSnapshot,
} from '../../lib/pauseAsk'

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
 *
 * 15/11-2026 (Bjørn): «pause_and_ask forsvinder ikk når man trykker send og det
 * mangler et kryds». Blokken ligger VARIGT i stream-state — den forsvinder først
 * når run'et ryddes — så kortet blev stående som «Svar sendt» længe efter
 * svaret var givet. Lukke-tilstanden bor derfor i `lib/pauseAsk.ts` på
 * modul-niveau, ikke i React-state: kortet monteres i både ChatView og
 * CodeView, og et view-skift ville ellers vække spørgsmålet igen.
 */
export function PauseAskKort() {
  const stream = useStream()
  // Re-render når et spørgsmål lukkes — ellers står kortet til næste stream-tick.
  useSyncExternalStore(abonnérPauseLukket, pauseLukketSnapshot, pauseLukketSnapshot)

  const ask = pauseAskIn(liveChatBlokke(stream))
  const ident = ask ? pauseIdentitet(ask) : ''

  // Et svar — sendt herfra eller ad en anden vej — lukker spørgsmålet med det
  // samme. Svaret bliver selv den næste brugerbesked, så det er synligt i
  // tråden; kortet behøver ikke stå tilbage som kvittering.
  useEffect(() => {
    if (!ident) return
    return onPauseSvar(() => lukPause(ident))
  }, [ident])

  if (!ask || erPauseLukket(ident)) return null
  return (
    <PauseAndAskCard
      ask={ask}
      onLuk={() => { lukPause(ident); emitPauseLuk() }}
    />
  )
}
