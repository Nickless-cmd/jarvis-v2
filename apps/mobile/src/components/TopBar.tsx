import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native'
import { ArrowLeft, MoreVertical } from 'lucide-react-native'
import { SegmentedControl } from './SegmentedControl'
import { ContextRing } from './ContextRing'
import { CodeTitle } from './CodeTitle'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import type { ContextUsage, GitStatus } from '../lib/apiClient'

export type AppMode = 'snak' | 'arbejde'

interface Props {
  mode: AppMode
  onModeChange: (next: AppMode) => void
  onMenu: () => void
  onSync: () => void
  pendingWork?: boolean
  syncing?: boolean
  /** Code-fladen: segmentet siger «Code» i stedet for «Snak». */
  kodeTilstand?: boolean
  /** Kontekst-fyld. Ringen tegner sig selv væk når den er null. */
  kontekst?: ContextUsage | null
  /** Åbner tre-prik menuen. Opdatér bor derinde nu. */
  onMereMenu?: () => void
  /** Code-fladens titel og kontekst. Kun brugt når kodeTilstand er sat. */
  kodeTitel?: string
  git?: GitStatus | null
}

/**
 * Appens øverste bjælke — geometrien er MÅLT i ChatGPT-appen på Bjørns enhed.
 *
 * DENSITETEN ER 2,625 — IKKE 3,0. Telefonen har `Override density: 420` mod
 * de fysiske 480 (display-zoom, en helt almindelig indstilling). Første forsøg
 * regnede med 3,0 og blev derfor 14 % for lille hele vejen: jeg satte 150 dp
 * og målte 394 px tilbage, hvilket kun går op ved 2,625. Måler man px i et
 * skærmbillede, skal man kende enhedens FAKTISKE densitet — ikke panelets.
 *
 *   venstre cirkel   115 px  →  44 dp
 *   segmented        452 px  → 172 dp, centrum x=539,5 = SKÆRMENS MIDTE
 *   kantmargen        37 px  →  14 dp
 *
 * BEVIDST AFVIGELSE: cirklerne er sat til 40 dp og bjælken gjort lavere, fordi
 * Bjørn bad om «et nummer mindre». Segmentets bredde og centrering følger
 * stadig målingen — det var dét der sad skævt.
 *
 * Kontrollen er ABSOLUT centreret, ikke flex-strakt mellem cirklerne. Med flex
 * bliver midten et gennemsnit af de to knappers bredde — og den var synligt
 * skæv.
 */
const CIRCLE = 40
const EDGE = 14
const SEGMENT_W = 172

export function TopBar({
  mode, onModeChange, onMenu, onSync, pendingWork, syncing,
  kodeTilstand, kontekst, onMereMenu, kodeTitel = '', git = null,
}: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <View style={styles.bar}>
      {/* Pilen og titlen hoerer SAMMEN, i ét spor til venstre. Titlen laa
          foerst centreret - samme plads som segmentet - men det er to
          forskellige slags oplysning: segmentet er en KONTAKT man sigter
          efter, og titlen er en ETIKET man laeser. En etiket midt paa
          skaermen tvinger oejet til at soege den; laengst til venstre
          begynder man der alligevel.

          ÉN pil, uanset flade. Foer skiftede ikonet mellem hamburger og pil,
          og de to foerte to forskellige steder hen - saa den samme plads
          gjorde to ting afhaengigt af en tilstand man ikke kunne se paa
          knappen. Vejen ud af code-fladen bor i menuen, sammen med vejen
          ind. */}
      <View style={styles.venstre}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Menu"
          onPress={onMenu}
          hitSlop={8}
          style={styles.circle}
          testID="topbar-venstre"
        >
          <ArrowLeft size={21} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        {kodeTilstand ? <CodeTitle titel={kodeTitel} git={git} /> : null}
      </View>

      {/* Segmentet bliver ved med at vaere ABSOLUT centreret. Dets geometri er
          maalt i ChatGPT-appen (172 dp, centrum paa skaermens midte), og den
          maaling holder kun hvis intet andet i raekken kan skubbe til den. */}
      {kodeTilstand ? null : (
        <View pointerEvents="box-none" style={styles.centerWrap}>
          <View testID="topbar-segment" style={styles.center}>
            <SegmentedControl<AppMode>
              options={[
                { value: 'snak', label: 'Snak' },
                { value: 'arbejde', label: 'Arbejde', badge: pendingWork }
              ]}
              value={mode}
              onChange={onModeChange}
            />
          </View>
        </View>
      )}

      {/* Hoejre felt: ringen FOERST, saa prikkerne - i samme felt. Ringen er
          det man laeser, prikkerne er det man trykker. Star de hver for sig
          bliver bjaelken til tre knapper der ligner hinanden. */}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Mere"
        accessibilityState={{ busy: Boolean(syncing) }}
        onPress={onMereMenu ?? onSync}
        hitSlop={8}
        // EGEN stil frem for [circle, pille]. Begge virker - StyleSheet.flatten
        // lader `width: undefined` fjerne en tidligere bredde - men to stilarter
        // der delvist ophaever hinanden er svaerere at laese end to der hver
        // beskriver én form.
        style={kontekst ? styles.pille : styles.circle}
        testID="topbar-mere"
      >
        {syncing ? (
          <ActivityIndicator size="small" color={tokens.color.fg1} />
        ) : (
          <>
            <ContextRing brug={kontekst ?? null} />
            <MoreVertical size={20} color={tokens.color.fg1} strokeWidth={2} />
          </>
        )}
      </Pressable>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: EDGE,
    paddingVertical: 6,
    // Halvgennemsigtig: tråden ANES bagved frem for at blive klippet af
    // en massiv bjælke. Det er dét der giver følelsen af ét sammenhængende
    // rum i stedet for tre etager.
    backgroundColor: tokens.color.scrim
  },
  // Fylder hele bjælken og lader tryk gå igennem til cirklerne udenfor.
  centerWrap: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center'
  },
  center: { width: SEGMENT_W },
  // Pil + titel som ét spor. `flexShrink` frem for en fast bredde: titlen
  // skal give plads til hoejre felt naar den er lang, ikke skubbe det ud
  // over kanten. `minWidth: 0` er det der faktisk tillader det - uden den
  // naegter en flex-boks at blive smallere end sit indhold.
  venstre: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexShrink: 1,
    minWidth: 0,
  },
  // Feltet vokser til en pille naar ringen er der. Polstringen er sat efter
  // ChatGPT-appens eget hoejre felt (Bjoerns skaermbillede 12/9-2026): der er
  // luft HELE vejen rundt om begge ikoner. Foerste forsoeg havde 9 dp og 4 dp
  // mellemrum, og saa roerte ringen kanten - baggrunden saa ud til at ligge
  // bag halvdelen af indholdet frem for at daekke det.
  //
  // Ingen `width`: indholdet bestemmer bredden. Segmentet er ABSOLUT centreret,
  // saa den maalte geometri i midten staar stille uanset hvor bred pillen er.
  pille: {
    height: CIRCLE,
    borderRadius: CIRCLE / 2,
    backgroundColor: tokens.color.bgFloat,
    ...tokens.elevation,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    paddingHorizontal: 13,
  },
  circle: {
    width: CIRCLE,
    height: CIRCLE,
    borderRadius: CIRCLE / 2,
    backgroundColor: tokens.color.bgFloat,
    ...tokens.elevation,
    alignItems: 'center',
    justifyContent: 'center'
  }
})
