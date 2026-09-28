import { useEffect, useState } from 'react'
import { BackHandler, FlatList, Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import { ChevronLeft, ChevronRight } from 'lucide-react-native'
import type { StoredModelChoice } from '../lib/sessionStore'
import type { ThinkingMode } from '../lib/chatSettings'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export type ModelChoice = StoredModelChoice

/** Tænke-tilstanden EJES af `chatSettings` — den gemmes pr. samtale, og det er
 *  dér den oversættes til stream-kroppen. Den var erklæret her OGSÅ, som en
 *  identisk union, og de to holdt kun hinanden i sync ved held: en fjerde
 *  tilstand tilføjet det ene sted ville tavst blive afvist det andet. Nu er
 *  der én, og den genbruges her. */
export type { ThinkingMode }

/** Tænke-tilstandenes navne — desks ord, ikke vores egne. */
const TANKE_NAVN: Record<ThinkingMode, string> = { fast: 'Hurtig', think: 'Automatisk', deep: 'Dyb' }
const TANKE_RAEKKE: ThinkingMode[] = ['fast', 'think', 'deep']

/**
 * Kompakt model-menu over composer. Rolle-bevidst indhold leveres af kalderen:
 * owner får hele paletten, member får kun Standard/Pro (= ollama flash/pro).
 *
 * ## Formen er lånt, ikke opfundet
 *
 * Bjørn 28/9-2026: «med samme visning når åbnet» — og viste to skærmbilleder.
 * Formen er den fra ChatGPT-appens egen vælger: det man skifter oftest står som
 * en LISTE øverst med et flueben ved det valgte, og de ting der sjældnere røres
 * ligger som UNDERMENUER nederst, hver med sin nuværende værdi og en chevron.
 *
 * Det er omvendt af hvad den var: modellisten laa øverst og taenkningen laa som
 * to segmenter nederst. Man skifter taenkning oftere end model, saa den hoerer
 * øverst — og et segment kan ikke vise «hvad er valgt lige nu» for et blik paa
 * samme maade som en raekke med et flueben kan.
 *
 * «Hastighed» fra billedet findes ikke her: i denne app er taenkning og
 * hastighed EET begreb (`think`/`fast`), hvor ChatGPT deler dem i to.
 */
export function ModelPicker({
  open,
  bottomOffset = 88,
  choices,
  selectedLabel,
  thinkingMode,
  onThinkingModeChange,
  onSelect,
  onClose
}: {
  open: boolean
  bottomOffset?: number
  choices: ModelChoice[]
  selectedLabel?: string
  thinkingMode?: ThinkingMode
  onThinkingModeChange?: (mode: ThinkingMode) => void
  onSelect: (c: ModelChoice) => void
  onClose: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { width, height } = useWindowDimensions()
  const [visning, setVisning] = useState<'hoved' | 'model'>('hoved')
  const harTaenkning = Boolean(onThinkingModeChange)

  // Hver åbning starter på hoved-visningen. Uden dette landede man i model-
  // listen fra sidste gang, og tænke-valget var skjult bag et tryk man ikke
  // vidste om — den slags husker sheet'en ikke imellem, og skal ikke gøre det.
  useEffect(() => {
    if (open) setVisning('hoved')
  }, [open])

  useEffect(() => {
    if (!open) return
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (visning === 'model' && harTaenkning) setVisning('hoved')
      else onClose()
      return true
    })
    return () => sub.remove()
  }, [open, visning, harTaenkning, onClose])

  const modelListe = (
    <FlatList
      data={choices}
      keyExtractor={(c) => c.label}
      style={styles.list}
      renderItem={({ item }) => {
        const active = item.label === selectedLabel
        return (
          <Pressable
            accessibilityRole="button"
            onPress={() => {
              onSelect(item)
              onClose()
            }}
            style={({ pressed }) => [styles.row, pressed ? styles.pressed : null]}
          >
            <Text style={[styles.rowLabel, active ? styles.rowActive : null]} numberOfLines={1}>
              {item.label}
            </Text>
            {active ? <Text style={styles.check}>✓</Text> : null}
          </Pressable>
        )
      }}
      ListEmptyComponent={<Text style={styles.empty}>Ingen modeller tilgængelige</Text>}
    />
  )

  if (!open) return null

  return (
    <View style={styles.overlay} pointerEvents="box-none">
      <Pressable style={styles.scrim} onPress={onClose} accessibilityLabel="Luk modelvælger" />
      <View testID="model-popover" style={[styles.sheet, { bottom: bottomOffset, width: Math.min(width - 32, 208), maxHeight: Math.max(200, height - bottomOffset - 64) }]}>

          {/* Uden tænke-valg er der kun én ting at vise — saa er der ingen
              undermenu at gaa ind i, og listen staar direkte. */}
          {!harTaenkning ? (
            <>
              <Text style={styles.title}>Model</Text>
              {modelListe}
            </>
          ) : visning === 'model' ? (
            <>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Tilbage"
                onPress={() => setVisning('hoved')}
                hitSlop={8}
                style={styles.tilbage}
              >
                <ChevronLeft size={18} color={tokens.color.fg2} strokeWidth={2} />
                <Text style={styles.tilbageTekst}>Tilbage</Text>
              </Pressable>
              <Text style={styles.title}>Model</Text>
              {modelListe}
            </>
          ) : (
            <>
              <Text style={styles.title}>Intelligens</Text>
              {TANKE_RAEKKE.map((m) => {
                const valgt = thinkingMode === m
                return (
                  <Pressable
                    key={m}
                    accessibilityRole="button"
                    accessibilityLabel={TANKE_NAVN[m]}
                    accessibilityState={{ selected: valgt }}
                    onPress={() => onThinkingModeChange?.(m)}
                    style={({ pressed }) => [styles.row, pressed ? styles.pressed : null]}
                  >
                    <Text style={[styles.rowLabel, valgt ? styles.rowActive : null]}>
                      {TANKE_NAVN[m]}
                    </Text>
                    {valgt ? <Text style={styles.check}>✓</Text> : null}
                  </Pressable>
                )
              })}

              <View style={styles.divider} />

              {/* Undermenuen: navnet til venstre, den nuværende værdi og en
                  chevron til højre — praecis som billedet Bjørn viste. */}
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`Model: ${selectedLabel ?? ''}`}
                onPress={() => setVisning('model')}
                style={({ pressed }) => [styles.underRow, pressed ? styles.pressed : null]}
              >
                <View style={styles.underTekst}>
                  <Text style={styles.underNavn}>Model</Text>
                  <Text style={styles.underVaerdi} numberOfLines={1}>{selectedLabel ?? 'Vælg'}</Text>
                </View>
                <ChevronRight size={16} color={tokens.color.fg2} strokeWidth={2} />
              </Pressable>
            </>
          )}
      </View>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  overlay: { ...StyleSheet.absoluteFill, zIndex: 31 },
  scrim: { ...StyleSheet.absoluteFill },
  sheet: {
    position: 'absolute', right: 14,
    backgroundColor: tokens.color.bg3,
    borderRadius: 24,
    borderColor: tokens.color.glassLine,
    borderWidth: StyleSheet.hairlineWidth,
    ...tokens.elevation,
    overflow: 'hidden',
    paddingHorizontal: tokens.spacing.lg,
    paddingTop: tokens.spacing.lg,
    paddingBottom: tokens.spacing.md
  },
  title: {
    color: tokens.color.fg2,
    fontSize: 15,
    fontWeight: '500',
    marginBottom: tokens.spacing.sm
  },
  tilbage: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: tokens.spacing.xs },
  tilbageTekst: { color: tokens.color.fg2, fontSize: 14, fontWeight: '600' },
  divider: { height: StyleSheet.hairlineWidth, backgroundColor: tokens.color.line, marginTop: tokens.spacing.md },
  list: { flexGrow: 0 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 54,
    paddingVertical: tokens.spacing.md
  },
  pressed: { opacity: 0.7 },
  rowLabel: { color: tokens.color.fg1, fontSize: 16, flexShrink: 1 },
  rowActive: { color: tokens.color.fg1, fontWeight: '700' },
  check: { color: tokens.color.accentText, fontSize: 16, fontWeight: '700' },
  underRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 62,
    paddingVertical: tokens.spacing.md,
    gap: tokens.spacing.md
  },
  underTekst: { flex: 1, minWidth: 0 },
  underNavn: { color: tokens.color.fg1, fontSize: 16 },
  underVaerdi: { color: tokens.color.fg2, fontSize: 12, marginTop: 2 },
  empty: { color: tokens.color.fg3, paddingVertical: tokens.spacing.lg, textAlign: 'center' }
})
