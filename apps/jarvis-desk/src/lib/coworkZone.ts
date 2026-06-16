/** Lille pub/sub for Jarvis-styret cowork-zone-skift (§5).
 *
 *  Når Jarvis kalder open_ui_panel(panel="settings") poller UiPanelWatcher det,
 *  skifter surface til cowork og kalder emitZone("settings"). CoworkZones
 *  abonnerer og viser indstillingszonen. Modul-niveau fordi watcher (i App) og
 *  CoworkZones (i CoworkView) ikke deler en fælles provider-gren.
 */
export type Zone = 'mc' | 'marketplace' | 'settings'

/** Cowork-menupunkterne i rækkefølge — vist i Sidebar (cowork-surface) med ikoner.
 *  `icon` er navnet på et lucide-react-ikon. */
export const COWORK_ZONES: ReadonlyArray<{ id: Zone; label: string; icon: string }> = [
  { id: 'mc', label: 'Mission Control', icon: 'LayoutDashboard' },
  { id: 'marketplace', label: 'Marketplace', icon: 'Blocks' },
  { id: 'settings', label: 'Indstillinger', icon: 'Settings' },
]

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
