import { useEffect, useRef, useState } from 'react'
import type { tilStreamFelter } from './chatSettings'

export interface FollowupItem {
  id: number
  sessionId: string
  text: string
  attachmentIds?: string[]
  controls?: ReturnType<typeof tilStreamFelter>
}

/** Lokal kø pr. samtale. Ét run ad gangen; næste besked går først afsted,
 * når den forrige har været aktiv og siden er afsluttet. */
export function useFollowupQueue({
  sessionId, busy, online, send, steer,
}: {
  sessionId: string | null
  busy: boolean
  online: boolean
  send: (item: FollowupItem) => void | Promise<void>
  steer: (item: FollowupItem) => Promise<void>
}) {
  const [queue, setQueue] = useState<FollowupItem[]>([])
  const [error, setError] = useState('')
  const nextId = useRef(0)
  const dispatched = useRef<string | null>(null)
  const sendRef = useRef(send)
  const steerRef = useRef(steer)
  sendRef.current = send
  steerRef.current = steer
  const visible = queue.filter((item) => item.sessionId === sessionId)

  useEffect(() => {
    if (dispatched.current && dispatched.current !== sessionId) dispatched.current = null
    if (busy) { dispatched.current = null; return }
    if (!online || !sessionId || dispatched.current || error) return
    const item = queue.find((entry) => entry.sessionId === sessionId)
    if (!item) return
    dispatched.current = sessionId
    setQueue((current) => current.filter((entry) => entry.id !== item.id))
    void Promise.resolve().then(() => sendRef.current(item)).catch((cause) => {
      setQueue((current) => [item, ...current])
      setError(cause instanceof Error ? cause.message : 'Kunne ikke sende beskeden')
    })
  }, [busy, online, queue, sessionId, error])

  return {
    items: visible,
    error,
    enqueue: (text: string, attachmentIds?: string[], controls?: ReturnType<typeof tilStreamFelter>) => {
      if (!sessionId) return
      setQueue((current) => [...current, { id: ++nextId.current, sessionId, text, attachmentIds, controls }])
      setError('')
    },
    remove: (id: number) => setQueue((current) => current.filter((item) => item.id !== id)),
    edit: (id: number, text: string) => setQueue((current) => current.map((item) =>
      item.id === id ? { ...item, text: text.trim() } : item)),
    move: (id: number, direction: -1 | 1) => setQueue((current) => {
      const from = current.findIndex((item) => item.id === id)
      if (from < 0) return current
      let to = from + direction
      while (to >= 0 && to < current.length && current[to]?.sessionId !== current[from]?.sessionId) to += direction
      if (to < 0 || to >= current.length) return current
      const next = [...current]
      ;[next[from], next[to]] = [next[to]!, next[from]!]
      return next
    }),
    sendNow: async (id: number) => {
      const item = queue.find((entry) => entry.id === id && entry.sessionId === sessionId)
      if (!item || !online) return
      if (busy && item.attachmentIds?.length) {
        setError('Vedhæftninger kan først sendes, når det aktuelle svar er færdigt.')
        return
      }
      try {
        if (busy) await steerRef.current(item)
        else {
          dispatched.current = sessionId
          setQueue((current) => current.filter((entry) => entry.id !== id))
          await sendRef.current(item)
        }
        if (busy) setQueue((current) => current.filter((entry) => entry.id !== id))
        setError('')
      } catch (cause) {
        if (!busy) setQueue((current) => [item, ...current])
        setError(cause instanceof Error ? cause.message : 'Kunne ikke sende beskeden')
      }
    },
  }
}
