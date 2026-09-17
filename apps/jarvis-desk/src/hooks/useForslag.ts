import { useEffect, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { hentNaesteForslag } from '../lib/forslag'

/**
 * Auto-forslag til komponisten — et bud på den NÆSTE besked.
 *
 * Forslaget bygger på samtalen (Jarvis' sidste svar), ikke på hvad der bliver
 * tastet. Det er hele pointen: et forslag der fyrer mens man skriver, lander
 * midt i ens egen sætning. Bjørn 17/9-2026: «det kommer dumpende mens jeg
 * skriver, det er virkelig træls». Så forslaget hentes når feltet er TOMT og
 * står dér hvor pladsholderen står, indtil Tab tager imod.
 *
 * ## Hvorfor de primitive deps
 *
 * `config` er et NYT objekt på hver render af kalderen (ChatView genskaber
 * `{apiBaseUrl, authToken}`), så at afhænge af objektets identitet ville give
 * et kald pr. render. Under polling er det ~2×/sek. Det er samme fælde
 * Composerens model-context-effekt blev bidt af 16/6-2026.
 *
 * ## Hvorfor en pause selv uden tastning
 *
 * `aktiv` bliver sand i samme øjeblik et svar er færdigt — dér er GPU'en stadig
 * varm fra turen. Pausen lader den komme fri, og den koster intet: feltet er
 * tomt, så der er ingen der venter på forslaget.
 */
export const HENT_PAUSE_MS = 700

export function useForslag(
  config: ApiConfig | undefined,
  sessionId: string | null | undefined,
  aktiv: boolean,
): string {
  const [forslag, setForslag] = useState('')
  const base = config?.apiBaseUrl
  const token = config?.authToken ?? null
  const sid = sessionId ?? ''

  useEffect(() => {
    // Ryd straks: et forslag hentet til en anden samtale — eller før det
    // seneste svar — er ikke længere et bud på hvad der kunne skrives nu.
    setForslag('')
    if (!aktiv || !base || !sid) return

    const ctrl = new AbortController()
    const t = window.setTimeout(() => {
      void hentNaesteForslag({ apiBaseUrl: base, authToken: token }, sid, ctrl.signal)
        .then((f) => { if (!ctrl.signal.aborted) setForslag(f) })
    }, HENT_PAUSE_MS)

    return () => {
      window.clearTimeout(t)
      ctrl.abort()
    }
  }, [base, token, sid, aktiv])

  return forslag
}
