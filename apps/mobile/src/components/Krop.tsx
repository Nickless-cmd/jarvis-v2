import { useState } from 'react'
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { highlight, type Span, type SpanKind } from '../lib/highlight'
import { ANSI_FARVER, ansiStykker, ryd, type AnsiStil } from '../lib/ansiTekst'
import { filTekst, exitKode, kropFor, udDel, type KropFamilie } from '../lib/krop'

const MONO = Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' })

/**
 * Kroppene — de få former, ikke de mange værktøjer.
 *
 * Bjørn 30/9-2026: «Tool result linjen mangler at kunne foldes ud.. og vises
 * hvad du lavet i run.. og vi har ingen form visning eller diff visningen».
 * Folden kunne åbnes, men viste rå tekst i fast bredde: et bash-kald og en
 * fil-læsning så ens ud. Desk har tolv kroppe; mobilen havde nul.
 *
 * Vi starter med de to der bærer mest af arbejdet — **terminal** og **fil** —
 * og lader `fald` bære halen, præcis som desk (`raekkeKroppe.tsx`).
 */

/* ══ Terminal ═══════════════════════════════════════════════════════════ */

/**
 * ANSI-farvet tekst.
 *
 * `ryd` fjerner alt UNDTAGEN SGR, så der kan stadig stå `\x1b[32m` tilbage —
 * det er meningen, det er dem vi oversætter. Er der ingen koder, tegner vi én
 * `<Text>` og sparer en masse noder.
 */
function AnsiTekst({ tekst, stil }: { tekst: string; stil: object }) {
  const ren = ryd(tekst)
  if (!ren.includes('\x1b')) return <Text style={stil} selectable>{ren}</Text>
  return (
    <Text style={stil} selectable>
      {ansiStykker(ren).map((d, i) => (
        <Text key={i} style={ansiStil(d.s)}>{d.t}</Text>
      ))}
    </Text>
  )
}

/** Farve, fed og dæmpet — desk's regler, overført til React Native. */
function ansiStil(s: AnsiStil): object {
  const ud: Record<string, unknown> = {}
  if (s.rgb) ud.color = s.rgb
  else if (s.fg !== undefined) ud.color = ANSI_FARVER[s.fg] ?? undefined
  if (s.bold) ud.fontWeight = '600'
  if (s.dim) ud.opacity = 0.7
  return ud
}

/**
 * Terminal-kroppen: stdout, og exit-koden når den betyder noget.
 *
 * Exit-pillen vises KUN når koden ikke er nul. Desk's CSS viser den altid, men
 * husets egen regel i `raekkeKroppe.tsx` siger det modsatte: «`exit 0` tegner
 * INGEN pille — kun ikke-nul markeres. Det er halvdelen af forskellen mellem
 * «rolig» og «terminal-agtig».» Vi følger reglen: en fejl er det man skal se,
 * «exit 0» er en bekræftelse på noget der gik som det skulle.
 */
export function TerminalKrop({
  ud, exit, running = false,
}: {
  ud: string
  exit: number
  running?: boolean
}) {
  const styles = useStyles(makestyles)
  if (!ud && !running) return null
  return (
    <View style={styles.terminal} testID="krop-terminal">
      {ud ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.termScroll}>
          <AnsiTekst tekst={ud} stil={styles.termTekst} />
        </ScrollView>
      ) : (
        <Text style={styles.termTom}>Kører…</Text>
      )}
      {exit !== 0 ? (
        <Text style={styles.exit} testID="krop-exit">exit {exit}</Text>
      ) : null}
    </View>
  )
}

/* ══ Fil ════════════════════════════════════════════════════════════════ */

/** Så mange linjer tegnes før filen klippes — med hale, som desk. */
export const MAX_LINJER = 24
const HALE_LINJER = 6

/**
 * Farvelagte linjer.
 *
 * Vi farver HELE teksten i ét kald og deler bagefter stykkerne ved `\n`. Den
 * modsatte vej — highlight pr. linje — ville være enklere, men så farves en
 * blokkommentar forkert: scanneren ser ikke at den fortsætter på næste linje.
 * Prisen er ét gennemløb, og den er værd at betale for en fil.
 */
function linjerMedFarve(tekst: string): Span[][] {
  const linjer: Span[][] = [[]]
  for (const s of highlight(tekst)) {
    const dele = s.text.split('\n')
    for (let i = 0; i < dele.length; i++) {
      if (i > 0) linjer.push([])
      const d = dele[i]!
      if (d) linjer[linjer.length - 1]!.push({ text: d, kind: s.kind })
    }
  }
  return linjer
}

const KODE_FARVE: Record<SpanKind, { color: string }> = {
  plain: { color: '#E6EDF3' },
  str: { color: '#7EE787' },
  com: { color: '#6E7681' },
  num: { color: '#FFA657' },
  kw: { color: '#79C0FF' },
}

/**
 * Fil-kroppen: linjenumre og syntaksfarver.
 *
 * En fil kan være tusind linjer. Uden et snit ville ét kald skubbe resten af
 * runden ud af syne — og det man leder efter er som regel begyndelsen og
 * slutningen. Derfor desk's model: hoved, hale, og et tal for hvad der er
 * udeladt i midten. Udfoldningen er LOKAL: teksten er der allerede.
 */
export function FilKrop({ tekst }: { tekst: string }) {
  const styles = useStyles(makestyles)
  const tokens = useTheme()
  const [alt, setAlt] = useState(false)
  const alle = tekst ? tekst.replace(/\n$/, '').split('\n') : []
  if (!alle.length) return null
  const klippet = !alt && alle.length > MAX_LINJER
  const hoved = klippet ? alle.slice(0, MAX_LINJER - HALE_LINJER) : alle
  const hale = klippet ? alle.slice(alle.length - HALE_LINJER) : []
  const udeladt = alle.length - hoved.length - hale.length

  const blok = (linjer: string[], fra: number) => (
    <View>
      {linjerMedFarve(linjer.join('\n')).map((spans, i) => (
        <View key={fra + i} style={styles.filLinje}>
          <Text style={styles.filNr}>{fra + i + 1}</Text>
          <Text style={styles.filKode}>
            {spans.map((s, j) => (
              <Text key={j} style={KODE_FARVE[s.kind]}>{s.text}</Text>
            ))}
          </Text>
        </View>
      ))}
    </View>
  )

  return (
    <View style={styles.fil} testID="krop-fil">
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filScroll}>
        <View>
          {blok(hoved, 0)}
          {klippet ? (
            <>
              <Text style={styles.filUdeladt}>{udeladt} linjer udeladt i midten</Text>
              {blok(hale, alle.length - hale.length)}
            </>
          ) : null}
        </View>
      </ScrollView>
      {alle.length > MAX_LINJER ? (
        <Pressable
          onPress={() => setAlt((v) => !v)}
          testID="krop-vis-alle"
          accessibilityRole="button"
          hitSlop={8}
          style={styles.filKnap}
        >
          <Text style={styles.filKnapTekst}>{alt ? 'Vis færre' : `Vis alle ${alle.length} linjer`}</Text>
        </Pressable>
      ) : null}
    </View>
  )
}

/* ══ Vælgeren ═══════════════════════════════════════════════════════════ */

/**
 * Krop efter RESULTATETS form.
 *
 * `fald` er ikke en fejl: for små status-objekter er den rå tekst den rigtige
 * form. Den tegnes af kaldsstedet (`InlineToolGroup`), som allerede har den
 * vej — vi duplikerer den ikke her.
 */
export function Krop({
  familie, result, running = false,
}: {
  familie: KropFamilie
  result?: string | null
  running?: boolean
}) {
  const rå = result ?? ''
  if (familie === 'terminal') {
    // Udtrækket sker her og ikke på kaldsstedet: så kan ingen kalde kroppen med
    // det rå JSON-blob og få «{"stdout": …» vist som om det var output.
    return <TerminalKrop ud={udDel(rå)} exit={exitKode(rå, false)} running={running} />
  }
  if (familie === 'fil') {
    return <FilKrop tekst={filTekst(rå)} />
  }
  return null
}

/** Kaldsstedets genvej: familie fra værktøjsnavnet. */
export function kropFamilieFor(tool: string): KropFamilie {
  return kropFor(tool)
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  terminal: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  termScroll: { paddingRight: 8 },
  termTekst: { color: tokens.color.fg3, fontSize: 12, lineHeight: 17, fontFamily: MONO },
  termTom: { color: tokens.color.fg3, fontSize: 12, fontStyle: 'italic' },
  exit: { color: tokens.color.error, fontSize: 11, fontFamily: MONO, marginTop: 3 },

  fil: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  filScroll: { paddingRight: 8 },
  filLinje: { flexDirection: 'row' },
  filNr: {
    color: tokens.color.fg3,
    opacity: 0.5,
    fontSize: 11,
    lineHeight: 17,
    fontFamily: MONO,
    minWidth: 26,
    textAlign: 'right',
    paddingRight: 8,
  },
  filKode: { fontSize: 12, lineHeight: 17, fontFamily: MONO },
  filUdeladt: { color: tokens.color.fg3, fontSize: 11, fontStyle: 'italic', paddingVertical: 3, paddingLeft: 34 },
  filKnap: { paddingTop: 4 },
  filKnapTekst: { color: tokens.color.fg2, fontSize: 11, textDecorationLine: 'underline' },
})
