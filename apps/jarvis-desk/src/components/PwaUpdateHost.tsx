import { useEffect, useState } from 'react'
import { useStreamUdsnit } from '../hooks/useStream'
import { registerPwa } from '../pwa/register'
import type { StreamStatus } from '../lib/streamReducer'
import '../styles/pwa.css'

/**
 * Kører der en tur lige NU? Måles på `status` alene.
 *
 * `activeRunId` er en IDENTITET, ikke en aktivitet: den sættes ved
 * `message_start` og nulstilles først ved næste tur — `message_stop` lader
 * den stå (se `streamReducer`, grenen sætter kun `status: 'done'`). Brugt som
 * aktivitetsflag blev svaret «travl» PERMANENT efter den første tur, og
 * opdateringsknappen blev aldrig vist.
 *
 * MÅLT 27/11-2026: Bjørn genindlæste PWA'en gentagne gange uden at få
 * 0.6.443. Serveringen var korrekt (`index-DZkmsibV.js` med `0.6.443`), men
 * den ventende service worker blev aldrig frigivet, fordi knappen der sender
 * `SKIP_WAITING` aldrig kom frem — så den gamle bundle blev ved med at blive
 * serveret fra cachen. `reconnecting` tæller som travl: der kører stadig en
 * tur, og et genindlæs ville afbryde den.
 */
export function erTurAktiv(status: StreamStatus): boolean {
  return status === 'working' || status === 'reconnecting'
}

/** Offer a new build only between runs; a live answer is never interrupted. */
export function PwaRunUpdateHost() {
  const status = useStreamUdsnit((stream) => stream.status)
  return <PwaUpdateHost busy={erTurAktiv(status)} />
}

export function PwaUpdateHost({ busy = false }: { busy?: boolean }) {
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null)
  const [updating, setUpdating] = useState(false)

  useEffect(() => registerPwa(setWaiting), [])
  useEffect(() => {
    if (!updating) return
    const onChange = () => window.location.reload()
    navigator.serviceWorker.addEventListener('controllerchange', onChange)
    return () => navigator.serviceWorker.removeEventListener('controllerchange', onChange)
  }, [updating])

  if (!__WEB_BUILD__ || !waiting || busy) return null
  return <div className="pwa-update" role="status">
    <span>En ny version af Jarvis er klar.</span>
    <button type="button" disabled={updating} onClick={() => {
      setUpdating(true)
      waiting.postMessage({ type: 'SKIP_WAITING' })
    }}>Genindlæs</button>
  </div>
}
