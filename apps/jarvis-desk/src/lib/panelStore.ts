const KEY = 'jarvis-desk:panelWidth'

export function loadPanelWidth(fallback: number): number {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw === null) return fallback
    const n = Number(raw)
    return Number.isFinite(n) && n > 0 ? n : fallback
  } catch {
    return fallback
  }
}

export function savePanelWidth(width: number): void {
  try {
    localStorage.setItem(KEY, String(Math.round(width)))
  } catch {
    /* ignoreres — UI-præference, ikke kritisk */
  }
}
