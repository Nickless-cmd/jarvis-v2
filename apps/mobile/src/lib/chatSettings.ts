import * as SecureStore from 'expo-secure-store'

/** Indstillinger PR. SAMTALE — ikke globalt.
 *
 *  Én samtale kan handle om kode og en anden om aftaler, og de har ikke brug
 *  for det samme. Derfor gemmes valgene pr. session.
 *
 *  Bjørns liste bad om fire: model, stemme, memory scope og tilladte
 *  værktøjer. Tre af dem kan faktisk sættes:
 *
 *    model    → `model` i stream-kroppen
 *    værktøj  → `mode`: "chat" begrænser listen, "code" åbner den (serveren
 *               oversætter mode → tool-scope, chat_stream_v2 linje 348-352)
 *    stemme   → ren klient-side: om svar læses højt
 *
 *  MEMORY SCOPE er UDELADT med vilje. Serveren har intet felt for det —
 *  hverken i stream-kroppen eller i prompt-assembly'en — så en kontakt her
 *  ville se ud som om den gjorde noget uden at gøre det. Den slags kontakt er
 *  værre end ingen: man tror man har begrænset hvad han husker.
 */

export type VaerktoejsOmfang = 'samtale' | 'fuldt'

export interface ChatIndstillinger {
  /** "" = brug appens globale valg. */
  model: string
  vaerktoejer: VaerktoejsOmfang
  /** Læs svar højt i denne samtale. */
  stemme: boolean
  /** Spørg før ændringer, eller stol på ham. */
  spoergFoerst: boolean
}

export const STANDARD: ChatIndstillinger = {
  model: '', vaerktoejer: 'samtale', stemme: false, spoergFoerst: true,
}

const PRAEFIKS = 'jarvis:chatcfg:'

function noegle(sessionId: string): string {
  return PRAEFIKS + String(sessionId || 'default').replace(/[^A-Za-z0-9._-]/g, '_')
}

function rens(v: unknown): ChatIndstillinger {
  const o = (v && typeof v === 'object' ? v : {}) as Record<string, unknown>
  return {
    model: typeof o.model === 'string' ? o.model : STANDARD.model,
    vaerktoejer: o.vaerktoejer === 'fuldt' ? 'fuldt' : 'samtale',
    stemme: o.stemme === true,
    spoergFoerst: o.spoergFoerst !== false,   // sikker vej som standard
  }
}

export async function laesIndstillinger(sessionId: string): Promise<ChatIndstillinger> {
  try {
    const raa = await SecureStore.getItemAsync(noegle(sessionId))
    return raa ? rens(JSON.parse(raa)) : { ...STANDARD }
  } catch {
    return { ...STANDARD }
  }
}

export async function gemIndstillinger(
  sessionId: string, next: Partial<ChatIndstillinger>,
): Promise<ChatIndstillinger> {
  const nu = await laesIndstillinger(sessionId)
  const ny = rens({ ...nu, ...next })
  try {
    await SecureStore.setItemAsync(noegle(sessionId), JSON.stringify(ny))
  } catch {
    /* stille — en indstilling der ikke kan gemmes må ikke vælte skærmen */
  }
  return ny
}

/** Oversæt til de felter stream-kroppen faktisk forstår.
 *
 *  Er der ikke valgt en model for samtalen, sendes den globale videre — så en
 *  tom per-chat-værdi betyder «som appen plejer», ikke «ingen model». */
export function tilStreamFelter(
  cfg: ChatIndstillinger, globalModel = '',
): { model: string; mode: 'chat' | 'code'; approvalMode: 'ask' | 'trust' } {
  return {
    model: cfg.model || globalModel || '',
    mode: cfg.vaerktoejer === 'fuldt' ? 'code' : 'chat',
    approvalMode: cfg.spoergFoerst ? 'ask' : 'trust',
  }
}
