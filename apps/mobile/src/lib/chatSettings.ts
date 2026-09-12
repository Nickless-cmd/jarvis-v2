import * as SecureStore from 'expo-secure-store'
import type { StoredModelChoice } from './sessionStore'

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
export type ResearchMode = 'off' | 'on'
export type ThinkingMode = 'fast' | 'think'

export interface ChatIndstillingerV2 {
  version: 2
  /** `null` = brug serverens default for denne samtale. */
  model: StoredModelChoice | null
  thinkingMode: ThinkingMode
  researchMode: ResearchMode
  vaerktoejer: VaerktoejsOmfang
  /** Læs svar højt i denne samtale. */
  stemme: boolean
  /** Spørg før ændringer, eller stol på ham. */
  spoergFoerst: boolean
}

export type ChatIndstillinger = ChatIndstillingerV2

export const STANDARD: ChatIndstillingerV2 = {
  version: 2,
  model: null,
  thinkingMode: 'think',
  researchMode: 'off',
  vaerktoejer: 'samtale',
  stemme: false,
  spoergFoerst: true,
}

// PUNKTUM, IKKE KOLON. Expo SecureStore tillader kun [A-Za-z0-9._-] i en
// nøgle. Præfikset var 'jarvis:chatcfg:', og rensningen nedenfor ramte KUN
// sessionId — så hver eneste nøgle indeholdt to ugyldige tegn, kaldet kastede,
// og `catch {}` i gemIndstillinger slugte det. Disse indstillinger har aldrig
// kunnet gemmes.
//
// Målt 12. sep 2026 på testtelefonen: sæt «Fuld adgang», tving-stop, start
// igen → «Spørg først», ved T+6s, T+14s og T+26s. Ikke en race; værdien var
// aldrig skrevet. Alle de præferencer der VIRKER bruger punktum-nøgler:
// jarvis.mobile.batterySaver, jarvis.mobile.bubblePersist,
// jarvis.mobile.lastSession, jarvis_theme_mode.
const PRAEFIKS = 'jarvis.chatcfg.'

function noegle(sessionId: string): string {
  // Rens HELE nøglen, ikke kun sessionId. Var det gjort fra start, havde
  // præfiksets kolon aldrig nået ud — og fejlen havde ikke kunnet opstå.
  return (PRAEFIKS + String(sessionId || 'default')).replace(/[^A-Za-z0-9._-]/g, '_')
}

function rensModel(v: unknown): StoredModelChoice | null {
  if (!v || typeof v !== 'object') return null
  const model = v as Record<string, unknown>
  // providerChoice må være TOM: en member-model kan lade serveren vælge
  // provider, og tom betyder netop det — ikke «ugyldig». Kun model og label
  // skal være sat; de bærer valget brugeren faktisk traf.
  if (
    typeof model.model !== 'string' || !model.model.trim()
    || typeof model.providerChoice !== 'string'
    || typeof model.label !== 'string' || !model.label.trim()
  ) return null
  return {
    model: model.model,
    providerChoice: model.providerChoice,
    label: model.label,
  }
}

export function parseChatIndstillinger(v: unknown): ChatIndstillingerV2 {
  const o = (v && typeof v === 'object' ? v : {}) as Record<string, unknown>
  return {
    version: 2,
    model: rensModel(o.model),
    thinkingMode: o.thinkingMode === 'fast' ? 'fast' : 'think',
    researchMode: o.researchMode === 'on' ? 'on' : 'off',
    vaerktoejer: o.vaerktoejer === 'fuldt' ? 'fuldt' : 'samtale',
    stemme: o.stemme === true,
    spoergFoerst: o.spoergFoerst !== false,   // sikker vej som standard
  }
}

export async function laesIndstillinger(sessionId: string): Promise<ChatIndstillinger> {
  try {
    const raa = await SecureStore.getItemAsync(noegle(sessionId))
    return raa ? parseChatIndstillinger(JSON.parse(raa)) : { ...STANDARD }
  } catch {
    return { ...STANDARD }
  }
}

export async function gemIndstillinger(
  sessionId: string, next: Partial<ChatIndstillinger>,
): Promise<ChatIndstillinger> {
  const nu = await laesIndstillinger(sessionId)
  const ny = parseChatIndstillinger({ ...nu, ...next })
  let skrevet = false
  try {
    await SecureStore.setItemAsync(noegle(sessionId), JSON.stringify(ny))
    skrevet = true
  } catch (fejl) {
    // IKKE STILLE. En indstilling der ikke kan gemmes må ikke vælte skærmen —
    // men den må heller ikke se ud som om den blev gemt. Den tavse udgave af
    // denne catch skjulte en ugyldig nøgle i hele funktionens levetid, og
    // kalderen fik den nye værdi retur som om alt var i orden.
    console.warn('chatSettings: kunne ikke gemme indstillinger', fejl)
  }
  return skrevet ? ny : nu
}

/** Oversæt til de felter stream-kroppen faktisk forstår.
 *
 *  Er der ikke valgt en model for samtalen, sendes den globale videre — så en
 *  tom per-chat-værdi betyder «som appen plejer», ikke «ingen model». */
export function tilStreamFelter(cfg: ChatIndstillinger): {
  model: string
  providerChoice: string
  mode: 'chat' | 'code'
  approvalMode: 'ask' | 'trust'
  thinkingMode: ThinkingMode
  researchMode: boolean
} {
  return {
    model: cfg.model?.model ?? '',
    providerChoice: cfg.model?.providerChoice ?? '',
    mode: cfg.vaerktoejer === 'fuldt' ? 'code' : 'chat',
    approvalMode: cfg.spoergFoerst ? 'ask' : 'trust',
    thinkingMode: cfg.thinkingMode,
    researchMode: cfg.researchMode === 'on',
  }
}
