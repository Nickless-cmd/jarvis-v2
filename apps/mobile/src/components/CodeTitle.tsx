import { StyleSheet, Text, View } from 'react-native'
import { FolderGit2, Monitor } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
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
 * ## Hvorfor prikken er grøn
 *
 * Den siger at værten svarede. Er der ingen git-status, tegnes hele
 * kontekstlinjen ikke — en linje med tomme navne og en grøn prik ville
 * påstå en forbindelse der ikke er efterprøvet.
 */
export function CodeTitle({ titel, git }: { titel: string; git: GitStatus | null }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <View style={styles.pille} testID="code-titel">
      <Text style={styles.titel} numberOfLines={1}>
        {titel || 'Kode-session'}
      </Text>
      {git ? (
        <View style={styles.kontekst}>
          <FolderGit2 size={11} color={tokens.color.fg2} strokeWidth={1.9} />
          <Text style={styles.meta} numberOfLines={1}>{git.repo || 'repo'}</Text>
          <Monitor size={11} color={tokens.color.fg2} strokeWidth={1.9} />
          <Text style={styles.meta} numberOfLines={1}>{git.host || 'vært'}</Text>
          <View style={styles.prik} />
        </View>
      ) : null}
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  pille: {
    backgroundColor: tokens.color.bgFloat,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 7,
    alignItems: 'center',
    ...tokens.elevation,
  },
  titel: { color: tokens.color.fg1, fontSize: 14, fontWeight: '600' },
  kontekst: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 2 },
  meta: { color: tokens.color.fg2, fontSize: 11, maxWidth: 92 },
  prik: {
    width: 6, height: 6, borderRadius: 3,
    backgroundColor: tokens.color.accent, marginLeft: 1,
  },
})
