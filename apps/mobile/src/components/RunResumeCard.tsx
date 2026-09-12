import { StyleSheet, Text, View } from 'react-native'
import { AlertTriangle, CheckCircle2, CircleSlash, Loader } from 'lucide-react-native'
import { formatVarighed, type RunResume } from '../lib/runResume'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Tre linjer i stedet for tres.
 *
 * Tidslinjen findes allerede nedenunder, og den er lang. Spørgsmålet man har
 * når man trykker på et afsluttet run er ikke «hvad skete der i rækkefølge» —
 * det er «gik det godt, hvor længe tog det, og hvad gik galt».
 *
 * ## Hvorfor fejlen står nederst og ikke øverst
 *
 * Fordi de fleste runs ikke har nogen. Et felt der er tomt i ni ud af ti
 * tilfælde må ikke stå der hvor øjet lander først — så lærer man at springe
 * netop den plads over, og så er den også væk den ene gang den betyder noget.
 */
export function RunResumeCard({ resume }: { resume: RunResume }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const farve = udfaldFarve(resume.udfald, tokens)

  return (
    <View style={styles.kort} testID="run-resume">
      <View style={styles.top}>
        {resume.udfald === 'lykkedes' ? <CheckCircle2 size={16} color={farve} strokeWidth={2} />
          : resume.udfald === 'fejlede' ? <AlertTriangle size={16} color={farve} strokeWidth={2} />
          : resume.udfald === 'afbrudt' ? <CircleSlash size={16} color={farve} strokeWidth={2} />
          : <Loader size={16} color={farve} strokeWidth={2} />}
        <Text style={[styles.udfald, { color: farve }]}>{ORD[resume.udfald]}</Text>
        {resume.sekunder !== null ? (
          <Text style={styles.tid}>{formatVarighed(resume.sekunder)}</Text>
        ) : null}
      </View>

      <View style={styles.tal}>
        <Tal navn="runder" v={resume.runder} />
        <Tal navn={resume.vaerktoejskald === 1 ? 'værktøjskald' : 'værktøjskald'} v={resume.vaerktoejskald} />
        {resume.godkendelser ? <Tal navn="godkendelser" v={resume.godkendelser} /> : null}
      </View>

      {resume.vaerktoejer.length ? (
        <Text style={styles.vaerktoejer} numberOfLines={2}>
          {resume.vaerktoejer.slice(0, 4).map((v) => `${v.navn} ×${v.antal}`).join('  ·  ')}
        </Text>
      ) : null}

      {resume.fejl.length ? (
        <View style={styles.fejlBoks}>
          {resume.fejl.slice(0, 3).map((f, i) => (
            <Text key={`${i}-${f.slice(0, 12)}`} style={styles.fejl} numberOfLines={3}>{f}</Text>
          ))}
        </View>
      ) : null}
    </View>
  )
}

function Tal({ navn, v }: { navn: string; v: number }) {
  const styles = useStyles(makestyles)
  return (
    <View style={styles.talPar}>
      <Text style={styles.talV}>{v}</Text>
      <Text style={styles.talN}>{navn}</Text>
    </View>
  )
}

const ORD: Record<RunResume['udfald'], string> = {
  'kører': 'Kører',
  lykkedes: 'Lykkedes',
  fejlede: 'Fejlede',
  afbrudt: 'Afbrudt',
}

/**
 * `ok`/`error`/`warn` — ikke accent. Semantik, ikke appens kulør.
 *
 * AFBRUDT er gul, ikke rød: noget man selv standsede er ikke en fejl, og rødt
 * på ens eget valg gør farven ubrugelig.
 */
export function udfaldFarve(u: RunResume['udfald'], tokens: Theme): string {
  if (u === 'fejlede') return tokens.color.error
  if (u === 'afbrudt') return tokens.color.warn
  if (u === 'lykkedes') return tokens.color.ok
  return tokens.color.fg2
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  kort: {
    backgroundColor: tokens.color.bg1, borderRadius: 14,
    padding: tokens.spacing.sm, marginBottom: tokens.spacing.sm, gap: 8,
  },
  top: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  udfald: { fontSize: 14, fontWeight: '600', flex: 1 },
  tid: { color: tokens.color.fg2, fontSize: 12.5, fontVariant: ['tabular-nums'] },
  tal: { flexDirection: 'row', gap: 18 },
  talPar: { flexDirection: 'row', alignItems: 'baseline', gap: 4 },
  talV: { color: tokens.color.fg1, fontSize: 15, fontWeight: '600', fontVariant: ['tabular-nums'] },
  talN: { color: tokens.color.fg2, fontSize: 11.5 },
  vaerktoejer: { color: tokens.color.fg2, fontSize: 11.5 },
  fejlBoks: {
    backgroundColor: tokens.color.bg2, borderRadius: 10, padding: 9, gap: 5,
  },
  fejl: { color: tokens.color.error, fontSize: 12 },
})
