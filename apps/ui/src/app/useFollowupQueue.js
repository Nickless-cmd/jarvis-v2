import { useEffect, useRef, useState } from 'react'

/** Køen tilhører en samtale, og én follow-up starter først efter forrige run. */
export function useFollowupQueue({ sessionId, isStreaming, onSend, onSteer }) {
  const [queue, setQueue] = useState([])
  const [error, setError] = useState('')
  const nextId = useRef(0)
  const sending = useRef(false)
  const sessionRef = useRef(sessionId)
  sessionRef.current = sessionId
  const queueRef = useRef(queue)
  queueRef.current = queue
  const sendRef = useRef(onSend)
  const steerRef = useRef(onSteer)
  sendRef.current = onSend
  steerRef.current = onSteer

  useEffect(() => {
    if (isStreaming) {
      sending.current = false
      return
    }
    if (sending.current || !sessionId || error) return
    const item = queue.find((entry) => entry.sessionId === sessionId)
    if (!item) return
    sending.current = true
    // Send after React has committed the completed run. The send callback
    // returns when its stream ends, but the next item waits for a new edge.
    setTimeout(() => {
      if (sessionRef.current !== item.sessionId) {
        sending.current = false
        return
      }
      const latest = queueRef.current.find((entry) => entry.sessionId === item.sessionId)
      if (!latest) { sending.current = false; return }
      setQueue((current) => current.filter((entry) => entry.id !== latest.id))
      Promise.resolve().then(() => sendRef.current(latest.msg, latest.opts)).catch((cause) => {
        setQueue((current) => [latest, ...current])
        setError(cause instanceof Error ? cause.message : 'Could not send follow-up')
      })
    }, 0)
  }, [isStreaming, queue, sessionId, error])

  return {
    items: queue.filter((item) => item.sessionId === sessionId),
    error,
    enqueue: (msg, opts) => {
      if (!sessionId) return
      setQueue((current) => [...current, { id: ++nextId.current, sessionId, msg, opts }])
      setError('')
    },
    remove: (id) => setQueue((current) => current.filter((item) => item.id !== id)),
    edit: (id, msg) => setQueue((current) => current.map((item) =>
      item.id === id ? { ...item, msg: msg.trim() } : item)),
    move: (id, direction) => setQueue((current) => {
      const from = current.findIndex((item) => item.id === id)
      if (from < 0) return current
      let to = from + direction
      while (to >= 0 && to < current.length && current[to].sessionId !== current[from].sessionId) to += direction
      if (to < 0 || to >= current.length) return current
      const next = [...current]
      ;[next[from], next[to]] = [next[to], next[from]]
      return next
    }),
    sendNow: async (id) => {
      const item = queue.find((entry) => entry.id === id && entry.sessionId === sessionId)
      if (!item) return
      if (isStreaming && item.opts?.attachmentIds?.length) {
        setError('Attachments can be sent after the current run finishes.')
        return
      }
      try {
        if (isStreaming) {
          const accepted = await steerRef.current(item.msg)
          if (!accepted) throw new Error('The active run is not ready for a steer yet.')
        } else {
          sending.current = true
          setQueue((current) => current.filter((entry) => entry.id !== id))
          await sendRef.current(item.msg, item.opts)
        }
        setQueue((current) => current.filter((entry) => entry.id !== id))
        setError('')
      } catch (cause) {
        if (!isStreaming) setQueue((current) => [item, ...current])
        setError(cause instanceof Error ? cause.message : 'Could not steer the active run')
      }
    },
  }
}
