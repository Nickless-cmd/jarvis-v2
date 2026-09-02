import * as FileSystem from 'expo-file-system/legacy'
import type { ApiConfig } from './types'

/** Voice-api til samtale-mode (Trin 3). STT via /transcribe (whisper), TTS via
 *  /api/tts/synthesize (ElevenLabs primær). Alt best-effort — kaster ved fejl så
 *  hook'en kan falde tilbage (device-native). */

/** Send optaget lyd (fil-uri fra expo-av) → /transcribe → tekst. */
export async function transcribeAudio(
  config: ApiConfig,
  fileUri: string,
): Promise<{ status: string; text: string; error?: string }> {
  const url = new URL('/transcribe', config.apiBaseUrl).toString()
  const form = new FormData()
  // RN FormData: fil-part via { uri, name, type }
  form.append('file', { uri: fileUri, name: 'utterance.m4a', type: 'audio/m4a' } as unknown as Blob)
  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${config.authToken}` },
    body: form,
  })
  if (!res.ok) throw new Error(`transcribe HTTP ${res.status}`)
  return res.json() as Promise<{ status: string; text: string; error?: string }>
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
