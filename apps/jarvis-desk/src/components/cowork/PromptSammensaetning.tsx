import { useEffect, useState } from 'react'
import { Layers } from 'lucide-react'
import { getRunPrompt, type PromptSammensaetning as Data } from '../../lib/coworkApi'
import type { ApiConfig } from '../../lib/api'

/** «Hvad byggede han svaret på?» — prompten for ét run, opdelt i sektioner.
 *
 *  Labels skrives med understreger på serversiden; de laves om til mellemrum
 *  her, fordi det er en visnings-ting og endpointet skal blive ved at være en
 *  tro projektion af hændelsen.
 */
const pænt = (s: string) => s.replace(/_/g, ' ').replace(/\s+/g, ' ').trim()

export function PromptSammensaetning({ config, runId }: { config?: ApiConfig; runId: string }) {
  const [data, setData] = useState<Data | null>(null)
  const [fejl, setFejl] = useState(false)

  useEffect(() => {
    if (!config || !runId) return
    let levende = true
    setFejl(false)
    getRunPrompt(config, runId)
      .then((d) => { if (levende) setData(d) })
      .catch(() => { if (levende) setFejl(true) })
    return () => { levende = false }
  }, [config?.apiBaseUrl, config?.authToken, runId])

  if (fejl) return <p className="ps-tom">Kunne ikke hente prompt-sammensætningen.</p>
  if (!data) return null
  if (!data.found) {
    return (
      <p className="ps-tom">
        Sammensætningen blev ikke gemt for denne tur. Det betyder ikke at prompten var tom.
      </p>
    )
  }

  const top = data.sections.slice(0, 12)
  const rest = data.sections.length - top.length

  return (
    <div className="ps">
      <div className="ps-head">
        <Layers size={13} />
        <span>
          {data.section_count} sektioner · {Math.round((data.total_chars ?? 0) / 1000)}k tegn
          {data.answer_chars ? ` · svar ${data.answer_chars} tegn` : ''}
        </span>
      </div>
      <ul className="ps-liste">
        {top.map((s) => (
          <li key={s.label} className="ps-rk">
            <span className="ps-label" title={pænt(s.label)}>{pænt(s.label)}</span>
            <span className="ps-bar"><span className="ps-fyld" style={{ width: `${s.pct}%` }} /></span>
            <span className="ps-tal">{s.pct}%</span>
          </li>
        ))}
      </ul>
      {rest > 0 && <p className="ps-rest">+ {rest} mindre sektioner</p>}
    </div>
  )
}
