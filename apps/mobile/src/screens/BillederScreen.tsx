import { useEffect, useMemo, useState } from 'react'
import { Image, Pressable, ScrollView, StyleSheet, Text, View, useWindowDimensions } from 'react-native'
import { Sparkles, Upload, X } from 'lucide-react-native'
import { billedUrl, hentSessionBilleder, type SessionBillede } from '../lib/billederApi'
import { aabnUdgivetFil } from '../lib/aabnFil'
import { useAuth } from '../state/AuthContext'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { StatusState } from '../components/StatusState'

/**
 * Billederne i denne samtale — Jarvis' egne og ens egne, i ét gitter.
 *
 * ## Hvorfor ophavet er mærket
 *
 * «Har han lavet det, eller sendte jeg det?» er det første man vil vide når
 * man ser et billede igen uger senere, og det er ikke til at se på selve
 * billedet. Mærket sidder i hjørnet frem for som to adskilte lister, fordi
 * man leder efter billedet — ikke efter kategorien.
 */
export function BillederScreen({
  sessionId, onClose,
}: { sessionId: string; onClose: () => void }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const { width } = useWindowDimensions()
  const [items, setItems] = useState<SessionBillede[] | null>(null)
  const [fejl, setFejl] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    hentSessionBilleder(config, sessionId)
      .then((n) => { if (alive) { setItems(n); setFejl(false) } })
      .catch(() => { if (alive) { setItems([]); setFejl(true) } })
    return () => { alive = false }
  }, [config, sessionId])

  // Tre i bredden, med luft. Regnes ud fra den FAKTISKE bredde frem for et
  // fast tal: en foldbar eller landskab ville ellers give tre smalle striber.
  const kant = useMemo(() => Math.floor((width - 16 * 2 - 8 * 2) / 3), [width])
  const headers = config?.authToken
    ? { Authorization: `Bearer ${config.authToken}` }
    : undefined

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} style={styles.circle}>
          <X size={20} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        <Text style={styles.title}>Billeder</Text>
        <View style={styles.circleGhost} />
      </View>

      {items === null ? (
        <StatusState title="Henter billeder" loading />
      ) : items.length === 0 ? (
        <StatusState
          title={fejl ? 'Kunne ikke hente billederne' : 'Ingen billeder i denne samtale'}
          // Skelner FEJL fra TOMT. De to ser ens ud paa skaermen og betyder
          // stik modsat: proev igen, eller lad vaere.
          detail={fejl
            ? 'Prøv igen om lidt.'
            : 'Billeder du sender, og dem Jarvis laver, samles her.'}
        />
      ) : (
        <ScrollView contentContainerStyle={styles.gitter}>
          {items.map((b) => (
            <Pressable
              key={b.attachmentId}
              testID={`billede-${b.attachmentId}`}
              accessibilityRole="button"
              accessibilityLabel={`${b.filnavn}, ${b.lavetAfJarvis ? 'lavet af Jarvis' : 'uploadet'}`}
              onPress={() => {
                if (!config) return
                void aabnUdgivetFil(config, billedUrl(config, b.attachmentId), b.filnavn, b.mime)
                  .catch(() => undefined)
              }}
              style={[styles.felt, { width: kant, height: kant }]}
            >
              <Image
                source={{ uri: billedUrl(config!, b.attachmentId), headers }}
                style={styles.billede}
                resizeMode="cover"
              />
              <View style={styles.maerke}>
                {b.lavetAfJarvis
                  ? <Sparkles size={11} color={tokens.color.accent} strokeWidth={2} />
                  : <Upload size={11} color={tokens.color.fg2} strokeWidth={2} />}
              </View>
            </Pressable>
          ))}
        </ScrollView>
      )}
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 14, paddingVertical: 8,
  },
  circle: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: tokens.color.bgFloat, alignItems: 'center', justifyContent: 'center',
  },
  circleGhost: { width: 40, height: 40 },
  title: { color: tokens.color.fg1, fontSize: 16, fontWeight: '600' },
  gitter: {
    flexDirection: 'row', flexWrap: 'wrap', gap: 8,
    paddingHorizontal: 16, paddingBottom: 32,
  },
  felt: { borderRadius: 12, overflow: 'hidden', backgroundColor: tokens.color.bg2 },
  billede: { width: '100%', height: '100%' },
  maerke: {
    position: 'absolute', top: 5, right: 5,
    width: 20, height: 20, borderRadius: 10,
    backgroundColor: 'rgba(0,0,0,0.55)',
    alignItems: 'center', justifyContent: 'center',
  },
})
