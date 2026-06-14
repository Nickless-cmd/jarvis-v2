// §22.3 i18n-fundament: locale-filer (da default, en) + t()-helper.
// Sprogvalg: setLocale() fra brugerens indstilling ELLER OS-locale (fallback da).
// da-DK ordblinde-tilpasning (større font, simplere formuleringer) er en fremtidig locale.
import da from '../locales/da.json'
import en from '../locales/en.json'

type Dict = Record<string, string>
const LOCALES: Record<string, Dict> = { da, en }
const DEFAULT = 'da'
let _current = DEFAULT

export function availableLocales(): string[] {
  return Object.keys(LOCALES)
}

export function setLocale(loc: string): void {
  const base = (loc || '').slice(0, 2).toLowerCase()
  if (LOCALES[base]) _current = base
}

export function getLocale(): string {
  return _current
}

/** Vælg sprog ud fra OS-locale hvis understøttet, ellers da. */
export function initLocaleFromOS(osLocale?: string): void {
  setLocale(osLocale || (typeof navigator !== 'undefined' ? navigator.language : DEFAULT))
}

/** Oversæt en nøgle. Falder tilbage: current → da → selve nøglen. {var}-interpolation. */
export function t(key: string, vars?: Record<string, string | number>): string {
  let s = LOCALES[_current]?.[key] ?? LOCALES[DEFAULT]?.[key] ?? key
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      s = s.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
    }
  }
  return s
}
