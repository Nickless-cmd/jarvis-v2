/** Delte localStorage-nøgler + læser for composer-præferencer.
 *  Én kilde, så Composer og auto-continue (CodeView) ikke duplikerer dem. */
export const PERM_KEY = 'jarvis-desk:permission'
export const PROV_KEY = 'jarvis-desk:provChoice'
export const MODEL_KEY = 'jarvis-desk:model'

/** Taenknings-effekt. 'think' = lad serveren vaelge (adaptivt); 'fast' og
 *  'deep' er eksplicitte overstyringer serveren ALTID respekterer. */
export type ThinkingMode = 'fast' | 'think' | 'deep'
export const THINK_KEY = 'jarvis-desk:thinking'

export function readThinkingMode(): ThinkingMode {
  try {
    const v = localStorage.getItem(THINK_KEY)
    if (v === 'fast' || v === 'think' || v === 'deep') return v
  } catch { /* ignore */ }
  return 'think'
}

export function writeThinkingMode(m: ThinkingMode): void {
  try { localStorage.setItem(THINK_KEY, m) } catch { /* ignore */ }
}

export function readModelPrefs(): { model: string; providerChoice: string } {
  let model = ''
  let providerChoice = 'deepseek'
  try { model = localStorage.getItem(MODEL_KEY) || '' } catch { /* ignore */ }
  try { providerChoice = localStorage.getItem(PROV_KEY) || 'deepseek' } catch { /* ignore */ }
  return { model, providerChoice }
}
