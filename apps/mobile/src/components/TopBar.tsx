import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native'
import { ArrowLeft, CornerLeftUp, MoreVertical } from 'lucide-react-native'
import { SegmentedControl } from './SegmentedControl'
import { ContextRing } from './ContextRing'
import { CodeTitle } from './CodeTitle'
import { BADGE_H } from './badgeGeometri'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import type { ContextUsage, GitStatus } from '../lib/apiClient'
import { useI18n } from '../i18n/I18nContext'
import { useStickyPrompt } from '../lib/stickyPrompt'
import { useOpmaerksomhed } from '../lib/opmaerksomhed'
import { farveFor } from './OpmaerksomhedsLinje'
import { PulsVedPil } from './AnimeretPuls'

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
  /** Tryk paa titlen: aabner workspace-vaelgeren. */
  onTrykTitel?: () => void
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
// Samme tal som titel-pillen. Se badgeGeometri for hvorfor det bor udenfor.
const CIRCLE = BADGE_H
const EDGE = 14
const SEGMENT_W = 172

export function TopBar({
  mode, onModeChange, onMenu, onSync, pendingWork, syncing,
  kodeTilstand, kontekst, onMereMenu, kodeTitel = '', git = null, onTrykTitel,
}: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { t } = useI18n()
  const sticky = useStickyPrompt()
  const opm = useOpmaerksomhed()
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
          // Prikken er kun farve — tilstanden skal også kunne høres.
          accessibilityLabel={opm && opm.tilstand !== 'idle' ? `${t('common.menu')} — ${opm.etiket}` : t('common.menu')}
          onPress={onMenu}
          hitSlop={8}
          style={styles.circle}
          testID="topbar-venstre"
        >
          <ArrowLeft size={21} color={tokens.color.fg1} strokeWidth={2} />
          {/* Tilstands-hjernens puls: noget kræver dig. Farven er tilstanden
              (gul venter, rød fejlede, grøn færdig, accent arbejder); linjen
              i panelet siger hvad. Bjørn 21/9-2026: den statiske prik blev
              mærket i bevægelse — den dukker op når der sker noget, og
              forsvinder når intet kræver dig. */}
          <PulsVedPil
            synlig={Boolean(opm && opm.tilstand !== 'idle')}
            farve={farveFor(tokens, opm?.tilstand ?? 'idle')}
          />
        </Pressable>
        {kodeTilstand ? <CodeTitle titel={kodeTitel} git={git} onPress={onTrykTitel} /> : null}
      </View>

      {/* Segmentet bliver ved med at vaere ABSOLUT centreret. Dets geometri er
          maalt i ChatGPT-appen (172 dp, centrum paa skaermens midte), og den
          maaling holder kun hvis intet andet i raekken kan skubbe til den. */}
      {kodeTilstand ? null : (
        <View pointerEvents="box-none" style={styles.centerWrap}>
          <View testID="topbar-segment" style={styles.center}>
            <SegmentedControl<AppMode>
              options={[
                { value: 'snak', label: t('app.chat') },
                { value: 'arbejde', label: t('app.work'), badge: pendingWork }
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
      <View style={styles.hoejre}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('common.more')}
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
            {/* Sticky prompt som ikon (19/9-2026): tilbage til din besked, når
                den er rullet ud af syne. Den stod før som en tekst-strimmel over
                selve samtalen og dækkede de linjer man læste.

                Bjørn 21/9-2026: den laa i sin EGEN cirkel ved siden af feltet,
                saa bjaelken blev tre knapper der ligner hinanden. Nu staar den
                MELLEM ringen og prikkerne — det man laeser, det man hopper
                efter, og det man trykker, i ét felt. */}
            {sticky ? (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`Rul til din besked: ${sticky.tekst.slice(0, 140)}`}
                onPress={sticky.hop}
                hitSlop={8}
                style={styles.stickyIkon}
                testID="sticky-prompt"
              >
                <CornerLeftUp size={19} color={tokens.color.fg1} strokeWidth={2} />
              </Pressable>
            ) : null}
            <MoreVertical size={20} color={tokens.color.fg1} strokeWidth={2} />
          </>
        )}
      </Pressable>
      </View>
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
  // Sticky-hoppet bor INDE i feltet nu — ikke i sin egen cirkel. Derfor er det
  // en trykflade uden baggrund: baggrunden er feltets.
  stickyIkon: {
    width: 24,
    height: CIRCLE,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Højre felt er ÉT felt nu: ringen, sticky-hoppet og prikkerne ligger alle
  // i pillen. Her er kun pillen tilbage at holde.
  hoejre: { flexDirection: 'row', alignItems: 'center', gap: 8 },
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
