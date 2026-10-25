import { useCallback, useEffect, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import {
  afgoerBrowserAnmodning,
  hentBrowserAnmodninger,
  type BrowserAnmodning,
} from '../lib/enheder'

function hasDeskBridge(): boolean {
  return Boolean((window as unknown as { jarvisDesk?: unknown }).jarvisDesk)
}

/** Global Desk prompt: browseren må ikke kræve at brugeren leder i settings. */
export function BrowserDeviceApprovalHost({ config }: { config?: ApiConfig }) {
  const [pending, setPending] = useState<BrowserAnmodning[]>([])
  const [busy, setBusy] = useState('')
  const refresh = useCallback(async () => {
    if (!config || !hasDeskBridge()) return
    const result = await hentBrowserAnmodninger(config)
    if (result.ok) setPending(result.data.anmodninger)
  }, [config?.apiBaseUrl, config?.authToken])

  useEffect(() => {
    if (!config || !hasDeskBridge()) return
    void refresh()
    const timer = window.setInterval(() => { void refresh() }, 2500)
    return () => window.clearInterval(timer)
  }, [config?.apiBaseUrl, config?.authToken, refresh])

  const item = pending[0]
  if (!item) return null
  const decide = async (approved: boolean) => {
    setBusy(item.id)
    const result = await afgoerBrowserAnmodning(config!, item.id, approved)
    if (result.ok) {
      setPending((items) => items.filter((candidate) => candidate.id !== item.id))
    }
    setBusy('')
    void refresh()
  }
  return (
    <aside className="browser-device-approval" role="dialog" aria-label="Godkend browser til Code Mode">
      <strong>Browser vil åbne Code Mode</strong>
      <p><span>{item.navn}</span> beder om adgang til kommandoer og filer. Godkend kun, hvis det er din browser.</p>
      <div className="enheder-knapper">
        <button type="button" className="account-google-btn" disabled={busy === item.id} onClick={() => void decide(true)}>Godkend</button>
        <button type="button" className="enheder-fortryd" disabled={busy === item.id} onClick={() => void decide(false)}>Afvis</button>
      </div>
    </aside>
  )
}
