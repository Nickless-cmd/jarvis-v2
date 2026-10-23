import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { subscribeWebPush, unsubscribeWebPush, webPushMulig } from '../../pwa/webPush'

type Tilstand = 'indlaeser' | 'utilgaengelig' | 'klar' | 'aktiv' | 'afvist' | 'arbejder' | 'fejl'

function erWebBuild(): boolean {
  return typeof __WEB_BUILD__ !== 'undefined' && __WEB_BUILD__
}

async function findTilstand(): Promise<Tilstand> {
  if (!webPushMulig()) return 'utilgaengelig'
  if (Notification.permission === 'denied') return 'afvist'
  if (Notification.permission !== 'granted') return 'klar'
  try {
    const reg = await navigator.serviceWorker.ready
    return (await reg.pushManager.getSubscription()) ? 'aktiv' : 'klar'
  } catch {
    return 'fejl'
  }
}

/** Førstegangs-tilmelding skal ske direkte fra et brugertryk på iPhone. */
export function WebPushControl({ config }: { config: ApiConfig }) {
  const [tilstand, setTilstand] = useState<Tilstand>('indlaeser')

  useEffect(() => {
    let aktiv = true
    void findTilstand().then((n) => { if (aktiv) setTilstand(n) })
    return () => { aktiv = false }
  }, [])

  if (!erWebBuild()) return null

  const aktiver = async () => {
    setTilstand('arbejder')
    const ok = await subscribeWebPush(config)
    if (ok) {
      setTilstand('aktiv')
      return
    }
    const faktisk = await findTilstand()
    setTilstand(['afvist', 'utilgaengelig'].includes(faktisk) ? faktisk : 'fejl')
  }
  const deaktiver = async () => {
    setTilstand('arbejder')
    const ok = await unsubscribeWebPush(config)
    setTilstand(ok ? 'klar' : 'fejl')
  }

  return (
    <div className="notif-web-push" aria-live="polite">
      <div>
        <strong>Notifikationer på denne enhed</strong>
        <p className="settings-hint">
          {tilstand === 'aktiv' && 'Aktiv — Jarvis kan nå denne iPhone, også når PWA’en er lukket.'}
          {tilstand === 'klar' && 'Aktivér én gang for at modtage Jarvis-beskeder på låseskærmen.'}
          {tilstand === 'afvist' && 'Blokeret af iPhone. Tillad Jarvis under Indstillinger → Notifikationer.'}
          {tilstand === 'utilgaengelig' && 'Åbn Jarvis fra hjemmeskærmen som webapp for at aktivere iPhone-notifikationer.'}
          {tilstand === 'indlaeser' && 'Kontrollerer denne enhed…'}
          {tilstand === 'arbejder' && 'Opdaterer…'}
          {tilstand === 'fejl' && 'Kunne ikke opdatere. Kontroller forbindelsen og prøv igen.'}
        </p>
      </div>
      {tilstand === 'aktiv' ? (
        <button type="button" onClick={() => void deaktiver()}>
          Deaktivér på denne enhed
        </button>
      ) : (
        <button type="button" disabled={!['klar', 'fejl'].includes(tilstand)} onClick={() => void aktiver()}>
          Aktivér notifikationer
        </button>
      )}
    </div>
  )
}
