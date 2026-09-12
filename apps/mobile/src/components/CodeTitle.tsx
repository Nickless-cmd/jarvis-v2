import { Pressable, StyleSheet, Text, View } from 'react-native'
import { FolderGit2, Monitor } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { BADGE_H } from './badgeGeometri'
import type { GitStatus } from '../lib/apiClient'

/**
 * Code-fladens midte: hvad man arbejder på, og hvor.
 *
 * ## Hvorfor segmentet ikke står her
 *
 * «Snak | Arbejde» hører til chat-fladen. I code har man allerede valgt hvad
 * man laver, og kontakten er derfor kun støj på appens mest værdifulde plads.
 * Den plads bruges i stedet på den ene oplysning telefonen ikke selv kan
 * regne ud: hvilket repo på hvilken maskine. API'et kører et andet sted end
 * appen, og forskellen på at VIDE det og at gætte det er hele pointen.
 *
 * ## Prikken har TRE farver
 *
 * Grøn: maskinen svarede. Gul: broen er der, men svarede ikke på det sidste
 * kald — en desk der genstarter står registreret et øjeblik endnu, og rødt
 * hver gang nogen genstartede sin app ville lære én at se bort fra farven.
 * Rød: ingen forbindelse.
 *
 * Er der ingen git-status overhovedet, tegnes hele kontekstlinjen ikke — en
 * linje med tomme navne og en grøn prik ville påstå en forbindelse der ikke
 * er efterprøvet.
 */
export function CodeTitle({ titel, git, onPress }: {
  titel: string
  git: GitStatus | null
  /** Åbner workspace-vælgeren. Uden den er pillen ren visning. */
  onPress?: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <Pressable
      testID="code-titel"
      accessibilityRole={onPress ? 'button' : 'text'}
      accessibilityLabel={onPress ? `${titel || 'Kode-session'} — vælg hvor Jarvis skal arbejde` : undefined}
      onPress={onPress}
      disabled={!onPress}
      style={({ pressed }) => [styles.pille, pressed && onPress ? styles.trykket : null]}
    >
      <Text style={styles.titel} numberOfLines={1}>
        {titel || 'Kode-session'}
      </Text>
      {git ? (
        <View style={styles.kontekst}>
          <FolderGit2 size={11} color={tokens.color.fg2} strokeWidth={1.9} />
          <Text style={styles.meta} numberOfLines={1}>{git.repo || 'repo'}</Text>
          <Monitor size={11} color={tokens.color.fg2} strokeWidth={1.9} />
          <Text style={styles.meta} numberOfLines={1}>{git.host || 'vært'}</Text>
          <View
            testID={`link-${git.link}`}
            accessibilityLabel={LINK_ORD[git.link]}
            style={[styles.prik, { backgroundColor: linkFarve(git.link, tokens) }]}
          />
        </View>
      ) : null}
    </Pressable>
  )
}

const LINK_ORD: Record<GitStatus['link'], string> = {
  ok: 'Forbundet',
  genforbinder: 'Genforbinder',
  nede: 'Ingen forbindelse',
}

/**
 * Farven på prikken.
 *
 * `ok` og `error` — IKKE accent. Det er semantik, ikke appens kulør: en
 * forbindelse må ikke skifte betydning fordi nogen vælger en anden accentfarve
 * i indstillingerne. Samme regel som diff-badgens plus og minus.
 */
export function linkFarve(link: GitStatus['link'], tokens: Theme): string {
  if (link === 'nede') return tokens.color.error
  if (link === 'genforbinder') return tokens.color.warn
  return tokens.color.ok
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  pille: {
    backgroundColor: tokens.color.bgFloat,
    // EKSPLICIT hoejde, ikke en der bliver til af sig selv. To tekstlinjer
    // plus polstring gav 47 dp mod de andre badges' 40, og forskellen var
    // ikke til at se paa koden.
    height: BADGE_H,
    borderRadius: BADGE_H / 2,
    paddingHorizontal: 14,
    justifyContent: 'center',
    alignItems: 'center',
    // Skal kunne blive smallere end sit indhold: en lang titel maa forkorte
    // sig selv frem for at skubbe hoejre felt ud over skaermkanten.
    flexShrink: 1,
    minWidth: 0,
    ...tokens.elevation,
  },
  // Faste linjehoejder: uden dem afhaenger indholdets hoejde af systemets
  // skriftindstilling, og saa ville pillen klippe sin egen tekst paa en
  // telefon med stoerre tekst.
  titel: {
    color: tokens.color.fg1, fontSize: 13.5, fontWeight: '600',
    lineHeight: 16, flexShrink: 1,
  },
  trykket: { opacity: 0.65 },
  kontekst: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 1 },
  meta: { color: tokens.color.fg2, fontSize: 10.5, lineHeight: 12, maxWidth: 92 },
  // Farven saettes inline efter forbindelsen; her staar kun formen.
  prik: { width: 6, height: 6, borderRadius: 3, marginLeft: 1 },
})
