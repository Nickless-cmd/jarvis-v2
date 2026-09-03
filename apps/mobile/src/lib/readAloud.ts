import { createAudioPlayer } from 'expo-audio'
import * as Speech from 'expo-speech'
import { synthesizeTtsToFile } from './voiceApi'
import { clampForSpeech, stripForSpeech } from './speechText'
import type { ApiConfig } from './types'

/**
 * Læs en besked op med JARVIS' EGEN stemme.
 *
 * To ting var galt før. Den læste beskedens RÅ markdown, så syntesen sagde
 * «stjerne stjerne» og stavede kodeblokke. Og den brugte telefonens indbyggede
 * stemme — så han lød som en oplæsningsmaskine og ikke som sig selv, selv om
 * ElevenLabs-kontoen har været aktiv hele tiden (stemmen hedder
 * «Mathias - Storyteller», verificeret 3. sept.).
 *
 * Telefonens stemme er stadig med som REDE, ikke som førstevalg: uden net eller
 * ved en fejl på serveren er en mekanisk oplæsning bedre end tavshed. Men den
 * får den rensede tekst, så den heller ikke citerer tegn.
 */

let player: ReturnType<typeof createAudioPlayer> | null = null

export function stopReading(): void {
  try { player?.remove() } catch { /* allerede væk */ }
  player = null
  try { Speech.stop() } catch { /* noop */ }
}

export async function readAloud(
  config: ApiConfig | null,
  markdown: string,
  onDone: () => void
): Promise<'jarvis' | 'device' | 'none'> {
  const text = clampForSpeech(stripForSpeech(markdown))
  if (!text) { onDone(); return 'none' }

  stopReading()

  if (config?.authToken) {
    try {
      const { uri } = await synthesizeTtsToFile(config, text)
      const p = createAudioPlayer({ uri })
      player = p
      p.addListener('playbackStatusUpdate', (st) => {
        if (st.didJustFinish) { stopReading(); onDone() }
      })
      p.play()
      return 'jarvis'
    } catch {
      // Falder igennem til telefonens stemme — se docstring.
    }
  }

  try {
    Speech.speak(text, { language: 'da-DK', onDone, onError: onDone })
    return 'device'
  } catch {
    onDone()
    return 'none'
  }
}
