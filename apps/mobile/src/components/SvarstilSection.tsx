import { useEffect, useRef, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { SVARSTILE, hentSvarstil, saetSvarstil, type Svarstil } from '../lib/svarstil'
import type { ApiConfig } from '../lib/types'
import { useStyles, type Theme } from '../theme/ThemeContext'

/**
 * Svarstil — Claude Codes «output styles». Samme valg som i desk: det gælder
 * brugeren på alle enheder, og Jarvis mindes om det hver tur.
 */
export function SvarstilSection({ config }: { config: ApiConfig | null }) {
  const styles = useStyles(makeStyles)
  const [stil, setStil] = useState<Svarstil | null>(null)
  const [gemt, setGemt] = useState(false)
  const [fejl, setFejl] = useState('')
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  useEffect(() => {
    if (!config) return
    let alive = true
    hentSvarstil(config)
      .then((s) => { if (alive) setStil(s) })
      .catch(() => { if (alive) setStil('balanced') })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  const vaelg = async (v: Svarstil) => {
    if (!config || v === stil) return
    const foer = stil
    setStil(v); setFejl('')
    try {
      await saetSvarstil(config, v)
      setGemt(true)
      if (timer.current) clearTimeout(timer.current)
      timer.current = setTimeout(() => setGemt(false), 1600)
    } catch (e) {
      setStil(foer)
      setFejl(e instanceof Error ? e.message : 'Kunne ikke gemme svarstilen')
    }
  }

  const valgt = SVARSTILE.find((s) => s.value === stil)
  return (
    <>
      <Text style={styles.sectionTitle}>Svarstil</Text>
      <View style={styles.card}>
        <Text style={styles.muted}>Hvordan Jarvis svarer — gælder alle dine samtaler og enheder.</Text>
        <View style={styles.row}>
          {SVARSTILE.map((s) => {
            const on = stil === s.value
            return (
              <Pressable
                key={s.value}
                accessibilityRole="button"
                accessibilityLabel={`Svarstil ${s.navn}`}
                accessibilityState={{ selected: on, disabled: stil === null }}
                disabled={stil === null}
                onPress={() => void vaelg(s.value)}
                style={({ pressed }) => [styles.chip, on && styles.chipOn, pressed && styles.pressed]}
              >
                <Text style={[styles.chipText, on && styles.chipTextOn]}>{s.navn}</Text>
              </Pressable>
            )
          })}
        </View>
        {valgt ? <Text style={styles.muted}>{valgt.forklaring}.</Text> : null}
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
