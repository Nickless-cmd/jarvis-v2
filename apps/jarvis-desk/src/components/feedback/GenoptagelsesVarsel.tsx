import { useStream } from '../../hooks/useStream'

/** Varslet om arbejde der aldrig blev færdigt, vist over composeren.
 *
 * Laa foer inde i `ChatView`. Det var forkert paa to maader, og den anden
 * kostede fire runder: varslet skal naa ham uanset hvilken flade han staar
 * paa, og `App` monterer kun én ad gangen (`surface === 'chat' && <ChatView/>`).
 * Maalt 25/9-2026 i den koerende renderer: `codeview-main` var i DOM'en, saa
 * `ChatView` — og dermed baade spoergsmaalet og banneret — fandtes slet ikke.
 *
 * 30/9-2026: banneret havde INGEN knap, og dets eneste ryddevej var et
 * `message_delta` med stop_reason `end_turn`/`completed`. En tvungen slutrunde
 * har per definition ikke det stop_reason — det er selve udloeseren. Altsaa
 * udelukkede betingelsen der rejste banneret den ene vej der kunne fjerne det,
 * og saa stod det resten af sessionen uden noget at trykke paa. Reduceren
 * rydder nu ogsaa ved et nyt run; knappen her er den sidste udvej.
 */
export function GenoptagelsesVarsel() {
  const stream = useStream()
  if (!stream.recoveryNotice) return null
  return (
    <div className="composer-notices recovery-notice" role="status" aria-live="polite">
      {/* `banner-reconnecting` har en PULSERENDE prik — den siger «der sker
          noget lige nu». Det er sandt mens han fortsætter, og misvisende når
          arbejdet er opgivet: så ville et dødt run ligne et levende.
          `banner-warn` er den samme farve uden pulsen. */}
      <div className={`banner ${stream.recoveryNotice.continuing ? 'banner-reconnecting' : 'banner-warn'}`}>
        <div className="banner-body">
          <span className="banner-message">{stream.recoveryNotice.message}</span>
        </div>
        <div className="banner-actions">
          <button
            type="button"
            className="banner-dismiss"
            aria-label="luk"
            onClick={() => stream.rydGenoptagelsesVarsel()}
          >
            ×
          </button>
        </div>
      </div>
    </div>
  )
}
