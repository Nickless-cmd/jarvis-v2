import { useState } from 'react'
import { apiFetch, type ApiConfig } from '../lib/api'

export interface Tilbagespolet { rewindId: string; fjernet: number }

/**
 * Spol tilbage + fortryd — Claude Desktops kontrakt (cc-desktop-chatview.md
 * §8): «Brings back the messages this rewind removed. Your files stay as they
 * are. Undo works until you send your next message.»
 *
 * Serveren flytter beskederne til et arkiv og lægger dem tilbage ved fortryd
 * (core/runtime/db_chat_rewind.py); her holdes kun det der skal til for at
 * tilbyde fortryd — og det glemmes ved næste besked (`glem`).
 */
export function useTilbagespol({ config, sessionId, genindlaes }: {
  config: ApiConfig | undefined
  sessionId: string | null | undefined
  genindlaes: () => void | Promise<void>
}) {
  const [tilbagespolet, setTilbagespolet] = useState<Tilbagespolet | null>(null)
  const [indsaet, setIndsaet] = useState<{ tekst: string; n: number } | null>(null)
  const [fejl, setFejl] = useState('')

  const spol = async (messageId: string) => {
    if (!config || !sessionId) return
    setFejl('')
    try {
      const r = await apiFetch<{ rewind_id: string; fjernet: number; tekst: string }>(
        config, `/chat/sessions/${encodeURIComponent(sessionId)}/rewind`,
        { method: 'POST', body: { message_id: messageId } },
      )
      setTilbagespolet({ rewindId: r.rewind_id, fjernet: r.fjernet })
      setIndsaet({ tekst: r.tekst, n: Date.now() })
      await genindlaes()
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Kunne ikke spole tilbage')
    }
  }

  const fortryd = async () => {
    if (!config || !sessionId || !tilbagespolet) return
    setFejl('')
    try {
      await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}/rewind/${encodeURIComponent(tilbagespolet.rewindId)}/undo`, { method: 'POST' })
      setTilbagespolet(null)
      setIndsaet({ tekst: '', n: Date.now() })
      await genindlaes()
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Kunne ikke fortryde')
    }
  }

  /** Fortryd lukker ved næste besked (og ved samtaleskift). */
  const glem = () => { setTilbagespolet(null); setFejl('') }

  return { tilbagespolet, indsaet, fejl, spol, fortryd, glem }
}
