import { useEffect, useRef, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import {
  SVARSTILE, hentSvarPreferences, saetChatStyle, saetSvarstil,
  type ChatStyle, type SvarPreferences, type Svarstil,
} from '../lib/svarstil'
import type { ApiConfig } from '../lib/types'
import { useStyles, type Theme } from '../theme/ThemeContext'

/**
 * Svarstil — Claude Codes «output styles». Samme valg som i desk: det gælder
 * brugeren på alle enheder, og Jarvis mindes om det hver tur.
 */
export function SvarstilSection({ config }: { config: ApiConfig | null }) {
  const styles = useStyles(makeStyles)
  const [prefs, setPrefs] = useState<SvarPreferences | null>(null)
  const [gemt, setGemt] = useState(false)
  const [fejl, setFejl] = useState('')
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  useEffect(() => {
    if (!config) return
    let alive = true
    hentSvarPreferences(config)
      .then((s) => { if (alive) setPrefs(s) })
      .catch(() => { if (alive) setPrefs({
        outputStyle: 'balanced', chatStyle: {
          tone: 'adaptive', emoji: 'adaptive', profanity: 'adaptive',
          visuals: 'adaptive', questions: 'adaptive',
        },
      }) })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  const vaelg = async (v: Svarstil) => {
    if (!config || !prefs || v === prefs.outputStyle) return
    const foer = prefs
    setPrefs({ ...prefs, outputStyle: v }); setFejl('')
    try {
      await saetSvarstil(config, v)
      setGemt(true)
      if (timer.current) clearTimeout(timer.current)
      timer.current = setTimeout(() => setGemt(false), 1600)
    } catch (e) {
      setPrefs(foer)
      setFejl(e instanceof Error ? e.message : 'Kunne ikke gemme svarstilen')
    }
  }

  const vaelgChat = async <K extends keyof ChatStyle>(key: K, value: ChatStyle[K]) => {
    if (!config || !prefs || value === prefs.chatStyle[key]) return
    const foer = prefs
    setPrefs({ ...prefs, chatStyle: { ...prefs.chatStyle, [key]: value } }); setFejl('')
    try {
      await saetChatStyle(config, { [key]: value })
      setGemt(true)
      if (timer.current) clearTimeout(timer.current)
      timer.current = setTimeout(() => setGemt(false), 1600)
    } catch (e) {
      setPrefs(foer)
      setFejl(e instanceof Error ? e.message : 'Kunne ikke gemme samtalestilen')
    }
  }

  const valgt = SVARSTILE.find((s) => s.value === prefs?.outputStyle)
  const grupper: Array<{ key: keyof ChatStyle; label: string; values: Array<[string, string]> }> = [
    { key: 'tone', label: 'Tone', values: [['adaptive', 'Adaptiv'], ['warm', 'Varm'], ['direct', 'Direkte'], ['playful', 'Legende']] },
    { key: 'emoji', label: 'Emoji', values: [['adaptive', 'Adaptiv'], ['rare', 'Sjældent'], ['expressive', 'Udtryksfuldt']] },
    { key: 'profanity', label: 'Kraftsprog', values: [['adaptive', 'Spejl'], ['avoid', 'Undgå'], ['comfortable', 'Tilladt']] },
    { key: 'visuals', label: 'Visuelle svar', values: [['adaptive', 'Når det hjælper'], ['plain', 'Mest tekst'], ['rich', 'Gerne visuelt']] },
    { key: 'questions', label: 'Spørgsmål', values: [['adaptive', 'Når det hjælper'], ['rare', 'Sjældent'], ['curious', 'Nysgerrigt']] },
  ]
  return (
    <>
      <Text style={styles.sectionTitle}>Svarstil</Text>
      <View style={styles.card}>
        <Text style={styles.muted}>Hvordan Jarvis svarer — gælder alle dine samtaler og enheder.</Text>
        <View style={styles.row}>
          {SVARSTILE.map((s) => {
            const on = prefs?.outputStyle === s.value
            return (
              <Pressable
                key={s.value}
                accessibilityRole="button"
                accessibilityLabel={`Svarstil ${s.navn}`}
                accessibilityState={{ selected: on, disabled: prefs === null }}
                disabled={prefs === null}
                onPress={() => void vaelg(s.value)}
                style={({ pressed }) => [styles.chip, on && styles.chipOn, pressed && styles.pressed]}
              >
                <Text style={[styles.chipText, on && styles.chipTextOn]}>{s.navn}</Text>
              </Pressable>
            )
          })}
        </View>
        {valgt ? <Text style={styles.muted}>{valgt.forklaring}.</Text> : null}
        <Text style={styles.subhead}>Samtalestil</Text>
        <Text style={styles.muted}>Valgene sætter rammerne; Jarvis tilpasser sig stadig den aktuelle samtale.</Text>
        {grupper.map((gruppe) => (
          <View key={gruppe.key} style={styles.group}>
            <Text style={styles.groupLabel}>{gruppe.label}</Text>
            <View style={styles.row}>
              {gruppe.values.map(([value, label]) => {
                const on = prefs?.chatStyle[gruppe.key] === value
                return (
                  <Pressable
                    key={value}
                    accessibilityRole="button"
                    accessibilityLabel={`${gruppe.label} ${label}`}
                    accessibilityState={{ selected: on, disabled: prefs === null }}
                    disabled={prefs === null}
                    onPress={() => void vaelgChat(gruppe.key, value as never)}
                    style={({ pressed }) => [styles.chip, on && styles.chipOn, pressed && styles.pressed]}
                  >
                    <Text style={[styles.chipText, on && styles.chipTextOn]}>{label}</Text>
                  </Pressable>
                )
              })}
            </View>
          </View>
        ))}
        {gemt ? <Text style={styles.saved}>Gemt</Text> : null}
        {fejl ? <Text style={styles.fejl} accessibilityRole="alert">{fejl}</Text> : null}
      </View>
    </>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  sectionTitle: {
    color: tokens.color.fg3,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginTop: tokens.spacing.md,
    marginBottom: tokens.spacing.xs,
  },
  card: {
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    borderWidth: 1,
    borderColor: tokens.color.line,
    gap: tokens.spacing.sm,
  },
  muted: { color: tokens.color.fg3 },
  subhead: { color: tokens.color.fg1, fontSize: 15, fontWeight: '800', marginTop: tokens.spacing.sm },
  group: { gap: tokens.spacing.xs },
  groupLabel: { color: tokens.color.fg2, fontSize: 13, fontWeight: '700' },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: tokens.spacing.sm },
  chip: {
    borderWidth: 1,
    borderColor: tokens.color.line,
    borderRadius: 999,
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  chipOn: { backgroundColor: tokens.color.accent, borderColor: tokens.color.accent },
  chipText: { color: tokens.color.fg2, fontWeight: '600' },
  chipTextOn: { color: tokens.color.bg0, fontWeight: '800' },
  saved: { color: tokens.color.accentText, fontWeight: '700' },
  fejl: { color: tokens.color.error },
  pressed: { opacity: 0.7 },
})
