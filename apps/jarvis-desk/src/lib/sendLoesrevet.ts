import type { ApiConfig } from './api'
import { readModelPrefs } from './composerPrefs'
import { startStream } from './streamClient'

/**
 * Send en besked i en samtale og SLIP strømmen, så snart runnet har et id.
 *
 * Turen kører videre på serveren (detached). Brugt af Jarvis-figurens
 * «Start ny chat» og af sideopgave-kortets «Start lokalt», «Start i
 * worktree» og «Send til baggrunden». Fordi ingen holder strømmen til
 * ende, bliver svaret til «Færdig — se svaret» i tilstands-hjernen — og
 * åbner man samtalen, følger desk det levende run som ved en overtagelse.
 *
 * Samme model-valg som composeren (readModelPrefs).
 */
export interface LoesrevetBesked {
  sessionId: string
  message: string
  mode?: 'chat' | 'code'
  workspaceKind?: 'container' | 'workstation'
  workspaceRoot?: string
}

export function sendLoesrevet(config: ApiConfig, b: LoesrevetBesked): Promise<void> {
  const besked = b.message.trim()
  if (!besked) return Promise.reject(new Error('Tom besked'))
  const prefs = readModelPrefs()
  return new Promise<void>((ok, fejl) => {
    let faerdig = false
    const slut = (f?: Error) => { if (faerdig) return; faerdig = true; if (f) fejl(f); else ok() }
    const ctl = startStream(
      {
        apiBaseUrl: config.apiBaseUrl, authToken: config.authToken, sessionId: b.sessionId,
        message: besked, mode: b.mode ?? 'chat', model: prefs.model, providerChoice: prefs.providerChoice,
        ...(b.workspaceKind ? { workspaceKind: b.workspaceKind } : {}),
        ...(b.workspaceRoot ? { workspaceRoot: b.workspaceRoot } : {}),
      },
      {
        onEvent: () => {},
        onRunId: () => { slut(); ctl.abort() },
        onError: (e) => slut(new Error(e.message || 'Kunne ikke sende')),
        onComplete: () => slut(),
      },
    )
  })
}
