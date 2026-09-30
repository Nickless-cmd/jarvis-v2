import { useEffect, useState } from 'react'
import { Image, Platform, Pressable, ScrollView, StyleSheet, Text, View, type StyleProp, type TextStyle } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { highlight, type Span, type SpanKind } from '../lib/highlight'
import { ANSI_FARVER, ansiStykker, ryd, type AnsiStil } from '../lib/ansiTekst'
import {
  filTekst, exitKode, kropFor, listePoster, udDel,
  mindeIndhold, webTraef, spoergsmaalIndhold, opgavePoster, skrivBesked, fejlBesked,
  billedeIndhold, agentIdFra,
  type KropFamilie,
} from '../lib/krop'
import { useAuthOptional } from '../state/AuthContext'
import { hentAgentKald } from '../lib/apiClient'
import { hentTilCache } from './AuthImage'

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

/* ══ Liste ══════════════════════════════════════════════════════════════ */

/** Så mange punkter tegnes før listen klippes — resten er ét tryk væk. */
export const MAX_PUNKTER = 12

/**
 * Liste-kroppen: hitlister, tabeller, oversigter.
 *
 * Desk har samme form (`Liste` i `raekkeKroppe.tsx`), og den er målt: stier er
 * **sans**, ikke mono. Derfor ingen `MONO` her — det er den ene forskel fra
 * terminal- og fil-kroppene, og den er hentet fra kilden og ikke gættet.
 *
 * Klippet er LOKALT, som i fil-kroppen: punkterne ligger allerede i hukommelsen,
 * så «Vis alle» folder dem ud uden et kald. Vi klipper frem for at scrolle, fordi
 * en indlejret lodret `ScrollView` inde i trådens liste giver to scrol-flader
 * oven på hinanden — og den slåskamp er der ingen der vinder.
 */
export function ListeKrop({ poster }: { poster: { p?: string; v: string }[] }) {
  const styles = useStyles(makestyles)
  const [alt, setAlt] = useState(false)
  if (!poster.length) return null
  const klippet = !alt && poster.length > MAX_PUNKTER
  const vist = klippet ? poster.slice(0, MAX_PUNKTER) : poster
  return (
    <View style={styles.liste} testID="krop-liste">
      {vist.map((r, i) => (
        <View key={i} style={styles.listePunkt}>
          {r.p ? <Text style={styles.listeP} numberOfLines={1}>{r.p}</Text> : null}
          <Text style={styles.listeV} numberOfLines={2}>{r.v}</Text>
        </View>
      ))}
      {klippet ? (
        <Pressable
          onPress={() => setAlt(true)}
          testID="krop-vis-alle-punkter"
          accessibilityRole="button"
          hitSlop={8}
          style={styles.listeKnap}
        >
          <Text style={styles.listeKnapTekst}>Vis alle {poster.length}</Text>
        </Pressable>
      ) : null}
    </View>
  )
}

/* ══ Delt klip-geometri ═════════════════════════════════════════════════ */

/**
 * Hoved, hale og et tal for det udeladte — for en tekst-krop.
 *
 * Fil-kroppen har sin egen (den skal vise linjenumre), men minde, skriv og
 * spoergsmaal deler den samme form. Udfoldningen er LOKAL: teksten ligger
 * allerede i hukommelsen, saa «Vis alle» koster intet kald. Det er forskellen
 * fra terminal-kroppens spill-knap, som henter noget serveren har.
 */
function LangTekst({ tekst, stil, knapTestID, testID }: {
  tekst: string
  stil: StyleProp<TextStyle>
  knapTestID: string
  testID: string
}) {
  const styles = useStyles(makestyles)
  const [alt, setAlt] = useState(false)
  const alle = tekst ? tekst.replace(/\n$/, '').split('\n') : []
  const klippet = !alt && alle.length > MAX_LINJER
  const hoved = klippet ? alle.slice(0, MAX_LINJER - HALE_LINJER) : alle
  const hale = klippet ? alle.slice(alle.length - HALE_LINJER) : []
  const udeladt = alle.length - hoved.length - hale.length
  return (
    <View testID={testID}>
      <Text style={stil} selectable>{hoved.join('\n')}</Text>
      {klippet ? (
        <>
          <Text style={styles.udeladt}>{udeladt} linjer udeladt i midten</Text>
          <Text style={stil} selectable>{hale.join('\n')}</Text>
          <Pressable
            onPress={() => setAlt(true)}
            testID={knapTestID}
            accessibilityRole="button"
            hitSlop={8}
            style={styles.knap}
          >
            <Text style={styles.knapTekst}>Vis alle {alle.length} linjer</Text>
          </Pressable>
        </>
      ) : null}
    </View>
  )
}

/* ══ Minde ══════════════════════════════════════════════════════════════ */

/**
 * Et minde der blev skrevet — hvad der blev husket, ikke id'et det fik.
 *
 * `remember_this` svarer kun `{id}` og `memory_upsert_section` med prosa
 * («MEMORY.md section 'X' added successfully.»). Indholdet staar KUN i
 * argumenterne, saa kroppen bygges af dem. Uden den viste raekken `id brn_…`:
 * beviset paa skrivningen i stedet for det der blev skrevet (Bjørn 23/9-2026).
 */
export function MindeKrop({ titel, meta, tekst }: { titel: string; meta: string; tekst: string }) {
  const styles = useStyles(makestyles)
  return (
    <View style={styles.minde} testID="krop-minde">
      <View style={styles.mindeHoved}>
        <Text style={styles.mindeTitel} numberOfLines={2}>{titel}</Text>
        {meta ? <Text style={styles.mindeMeta}>{meta}</Text> : null}
      </View>
      <LangTekst tekst={tekst} stil={styles.mindeTekst} knapTestID="krop-minde-vis-alle" testID="krop-minde-tekst" />
    </View>
  )
}

/* ══ Web ════════════════════════════════════════════════════════════════ */

/**
 * Soegetraef — domaenet over titlen.
 *
 * Desk har samme form (`Web`). Domaenet staar som en lille linje over titlen,
 * saa man kan se hvor et traef kommer fra uden at laese hele titlen.
 */
export function WebKrop({ traef }: { traef: { dom: string; titel: string }[] }) {
  const styles = useStyles(makestyles)
  const [alt, setAlt] = useState(false)
  if (!traef.length) return null
  const klippet = !alt && traef.length > MAX_PUNKTER
  const vist = klippet ? traef.slice(0, MAX_PUNKTER) : traef
  return (
    <View style={styles.web} testID="krop-web">
      {vist.map((t, i) => (
        <View key={i} style={styles.webTraef}>
          {t.dom ? <Text style={styles.webDom} numberOfLines={1}>{t.dom}</Text> : null}
          <Text style={styles.webTitel} numberOfLines={3}>{t.titel}</Text>
        </View>
      ))}
      {klippet ? (
        <Pressable
          onPress={() => setAlt(true)}
          testID="krop-web-vis-alle"
          accessibilityRole="button"
          hitSlop={8}
          style={styles.knap}
        >
          <Text style={styles.knapTekst}>Vis alle {traef.length}</Text>
        </Pressable>
      ) : null}
    </View>
  )
}

/* ══ Spørgsmål ══════════════════════════════════════════════════════════ */

/**
 * Spoergsmaalet i argumenterne, svaret i resultatet.
 *
 * `pause_and_ask` stiller et spoergsmaal og faar et svar. Uden denne form stod
 * spoergsmaalet ulæst i argumenterne og svaret som raa JSON.
 */
export function SpoergsmaalKrop({ q, svar }: { q: string; svar: string }) {
  const styles = useStyles(makestyles)
  return (
    <View style={styles.spoergsmaal} testID="krop-spoergsmaal">
      {q ? <Text style={styles.spQ} selectable>{q}</Text> : null}
      {svar ? (
        <View style={styles.spSvar}>
          <Text style={styles.spMrk}>svar</Text>
          <Text style={styles.spTekst} selectable>{svar}</Text>
        </View>
      ) : null}
    </View>
  )
}

/* ══ Opgaveliste ════════════════════════════════════════════════════════ */

/**
 * Opgavelisten — ☑ færdig, ◐ i gang, ☐ venter.
 *
 * Formen er LINJER, ikke felter: en opgaveliste er en tilstand man læser ned
 * ad, og rækkefølgen er arbejdets. Den aktive linje fremhæves, for den er dét
 * man leder efter. Desk har samme form (`Opgaveliste`).
 */
export function OpgaveKrop({ poster }: { poster: { tekst: string; status: string }[] }) {
  const styles = useStyles(makestyles)
  if (!poster.length) return null
  const faerdige = poster.filter((p) => p.status === 'completed').length
  const igang = poster.filter((p) => p.status === 'in_progress').length
  return (
    <View style={styles.opgave} testID="krop-opgave">
      <Text style={styles.opgaveHoved}>
        {faerdige} af {poster.length}
        {igang > 0 ? ` · ${igang} i gang` : ''}
      </Text>
      {poster.map((p, i) => (
        <View key={i} style={styles.opgaveLinje}>
          <Text style={[styles.opgaveG, p.status === 'in_progress' ? styles.opgaveGnu : null]}>
            {p.status === 'completed' ? '☑' : p.status === 'in_progress' ? '◐' : '☐'}
          </Text>
          <Text style={[styles.opgaveTekst, p.status === 'completed' ? styles.opgaveFaerdig : null]}>{p.tekst}</Text>
        </View>
      ))}
    </View>
  )
}

/* ══ Rå data ════════════════════════════════════════════════════════════ */

/**
 * Kaldets IN og OUT, bag ét tryk.
 *
 * Desk har samme form (`Raadata`): den viste form er et RESUMÉ, og de rå data
 * skal stadig kunne naas — ellers kunne man ikke se hvad et kald faktisk fik
 * og gav. Folden starter LUKKET: resuméet er det man læser, rådata er det man
 * slår op.
 */
export function Raadata({ ind, ud }: { ind: string; ud: string }) {
  const styles = useStyles(makestyles)
  const [aaben, setAaben] = useState(false)
  return (
    <View style={styles.raadata} testID="krop-raadata">
      <Pressable
        onPress={() => setAaben((v) => !v)}
        accessibilityRole="button"
        accessibilityState={{ expanded: aaben }}
        hitSlop={8}
        testID="krop-raadata-knap"
      >
        <Text style={styles.raadataKnap}>{aaben ? 'Skjul rå data' : 'Vis rå data'}</Text>
      </Pressable>
      {aaben ? (
        <>
          <View style={styles.par}>
            <Text style={styles.mrk}>IN</Text>
            <Text style={styles.parTekst} selectable>{ind}</Text>
          </View>
          <View style={styles.par}>
            <Text style={styles.mrk}>OUT</Text>
            <Text style={styles.parTekst} selectable>{ud}</Text>
          </View>
        </>
      ) : null}
    </View>
  )
}

/* ══ Skriv ══════════════════════════════════════════════════════════════ */

/**
 * En skrivning der blev BEKRÆFTET — ikke vist.
 *
 * `publish_file`, `notify_user` og `verify_file_contains` svarer med beviset:
 * en stoerrelse, en URL, et antal. Indholdet staar i argumenterne. Kroppen
 * viser bekræftelsen og lader rådata vaere ét tryk væk.
 */
export function SkrivKrop({ besked, ind, ud }: { besked: string; ind: string; ud: string }) {
  const styles = useStyles(makestyles)
  return (
    <View style={styles.skriv} testID="krop-skriv">
      <Text style={styles.skrivBesked} selectable>{besked}</Text>
      <Raadata ind={ind} ud={ud} />
    </View>
  )
}

/* ══ Fejl ═══════════════════════════════════════════════════════════════ */

/**
 * Et kald der ikke gik igennem — beskeden, ikke den tomme form.
 *
 * En afvist handling (`approval_needed`, `guard_blocked`) eller en fejlstatus
 * skal vise HVORFOR. Uden grenen viste et afvist bash-kald sin tomme stdout og
 * et exit-tal, som om det var koert.
 */
export function FejlKrop({ besked, ind, ud }: { besked: string; ind: string; ud: string }) {
  const styles = useStyles(makestyles)
  return (
    <View style={styles.fejl} testID="krop-fejl">
      <Text style={styles.fejlBesked} selectable>{besked || 'Kaldet kunne ikke gennemføres'}</Text>
      <Raadata ind={ind} ud={ud} />
    </View>
  )
}

/* ══ Billede ════════════════════════════════════════════════════════════ */

/**
 * Et billede — hentet gennem den hvidlistede rute.
 *
 * Stien er Jarvis' EGEN, ikke telefonens: et skaermbillede tages paa serveren.
 * Derfor gaar den gennem `/visning/billede` (samme vej som `ImageAnalysisCard`
 * og desk's raekkevisning) frem for at pege `<Image>` paa en fil telefonen
 * ikke har. En http-URL bruges derimod direkte — den ligger allerede et sted
 * vi kan naa.
 */
export function BilledeKrop({ sti, navn, meta, spoergsmaal, tekst }: {
  sti: string; navn: string; meta: string; spoergsmaal: string; tekst: string
}) {
  const styles = useStyles(makestyles)
  const { config } = useAuthOptional()
  const [lokal, setLokal] = useState<string | null>(null)
  useEffect(() => {
    setLokal(null)
    if (!sti) return
    if (/^https?:\/\//i.test(sti)) { setLokal(sti); return }
    if (!config) return
    let levende = true
    // Hele stien er cache-navn: `hentTilCache` saniterer selv, og to billeder
    // med samme basnavn i hver sin mappe maa ikke dele fil.
    void hentTilCache(config, `/visning/billede?sti=${encodeURIComponent(sti)}`, sti)
      .then((p) => { if (levende) setLokal(p) })
      // Tavs: maa stien ikke vises, staar navnet — praecis som før.
      .catch(() => { if (levende) setLokal(null) })
    return () => { levende = false }
  }, [config?.apiBaseUrl, config?.authToken, sti])
  return (
    <View style={styles.billede} testID="krop-billede">
      <View style={styles.billedeHoved}>
        {lokal ? (
          <Image testID="krop-billede-img" source={{ uri: lokal }} style={styles.billedeImg} resizeMode="cover" />
        ) : null}
        <View style={styles.billedeTekstBlok}>
          <Text style={styles.billedeNavn} numberOfLines={1}>{navn || 'Billede'}</Text>
          {meta ? <Text style={styles.billedeMeta}>{meta}</Text> : null}
        </View>
      </View>
      {spoergsmaal ? <Text style={styles.billedeSp} selectable>{spoergsmaal}</Text> : null}
      {tekst ? <Text style={styles.billedeTekst} selectable>{tekst}</Text> : null}
    </View>
  )
}

/* ══ Underagent ═════════════════════════════════════════════════════════ */

/**
 * Underagentens egne kald — hentet naar rækken foldes ud.
 *
 * `scout_agent` svarer med agentens id. Dens otte kald ligger bag et
 * endepunkt der allerede findes; uden kroppen stod rækken med et resumé mens
 * agentens arbejde laa uroert. Kroppen monteres foerst naar folden aabnes, saa
 * `useEffect` her er dovent af sig selv — samme greb som desk's `Underagent`.
 */
export function UnderagentKrop({ agentId, resultat }: { agentId: string; resultat: string }) {
  const styles = useStyles(makestyles)
  const { config } = useAuthOptional()
  const [kald, setKald] = useState<Awaited<ReturnType<typeof hentAgentKald>> | null>(null)
  const [fejl, setFejl] = useState(false)
  useEffect(() => {
    if (!config) return
    let levende = true
    hentAgentKald(config, agentId)
      .then((k) => { if (levende) setKald(k) })
      .catch(() => { if (levende) setFejl(true) })
    return () => { levende = false }
  }, [config?.apiBaseUrl, config?.authToken, agentId])
  return (
    <View style={styles.underagent} testID="krop-underagent">
      {resultat ? <Text style={styles.uaResume} selectable>{resultat}</Text> : null}
      {/* Uden config kan vi ikke spoerge — sig det, frem for en tom liste der
          ligner «agenten gjorde ingenting». */}
      {!config ? <Text style={styles.uaTom}>Ingen forbindelse — kan ikke hente agentens kald.</Text>
        : fejl ? <Text style={styles.uaTom}>Agentens kald kunne ikke hentes.</Text>
          : kald === null ? <Text style={styles.uaTom}>Henter agentens kald…</Text>
            : kald.length === 0 ? <Text style={styles.uaTom}>Agenten kaldte ingen værktøjer.</Text>
              : (
                <View testID="krop-underagent-liste">
                  <Text style={styles.uaHoved}>{kald.length} kald i underagenten</Text>
                  {kald.map((k, i) => (
                    <View key={i} style={styles.uaKald}>
                      <Text style={styles.uaNavn} numberOfLines={1}>{k.tool_name || 'tool'}</Text>
                      <Text style={styles.uaArg} numberOfLines={2}>{(k.arguments_json || '').slice(0, 120)}</Text>
                    </View>
                  ))}
                </View>
              )}
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
  familie, result, input, running = false,
}: {
  familie: KropFamilie
  result?: string | null
  /** Kaldets argumenter — nødvendige for minde, spørgsmål og skriv. */
  input?: unknown
  running?: boolean
}) {
  const rå = result ?? ''
  const ind = typeof input === 'string' ? input : input ? JSON.stringify(input, null, 2) : ''
  if (familie === 'terminal') {
    // Udtrækket sker her og ikke på kaldsstedet: så kan ingen kalde kroppen med
    // det rå JSON-blob og få «{"stdout": …» vist som om det var output.
    return <TerminalKrop ud={udDel(rå)} exit={exitKode(rå, false)} running={running} />
  }
  if (familie === 'fil') {
    return <FilKrop tekst={filTekst(rå)} />
  }
  if (familie === 'liste') {
    // `listePoster` giver null når der hverken er en liste eller tekst-linjer at
    // vise. Så tegner vi INTET — kaldsstedet falder til den rå tekst, og vi står
    // ikke med en tom ramme der ligner en fejl.
    const poster = listePoster(rå)
    return poster ? <ListeKrop poster={poster} /> : null
  }
  if (familie === 'minde') {
    const m = mindeIndhold(input)
    return m ? <MindeKrop titel={m.titel} meta={m.meta} tekst={m.tekst} /> : null
  }
  if (familie === 'web') {
    const traef = webTraef(rå)
    return traef ? <WebKrop traef={traef} /> : null
  }
  if (familie === 'spoergsmaal') {
    const s = spoergsmaalIndhold(input, rå)
    return s ? <SpoergsmaalKrop q={s.q} svar={s.svar} /> : null
  }
  if (familie === 'opgave') {
    const poster = opgavePoster(rå)
    return poster ? <OpgaveKrop poster={poster} /> : null
  }
  if (familie === 'skriv') {
    return <SkrivKrop besked={skrivBesked(rå)} ind={ind} ud={udDel(rå)} />
  }
  if (familie === 'fejl') {
    return <FejlKrop besked={fejlBesked(rå)} ind={ind} ud={udDel(rå)} />
  }
  if (familie === 'billede') {
    const b = billedeIndhold(input, rå)
    return b ? <BilledeKrop sti={b.sti} navn={b.navn} meta={b.meta} spoergsmaal={b.spoergsmaal} tekst={b.tekst} /> : null
  }
  if (familie === 'underagent') {
    const id = agentIdFra(rå)
    return id ? <UnderagentKrop agentId={id} resultat={udDel(rå)} /> : null
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

  liste: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  listePunkt: { flexDirection: 'row', gap: 6, paddingVertical: 2 },
  // Ingen `MONO`: desk målte at stier i en hitliste er sans, ikke mono.
  // Præfikset dæmpes som filnummeret i fil-kroppen, så de to kroppe taler
  // samme sprog om hvad der er sted og hvad der er indhold.
  listeP: { color: tokens.color.fg3, fontSize: 12, lineHeight: 17, flexShrink: 0, maxWidth: '55%' },
  listeV: { color: tokens.color.fg2, fontSize: 13, lineHeight: 17, flex: 1 },
  listeKnap: { paddingTop: 4 },
  listeKnapTekst: { color: tokens.color.fg2, fontSize: 11, textDecorationLine: 'underline' },

  /* Delt klip-geometri */
  udeladt: { color: tokens.color.fg3, fontSize: 11, fontStyle: 'italic', paddingVertical: 3 },
  knap: { paddingTop: 4 },
  knapTekst: { color: tokens.color.fg2, fontSize: 11, textDecorationLine: 'underline' },

  /* Minde */
  minde: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  mindeHoved: { marginBottom: 3 },
  mindeTitel: { color: tokens.color.fg1, fontSize: 13, fontWeight: '600' },
  mindeMeta: { color: tokens.color.fg3, fontSize: 11, marginTop: 1 },
  mindeTekst: { color: tokens.color.fg2, fontSize: 12, lineHeight: 17 },

  /* Web */
  web: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  webTraef: { paddingVertical: 3 },
  webDom: { color: tokens.color.fg3, fontSize: 11 },
  webTitel: { color: tokens.color.fg2, fontSize: 13, lineHeight: 18 },

  /* Spørgsmål */
  spoergsmaal: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  spQ: { color: tokens.color.fg1, fontSize: 13, lineHeight: 18 },
  spSvar: { flexDirection: 'row', gap: 6, marginTop: 4 },
  spMrk: { color: tokens.color.fg3, fontSize: 11, marginTop: 2 },
  spTekst: { color: tokens.color.fg2, fontSize: 13, lineHeight: 18, flex: 1 },

  /* Opgaveliste */
  opgave: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  opgaveHoved: { color: tokens.color.fg3, fontSize: 11, marginBottom: 3 },
  opgaveLinje: { flexDirection: 'row', gap: 6, paddingVertical: 1 },
  opgaveG: { color: tokens.color.fg3, fontSize: 13 },
  opgaveGnu: { color: tokens.color.accent },
  opgaveTekst: { color: tokens.color.fg2, fontSize: 13, lineHeight: 18, flex: 1 },
  opgaveFaerdig: { color: tokens.color.fg3, textDecorationLine: 'line-through' },

  /* Rå data */
  raadata: { marginTop: 4 },
  raadataKnap: { color: tokens.color.fg2, fontSize: 11, textDecorationLine: 'underline' },
  par: { flexDirection: 'row', gap: 8, marginTop: 4 },
  mrk: { color: tokens.color.fg3, fontSize: 10, fontFamily: MONO, minWidth: 26, paddingTop: 1 },
  parTekst: { color: tokens.color.fg2, fontSize: 12, lineHeight: 16, fontFamily: MONO, flex: 1 },

  /* Skriv */
  skriv: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  skrivBesked: { color: tokens.color.fg2, fontSize: 13, lineHeight: 18 },

  /* Fejl */
  fejl: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.error,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  fejlBesked: { color: tokens.color.error, fontSize: 13, lineHeight: 18 },

  /* Billede */
  billede: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  billedeHoved: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  billedeImg: { width: 64, height: 64, borderRadius: 4, backgroundColor: tokens.color.bg2 },
  billedeTekstBlok: { flex: 1 },
  billedeNavn: { color: tokens.color.fg1, fontSize: 13, fontWeight: '600' },
  billedeMeta: { color: tokens.color.fg3, fontSize: 11, marginTop: 1 },
  billedeSp: { color: tokens.color.fg2, fontSize: 12, fontStyle: 'italic', marginTop: 4 },
  billedeTekst: { color: tokens.color.fg2, fontSize: 12, lineHeight: 17, marginTop: 4 },

  /* Underagent */
  underagent: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.line,
    paddingLeft: 8,
    marginLeft: 6,
    marginTop: 2,
    marginBottom: 2,
  },
  uaResume: { color: tokens.color.fg2, fontSize: 12, lineHeight: 17 },
  uaTom: { color: tokens.color.fg3, fontSize: 12, fontStyle: 'italic', marginTop: 4 },
  uaHoved: { color: tokens.color.fg3, fontSize: 11, marginTop: 6, marginBottom: 2 },
  uaKald: { flexDirection: 'row', gap: 6, paddingVertical: 2 },
  uaNavn: { color: tokens.color.fg1, fontSize: 12, fontFamily: MONO, flexShrink: 0, maxWidth: '45%' },
  uaArg: { color: tokens.color.fg3, fontSize: 11, fontFamily: MONO, flex: 1 },
})
