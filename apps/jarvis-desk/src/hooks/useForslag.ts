import { useEffect, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { PAUSE_MS, boerSpoerge, hentForslag } from '../lib/forslag'

/**
 * Auto-forslag til komponisten — hvad der kunne skrives videre.
 *
 * Henter fra `/composer/suggest` (lokal ollama; udkastet forlader aldrig
 * maskinen) efter en pause i tastningen, og kaster svaret væk hvis brugeren
 * nåede at skrive videre imens.
 *
 * ## Hvorfor de primitive deps
 *
 * `config` er et NYT objekt på hver render af kalderen (ChatView genskaber
 * `{apiBaseUrl, authToken}`), så at afhænge af objektets identitet ville give
 * et kald pr. render. Under polling er det ~2×/sek. Det er samme fælde
 * Composerens model-context-effekt blev bidt af 16/6-2026.
 *
 * `aktiv` slukker for hentningen — fx mens et svar streamer, hvor forslaget
 * ville konkurrere med det synlige svar om den samme GPU.
 */
export function useForslag(
  config: ApiConfig | undefined,
  tekst: string,
  aktiv: boolean,
): string {
  const [forslag, setForslag] = useState('')
  const base = config?.apiBaseUrl
  const token = config?.authToken ?? null

  useEffect(() => {
    // Ryd straks: et forslag der blev hentet til en kortere tekst er ikke
    // længere en gyldig fortsættelse af den der står nu.
    setForslag('')
    if (!aktiv || !base || !boerSpoerge(tekst)) return

    const ctrl = new AbortController()
    const t = window.setTimeout(() => {
      void hentForslag({ apiBaseUrl: base, authToken: token }, tekst, ctrl.signal)
        .then((f) => { if (!ctrl.signal.aborted) setForslag(f) })
    }, PAUSE_MS)

    return () => {
      window.clearTimeout(t)
      ctrl.abort()
    }
  }, [base, token, tekst, aktiv])

  return forslag
}
