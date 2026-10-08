import { useEffect, useState } from 'react'
import { useStreamUdsnit } from '../hooks/useStream'
import { registerPwa } from '../pwa/register'
import '../styles/pwa.css'

/** Offer a new build only between runs; a live answer is never interrupted. */
export function PwaRunUpdateHost() {
  const status = useStreamUdsnit((stream) => stream.status)
  const activeRunId = useStreamUdsnit((stream) => stream.activeRunId)
  return <PwaUpdateHost busy={status === 'working' || Boolean(activeRunId)} />
}

export function PwaUpdateHost({ busy = false }: { busy?: boolean }) {
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null)
  const [updating, setUpdating] = useState(false)

  useEffect(() => registerPwa(setWaiting), [])
  useEffect(() => {
    if (!updating) return
    const onChange = () => window.location.reload()
    navigator.serviceWorker.addEventListener('controllerchange', onChange)
    return () => navigator.serviceWorker.removeEventListener('controllerchange', onChange)
  }, [updating])

  if (!__WEB_BUILD__ || !waiting || busy) return null
  return <div className="pwa-update" role="status">
    <span>En ny version af Jarvis er klar.</span>
    <button type="button" disabled={updating} onClick={() => {
      setUpdating(true)
      waiting.postMessage({ type: 'SKIP_WAITING' })
    }}>Genindlæs</button>
  </div>
}
