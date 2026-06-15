export type Theme = 'dark' | 'light' | 'contrast'

const KEY = 'jarvisDeskTheme'
const THEMES: Theme[] = ['dark', 'light', 'contrast']

export function loadTheme(): Theme {
  try {
    const v = localStorage.getItem(KEY)
    if (v && (THEMES as string[]).includes(v)) return v as Theme
  } catch {
    /* localStorage utilgængelig — fald tilbage til default */
  }
  return 'dark'
}

export function saveTheme(theme: Theme): void {
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    /* ignorér — tema persisteres ikke uden localStorage */
  }
}

export function applyTheme(theme: Theme): void {
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = theme
  }
}
