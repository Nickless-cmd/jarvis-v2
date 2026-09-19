import { useEffect, useState } from 'react'
import type { ComposerSendOpts } from '../components/shell/Composer'

export interface KoetBesked { text: string; opts: ComposerSendOpts }

/**
 * Køen: skriver man mens Jarvis svarer ELLER mens man er offline, lægges
 * beskeden i kø og sendes af sig selv når turen er færdig / forbindelsen er
 * tilbage.
 *
 * Fælles for ChatView og CodeView (19/9-2026). Før havde kun ChatView en kø;
 * CodeView sendte straks og startede en NY kørsel oven i den der kørte —
 * selvom skrivefeltet lovede «sendes når J.A.R.V.I.S. er færdig».
 *
 * Claude Desktops regel (cc-desktop-chatview.md §6): «Cancelling a queued
 * message no longer interrupts the turn in progress». `annuller` rører derfor
 * KUN køen — aldrig streamen.
 */
export function useSendeKoe({ arbejder, online, send }: {
  arbejder: boolean
  online: boolean
  send: (text: string, opts: ComposerSendOpts) => void | Promise<void>
}) {
  const [koet, setKoet] = useState<KoetBesked | null>(null)

  const sendEllerKoe = (text: string, opts: ComposerSendOpts) => {
    if (arbejder || !online) setKoet({ text, opts })
    else void send(text, opts)
  }

  useEffect(() => {
    // Flush når der hverken arbejdes eller er offline (færdig tur OG genforbindelse).
    if (koet && !arbejder && online) {
      const k = koet
      setKoet(null)
      void send(k.text, k.opts)
    }
  }, [arbejder, koet, online]) // eslint-disable-line react-hooks/exhaustive-deps

  return { koet, sendEllerKoe, annuller: () => setKoet(null) }
}
