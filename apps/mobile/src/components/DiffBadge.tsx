import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useStyles, type Theme } from '../theme/ThemeContext'
import type { GitStatus } from '../lib/apiClient'

/**
 * «73 filer ændret  +2925  −1407» — lige over komponisten.
 *
 * ## Hvad tallene ER, og hvad de ikke er
 *
 * Arbejdstræet målt mod HEAD: det der er ændret og endnu ikke committet. Det
 * er IKKE et regnskab over hvad netop denne samtale har lavet — der findes
 * intet sådant, og et tal der lod som om, ville lyve så snart to ting
 * arbejdede i samme repo.
 *
 * Det er stadig det rigtige tal at vise. Når Jarvis er midt i en opgave, ER
 * arbejdstræet dét arbejde; og har han committet, forsvinder badgen — hvilket
 * i sig selv er den besked man vil have.
 *
 * ## Hvorfor den forsvinder frem for at vise nul
 *
 * En badge der altid står der, holder man op med at læse. Den skal betyde
 * «der ligger noget uafsluttet», og så må den ikke også kunne betyde «der
 * ligger ingenting». Samme regel som prikken på Godkend.
 */
export function DiffBadge({ git, onPress }: { git: GitStatus | null; onPress?: () => void }) {
  const styles = useStyles(makestyles)
  if (!diffVaerdAtVise(git)) return null
  const g = git as GitStatus
  return (
    <Pressable
      testID="diff-badge"
      accessibilityRole={onPress ? 'button' : 'text'}
      accessibilityLabel={`${g.dirty} filer ændret, ${g.added} linjer tilføjet, ${g.removed} fjernet`}
      onPress={onPress}
      style={({ pressed }) => [styles.pille, pressed && onPress ? styles.trykket : null]}
    >
      <Text style={styles.filer}>{g.dirty} {g.dirty === 1 ? 'fil' : 'filer'} ændret</Text>
      {g.added ? <Text style={[styles.tal, styles.plus]}>+{g.added}</Text> : null}
      {g.removed ? <Text style={[styles.tal, styles.minus]}>−{g.removed}</Text> : null}
    </Pressable>
  )
}

/**
 * Er der noget at vise?
 *
 * Nul berørte filer er ikke «0 filer ændret» — det er et rent træ, og der skal
 * badgen ikke være. Men et træ med berørte filer og nul linjer ER værd at vise:
 * en tom fil der blev oprettet, eller en binær fil som numstat ikke kan tælle,
 * giver præcis dét.
 */
export function diffVaerdAtVise(git: GitStatus | null | undefined): boolean {
  if (!git || !git.isGit) return false
  return Number(git.dirty) > 0
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  pille: {
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: tokens.color.bgFloat,
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 7,
    marginBottom: 8,
    ...tokens.elevation,
  },
  filer: { color: tokens.color.fg2, fontSize: 12.5 },
  // Tal-kolonner skal staa stille naar de aendrer sig. Uden tabular-nums
  // hopper hele pillen hver gang et ciffer skifter bredde.
  tal: { fontSize: 12.5, fontWeight: '600', fontVariant: ['tabular-nums'] },
  // `ok` og `error` — IKKE accent og warn. Groen/roed er her semantik
  // (tilfoejet/fjernet), ikke appens kulør; en diff maa ikke skifte betydning
  // fordi nogen vaelger en anden accentfarve i indstillingerne.
  plus: { color: tokens.color.ok },
  minus: { color: tokens.color.error },
  trykket: { opacity: 0.6 },
})
