import { NativeEventEmitter, NativeModules } from 'react-native'
import type { DeltIntent } from './shareIntake'

interface ShareNative {
  hentDeling(): Promise<DeltIntent | null>
}

const native: ShareNative | undefined = NativeModules.ShareModule

/** Tynd wrapper om det native ShareModule. Mangler modulet (iOS, gammel
 *  build, jest) er alt no-op — præcis som [[bubbleModule]]. */
export const deling = {
  /** Delingen der åbnede appen, hvis nogen. Kaldes ÉN gang ved opstart. */
  async vedOpstart(): Promise<DeltIntent | null> {
    if (!native) return null
    try {
      return await native.hentDeling()
    } catch {
      return null
    }
  },

  /** Delinger der kommer mens appen kører. Returnerer en afmelder. */
  lyt(paa: (intent: DeltIntent) => void): () => void {
    if (!native) return () => undefined
    try {
      const emitter = new NativeEventEmitter(NativeModules.ShareModule)
      const sub = emitter.addListener('jarvis.share', (e: DeltIntent) => paa(e))
      return () => sub.remove()
    } catch {
      return () => undefined
    }
  }
}
