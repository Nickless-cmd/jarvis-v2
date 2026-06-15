/** Delte localStorage-nøgler + læser for composer-præferencer.
 *  Én kilde, så Composer og auto-continue (CodeView) ikke duplikerer dem. */
export const PERM_KEY = 'jarvis-desk:permission'
export const PROV_KEY = 'jarvis-desk:provChoice'
export const MODEL_KEY = 'jarvis-desk:model'

export function readModelPrefs(): { model: string; providerChoice: string } {
  let model = ''
  let providerChoice = 'deepseek'
  try { model = localStorage.getItem(MODEL_KEY) || '' } catch { /* ignore */ }
  try { providerChoice = localStorage.getItem(PROV_KEY) || 'deepseek' } catch { /* ignore */ }
  return { model, providerChoice }
}
