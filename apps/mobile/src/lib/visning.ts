import { useEffect, useState } from 'react'
import * as SecureStore from 'expo-secure-store'
import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

/**
 * Samtalens visningstilstand — Claude Desktops tre (cc-desktop-chatview.md
 * §1), som desk'ens `lib/visning.ts`:
 *
 *   normal   — værktøjsrunder foldet, tænkning som én linje
 *   thinking — et resumé af tænkningen over hver værktøjsgruppe
 *   verbose  — alt åbent fra start
 *
 * Bor på serveren pr. samtale, fordi «thinking» ændrer hvad kørslen LAVER
 * (et tænke-resumé pr. gruppe). Lokalt huskes kun standarden for nye samtaler.
 */
export type Visning = 'normal' | 'thinking' | 'verbose'
export const VISNINGER: Visning[] = ['normal', 'thinking', 'verbose']
export const VISNING_NAVN: Record<Visning, string> = { normal: 'Normal', thinking: 'Tænkning', verbose: 'Alt' }

const STANDARD_NOEGLE = 'visning-standard'

export function erVisning(v: unknown): v is Visning {
  return typeof v === 'string' && (VISNINGER as string[]).includes(v)
}

export async function standardVisning(): Promise<Visning> {
  try {
    const v = await SecureStore.getItemAsync(STANDARD_NOEGLE)
    return erVisning(v) ? v : 'normal'
  } catch { return 'normal' }
}

export async function saetStandardVisning(v: Visning): Promise<void> {
  try { await SecureStore.setItemAsync(STANDARD_NOEGLE, v) } catch { /* utilgængelig */ }
}

export async function hentVisning(config: ApiConfig, sessionId: string): Promise<Visning> {
  const r = await apiFetch<{ view?: string }>(config, `/chat/sessions/${encodeURIComponent(sessionId)}/view`)
  return erVisning(r?.view) ? r.view : 'normal'
}

export async function saetVisning(config: ApiConfig, sessionId: string, v: Visning): Promise<void> {
  await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}/view`, { method: 'PUT', body: { view: v } })
}

/** Tilstanden for én samtale; uden samtale gælder den lokale standard. */
export function useVisning(config: ApiConfig | null | undefined, sessionId: string | null | undefined) {
  const [visning, setVisning] = useState<Visning>('normal')
  useEffect(() => {
    let aktiv = true
    if (!config || !sessionId) {
      void standardVisning().then((v) => { if (aktiv) setVisning(v) })
      return () => { aktiv = false }
    }
    hentVisning(config, sessionId)
      .then((v) => { if (aktiv) setVisning(v) })
      .catch(() => undefined)
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
