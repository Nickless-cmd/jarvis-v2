/**
 * Broen koblet på appen — ellers findes den ikke.
 *
 * `broKlient` kan protokollen og `telefonHandlere` kan organerne, men uden
 * det her er begge dele kode ingen kalder. Det er det hyppigste mønster i
 * dette projekt, så den her fil er med vilje tynd og med vilje til stede.
 *
 * Installations-id'et er stabilt pr. app-installation, fordi broen nu holder
 * flere klienter pr. bruger og skelner dem på `client_id`. Ville vi sende et
 * nyt id hver opstart, ville registret samle døde forbindelser; ville vi
 * sende det samme som computeren, ville de sparke hinanden af.
 */

import * as SecureStore from 'expo-secure-store'
import * as Application from 'expo-application'
import { opretBro, type Bro } from './broKlient'
import { KAN_UDFOERE, udfoerVaerktoej } from './telefonHandlere'
import type { ApiConfig } from './types'

const ID_NOEGLE = 'jarvis.mobile.broKlientId'

/** Stabilt id pr. installation. Overlever genstart, ikke geninstallation. */
export async function klientId(): Promise<string> {
  try {
    const gemt = await SecureStore.getItemAsync(ID_NOEGLE)
    if (gemt) return gemt
  } catch { /* SecureStore utilgængelig — vi laver et nyt nedenfor */ }
  const nyt = `mobil-${Math.random().toString(36).slice(2, 10)}`
  try {
    await SecureStore.setItemAsync(ID_NOEGLE, nyt)
  } catch { /* så bliver det et nyt id næste gang; broen overlever stadig */ }
  return nyt
}

/** Start broen. Returnerer en stopper — kald den når token'et skifter. */
export function startBro(config: ApiConfig): () => void {
  let bro: Bro | null = null
  let annulleret = false

  void (async () => {
    const id = await klientId()
    if (annulleret) return
    bro = opretBro({
      apiBaseUrl: config.apiBaseUrl,
      authToken: config.authToken,
      capabilities: KAN_UDFOERE,
      clientId: id,
      version: Application.nativeApplicationVersion ?? '',
      udfoer: udfoerVaerktoej,
      // Uden denne er `log` en no-op, og BROENS livscyklus er usynlig: hverken
      // «registreret», «lukket, prøver igen» eller trafik-vagtens «ingen trafik
      // i Ns» naar nogen steder. En mekanisme ingen kan se virke er ikke til at
      // skelne fra en der ikke virker. `console.log` lander i logcat under
      // ReactNativeJS, så `adb logcat` kan følge broen.
      log: (besked, ...rest) => console.log(besked, ...rest)
    })
    bro.start()
  })()

  return () => {
    annulleret = true
    bro?.stop()
  }
}
