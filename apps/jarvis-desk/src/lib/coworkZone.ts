/** Lille pub/sub for Jarvis-styret cowork-zone-skift (§5).
 *
 *  Når Jarvis kalder open_ui_panel(panel="settings") poller UiPanelWatcher det,
 *  skifter surface til cowork og kalder emitZone("settings"). CoworkZones
 *  abonnerer og viser indstillingszonen. Modul-niveau fordi watcher (i App) og
 *  CoworkZones (i CoworkView) ikke deler en fælles provider-gren.
 */
export type Zone =
  | 'mc' | 'marketplace'
  | 'konto' | 'privacy' | 'notifications'
  | 'appearance' | 'sprog' | 'location'
  | 'memory' | 'workspace' | 'connections'
  | 'central' | 'jarvisMind' | 'jarvis'
  | 'about'
  | 'settings' // legacy-alias (open_ui_panel(panel="settings")) → 'konto'

/** Cowork-menupunkterne i rækkefølge — vist i Sidebar (cowork-surface) med ikoner.
 *  Bjørn 2026-07-01: SIMPELHED SLÅR KOMPAKTHED. Hver indstillings-sektion er sit EGET
 *  klare punkt (ingen nesting/undermenuer) — grupperet med scanbare overskrifter, så en
 *  almindelig bruger (Mikkel) bæres igennem i stedet for at lede. `icon` = lucide-react-navn.
 *  `group` = ikke-klikbar sidebar-overskrift. `ownerOnly` skjuler punktet for ikke-ejere. */
export const COWORK_ZONES: ReadonlyArray<{
  id: Zone; label: string; icon: string; group: string; ownerOnly?: boolean
}> = [
  { id: 'mc', label: 'Mission Control', icon: 'LayoutDashboard', group: 'Arbejde' },
  { id: 'marketplace', label: 'Marketplace', icon: 'Blocks', group: 'Arbejde' },

  { id: 'konto', label: 'Konto', icon: 'User', group: 'Konto' },
  { id: 'privacy', label: 'Privatliv & Data', icon: 'ShieldCheck', group: 'Konto' },
  { id: 'notifications', label: 'Notifikationer', icon: 'Bell', group: 'Konto' },

  { id: 'appearance', label: 'Udseende', icon: 'Palette', group: 'Tilpasning' },
  { id: 'sprog', label: 'Sprog', icon: 'Languages', group: 'Tilpasning' },
  { id: 'location', label: 'Placering', icon: 'MapPin', group: 'Tilpasning' },

  { id: 'memory', label: 'Hukommelse', icon: 'Database', group: 'Data & værktøjer' },
  { id: 'workspace', label: 'Workspace', icon: 'Folder', group: 'Data & værktøjer' },
  { id: 'connections', label: 'Forbindelser', icon: 'Plug', group: 'Data & værktøjer' },

  { id: 'central', label: 'Central', icon: 'Cpu', group: 'System', ownerOnly: true },
  { id: 'jarvisMind', label: 'Jarvis Mind', icon: 'Brain', group: 'System', ownerOnly: true },
  { id: 'jarvis', label: 'Jarvis', icon: 'Bot', group: 'System', ownerOnly: true },

  { id: 'about', label: 'Om & hjælp', icon: 'Info', group: 'Om' },
]

/** Legacy-alias → kanonisk zone. 'settings' (Jarvis' open_ui_panel + tandhjul) lander på Konto. */
export function normalizeZone(zone: Zone): Zone {
  return zone === 'settings' ? 'konto' : zone
}

type Listener = (zone: Zone) => void

let listeners: Listener[] = []

export function emitZone(zone: Zone): void {
  for (const l of listeners) {
    try { l(zone) } catch { /* en lytter må ikke vælte de andre */ }
  }
}

export function onZone(listener: Listener): () => void {
  listeners.push(listener)
  return () => { listeners = listeners.filter((l) => l !== listener) }
}
