import { useEffect, useState } from 'react'
import { Activity, Cpu, HardDrive, Zap } from 'lucide-react'
import { getKrop, type Krop } from '../../lib/coworkApi'
import type { ApiConfig } from '../../lib/api'
import { DESK_CHROME } from '../../lib/deskChrome'

/** Maskinstatus i miljø-feltet — læsbar uden at åbne en log.
 *
 *  Bevidst udeladt: cache hit/miss. Tallet er målt forkert (input-tokens
 *  tælles dobbelt på store kald), og et forkert tal man træffer beslutninger
 *  på er værre end intet tal.
 */
const TRYK_DA: Record<string, string> = { low: 'lavt', medium: 'middel', high: 'højt' }

/** 1.000.000 skal staa som «1M», ikke «1000k». Hans vindue ER 1M. */
function vindue(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000
    return `${m % 1 === 0 ? m : m.toFixed(1)}M`
  }
  return `${Math.round(n / 1000)}k`
}

export function RunHealth({
  config, tokens = 0, komprimerVed = 0,
}: {
  config?: ApiConfig
  tokens?: number
  komprimerVed?: number
}) {
  const [krop, setKrop] = useState<Krop | null>(null)

  useEffect(() => {
    // Poll'en henter KUN maskin-tallene. Er de slået fra, er der intet at
    // hente — og en usynlig poll hvert 15. sekund er ren omkostning.
    if (!config || !DESK_CHROME.envMachineRows) return
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

  const gpu = krop?.gpus?.[0]
  const tokenPct = komprimerVed > 0 ? Math.round((tokens / komprimerVed) * 100) : 0
  const visMaskine = DESK_CHROME.envMachineRows && !!krop
  // Kontekst hænger ikke på maskin-kaldet: den kommer fra tokens/komprimerVed.
  // Før returnerede vi null når `krop` manglede — og så forsvandt kontekst-
  // tallet med maskin-tallene, selv om det ikke havde noget med dem at gøre.
  if (!visMaskine && !(komprimerVed > 0)) return null

  return (
    <ul className="env-rows rh-rows">
      {visMaskine && krop && (
      <li className="env-row">
        <span className="env-label"><Cpu size={13} /> Maskine</span>
        <span className="env-val">
          {Math.round(krop.cpu_pct)}% cpu · {Math.round(krop.ram_pct)}% ram
          {krop.cpu_temp_c ? ` · ${Math.round(krop.cpu_temp_c)}°` : ''}
        </span>
      </li>
      )}
      {visMaskine && gpu && (
        <li className="env-row">
          <span className="env-label"><Zap size={13} /> GPU</span>
          <span className="env-val">
            {gpu.util_pct}% · {Math.round(gpu.vram_pct)}% vram
            {gpu.temp_c ? ` · ${gpu.temp_c}°` : ''}
          </span>
        </li>
      )}
      {visMaskine && krop && (
      <li className="env-row">
        <span className="env-label"><HardDrive size={13} /> Disk</span>
        <span className="env-val">
          {Math.round(krop.disk_free_gb)} GB fri
          <span className={`rh-tryk rh-${krop.pressure}`}> · tryk {TRYK_DA[krop.pressure] ?? krop.pressure}</span>
        </span>
      </li>
      )}
      {komprimerVed > 0 && (
        <li className="env-row">
          <span className="env-label"><Activity size={13} /> Kontekst</span>
          <span className="env-val">
            {/* Samme zoner som ringen i skrivefeltet: <60 blaa, <85 gul, ellers
                roed. Tallet og ringen maaler nu ogsaa det samme — foer havde de
                hver sin taeller OG naevner under samme overskrift. */}
            <span className={`rh-pct zone-${tokenPct >= 85 ? 'roed' : tokenPct >= 60 ? 'gul' : 'blaa'}`}>
              {tokenPct}%
            </span>
            {' af '}{vindue(komprimerVed)}
          </span>
        </li>
      )}
    </ul>
  )
}
