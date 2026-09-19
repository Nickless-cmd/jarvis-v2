import { createSession, type ApiConfig } from '../lib/api'
import { readModelPrefs } from '../lib/composerPrefs'
import { startStream } from '../lib/streamClient'

/**
 * «Start ny chat» fra figuren (Codex' Quick Chat).
 *
 * Opretter en samtale og sender beskeden ad SAMME vej som composeren
 * (/chat/stream/v2, samme model-valg). Så snart runnet har et id, slipper
 * figuren strømmen: turen kører videre på serveren (detached), og fordi
 * ingen så den til ende, bliver den til «Færdig — se svaret» i
 * tilstands-hjernen. Holdt figuren strømmen, ville svaret tælle som set.
 */
export async function sendHurtigt(config: ApiConfig, tekst: string): Promise<string> {
  const besked = tekst.trim()
  if (!besked) throw new Error('Tom besked')
  const titel = besked.length > 60 ? `${besked.slice(0, 57)}…` : besked
  const session = await createSession(config, titel, 'chat')
  const prefs = readModelPrefs()
  await new Promise<void>((ok, fejl) => {
    let faerdig = false
    const slut = (f?: Error) => { if (faerdig) return; faerdig = true; if (f) fejl(f); else ok() }
    const ctl = startStream(
      {
        apiBaseUrl: config.apiBaseUrl, authToken: config.authToken, sessionId: session.id,
        message: besked, mode: 'chat', model: prefs.model, providerChoice: prefs.providerChoice,
      },
      {
        onEvent: () => {},
        onRunId: () => { slut(); ctl.abort() },
        onError: (e) => slut(new Error(e.message || 'Kunne ikke sende')),
        onComplete: () => slut(),
      },
    )
  })
  return session.id
}
