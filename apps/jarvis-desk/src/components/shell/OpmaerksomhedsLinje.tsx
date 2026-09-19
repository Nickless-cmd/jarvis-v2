import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { hentOpmaerksomhed, markerSet, skalKvittere, type Opmaerksomhed } from '../../lib/opmaerksomhed'

/**
 * Tilstands-hjernens stemme i desk: én linje nederst i sidepanelet.
 *
 * Tavs når intet kræver dig — den skal ikke være endnu en ting at kigge på.
 * Klik åbner den samtale der vinder prioriteten. Åbner du en samtale med et
 * «færdig»/«fejlede», kvitteres det på serveren, så det også forsvinder på
 * telefonen.
 */
export function OpmaerksomhedsLinje({ config, aktivId, onAabn }: {
  config: ApiConfig | null
  aktivId: string | null
  onAabn: (sessionId: string) => void
}) {
  const [o, setO] = useState<Opmaerksomhed | null>(null)

  useEffect(() => {
    if (!config) return
    let aktiv = true
    const tick = () => {
      void hentOpmaerksomhed(config)
        .then((d) => { if (aktiv) setO(d) })
        .catch(() => { /* behold sidste — ingen flimren ved netværks-blip */ })
    }
    tick()
    const id = setInterval(tick, 5000)
    return () => { aktiv = false; clearInterval(id) }
  }, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!config || !aktivId || !skalKvittere(o, aktivId)) return
    setO((f) => (f ? { ...f, punkter: f.punkter.filter((p) => p.session_id !== aktivId) } : f))
    void markerSet(config, aktivId).catch(() => {})
  }, [aktivId, o, config])

  if (!o || o.tilstand === 'idle') return null
  const antal = o.antal[o.tilstand as keyof Opmaerksomhed['antal']] ?? 0
  const fokus = o.fokus
  const kanAabnes = Boolean(fokus?.session_id)
  return (
    <button
      type="button"
      className={`opm-linje opm-${o.tilstand}`}
      data-testid="opmaerksomhed"
      disabled={!kanAabnes}
      title={fokus?.tekst || fokus?.titel || o.etiket}
      onClick={() => { if (fokus?.session_id) onAabn(fokus.session_id) }}
    >
      <span className="opm-prik" aria-hidden />
      <span className="opm-etiket">{o.etiket}{antal > 1 ? ` · ${antal}` : ''}</span>
      {fokus?.titel ? <span className="opm-titel">{fokus.titel}</span> : null}
    </button>
  )
}
