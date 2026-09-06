import { useEffect, useState } from 'react'
import { Activity, Cpu, HardDrive, Zap } from 'lucide-react'
import { getKrop, type Krop } from '../../lib/coworkApi'
import type { ApiConfig } from '../../lib/api'

/** Maskinstatus i miljø-feltet — læsbar uden at åbne en log.
 *
 *  Bevidst udeladt: cache hit/miss. Tallet er målt forkert (input-tokens
 *  tælles dobbelt på store kald), og et forkert tal man træffer beslutninger
 *  på er værre end intet tal.
 */
const TRYK_DA: Record<string, string> = { low: 'lavt', medium: 'middel', high: 'højt' }

export function RunHealth({
  config, tokens = 0, komprimerVed = 0,
}: {
  config?: ApiConfig
  tokens?: number
  komprimerVed?: number
}) {
  const [krop, setKrop] = useState<Krop | null>(null)

  useEffect(() => {
    if (!config) return
    let levende = true
    const hent = () => {
      // Ikke mens fanen er skjult: en usynlig poll er ren omkostning.
      if (document.hidden) return
      getKrop(config).then((d) => { if (levende) setKrop(d.krop) }).catch(() => { /* stille */ })
    }
    hent()
    const id = setInterval(hent, 15_000)
    return () => { levende = false; clearInterval(id) }
  }, [config?.apiBaseUrl, config?.authToken])

  if (!krop) return null

  const gpu = krop.gpus?.[0]
  const tokenPct = komprimerVed > 0 ? Math.round((tokens / komprimerVed) * 100) : 0

  return (
    <ul className="env-rows rh-rows">
      <li className="env-row">
        <span className="env-label"><Cpu size={13} /> Maskine</span>
        <span className="env-val">
          {Math.round(krop.cpu_pct)}% cpu · {Math.round(krop.ram_pct)}% ram
          {krop.cpu_temp_c ? ` · ${Math.round(krop.cpu_temp_c)}°` : ''}
        </span>
      </li>
      {gpu && (
        <li className="env-row">
          <span className="env-label"><Zap size={13} /> GPU</span>
          <span className="env-val">
            {gpu.util_pct}% · {Math.round(gpu.vram_pct)}% vram
            {gpu.temp_c ? ` · ${gpu.temp_c}°` : ''}
          </span>
        </li>
      )}
      <li className="env-row">
        <span className="env-label"><HardDrive size={13} /> Disk</span>
        <span className="env-val">
          {Math.round(krop.disk_free_gb)} GB fri
          <span className={`rh-tryk rh-${krop.pressure}`}> · tryk {TRYK_DA[krop.pressure] ?? krop.pressure}</span>
        </span>
      </li>
      {komprimerVed > 0 && (
        <li className="env-row">
          <span className="env-label"><Activity size={13} /> Kontekst</span>
          <span className={`env-val${tokenPct >= 85 ? ' rh-hoej' : ''}`}>
            {tokenPct}% af {Math.round(komprimerVed / 1000)}k
          </span>
        </li>
      )}
    </ul>
  )
}
