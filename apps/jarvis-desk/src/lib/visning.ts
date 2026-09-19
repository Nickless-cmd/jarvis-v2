import { createContext, useContext, useEffect, useState } from 'react'
import { apiFetch, type ApiConfig } from './api'

/**
 * Samtalens visningstilstand — Claude Desktops tre (cc-desktop-chatview.md §1):
 *
 *   normal   — værktøjsrunder foldet, tænkning som én linje
 *   thinking — et resumé af tænkningen over hver værktøjsgruppe
 *   verbose  — alt åbent: hvert kald for sig, tankerne foldet ud
 *
 * Tilstanden bor på SERVEREN pr. samtale, fordi den ændrer hvad der
 * PRODUCERES: i «thinking» laver kørslen et tænke-resumé pr. gruppe (et
 * modelkald). Her huskes kun standarden for nye samtaler, lokalt pr. maskine
 * — deres `epitaxy.transcriptMode`.
 */
export type Visning = 'normal' | 'thinking' | 'verbose'
export const VISNINGER: Visning[] = ['normal', 'thinking', 'verbose']
export const VISNING_NAVN: Record<Visning, string> = { normal: 'Normal', thinking: 'Tænkning', verbose: 'Alt' }

const STANDARD_NOEGLE = 'jarvis-desk:visning-standard'

/** Deres `Dt()`: en ukendt værdi falder tilbage til normal frem for at fejle. */
export function erVisning(v: unknown): v is Visning {
  return typeof v === 'string' && (VISNINGER as string[]).includes(v)
}

export function standardVisning(): Visning {
  try {
    const v = localStorage.getItem(STANDARD_NOEGLE)
    return erVisning(v) ? v : 'normal'
  } catch { return 'normal' }
}

export function saetStandardVisning(v: Visning): void {
  try { localStorage.setItem(STANDARD_NOEGLE, v) } catch { /* utilgængelig */ }
}

export const VisningContext = createContext<Visning>('normal')
export const useVisningen = () => useContext(VisningContext)

export async function hentVisning(config: ApiConfig, sessionId: string): Promise<Visning> {
  const r = await apiFetch<{ view?: string }>(config, `/chat/sessions/${encodeURIComponent(sessionId)}/view`)
  return erVisning(r?.view) ? r.view : 'normal'
}

export async function saetVisning(config: ApiConfig, sessionId: string, v: Visning): Promise<void> {
  await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}/view`, { method: 'PUT', body: { view: v } })
}

/**
 * Tilstanden for én samtale. Uden samtale (ny chat) gælder standarden; når
 * samtalen findes, gælder serverens værdi. Et skift sendes til serveren, så
 * næste runde laver (eller dropper) tænke-resuméerne.
 */
export function useVisning(config: ApiConfig | undefined, sessionId: string | null | undefined) {
  const [visning, setVisning] = useState<Visning>(standardVisning)
  useEffect(() => {
    if (!config || !sessionId) { setVisning(standardVisning()); return }
    let aktiv = true
    hentVisning(config, sessionId)
      .then((v) => { if (aktiv) setVisning(v) })
      .catch(() => { /* behold den lokale — serveren svarer måske ikke endnu */ })
    return () => { aktiv = false }
  }, [config?.apiBaseUrl, sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  const skift = async (v: Visning) => {
    setVisning(v)
    if (config && sessionId) {
      try { await saetVisning(config, sessionId, v) } catch { /* vises lokalt alligevel */ }
    }
  }
  return { visning, skift }
}
