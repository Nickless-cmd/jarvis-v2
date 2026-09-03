import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { Appearance, StyleSheet } from 'react-native'
import * as SecureStore from 'expo-secure-store'
import {
  ACCENTS, accentByName, onAccent, paletteFor,
  type Accent, type AccentName, type Scheme, type ThemeMode, elevation } from './palettes'
import { tokens as baseTokens } from './tokens'

/**
 * Tema — mørk, lys eller automatisk, med valgbar accent.
 *
 * «Automatisk» følger systemets dag/nat via Appearance. Det er ikke en tredje
 * palet, men en REGEL for hvilken af de to der gælder lige nu — derfor tre
 * valgmuligheder i indstillingerne, men kun to paletter i koden.
 *
 * Valget gemmes lokalt og ikke på serveren: det handler om denne telefon i
 * dette lys, ikke om brugeren. Den samme konto kan sagtens ville have mørkt på
 * mobilen og lyst på skrivebordet.
 */

export interface Theme {
  mode: ThemeMode
  scheme: Scheme
  accent: Accent
  color: ReturnType<typeof paletteFor> & { onAccent: string }
  radius: typeof baseTokens.radius
  spacing: typeof baseTokens.spacing
  motion: typeof baseTokens.motion
  /** Stil der får en flade til at ligge OVENPÅ resten. Se elevation(). */
  elevation: ReturnType<typeof elevation>
}

const MODE_KEY = 'jarvis_theme_mode'
const ACCENT_KEY = 'jarvis_theme_accent'

export function buildTheme(mode: ThemeMode, accentName: AccentName, systemScheme: Scheme): Theme {
  const accent = accentByName(accentName)
  const scheme: Scheme = mode === 'auto' ? systemScheme : mode
  return {
    mode,
    scheme,
    accent,
    color: { ...paletteFor(scheme, accent), onAccent: onAccent(accent) },
    elevation: elevation(scheme),
    radius: baseTokens.radius,
    spacing: baseTokens.spacing,
    motion: baseTokens.motion
  }
}

interface Ctx {
  theme: Theme
  setMode: (m: ThemeMode) => void
  setAccent: (a: AccentName) => void
  accents: Accent[]
}

const ThemeCtx = createContext<Ctx | null>(null)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>('dark')
  const [accentName, setAccentState] = useState<AccentName>('gron')
  const [systemScheme, setSystemScheme] = useState<Scheme>(
    Appearance.getColorScheme() === 'light' ? 'light' : 'dark'
  )

  // Systemets dag/nat. Lytteren kører ALTID, også når mode ikke er 'auto' —
  // ellers ville et skift til 'auto' vise gårsdagens systemvalg indtil næste
  // gang systemet ændrede sig.
  useEffect(() => {
    const sub = Appearance.addChangeListener(({ colorScheme }) => {
      setSystemScheme(colorScheme === 'light' ? 'light' : 'dark')
    })
    return () => sub.remove()
  }, [])

  useEffect(() => {
    void (async () => {
      try {
        const [m, a] = await Promise.all([
          SecureStore.getItemAsync(MODE_KEY),
          SecureStore.getItemAsync(ACCENT_KEY)
        ])
        if (m === 'dark' || m === 'light' || m === 'auto') setModeState(m)
        if (a) setAccentState(a as AccentName)
      } catch {
        // Kan valget ikke læses, står vi på mørk — appens hidtidige udseende.
      }
    })()
  }, [])

  const setMode = useCallback((m: ThemeMode) => {
    setModeState(m)
    void SecureStore.setItemAsync(MODE_KEY, m).catch(() => undefined)
  }, [])

  const setAccent = useCallback((a: AccentName) => {
    setAccentState(a)
    void SecureStore.setItemAsync(ACCENT_KEY, a).catch(() => undefined)
  }, [])

  const theme = useMemo(
    () => buildTheme(mode, accentName, systemScheme),
    [mode, accentName, systemScheme]
  )

  const value = useMemo(
    () => ({ theme, setMode, setAccent, accents: ACCENTS }),
    [theme, setMode, setAccent]
  )
  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>
}

/**
 * Temaet. Uden for en provider falder vi tilbage på mørk frem for at kaste:
 * en manglende provider må ikke kunne sortne skærmen i en test eller i en
 * komponent der renderes uden for træet.
 */
export function useTheme(): Theme {
  return useContext(ThemeCtx)?.theme ?? buildTheme('dark', 'gron', 'dark')
}

export function useThemeControls(): Ctx {
  const ctx = useContext(ThemeCtx)
  return ctx ?? {
    theme: buildTheme('dark', 'gron', 'dark'),
    setMode: () => undefined,
    setAccent: () => undefined,
    accents: ACCENTS
  }
}

/**
 * Stilarter der følger temaet.
 *
 * StyleSheet.create fastfryser værdierne når den kaldes, så et modul-niveau
 * `const styles = StyleSheet.create({...})` kan ALDRIG skifte tema. Derfor
 * skrives stilarter nu som en funktion af temaet, og bygges her — memoiseret,
 * så vi ikke laver et nyt ark ved hver render.
 */
export function useStyles<T extends StyleSheet.NamedStyles<T>>(
  factory: (t: Theme) => T
): T {
  const theme = useTheme()
  return useMemo(() => factory(theme), [factory, theme])
}
