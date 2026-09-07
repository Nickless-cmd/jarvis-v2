import { useEffect, useRef } from 'react'

/** Hent det færdige svar hjem når strømmen brister.
 *
 *  SPORET 7/9-2026: serveren gennemfører turen og PERSISTERER svaret; det er
 *  kun leveringen der fejler. Beskeden lå i basen (2.069 tegn, hel sætning til
 *  sidst) og API'et returnerede den fint — men skærmen fik den aldrig.
 *
 *  `autoReconnect: false` i chat-banen er KORREKT og bliver: en blind
 *  genforbindelse re-POSTer beskeden og duplikerer turen (buggen fra 2/9). Det
 *  der manglede var en LÆSE-vej tilbage.
 *
 *  Der findes en 1,5-sekunders poll der kalder `sessions.refresh()`, og den
 *  virker når den kører. Men den er ambient: den fejler tavst mens serveren
 *  genstarter, og der er intet spor bagefter der siger om den greb. Derfor det
 *  her — en HANDLING knyttet til bruddet, med prøv-igen og et synligt udfald.
 *
 *  Virker uanset ÅRSAG til bruddet — genstart, poll-storm, netværkshik,
 *  socket-abort. Det er hele pointen: årsagerne bliver ved med at skifte, og
 *  de har alle samme konsekvens.
 */
export function useGenopretEfterBrud(
  status: string,
  sessionId: string | null,
  refresh: () => Promise<void>,
): void {
  const kørerFor = useRef<string | null>(null)
  useEffect(() => {
    if (status !== 'interrupted' && status !== 'hung') { kørerFor.current = null; return }
    if (!sessionId || kørerFor.current === sessionId) return
    kørerFor.current = sessionId
    let afbrudt = false
    // Tre forsøg med voksende pause: bruddet skyldes ofte at serveren er nede
    // netop nu, og et enkelt kald ville ramme det samme hul.
    const forsøg = async () => {
      for (const pause of [0, 1500, 4000]) {
        if (afbrudt) return
        if (pause) await new Promise((r) => setTimeout(r, pause))
        try {
          await refresh()
          return
        } catch {
          /* næste forsøg */
        }
      }
    }
    void forsøg()
    return () => { afbrudt = true }
  }, [status, sessionId, refresh])
}
