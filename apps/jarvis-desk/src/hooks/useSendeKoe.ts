import { useEffect, useRef, useState } from 'react'
import type { ComposerSendOpts } from '../components/shell/Composer'

export interface KoetItem {
  id: number
  text: string
  opts: ComposerSendOpts
}

/**
 * Køen: skriver man mens Jarvis svarer ELLER mens man er offline, lægges
 * beskeden i kø og sendes af sig selv når turen er færdig / forbindelsen er
 * tilbage.
 *
 * 3/10-2026 (Bjørn): «que beskeder over composer mangler styr funktion lige
 * som i mobilen». Før var køen ÉN besked med en ×-knap. Nu er den en liste
 * med samme styring som mobilens `useFollowupQueue`: rediger, flyt op/ned,
 * «send nu» (serverens mid-flight steer) og fjern.
 *
 * Fælles for ChatView og CodeView (19/9-2026). Før havde kun ChatView en kø;
 * CodeView sendte straks og startede en NY kørsel oven i den der kørte —
 * selvom skrivefeltet lovede «sendes når J.A.R.V.I.S. er færdig».
 *
 * Claude Desktops regel (cc-desktop-chatview.md §6): «Cancelling a queued
 * message no longer interrupts the turn in progress». `fjern` rører derfor
 * KUN køen — aldrig streamen. Det gør `sendNu` midt i et run heller ikke:
 * den bruger serverens steer, der samles op ved næste runde-grænse.
 */
export function useSendeKoe({ arbejder, online, send, steer, kanSteer = false }: {
  arbejder: boolean
  online: boolean
  send: (text: string, opts: ComposerSendOpts) => void | Promise<void>
  /** Injicér midt i et kørende run. Uden den virker «send nu» kun når turen er fri. */
  steer?: (text: string) => Promise<void>
  kanSteer?: boolean
}) {
  const [items, setItems] = useState<KoetItem[]>([])
  const [error, setError] = useState('')
  const naesteId = useRef(0)
  // Vagt: én afsendelse ad gangen. Uden den kunne to kø-beskeder sendes i
  // samme vindue før `arbejder` nåede at slå til. Nulstilles når et run tager over.
  const sendt = useRef(false)

  const sendEllerKoe = (text: string, opts: ComposerSendOpts) => {
    if (arbejder || !online) {
      setItems((k) => [...k, { id: ++naesteId.current, text, opts }])
      setError('')
    } else void send(text, opts)
  }

  useEffect(() => {
    // Flush når der hverken arbejdes eller er offline (færdig tur OG genforbindelse).
    if (arbejder) { sendt.current = false; return }
    if (!online || items.length === 0 || sendt.current) return
    const foerste = items[0]!
    sendt.current = true
    setItems((k) => k.slice(1))
    // Fejlede afsendelsen, er beskeden ikke tabt — den lægges forrest igen.
    const genindsæt = (e: unknown) => {
      sendt.current = false
      setItems((k) => [foerste, ...k])
      setError(e instanceof Error ? e.message : 'Kunne ikke sende beskeden')
    }
    // Kaldet sker SYNKRONT (som før listen kom til). Lå vi det i en microtask,
    // ville afsendelsen først ske efter næste tick — og en hurtig anden
    // kø-besked kunne nå at se en kø der så tom ud. Fejlen fanges stadig.
    try {
      const p = send(foerste.text, foerste.opts)
      void Promise.resolve(p).catch(genindsæt)
    } catch (e) {
      genindsæt(e)
    }
  }, [arbejder, online, items]) // eslint-disable-line react-hooks/exhaustive-deps

  return {
    items,
    error,
    sendEllerKoe,
    fjern: (id: number) => setItems((k) => k.filter((i) => i.id !== id)),
    rediger: (id: number, text: string) => setItems((k) => k.map((i) => (i.id === id ? { ...i, text } : i))),
    flyt: (id: number, retning: -1 | 1) => setItems((k) => {
      const fra = k.findIndex((i) => i.id === id)
      if (fra < 0) return k
      const til = fra + retning
      if (til < 0 || til >= k.length) return k
      const n = [...k]
      ;[n[fra], n[til]] = [n[til]!, n[fra]!]
      return n
    }),
    sendNu: async (id: number) => {
      const item = items.find((i) => i.id === id)
      if (!item || !online) return
      try {
        if (arbejder) {
          if (!kanSteer || !steer) return
          await steer(item.text)
        } else {
          await send(item.text, item.opts)
        }
        setItems((k) => k.filter((i) => i.id !== id))
        setError('')
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Kunne ikke sende beskeden')
      }
    },
  }
}
