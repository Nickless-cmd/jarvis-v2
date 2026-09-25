import { useEffect, useRef } from 'react'
import { useSettings } from '../../hooks/useSettings'
import { useStream } from '../../hooks/useStream'
import { hentGenoptagelsesVarsel } from '../../lib/api'
import { skalSpoergeOmVarsel } from '../../lib/genoptagelsesVarsel'

/** Spoerger om der ligger et varsel for den aktive samtale.
 *
 * Hosten er monteret i `App` ved siden af de andre — altsaa ALTID, uanset
 * hvilken flade der vises. Det er hele pointen: effekten laa foer i
 * `ChatView`, som `App` kun monterer naar `surface === 'chat'`, saa paa
 * kode-fladen blev der aldrig spurgt. Fire rettelser gik til en komponent
 * der ikke var paa skaermen, fordi nabo-effekten `warm` fandtes i BEGGE
 * views og derfor saa ud til at bevise at komponenten koerte.
 *
 * HVORNAAR der spoerges bor i `lib/genoptagelsesVarsel.ts`.
 */
export function GenoptagelsesVarselHost({ sessionId }: { sessionId: string | null }) {
  const { settings } = useSettings()
  const stream = useStream()
  const spurgtRef = useRef<string | null>(null)
  const forrigeStatusRef = useRef<string>('')

  useEffect(() => {
    const forrige = forrigeStatusRef.current
    forrigeStatusRef.current = stream.status
    if (!settings || !sessionId) return
    const beslutning = skalSpoergeOmVarsel({
      forrige,
      status: stream.status,
      sessionId,
      alleredeSpurgt: spurgtRef.current,
    })
    if (beslutning.nulstil) spurgtRef.current = null
    if (!beslutning.spoerg) return
    spurgtRef.current = sessionId
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let afbrudt = false
    hentGenoptagelsesVarsel(cfg, sessionId)
      .then((v) => {
        if (afbrudt || !v?.notice?.message) return
        stream.visGenoptagelsesVarsel({
          reason: v.notice.reason,
          message: v.notice.message,
          continuing: v.notice.continuing,
        })
      })
      .catch(() => {
        // Kan vi ikke spørge, må samtalen ikke gå i stå — men lad os kunne
        // spørge igen næste gang sessionen åbnes.
        spurgtRef.current = null
      })
    return () => { afbrudt = true }
  }, [settings, sessionId, stream.status])

  return null
}
