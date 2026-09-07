/**
 * Hvad Jarvis faktisk kan på telefonen — ét sted, bag ét navn.
 *
 * `broKlient` kender kun protokollen; det her er organerne. Delingen betyder
 * at protokollen kan testes uden native moduler, og at hver handler kan
 * testes for sig.
 *
 * Navnene SKAL matche `core/tools/phone_tools.py::PHONE_TOOL_NAMES` — det er
 * dem serveren annoncerer og router på. `KAN_UDFOERE` eksporteres, så
 * registreringen melder præcis det der findes her, i stedet for en håndholdt
 * kopi der kan glide.
 *
 * **Kameraet kræver forgrunden.** Android lader ikke en app åbne kameraet fra
 * baggrunden, og der findes ingen vej udenom. Appen registrerer sit
 * kamera-håndtag når et CameraView er monteret; er der intet, fejler
 * `phone_photo` med en grund der siger hvorfor, i stedet for at hænge indtil
 * serveren timer ud.
 */

import * as Location from 'expo-location'
import * as Clipboard from 'expo-clipboard'
import * as Speech from 'expo-speech'
import * as FileSystem from 'expo-file-system/legacy'
import { Share } from 'react-native'
import { bubble } from './bubbleModule'

/** Det CameraView-håndtag appen monterer. Kun `takePictureAsync` bruges. */
export interface KameraHaandtag {
  takePictureAsync(opt?: { base64?: boolean; quality?: number }): Promise<{ base64?: string; uri?: string }>
}

let kamera: KameraHaandtag | null = null
/** Kaldes af skærmen når et CameraView monteres/afmonteres. */
export function saetKamera(h: KameraHaandtag | null): void { kamera = h }

/** Optager — injiceres, fordi expo-audios optage-API er en hook i SDK 56 og
 *  ikke kan kaldes herfra. Skærmen giver os en funktion i stedet. */
export type Optager = (sekunder: number) => Promise<{ base64?: string; uri?: string }>
let optag: Optager | null = null
export function saetOptager(f: Optager | null): void { optag = f }

function appMappe(): string {
  return FileSystem.documentDirectory || FileSystem.cacheDirectory || ''
}

/** Hold stier inde i appens eget område.
 *
 *  Uden det kunne et `sti: '../../..'` nå uden for appens mappe. Det er ikke
 *  fordi Jarvis ville gøre det med vilje — det er fordi en model der gætter
 *  en sti ikke skal kunne ramme noget den ikke burde. */
export function samlSti(sti: string): string {
  const rod = appMappe()
  const renset = String(sti || '').replace(/^\/+/, '')
  if (renset.split('/').some((d) => d === '..')) {
    throw new Error('sti_uden_for_appen: .. er ikke tilladt')
  }
  return rod + renset
}

export const HANDLERE: Record<string, (args: Record<string, unknown>) => Promise<unknown>> = {
  async phone_location(args) {
    const noejagtighed = String(args.noejagtighed ?? 'balanced')
    const { status } = await Location.getForegroundPermissionsAsync()
    if (status !== 'granted') throw new Error('lokation_ikke_tilladt')
    const pos = await Location.getCurrentPositionAsync({
      accuracy: noejagtighed === 'high'
        ? Location.Accuracy.High
        : noejagtighed === 'low' ? Location.Accuracy.Low : Location.Accuracy.Balanced
    })
    return {
      breddegrad: pos.coords.latitude,
      laengdegrad: pos.coords.longitude,
      noejagtighed_m: pos.coords.accuracy,
      hoejde_m: pos.coords.altitude,
      fart_ms: pos.coords.speed,
      tidspunkt: new Date(pos.timestamp).toISOString()
    }
  },

  async phone_photo(args) {
    if (!kamera) {
      throw new Error(
        'kamera_ikke_klar: appen skal være i forgrunden med kameraet åbent. ' +
        'Android tillader ikke kamera fra baggrunden.'
      )
    }
    const billede = await kamera.takePictureAsync({ base64: true, quality: 0.7 })
    const ud: Record<string, unknown> = { format: 'jpeg', kamera: String(args.kamera ?? 'back') }
    const gemSti = args.gem_sti ? String(args.gem_sti) : ''
    if (gemSti && billede.base64) {
      const maal = samlSti(gemSti)
      await FileSystem.writeAsStringAsync(maal, billede.base64, { encoding: 'base64' })
      ud.gem_sti = maal
    } else {
      ud.jpeg_base64 = billede.base64
    }
    return ud
  },

  async phone_record_audio(args) {
    if (!optag) throw new Error('optager_ikke_klar: appen skal køre')
    const sekunder = Number(args.sekunder ?? 5)
    const r = await optag(sekunder)
    return { sekunder, format: 'm4a', lyd_base64: r.base64, uri: r.uri }
  },

  async phone_speak(args) {
    const tekst = String(args.tekst ?? '')
    if (!tekst) throw new Error('tekst_mangler')
    Speech.speak(tekst, { language: String(args.sprog ?? 'da-DK') })
    return { sagt: true, tegn: tekst.length }
  },

  async phone_bubble(args) {
    const tekst = String(args.tekst ?? '')
    if (!(await bubble.isSupported())) throw new Error('boble_ikke_tilgaengelig')
    bubble.showConversationBubble('', 'Jarvis', tekst)
    return { vist: true }
  },

  async phone_read_file(args) {
    return FileSystem.readAsStringAsync(samlSti(String(args.sti ?? '')))
  },

  async phone_write_file(args) {
    const maal = samlSti(String(args.sti ?? ''))
    await FileSystem.writeAsStringAsync(maal, String(args.indhold ?? ''))
    return { skrevet: true, sti: maal }
  },

  async phone_list_files(args) {
    return FileSystem.readDirectoryAsync(samlSti(String(args.sti ?? '')))
  },

  async phone_share(args) {
    // React Natives egen Share — IKKE vores DelingModule, som kun går den
    // anden vej (den modtager delinger ind i appen; der er ingen udgående
    // metode på den). Netop dén indbyggede ShareModule var i øvrigt den vores
    // eget modul kolliderede med, indtil det blev omdøbt til DelingModule.
    const tekst = String(args.tekst ?? '')
    if (!tekst) throw new Error('tekst_mangler')
    const r = await Share.share({ message: tekst })
    // Arket ER åbnet; hvad Bjørn vælger derinde er hans. Værktøjet afleverer,
    // det sender ikke — og resultatet lover heller ikke andet.
    return { ark_aabnet: true, handling: r.action }
  },

  async phone_clipboard_read() {
    return Clipboard.getStringAsync()
  },

  async phone_clipboard_write(args) {
    await Clipboard.setStringAsync(String(args.tekst ?? ''))
    return { lagt: true }
  }
}

/** Præcis det denne enhed kan — meldes som `capabilities` ved registrering. */
export const KAN_UDFOERE: string[] = Object.keys(HANDLERE)

export async function udfoerVaerktoej(
  vaerktoej: string, args: Record<string, unknown>
): Promise<unknown> {
  const h = HANDLERE[vaerktoej]
  if (!h) throw new Error(`ukendt_vaerktoej: ${vaerktoej}`)
  return h(args)
}
