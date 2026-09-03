import * as FileSystem from 'expo-file-system/legacy'
import { File, UploadType } from 'expo-file-system'
import type { ApiConfig } from './types'

/** Voice-api til samtale-mode (Trin 3). STT via /transcribe (whisper), TTS via
 *  /api/tts/synthesize (ElevenLabs primær). Alt best-effort — kaster ved fejl så
 *  hook'en kan falde tilbage (device-native). */

/** Send optaget lyd (fil-uri fra optageren) → /transcribe → tekst.
 *
 *  UPLOADET SKER NATIVT, ikke gennem fetch. Den oplagte RN-genvej —
 *  `form.append('file', { uri, name, type })` — er død under Expos fetch:
 *  den serialiserer multipart i JavaScript og kan ikke læse en fil-uri.
 *  Expo skriver det selv i convertFormData.ts: «uri is not supported for
 *  React Native's FormData». Resultatet var «Unsupported FormDataPart
 *  implementation» — kastet FØR noget som helst forlod telefonen, så
 *  serveren så aldrig et kald og der var intet at fejlsøge i logs.
 *
 *  File.upload() lader den native side bygge multipart-kroppen direkte fra
 *  filen. Den er ikke bare en omvej udenom fejlen: lyden passerer aldrig
 *  gennem JS-heapen, så en lang ytring koster ikke en base64-kopi i
 *  hukommelsen.
 *
 *  Filnavnet betyder noget i den anden ende: serveren vælger demuxer ud fra
 *  endelsen (.m4a), så en optagelse uden endelse ville blive gættet som webm.
 */
export async function transcribeAudio(
  config: ApiConfig,
  fileUri: string,
): Promise<{ status: string; text: string; error?: string }> {
  const url = new URL('/transcribe', config.apiBaseUrl).toString()
  const res = await new File(fileUri).upload(url, {
    uploadType: UploadType.MULTIPART,
    fieldName: 'file',
    mimeType: 'audio/m4a',
    parameters: { language: 'da' },
    headers: { Authorization: `Bearer ${config.authToken}` },
  })
  if (res.status < 200 || res.status >= 300) throw new Error(`transcribe HTTP ${res.status}`)
  try {
    return JSON.parse(res.body) as { status: string; text: string; error?: string }
  } catch {
    throw new Error('transcribe: uventet svar fra serveren')
  }
}

function _b64(bytes: Uint8Array): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  let out = ''
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i] ?? 0, b = bytes[i + 1] ?? 0, c = bytes[i + 2] ?? 0
    out += chars[a >> 2]
    out += chars[((a & 3) << 4) | (b >> 4)]
    out += i + 1 < bytes.length ? chars[((b & 15) << 2) | (c >> 6)] : '='
    out += i + 2 < bytes.length ? chars[c & 63] : '='
  }
  return out
}

/** Syntetisér tekst → MP3, skriv til cache-fil, returnér {uri, provider}.
 *  expo-av afspiller fra fil-uri (RN kan ikke afspille en Blob direkte). */
export async function synthesizeTtsToFile(
  config: ApiConfig,
  text: string,
): Promise<{ uri: string; provider: string }> {
  const url = new URL('/api/tts/synthesize', config.apiBaseUrl).toString()
  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${config.authToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, provider: 'auto' }),
  })
  if (!res.ok) throw new Error(`tts HTTP ${res.status}`)
  const provider = res.headers.get('X-TTS-Provider') || 'unknown'
  const buf = new Uint8Array(await res.arrayBuffer())
  const dir = FileSystem.cacheDirectory || FileSystem.documentDirectory || ''
  const uri = `${dir}jarvis_tts_${Date.now()}.mp3`
  await FileSystem.writeAsStringAsync(uri, _b64(buf), { encoding: 'base64' })
  return { uri, provider }
}
