export type Locale = 'da' | 'en'
export type LocaleChoice = Locale | 'auto'

type Dict = Record<string, string>

const DA: Dict = {
  'settings.title': 'Indstillinger',
  'settings.close': 'Luk',
  'settings.account': 'Konto',
  'settings.language': 'Sprog',
  'settings.language.hint': 'Vælg hvilket sprog appen bruger.',
  'settings.language.auto': 'Automatisk',
  'settings.language.da': 'Dansk',
  'settings.language.en': 'English',
  'settings.saved': 'Gemt',
  'devices.section': 'Enheder',
  'devices.current': 'Denne enhed: {name}',
  'devices.none': 'Ikke hentet endnu',
  'appearance.title': 'Udseende',
  'appearance.light': 'Lys',
  'appearance.light.hint': 'Altid lys',
  'appearance.dark': 'Mørk',
  'appearance.dark.hint': 'Altid mørk',
  'appearance.auto': 'Automatisk',
  'appearance.auto.hint': 'Følger telefonen',
  'appearance.now': 'Lige nu: {scheme}.',
  'appearance.scheme.light': 'lyst',
  'appearance.scheme.dark': 'mørkt',
  'appearance.color': 'Farve',
}

const EN: Dict = {
  'settings.title': 'Settings',
  'settings.close': 'Close',
  'settings.account': 'Account',
  'settings.language': 'Language',
  'settings.language.hint': 'Choose which language the app uses.',
  'settings.language.auto': 'Automatic',
  'settings.language.da': 'Dansk',
  'settings.language.en': 'English',
  'settings.saved': 'Saved',
  'devices.section': 'Devices',
  'devices.current': 'This device: {name}',
  'devices.none': 'Not fetched yet',
  'appearance.title': 'Appearance',
  'appearance.light': 'Light',
  'appearance.light.hint': 'Always light',
  'appearance.dark': 'Dark',
  'appearance.dark.hint': 'Always dark',
  'appearance.auto': 'Automatic',
  'appearance.auto.hint': 'Follows phone',
  'appearance.now': 'Right now: {scheme}.',
  'appearance.scheme.light': 'light',
  'appearance.scheme.dark': 'dark',
  'appearance.color': 'Color',
}

const LOCALES: Record<Locale, Dict> = { da: DA, en: EN }
const DEFAULT: Locale = 'da'

export function availableLocales(): Locale[] {
  return Object.keys(LOCALES) as Locale[]
}

export function normalizeLocale(locale: string | null | undefined): LocaleChoice {
  if (locale === 'auto') return 'auto'
  const base = (locale || '').slice(0, 2).toLowerCase()
  return base === 'en' || base === 'da' ? base : DEFAULT
}

export function resolveLocale(choice: string | null | undefined, systemLocale = DEFAULT): Locale {
  const normalized = normalizeLocale(choice)
  if (normalized !== 'auto') return normalized
  const system = normalizeLocale(systemLocale)
  return system === 'auto' ? DEFAULT : system
}

export function translate(
  locale: string | null | undefined,
  key: string,
  vars?: Record<string, string | number>
): string {
  const resolved = resolveLocale(locale)
  let s = LOCALES[resolved]?.[key] ?? LOCALES[DEFAULT]?.[key] ?? key
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      s = s.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
    }
  }
  return s
}
