import { useEffect, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { getCheckpoints, rollbackCheckpoint } from '../lib/coworkApi'
import { usePermission } from './usePermission'
import type { Redning } from '../components/feedback/ErrorCard'

/** Redningshandlinger når et run er gået galt.
 *
 *  Hver handling tilbydes KUN når den kan udrette noget: «prøv med Pro» kun
 *  hvor der findes en stærkere tier, «fortryd» kun når sessionen faktisk har
 *  checkpoints, «spørg først» kun når man står i trust. En knap der ikke kan
 *  gøre noget koster et klik og et håb.
 */
export function useRedning({
  config, sessionId, isOwner, aktiv, model, prøvIgenMed,
}: {
  config?: ApiConfig
  sessionId?: string | null
  isOwner: boolean
  /** Kun slå op når der ER en fejl — ellers er det en poll uden formål. */
  aktiv: boolean
  model: string
  prøvIgenMed: (model: string) => void
}): Redning {
  const { permission, setPermission } = usePermission()
  const [harCheckpoints, setHarCheckpoints] = useState(false)

  useEffect(() => {
    if (!aktiv || !config) { setHarCheckpoints(false); return }
    let levende = true
    getCheckpoints(config, sessionId ?? undefined)
      .then((d) => { if (levende) setHarCheckpoints((d.antal ?? 0) > 0) })
      .catch(() => { if (levende) setHarCheckpoints(false) })
    return () => { levende = false }
  }, [aktiv, config?.apiBaseUrl, config?.authToken, sessionId])

  const r: Redning = {}

  // Owner sender et konkret model-id bundet til provider; der findes ingen
  // veldefineret «stærkere», og et gæt kunne lige så godt ramme dårligere.
  if (!isOwner && model !== 'pro') {
    r.onStaerkere = () => prøvIgenMed('pro')
  }

  if (harCheckpoints && config) {
    r.onFortryd = async () => {
      const svar = await rollbackCheckpoint(config, sessionId ?? undefined)
      return svar.status === 'ok'
        ? `Rullet tilbage til ${svar.gendannet ?? 'sidste checkpoint'}`
        : (svar.error ?? 'Kunne ikke fortryde')
    }
  }

  if (permission === 'trust') {
    r.onSpoergFoerst = () => setPermission('ask')
  }

  return r
}
