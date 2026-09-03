import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Check } from 'lucide-react-native'
import { useStyles, useTheme, useThemeControls, type Theme } from '../theme/ThemeContext'
import type { ThemeMode } from '../theme/palettes'

/**
 * Udseende — lys/mørk/automatisk og accentfarve.
 *
 * To valg, ikke ét, fordi de svarer på hver sit spørgsmål: «lys eller mørk?»
 * handler om omgivelserne, «hvilken farve?» handler om hvem han er. Man skal
 * kunne skifte det ene uden det andet.
 *
 * «Automatisk» er ikke et tredje udseende, men en regel: følg telefonens dag og
 * nat. Derfor står den som et ligeværdigt valg og ikke som en kontakt ved siden
 * af de to andre.
 */

const MODES: { value: ThemeMode; label: string; hint: string }[] = [
  { value: 'light', label: 'Lys', hint: 'Altid lys' },
  { value: 'dark', label: 'Mørk', hint: 'Altid mørk' },
  { value: 'auto', label: 'Automatisk', hint: 'Følger telefonen' }
]

export function AppearanceSection() {
  const t = useTheme()
  const styles = useStyles(makeStyles)
  const { setMode, setAccent, accents } = useThemeControls()

  return (
    <>
      <Text style={styles.sectionTitle}>Udseende</Text>

      <View style={styles.card}>
        <View style={styles.modeRow}>
          {MODES.map((m) => {
            const on = t.mode === m.value
            return (
              <Pressable
                key={m.value}
                testID={`mode-${m.value}`}
                accessibilityRole="button"
                accessibilityState={{ selected: on }}
                onPress={() => setMode(m.value)}
                style={({ pressed }) => [
                  styles.mode, on && styles.modeOn, pressed && styles.pressed
                ]}
              >
                <Text style={[styles.modeLabel, on && styles.modeLabelOn]}>{m.label}</Text>
                <Text style={[styles.modeHint, on && styles.modeHintOn]}>{m.hint}</Text>
              </Pressable>
            )
          })}
        </View>
        {t.mode === 'auto' ? (
          <Text style={styles.autoNote}>
            Lige nu: {t.scheme === 'light' ? 'lyst' : 'mørkt'}.
          </Text>
        ) : null}
      </View>

      <Text style={styles.groupLabel}>Farve</Text>
      <View style={styles.card}>
        <View style={styles.swatches}>
          {accents.map((a) => {
            const on = t.accent.name === a.name
            return (
              <Pressable
                key={a.name}
                testID={`accent-${a.name}`}
                accessibilityRole="button"
                accessibilityLabel={a.label}
                accessibilityState={{ selected: on }}
                onPress={() => setAccent(a.name)}
                style={({ pressed }) => [styles.swatchWrap, pressed && styles.pressed]}
              >
                <View style={[styles.swatch, { backgroundColor: a.color }]}>
                  {on ? <Check size={18} color={t.color.onAccent} strokeWidth={3} /> : null}
                </View>
                <Text style={[styles.swatchLabel, on && styles.swatchLabelOn]}>{a.label}</Text>
              </Pressable>
            )
          })}
        </View>
      </View>
    </>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  sectionTitle: {
    color: tokens.color.fg3, fontSize: 12, fontWeight: '700',
    letterSpacing: 0.8, textTransform: 'uppercase',
    marginTop: tokens.spacing.lg, marginBottom: tokens.spacing.sm
  },
  groupLabel: {
    color: tokens.color.fg3, fontSize: 13,
    marginTop: tokens.spacing.md, marginBottom: tokens.spacing.xs
  },
  card: {
    backgroundColor: tokens.color.bg2, borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md, gap: tokens.spacing.sm
  },
  modeRow: { flexDirection: 'row', gap: tokens.spacing.sm },
  mode: {
    flex: 1, alignItems: 'center', gap: 2,
    paddingVertical: tokens.spacing.md, borderRadius: tokens.radius.md,
    borderWidth: 1, borderColor: tokens.color.line
  },
  modeOn: { borderColor: tokens.color.accent, backgroundColor: tokens.color.accentGhost },
  modeLabel: { color: tokens.color.fg1, fontSize: 15, fontWeight: '600' },
  modeLabelOn: { color: tokens.color.accentText },
  modeHint: { color: tokens.color.fg3, fontSize: 11.5 },
  modeHintOn: { color: tokens.color.fg2 },
  autoNote: { color: tokens.color.fg3, fontSize: 12.5, paddingLeft: 2 },
  swatches: { flexDirection: 'row', flexWrap: 'wrap', gap: tokens.spacing.md },
  swatchWrap: { alignItems: 'center', gap: 5, width: 64 },
  swatch: {
    width: 40, height: 40, borderRadius: 20,
    alignItems: 'center', justifyContent: 'center'
  },
  swatchLabel: { color: tokens.color.fg3, fontSize: 12 },
  swatchLabelOn: { color: tokens.color.fg1, fontWeight: '600' },
  pressed: { opacity: 0.7 }
})
