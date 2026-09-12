import * as SecureStore from 'expo-secure-store'

/** Vis HELE tankestrømmen — et tilvalg for den avancerede bruger.
 *
 *  Bjørns valg (12/9-2026): standarden er ChatGPT-agtig. Tænke-linjen folder
 *  ud til den halen serveren sender (de sidste 4.000 tegn) — det er nok for
 *  de fleste, og det er hvad man ser i ChatGPT.
 *
 *  Slår man dette til, henter fold-ud i stedet HELE ræsonneringen for den
 *  besked fra serveren (`GET /messages/{id}/reasoning`). Det er et bevidst
 *  valg den enkelte tager: fuld CoT er titusindvis af tegn, og den hentes
 *  kun når man faktisk beder om den — aldrig som en del af session-pollingen.
 *
 *  Global præference (ikke pr. samtale): det handler om hvordan man læser,
 *  ikke om hvad samtalen drejer sig om. Samme mønster som
 *  `batteryPrefs`/`bubbleSetting` — `jarvis.mobile.*` i SecureStore.
 */
const KEY = 'jarvis.mobile.fullThinking'

export async function loadFullThinking(): Promise<boolean> {
  try {
    return (await SecureStore.getItemAsync(KEY)) === '1'
  } catch {
    // Kan præferencen ikke læses, er standarden den sikre: kun halen.
    // (Samme valg som `spoergFoerst` i chatSettings — sikker vej ved tvivl.)
    return false
  }
}

export async function saveFullThinking(on: boolean): Promise<void> {
  try {
    await SecureStore.setItemAsync(KEY, on ? '1' : '0')
  } catch {
    /* best-effort — en indstilling der ikke kan gemmes må ikke vælte skærmen */
  }
}
