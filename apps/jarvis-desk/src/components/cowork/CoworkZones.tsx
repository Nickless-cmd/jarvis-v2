import { useState, useEffect, type ReactNode } from 'react'
import { onZone, type Zone } from '../../lib/coworkZone'

/** Cowork command center — ÉT panel. Zone-valget bor i Sidebar (cowork-menu);
 *  her abonnerer vi blot på den aktive zone via emitZone/onZone og giver den til
 *  render-prop'en. Intet internt rail længere (undgår dobbelt-panel, spec §3.2). */
export function CoworkZones({
  children,
}: {
  children: (zone: Zone) => ReactNode
}) {
  const [zone, setZone] = useState<Zone>('mc')
  useEffect(() => onZone(setZone), [])
  return (
    <div className="cowork-zones">
      <div className="cowork-zone-body">{children(zone)}</div>
    </div>
  )
}
