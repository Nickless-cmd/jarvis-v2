import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { hentOpmaerksomhed, markerSet, skalKvittere, type Opmaerksomhed } from '../../lib/opmaerksomhed'
import { JarvisRing } from './JarvisRing'
import { maaPolle } from '../../lib/ro'

/**
 * Tilstands-hjernens stemme i desk: én linje der kommer og går.
 *
 * Tavs når intet kræver dig — den skal ikke være endnu en ting at kigge på.
 * Klik åbner den samtale der vinder prioriteten. Åbner du en samtale med et
 * «færdig»/«fejlede», kvitteres det på serveren, så det også forsvinder på
 * telefonen.
 *
 * ## Hvor den bor (Bjørn 21/9-2026)
 *
 * Den lå nederst i VENSTRE panel, klemt mellem samtalelisten og hans navn.
 * Den hører til nederst til HØJRE i vinduet: «det vil jeg gerne have flyttet
 * til højre side og nede i bunden af siden». Derfor er den nu fast placeret i
 * vinduet frem for at ligge i sidepanelets flow — den skal kunne komme og gå
 * uden at skubbe til noget.
 *
 * Prikken var en farvet cirkel. Nu er det Jarvis' eget mærke, og det
 * bevæger sig når han arbejder: det er HAM der er i gang, og mærket er det
 * samme som i headeren og ved composeren.
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
      if (!maaPolle('opmaerksomhed', 5000)) return  // ingen kigger -> sjaeldnere (ro.ts)
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
      <JarvisRing size={15} spinning={o.tilstand === 'running'}
                  tone={o.tilstand === 'failed' ? 'error' : o.tilstand === 'running' ? 'working' : 'idle'} />
      <span className="opm-etiket">{o.etiket}{antal > 1 ? ` · ${antal}` : ''}</span>
      {fokus?.titel ? <span className="opm-titel">{fokus.titel}</span> : null}
    </button>
  )
}
