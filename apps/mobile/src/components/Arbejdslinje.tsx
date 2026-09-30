import { useEffect, useRef, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { AnimeretPuls } from './AnimeretPuls'
import { Prikker } from './Prikker'
import { formatTid, kortTokens } from '../lib/arbejdslinje'

/**
 * Arbejdslinjen — nederst i beskeden, kun mens der streames.
 *
 * Bjørn 29/9-2026: linjen skal ligge i BUNDEN af beskeden (ikke over
 * composeren), leve fra streamen starter til den slutter, og forsvinde igen.
 * Så forlader den skærmen sammen med arbejdet i stedet for at stå tilbage som
 * en tom bjælke — og den melder hvad der sker LIGE NU, hvor intet andet i
 * beskeden gør det mens turen kører.
 *
 * Puls-mærket er mobilens EGEN komponent i sin ANIMEREDE form
 * (`AnimeretPuls`, ikke det statiske `PulsIkon`): samme geometri og samme
 * rytme som desks `JarvisRing`, så de to klienter viser samme tegn — og
 * samme bevægelse. Bjørn 30/9-2026: «dit/husets ikon mangler animation som i
 * header» — mærket i tilbage-badgen pulserer, og prikkerne ved siden af
 * rullede allerede, så det statiske mærke imellem dem stod stille i en linje
 * hvor alt andet bevægede sig.
 *
 * ## Tal og prikker er flyttet herned (Bjørn 30/9-2026)
 *
 * Runde-linjen bar sin egen klokke og sine egne tre prikker. Men runden er
 * kort og forsvinder, mens arbejdet fortsætter — så tallene hørte til den
 * linje der LEVER hele streamen, ikke til den der slukkes undervejs. Række-
 * følgen er Bjørns: **animation → tokens → min/sec → det linjen ellers
 * viser** (sætningen), med prikkerne til sidst.
 *
 * Desk har præcis samme indhold i sin liveness-linje over composeren
 * (`LivenessIndicator.tsx`: ring → varighed → tokens → arbejdsteksten). De to
 * eneste forskelle er med vilje: her sidder linjen i bunden af BESKEDEN, og
 * den er mere kompakt — og så forsvinder den når streamen slutter.
 *
 * ## Uret hører til linjen
 *
 * `workingStep` bevares gennem hele kørslen (reduceren rydder den først ved
 * `message_start`, se `streamReducer.ts`), så linjen monteres ÉN gang pr.
 * stream. Derfor er dens levetid varigheden — og uret kan bo her. Det er
 * også det billige valg: et ur i stream-tilstanden ville tegne hele træet om
 * hvert kvart sekund, hvor kun denne linje nu tegner om.
 *
 * Teksten kommer fra `arbejdslinjeTekst` — sætningen er bygget i Jarvis'
 * stemme, ikke i serverens label-sprog. `null` = intet at vise = ingen linje.
 */
export function Arbejdslinje({ tekst, tokens = 0 }: { tekst: string | null; tokens?: number }) {
  // `farver` og ikke `tokens`: navnet er optaget af token-TALLET, som er en
  // prop her og ikke temaet.
  const farver = useTheme()
  const styles = useStyles(makestyles)
  const startet = useRef(Date.now())
  const [, tick] = useState(0)

  useEffect(() => {
    const iv = setInterval(() => tick((n) => n + 1), TICK_MS)
    return () => clearInterval(iv)
  }, [])

  if (!tekst) return null

  // «0s» er ikke et tal — det er en kørsel der lige er begyndt. Først fra ét
  // sekund er der noget at vise (samme vægn som SkillLinjen bruger).
  const sek = Math.floor((Date.now() - startet.current) / 1000)

  return (
    <View
      style={styles.linje}
      testID="arbejdslinje"
      accessibilityRole="text"
      accessibilityLabel={tekst}
    >
      {/* `size={15}` er mærkets mål i denne linje: bjælkerne bliver 2,85 x
          9,15 dp — præcis de tal det statiske `PulsIkon` tegnede ved 15. Kun
          bevægelsen er ny. `testID` bevares, så tegnet kan findes som før. */}
      <AnimeretPuls size={15} farve={farver.color.accent} testID="puls-ikon" />
      {tokens > 0 ? (
        <Text style={styles.tal} testID="arbejdslinje-tokens" numberOfLines={1}>{kortTokens(tokens)} tokens</Text>
      ) : null}
      {sek >= 1 ? (
        <Text style={styles.tal} testID="arbejdslinje-tid" numberOfLines={1}>{formatTid(sek)}</Text>
      ) : null}
      <Text style={styles.tekst} numberOfLines={2}>{tekst}</Text>
      <Prikker farve={farver.color.fg3} />
    </View>
  )
}

/** Så tit uret regnes om mens linjen står der. */
const TICK_MS = 250

const makestyles = (tokens: Theme) => StyleSheet.create({
  linje: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.lg,
    paddingVertical: tokens.spacing.sm,
  },
  // Tallene står FAST: de er det linjen melder om arbejdet, og en lang sti må
  // ikke skubbe dem ud af skærmen. Det er teksten der viger.
  tal: {
    color: tokens.color.fg2, fontSize: 12, opacity: 0.65,
    fontVariant: ['tabular-nums'], flexShrink: 0,
  },
  tekst: { color: tokens.color.fg2, fontSize: 13.5, flexShrink: 1, minWidth: 0 },
})
