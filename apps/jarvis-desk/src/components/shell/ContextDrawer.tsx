import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, Layers } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { getKontekst, type KontekstResume } from '../../lib/coworkApi'

/**
 * Kontekst-drawer ved komponisten — «hvad bruger Jarvis lige nu».
 *
 * Codex' punkt 3: brugeren skulle kunne se hvilke filer, memories og regler
 * der er i spil, uden at grave i indstillinger.
 *
 * Tallene er MÅLTE, ikke estimerede. De kommer fra sidste turs faktiske
 * prompt-sammensætning, som gemmes når turen bygges. Et estimat før
 * afsendelse ville være et gæt præsenteret som en måling — og at bygge
 * prompten for at vise den koster sekunder.
 *
 * Derfor siger overskriften «sidste tur» og ikke «denne tur». Forskellen er
 * lille i praksis og stor i ærlighed.
 */
export function ContextDrawer({
  config, sessionId,
}: { config: ApiConfig | undefined; sessionId?: string }) {
  const [data, setData] = useState<KontekstResume | null>(null)
  const [åben, setÅben] = useState(false)

  useEffect(() => {
    if (!config) return
    let levende = true
    getKontekst(config, sessionId)
      .then((d) => { if (levende) setData(d) })
      .catch(() => { if (levende) setData(null) })
    return () => { levende = false }
  }, [config?.apiBaseUrl, config?.authToken, sessionId, åben])

  if (!data?.har_data) return null

  const kTokens = Math.round(data.tegn / 4 / 100) / 10

  return (
    <div className={åben ? 'ctx-drawer aaben' : 'ctx-drawer'}>
      <button
        type="button"
        className="ctx-head"
        aria-expanded={åben}
        onClick={() => setÅben((v) => !v)}
        title="Hvad Jarvis brugte i sidste tur"
      >
        <Layers size={12} />
        <span>{data.filer.length} filer · {data.kilder.length} kilder · ~{kTokens}k tokens</span>
        {åben ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
      </button>

      {åben && (
        <div className="ctx-krop">
          <p className="ctx-note">Målt på sidste tur — ikke et estimat.</p>
          <Gruppe titel="Filer" ting={data.filer} />
          <Gruppe titel="Kilder" ting={data.kilder} maks={18} />
          {data.udeladt.length > 0 && (
            <Gruppe titel="Udeladt (plads)" ting={data.udeladt} maks={8} />
          )}
        </div>
      )}
    </div>
  )
}

function Gruppe({ titel, ting, maks = 12 }: { titel: string; ting: string[]; maks?: number }) {
  if (ting.length === 0) return null
  return (
    <div className="ctx-gruppe">
      <span className="ctx-gruppe-titel">{titel}</span>
      <div className="ctx-chips">
        {ting.slice(0, maks).map((t) => (
          <span key={t} className="ctx-chip" title={t}>{t}</span>
        ))}
        {ting.length > maks && <span className="ctx-mere">+{ting.length - maks}</span>}
      </div>
    </div>
  )
}
