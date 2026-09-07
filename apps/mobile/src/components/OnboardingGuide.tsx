import { useMemo, useState } from 'react'
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { statusFor, resterendeTrin, markerGennemfoert, type Tilladelse } from '../lib/onboarding'
import { bedOmTilladelse } from '../lib/permissionRequests'
import { useStyles, type Theme } from '../theme/ThemeContext'

/** Tilladelses-guiden — ét spørgsmål ad gangen, med grunden skrevet ud.
 *
 *  Al rækkefølge- og trin-logik ligger i `lib/onboarding`; her er kun fladen
 *  og kaldet til den native dialog. Det er dét der gør rækkefølgen testbar
 *  uden at mocke fire tilladelses-moduler.
 *
 *  «Ikke nu» springer trinnet over UDEN at spørge systemet. På Android kan en
 *  systemdialog kun afvises to gange, hvorefter den aldrig vises igen — at
 *  fyre den af på et trin brugeren ikke vil have, ville brænde den mulighed
 *  af for altid.
 */

export interface OnboardingGuideProps {
  visible: boolean
  /** Tilladelser der allerede er givet — de trin springes helt over. */
  alleredeGivet?: Tilladelse[]
  onDone: () => void
  /** Injiceres i tests. Standard er den ægte native dialog. */
  spoerg?: (t: Tilladelse) => Promise<boolean>
}

export function OnboardingGuide({
  visible, alleredeGivet = [], onDone, spoerg = bedOmTilladelse,
}: OnboardingGuideProps) {
  const styles = useStyles(makestyles)
  const trin = useMemo(() => resterendeTrin(alleredeGivet), [alleredeGivet])
  const [indeks, setIndeks] = useState(0)
  const [venter, setVenter] = useState(false)

  const status = statusFor(trin, indeks)

  const afslut = () => {
    void markerGennemfoert()
    onDone()
  }

  const videre = () => {
    if (indeks + 1 >= trin.length) afslut()
    else setIndeks(indeks + 1)
  }

  if (!visible) return null
  if (status.faerdig || !status.trin) {
    // Intet at spørge om (alt er givet) — så er guiden allerede gennemført.
    return null
  }

  const t = status.trin

  return (
    <Modal visible animationType="slide" onRequestClose={afslut} statusBarTranslucent>
      <View style={styles.root} testID="onboarding">
        <Text style={styles.count} testID="onboarding-count">{status.nummer} af {status.ialt}</Text>
        <View style={styles.body}>
          <Text style={styles.titel}>{t.titel}</Text>
          <Text style={styles.hvorfor}>{t.hvorfor}</Text>
          {/* Hvad man mister ved at sige nej står HER, før man vælger — ikke
              som en advarsel bagefter. */}
          <Text style={styles.uden}>Siger du nej: {t.udenDen}</Text>
        </View>
        <Pressable
          testID="onboarding-ja"
          accessibilityRole="button"
          disabled={venter}
          onPress={async () => {
            setVenter(true)
            try { await spoerg(t.tilladelse) } finally { setVenter(false) }
            // Svaret ændrer ikke hvad guiden gør: et nej er lige så gyldigt
            // som et ja, og begge fører videre.
            videre()
          }}
          style={({ pressed }) => [styles.primary, pressed && styles.pressed]}
        >
          <Text style={styles.primaryText}>Ja, spørg mig</Text>
        </Pressable>
        <Pressable
          testID="onboarding-spring"
          accessibilityRole="button"
          onPress={videre}
          style={styles.ghost}
        >
          <Text style={styles.ghostText}>Ikke nu</Text>
        </Pressable>
        <Pressable
          testID="onboarding-luk"
          accessibilityRole="button"
          accessibilityLabel="Spring guiden over"
          onPress={afslut}
          style={styles.ghost}
        >
          <Text style={styles.ghostSmall}>Spring det hele over</Text>
        </Pressable>
      </View>
    </Modal>
  )
}

const makestyles = (t: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: t.color.bg0, paddingHorizontal: 26, paddingTop: 64, paddingBottom: 40 },
  count: { color: t.color.fg3, fontSize: 13, fontVariant: ['tabular-nums'] },
  body: { flex: 1, justifyContent: 'center', gap: 14 },
  titel: { color: t.color.fg1, fontSize: 27, fontWeight: '600', lineHeight: 33 },
  hvorfor: { color: t.color.fg2, fontSize: 16, lineHeight: 23 },
  uden: { color: t.color.fg3, fontSize: 13.5, lineHeight: 20 },
  primary: {
    backgroundColor: t.color.accent, borderRadius: 26, paddingVertical: 15, alignItems: 'center',
  },
  primaryText: { color: t.color.bg0, fontSize: 16, fontWeight: '600' },
  pressed: { opacity: 0.75 },
  ghost: { paddingVertical: 13, alignItems: 'center' },
  ghostText: { color: t.color.fg2, fontSize: 15 },
  ghostSmall: { color: t.color.fg3, fontSize: 13 },
})
