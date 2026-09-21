import { OpmaerksomhedsLinje } from './OpmaerksomhedsLinje'
import { useSessions } from '../../hooks/useSessions'
import { useSettings } from '../../hooks/useSettings'
import type { Surface } from './Sidebar'

/**
 * Hvor opmærksomhedslinjen bor.
 *
 * Den lå nederst i venstre panel og skubbede til samtalelisten hver gang den
 * kom og gik. Bjørn 21/9-2026: «det vil jeg gerne have flyttet til højre side
 * og nede i bunden af siden.»
 *
 * Den ligger derfor som et FAST lag i vinduet, side om side med de andre
 * værter i App — ikke som et element inde i sidepanelets flow. Det er ikke
 * kosmetik: sidepanelet har `overflow: hidden`, og en linje der kommer og går
 * inde i en scrollende liste flytter alt under sig.
 */
export function OpmaerksomhedsVaert({ setSurface }: { setSurface: (s: Surface) => void }) {
  const { settings } = useSettings()
  const { activeId, select } = useSessions()
  return (
    <div className="opm-vaert">
      <OpmaerksomhedsLinje
        config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : null}
        aktivId={activeId}
        onAabn={(id) => { select(id); setSurface('chat') }}
      />
    </div>
  )
}
