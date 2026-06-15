import { useState, type ReactNode } from 'react'

type Zone = 'mc' | 'settings'

/** To-zone-skal for cowork command center (spec §2). Venstre nav-rail vælger
 *  mellem Mission Control (fælles arbejdsrum) og Indstillinger (konfiguration). */
export function CoworkZones({
  missionControl, settings,
}: { missionControl: ReactNode; settings: ReactNode }) {
  const [zone, setZone] = useState<Zone>('mc')
  return (
    <div className="cowork-zones">
      <nav className="cowork-rail">
        <button
          type="button"
          className={zone === 'mc' ? 'rail-btn active' : 'rail-btn'}
          onClick={() => setZone('mc')}
        >Mission Control</button>
        <button
          type="button"
          className={zone === 'settings' ? 'rail-btn active' : 'rail-btn'}
          onClick={() => setZone('settings')}
        >Indstillinger</button>
      </nav>
      <div className="cowork-zone-body">
        {zone === 'mc' ? missionControl : settings}
      </div>
    </div>
  )
}
