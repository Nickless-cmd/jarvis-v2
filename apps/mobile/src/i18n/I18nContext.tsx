import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { resolveLocale, translate, type LocaleChoice } from './i18n'

interface I18nContextValue {
  locale: LocaleChoice
  resolvedLocale: 'da' | 'en'
  setLocale: (locale: LocaleChoice) => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

export function I18nProvider({
  children,
  initialLocale = 'da',
}: {
  children: ReactNode
  initialLocale?: LocaleChoice
}) {
  const [locale, setLocale] = useState<LocaleChoice>(initialLocale)
  const resolvedLocale = resolveLocale(locale)
  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => translate(resolvedLocale, key, vars),
    [resolvedLocale],
  )
  const value = useMemo(
    () => ({ locale, resolvedLocale, setLocale, t }),
    [locale, resolvedLocale, t],
  )
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (ctx) return ctx
  return {
    locale: 'da',
    resolvedLocale: 'da',
    setLocale: () => undefined,
    t: (key, vars) => translate('da', key, vars),
  }
}
