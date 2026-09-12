import * as SecureStore from 'expo-secure-store'
import type { AccentName, ThemeMode } from '../theme/palettes'

const MODE_KEY = 'jarvis_theme_mode'
const ACCENT_KEY = 'jarvis_theme_accent'
const MODES: ThemeMode[] = ['dark', 'light', 'auto']
const ACCENTS: AccentName[] = ['gron', 'teal', 'lilla', 'rav', 'bla', 'rose']

export interface StoredThemePrefs {
  mode: ThemeMode
  accent: AccentName
}

export async function loadThemePrefs(): Promise<StoredThemePrefs> {
  try {
    const [rawMode, rawAccent] = await Promise.all([
      SecureStore.getItemAsync(MODE_KEY),
      SecureStore.getItemAsync(ACCENT_KEY),
    ])
    return {
      mode: MODES.includes(rawMode as ThemeMode) ? rawMode as ThemeMode : 'dark',
      accent: ACCENTS.includes(rawAccent as AccentName) ? rawAccent as AccentName : 'gron',
    }
  } catch {
    return { mode: 'dark', accent: 'gron' }
  }
}

export async function saveThemeMode(mode: ThemeMode): Promise<void> {
  await SecureStore.setItemAsync(MODE_KEY, mode)
}

export async function saveThemeAccent(accent: AccentName): Promise<void> {
  await SecureStore.setItemAsync(ACCENT_KEY, accent)
}
