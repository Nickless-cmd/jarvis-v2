import { NativeEventEmitter, NativeModules } from 'react-native'
import type { DeltIntent } from './shareIntake'

interface ShareNative {
  hentDeling(): Promise<DeltIntent | null>
}

// HED «ShareModule» indtil 7/9-2026. React Native har SELV et modul med det
// navn (bag `Share.share()`), og kernens vandt: JS fik et objekt uden metoder,
// og vores pakke blev aldrig spurgt. Fejlen var helt tavs.
const native: ShareNative | undefined = NativeModules.DelingModule

/** Tynd wrapper om det native ShareModule. Mangler modulet (iOS, gammel
 *  build, jest) er alt no-op — præcis som [[bubbleModule]]. */
export const deling = {
  /** Delingen der åbnede appen, hvis nogen. Kaldes ÉN gang ved opstart. */
  async vedOpstart(): Promise<DeltIntent | null> {
    if (!native) return null
    try {
      const r = await native.hentDeling()
      return r
    } catch {
      return null
    }
  },

  /** Delinger der kommer mens appen kører. Returnerer en afmelder. */
  lyt(paa: (intent: DeltIntent) => void): () => void {
    if (!native) return () => undefined
    try {
      const emitter = new NativeEventEmitter(NativeModules.DelingModule)
      const sub = emitter.addListener('jarvis.share', (e: DeltIntent) => paa(e))
      return () => sub.remove()
    } catch {
      return () => undefined
    }
  }
}
