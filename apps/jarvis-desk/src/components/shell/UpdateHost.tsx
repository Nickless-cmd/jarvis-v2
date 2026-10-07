import { useEffect, useRef, useState } from 'react'
import { updatesBridge } from '../../lib/updatesBridge'
import { UpdateCard } from './UpdateCard'

const DISMISSED_KEY = 'jarvis-desk:afvist-opdatering'

function dismissedVersion(): string {
  try { return localStorage.getItem(DISMISSED_KEY) || '' } catch { return '' }
}

/** Electron-opdateringen og dens version huskes på tværs af vinduets genindlæsning. */
export function UpdateHost() {
  const [upd, setUpd] = useState<{ version: string; phase: 'available' | 'ready' } | null>(null)
  const [busy, setBusy] = useState(false)
  const [fejl, setFejl] = useState('')
  const dismissedRef = useRef(dismissedVersion())

  useEffect(() => {
    const bridge = updatesBridge()
    if (!bridge) return
    const show = (version: string, phase: 'available' | 'ready') => {
      if (version && version === dismissedRef.current) return
      setBusy(false)
      setFejl('')
      setUpd({ version, phase })
    }
    const offA = bridge.onAvailable((i) => show(i.version ?? '', 'available'))
    const offR = bridge.onReady((i) => show(i.version ?? '', 'ready'))
    return () => { offA(); offR() }
  }, [])

  if (!upd) return null
  const dismiss = () => {
    dismissedRef.current = upd.version
    if (upd.version) {
      try { localStorage.setItem(DISMISSED_KEY, upd.version) } catch { /* privat lagring kan mangle */ }
    }
    setUpd(null); setFejl('')
  }
  const run = (action: () => Promise<void>) => {
    setBusy(true); setFejl('')
    void action().catch((e: unknown) => {
      setBusy(false)
      setFejl(String(e instanceof Error ? e.message : e))
    })
  }
  const bridge = updatesBridge()
  return <UpdateCard
    version={upd.version} phase={upd.phase} busy={busy} error={fejl}
    onUpdate={() => { if (bridge) run(() => bridge.download()) }}
    onInstallNow={() => { if (bridge) run(() => bridge.installNow()) }}
    onInstall={() => { if (bridge) run(() => bridge.install()) }}
    onDismiss={dismiss}
  />
}
