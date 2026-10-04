import { useEffect, useRef, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { AnimeretPuls } from './AnimeretPuls'
import { Prikker } from './Prikker'
import { CIF_HOEJDE, RullendeTokens, RullendeUr } from './RullendeTal'

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
 * følgen er desks (Bjørn 4/10-2026): **animation → min/sec → tokens → det
 * linjen ellers viser** (sætningen), med prikkerne til sidst. Token-tallet
 * stod FØRST indtil da — nu matcher rækkefølgen liveness-linjen i desk.
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
      {/* Rækkefølgen er desks (Bjørn 4/10-2026): min:sek FØR token-tallet —
          «min/sek først og så token count». Det er samme orden som
          liveness-linjen over composeren, så de to klienter læser ens. */}
      {sek >= 1 ? (
        <View style={styles.talRaekke} testID="arbejdslinje-tid">
          <RullendeUr sek={sek} farve={farver.color.fg2} tegnFarve={farver.color.fg3} />
        </View>
      ) : null}
      {tokens > 0 ? (
        <View style={styles.talRaekke} testID="arbejdslinje-tokens">
          <RullendeTokens tokens={tokens} farve={farver.color.fg2} tegnFarve={farver.color.fg3} />
          <Text style={styles.talTekst}> tokens</Text>
        </View>
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
  talRaekke: { flexDirection: 'row', alignItems: 'center', flexShrink: 0, opacity: 0.65 },
  // 4/10-2026: SAMME kasse som hjulene (`CIF_HOEJDE`). Uden den centrerer
  // rækken en lavere tekstkasse (fontens egen line-height) mod hjulets 16 px,
  // og cifferet løftes. Desk havde samme fejl i en anden form — der var det
  // flex-baseline, her er det to kasser i forskellig højde. Med identiske
  // kasser lander begge glyffer ens, uanset hvordan platformen placerer
  // teksten i sin line-height.
  talTekst: {
    color: tokens.color.fg2, fontSize: 12, lineHeight: CIF_HOEJDE,
    height: CIF_HOEJDE, fontVariant: ['tabular-nums'],
  },
  tekst: { color: tokens.color.fg2, fontSize: 13.5, flexShrink: 1, minWidth: 0 },
})
