export type Theme = 'dark' | 'light' | 'auto'
export type AccentName = 'gron' | 'teal' | 'lilla' | 'rav' | 'bla' | 'rose'

export interface Accent {
  name: AccentName
  label: string
  color: string
}

export const ACCENTS: Accent[] = [
  { name: 'gron', label: 'Grøn', color: '#6EE7A8' },
  { name: 'teal', label: 'Teal', color: '#3FC7B4' },
  { name: 'lilla', label: 'Lilla', color: '#A07FEB' },
  { name: 'rav', label: 'Rav', color: '#E8A33D' },
  { name: 'bla', label: 'Blå', color: '#5B8DEF' },
  { name: 'rose', label: 'Rosa', color: '#F4849B' },
]

const KEY = 'jarvisDeskTheme'
const ACCENT_KEY = 'jarvisDeskAccent'
const THEMES: Theme[] = ['dark', 'light', 'auto']
const ACCENT_NAMES = ACCENTS.map((accent) => accent.name)
let autoQuery: MediaQueryList | null = null
let autoListener: ((event: MediaQueryListEvent) => void) | null = null

export function loadTheme(): Theme {
  try {
    const v = localStorage.getItem(KEY)
    if (v && (THEMES as string[]).includes(v)) return v as Theme
    // Det gamle Desk-valg findes ikke i APK-paletten. Bevar en mørk, læsbar
    // flade i stedet for at lade et forældet navn blive hængende i DOM'en.
    if (v === 'contrast') return 'dark'
  } catch {
    /* localStorage utilgængelig — fald tilbage til default */
  }
  return 'dark'
}

export function loadAccent(): AccentName {
  try {
    const value = localStorage.getItem(ACCENT_KEY)
    if (value && (ACCENT_NAMES as string[]).includes(value)) return value as AccentName
  } catch {
    /* localStorage utilgængelig — fald tilbage til APK'ens standard */
  }
  return 'gron'
}

export function saveTheme(theme: Theme): void {
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    /* ignorér — tema persisteres ikke uden localStorage */
  }
}

export function saveAccent(accent: AccentName): void {
  try {
    localStorage.setItem(ACCENT_KEY, accent)
  } catch {
    /* ignorér — accent persisteres ikke uden localStorage */
  }
}

function stopAutoTheme(): void {
  if (autoQuery && autoListener) autoQuery.removeEventListener('change', autoListener)
  autoQuery = null
  autoListener = null
}

export function applyTheme(theme: Theme, accent: AccentName = loadAccent()): void {
  if (typeof document === 'undefined') return
  stopAutoTheme()
  const root = document.documentElement
  const setScheme = (dark: boolean) => { root.dataset.theme = dark ? 'dark' : 'light' }
  root.dataset.themeMode = theme
  root.dataset.accent = accent
  if (theme !== 'auto' || typeof window === 'undefined' || !window.matchMedia) {
    setScheme(theme !== 'light')
    return
  }
  autoQuery = window.matchMedia('(prefers-color-scheme: dark)')
  setScheme(autoQuery.matches)
  autoListener = (event) => setScheme(event.matches)
  autoQuery.addEventListener('change', autoListener)
}
