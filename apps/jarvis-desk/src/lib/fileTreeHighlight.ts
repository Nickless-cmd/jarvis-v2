/** Lille pub/sub for Jarvis-styret fil-træ-highlight.
 *
 *  Når Jarvis kalder open_ui_panel(panel="file_tree", detail="<sti>", scope="...") poller
 *  UiPanelWatcher det og kalder emitHighlight(sti, scope). CodeView abonnerer og
 *  scroller-til + markerer filen. Modul-niveau (ingen context-plumbing) fordi
 *  watcher (i App) og CodeView (i Shell) ikke deler en fælles provider-gren.
 */
export type HighlightScope = 'repo' | 'workstation'

export type Listener = (path: string, scope: HighlightScope) => void

let listeners: Listener[] = []

export function emitHighlight(path: string, scope: HighlightScope = 'repo'): void {
  for (const l of listeners) {
    try { l(path, scope) } catch { /* en lytter må ikke vælte de andre */ }
  }
}

export function onHighlight(listener: Listener): () => void {
  listeners.push(listener)
  return () => { listeners = listeners.filter((l) => l !== listener) }
}
