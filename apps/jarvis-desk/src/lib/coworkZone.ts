/** Navigation for Arbejde. Old zone names remain accepted because Jarvis,
 * command search and older clients can still open a specific panel. */
export type Zone =
  | 'mc' | 'agentPool' | 'capacity' | 'integrations'
  | 'general' | 'account' | 'workspace' | 'jarvis' | 'system' | 'about'
  | 'marketplace' | 'cheapLane' | 'providers'
  | 'konto' | 'privacy' | 'notifications' | 'appearance' | 'sprog'
  | 'location' | 'presence' | 'memory' | 'connections'
  | 'central' | 'jarvisMind' | 'settings'

export const COWORK_ZONES: ReadonlyArray<{
  id: Zone; label: string; icon: string; group: string; ownerOnly?: boolean
}> = [
  { id: 'mc', label: 'Mission Control', icon: 'LayoutDashboard', group: 'Arbejde' },
  { id: 'agentPool', label: 'Agent pool', icon: 'Users', group: 'Arbejde', ownerOnly: true },
  { id: 'capacity', label: 'Modeller og kapacitet', icon: 'Gauge', group: 'Arbejde', ownerOnly: true },
  { id: 'integrations', label: 'Værktøjer og forbindelser', icon: 'Blocks', group: 'Arbejde' },
  { id: 'general', label: 'Generelt', icon: 'Settings', group: 'Indstillinger' },
  { id: 'account', label: 'Konto og sikkerhed', icon: 'ShieldCheck', group: 'Indstillinger' },
  { id: 'workspace', label: 'Arbejdsområde', icon: 'Folder', group: 'Indstillinger' },
  { id: 'jarvis', label: 'Jarvis og hukommelse', icon: 'Brain', group: 'Indstillinger' },
  { id: 'system', label: 'Systemstatus', icon: 'Cpu', group: 'System', ownerOnly: true },
  { id: 'about', label: 'Om og hjælp', icon: 'Info', group: 'Om' },
]

const ALIAS: Partial<Record<Zone, Zone>> = {
  marketplace: 'integrations', connections: 'integrations',
  cheapLane: 'capacity', providers: 'capacity',
  konto: 'account', privacy: 'account', settings: 'account',
  notifications: 'general', appearance: 'general', sprog: 'general', location: 'general',
  memory: 'jarvis', presence: 'jarvis',
  central: 'system', jarvisMind: 'system',
}

export function normalizeZone(zone: Zone): Zone {
  return ALIAS[zone] ?? zone
}

type Listener = (zone: Zone) => void
let listeners: Listener[] = []
let currentZone: Zone = 'mc'

export function getCurrentZone(): Zone { return currentZone }

export function emitZone(zone: Zone): void {
  currentZone = zone
  for (const l of listeners) {
    try { l(zone) } catch { /* en lytter må ikke vælte de andre */ }
  }
}

export function onZone(listener: Listener): () => void {
  listeners.push(listener)
  return () => { listeners = listeners.filter((l) => l !== listener) }
}
