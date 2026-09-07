import { Camera } from 'expo-camera'
import * as Audio from 'expo-audio'
import * as Location from 'expo-location'
import notifee from '@notifee/react-native'
import type { Tilladelse } from './onboarding'

/** Det ene sted hvor tilladelser faktisk BEDES om.
 *
 *  Guiden skal kunne testes uden at mocke fire native moduler, og skærmen
 *  skal ikke kende forskellen på notifee og expo-camera. Derfor ligger de fire
 *  kald her, bag ét navn.
 *
 *  Alle fire fejler STILLE til `false`. Et nej og en fejl er det samme for
 *  guiden: den går videre til næste trin. En crash midt i en tilladelses-
 *  guide ville være den værste mulige første oplevelse med appen.
 */
export async function bedOmTilladelse(hvilken: Tilladelse): Promise<boolean> {
  try {
    if (hvilken === 'push') {
      const r = await notifee.requestPermission()
      // authorizationStatus > 0 = tilladt eller provisorisk.
      return Number(r?.authorizationStatus ?? 0) > 0
    }
    if (hvilken === 'mikrofon') {
      return (await Audio.requestRecordingPermissionsAsync()).granted === true
    }
    if (hvilken === 'kamera') {
      return (await Camera.requestCameraPermissionsAsync()).granted === true
    }
    // Kun forgrund. Baggrunds-lokation er et separat, langt mere indgribende
    // valg — det hører hjemme i indstillinger, ikke i en velkomst-guide.
    return (await Location.requestForegroundPermissionsAsync()).status === 'granted'
  } catch {
    return false
  }
}
