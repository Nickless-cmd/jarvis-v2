import * as FileSystem from 'expo-file-system/legacy'
import * as IntentLauncher from 'expo-intent-launcher'
import type { ApiConfig } from './types'

const GRANT_READ_URI_PERMISSION = 1

/**
 * Åbn en fil Jarvis har udgivet — hentet MED token, vist fra telefonen.
 *
 * ## Hvorfor den ikke bare er et link
 *
 * `/files/{navn}` kræver godkendelse: målt 12/9-2026 svarer både
 * `localhost:8080` og den udadvendte adresse 401 uden `Authorization`. Et
 * almindeligt browser-tryk ville derfor give «unauthorized» på en fil der
 * findes og er ens egen.
 *
 * Appen har token'et. Så den henter filen selv, lægger den i telefonens eget
 * lager og beder systemet vise DEN kopi. Så virker det for alle filtyper uden
 * at token'et skal ud i en browser eller ind i en URL.
 *
 * Mønstret er `installApk.ts`' — samme download-med-header og samme
 * content-URI-intent. Den klassiske file-system-API lever i `/legacy` i SDK 56.
 */
export async function aabnUdgivetFil(
  config: ApiConfig,
  url: string,
  filnavn: string,
  mime = '',
): Promise<void> {
  const rent = String(filnavn || 'fil').replace(/[^A-Za-z0-9._-]/g, '_')
  const dest = `${FileSystem.documentDirectory}${rent}`
  const task = FileSystem.createDownloadResumable(
    url,
    dest,
    { headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {} },
  )
  const result = await task.downloadAsync()
  if (!result?.uri) throw new Error('hentningen gav ingen fil')
  const contentUri = await FileSystem.getContentUriAsync(result.uri)
  await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
    data: contentUri,
    flags: GRANT_READ_URI_PERMISSION,
    // Uden en type gætter systemet ud fra endelsen, og en HTML uden endelse
    // ender i en tekst-editor. Med typen rammer den browseren.
    type: mime || undefined,
  })
}

/**
 * Hvilken adresse hører blokken til?
 *
 * En UDGIVET fil bærer sin egen `url` og hentes over `/files/{navn}`. En
 * VEDHÆFTNING bærer et `attachment_id` og hentes over det bruger-scopede
 * `/attachments/...`. De to har hver sin rute, og en blok der blander dem ville
 * hente det forkerte sted — derfor afgøres det ét sted frem for i hver
 * komponent der viser en fil.
 */
export function blokUrl(
  blok: { url?: string; attachment_id?: string; type?: string },
  apiBaseUrl: string,
): string {
  const direkte = String(blok.url || '').trim()
  if (direkte) {
    // Serveren kan have gemt en absolut adresse (public_base_url) eller en
    // relativ. Begge skal ende som noget klienten kan hente.
    return /^https?:\/\//i.test(direkte)
      ? direkte
      : new URL(direkte, apiBaseUrl).toString()
  }
  const id = String(blok.attachment_id || '').trim()
  if (!id) return ''
  const sti = blok.type === 'image'
    ? `/attachments/image/${encodeURIComponent(id)}`
    : `/attachments/${encodeURIComponent(id)}`
  return new URL(sti, apiBaseUrl).toString()
}
