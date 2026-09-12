import { useEffect, useState } from 'react'
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native'
import type { LiveStep } from '../lib/streamReducer'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Et værktøj der KØRER — vist mens det kører, ikke bagefter.
 *
 * ## Hvorfor det findes
 *
 * Serveren annoncerer hvert kald (`working_step`) FØR det udføres, men sender
 * først `tool_use` + `tool_result` når resultatet findes — begge fra samme
 * payload. Indtil da var der én statuslinje, og et værktøj der tog et minut
 * så ud som om han var gået i stå. Bjørn: «det laver nogen lange gaps der kan
 * virke som om han er stalled».
 *
 * ## Hvorfor tiden tælles HER og ikke af serveren
 *
 * Modsat baggrundsjobs, hvor serveren kender starttidspunktet og vi ville få
 * to ure der driver: her findes tallet slet ikke andre steder. Kortet lever
 * sekunder, ikke timer, og det eneste det skal sige er «der sker stadig
 * noget». En drift på et par hundrede millisekunder over ti sekunder betyder
 * ingenting; en fastfrossen linje betyder alt.
 */
export function LiveToolCard({ step, now }: { step: LiveStep; now?: number }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [nu, setNu] = useState(now ?? Date.now())

  useEffect(() => {
    if (now !== undefined) return          // styret udefra (test)
    const t = setInterval(() => setNu(Date.now()), 1000)
    return () => clearInterval(t)
  }, [now])

  const sek = Math.max(0, Math.floor(((now ?? nu) - step.setAt) / 1000))

  return (
    <View style={styles.kort} testID={`live-tool-${step.navn}`}>
      <ActivityIndicator size="small" color={tokens.color.accent} />
      <Text style={styles.etiket} numberOfLines={2}>{step.etiket}</Text>
      <Text style={styles.tid}>{sek}s</Text>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  kort: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: tokens.color.bg1, borderRadius: 12,
    paddingVertical: 10, paddingHorizontal: 12, marginBottom: 6,
  },
  etiket: { color: tokens.color.fg1, fontSize: 13.5, flex: 1 },
  // Tabular-nums: uden dem hopper hele kortet hver gang et ciffer skifter
  // bredde, og et kort der hopper hvert sekund er vaerre end ingen tid.
  tid: {
    color: tokens.color.fg2, fontSize: 12,
    fontVariant: ['tabular-nums'], minWidth: 30, textAlign: 'right',
  },
})
