import { useCallback, useEffect, useState } from 'react'
import {
  ActivityIndicator, Alert, Pressable, ScrollView, Share, StyleSheet, Text, View
} from 'react-native'
import * as FileSystem from 'expo-file-system/legacy'
import { Download, ShieldAlert, X } from 'lucide-react-native'
import {
  deleteLayer, describeLayer, describeResult, exportUrl, fetchDataOverview,
  type DataLayer
} from '../lib/accountData'
import { useAuth } from '../state/AuthContext'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Datastyring — hvad Jarvis har om dig, og hvordan du får det væk.
 *
 * Bygget efter GDPR-mønsteret i ChatGPT-appen (set 3. sept.): eksport og
 * sletning som SELVSTÆNDIGE kort, ikke rækker begravet i en liste, og det
 * destruktive i rødt med luft omkring.
 *
 * Men sletningen er LAGVIS, hvor deres er én knap. Jarvis' hukommelse er fire
 * forskellige ting, og «slet alt» ville skjule fire meget forskellige tab: at
 * slette sine samtaler er noget andet end at få ham til at glemme hvem man er.
 *
 * Hvert lag viser sit TAL. En sletteknap uden et tal ved siden af beder folk om
 * at gætte hvad de mister.
 */
export function DataControlsScreen({ onClose }: { onClose: () => void }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const [layers, setLayers] = useState<DataLayer[] | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!config) return
    setLayers(await fetchDataOverview(config))
  }, [config])

  useEffect(() => { void load() }, [load])

  const confirmDelete = (layer: DataLayer) => {
    Alert.alert(
      `Slet ${layer.label.toLowerCase()}?`,
      `${layer.detail}\n\nDette sletter ${describeLayer(layer)}.\n\n` +
      'Dine data er krypteret — der findes ingen kopi at hente tilbage fra.',
      [
        { text: 'Annullér', style: 'cancel' },
        { text: 'Slet', style: 'destructive', onPress: () => void run(layer.key, layer.label) }
      ]
    )
  }

  const confirmDeleteAll = () => {
    Alert.alert(
      'Slet alt?',
      'Samtaler, Sansernes Arkiv, hans viden om dig og hans billede af hvem du er.\n\n' +
      'Han starter forfra. Dine data er krypteret — der findes ingen kopi at ' +
      'hente tilbage fra, heller ikke for Bjørn.',
      [
        { text: 'Annullér', style: 'cancel' },
        { text: 'Slet alt', style: 'destructive', onPress: () => void run('all', 'Alt') }
      ]
    )
  }

  const run = async (key: string, label: string) => {
    if (!config) return
    setBusy(key)
    const res = await deleteLayer(config, key)
    setBusy(null)
    await load()
    Alert.alert(label, describeResult(res))
  }

  const doExport = async () => {
    if (!config) return
    setBusy('export')
    try {
      // NED PÅ DISK, ikke ind i en streng.
      //
      // Første udgave hentede svaret med fetch().text() og delte det som
      // Share({message}). Målt på Bjørns konto er eksporten 106 MB — den ville
      // være blevet læst ind i JavaScript-hukommelsen som ÉN streng og derefter
      // sendt videre som «tekst». Appen ville i bedste fald hænge.
      //
      // downloadAsync skriver direkte til fil uden at gå gennem JS-heapen, og
      // så deler vi STIEN. Det er også den rigtige form: en eksport er en fil
      // man gemmer, ikke en besked man sender.
      const target = `${FileSystem.cacheDirectory}jarvis-data-${Date.now()}.json`
      const res = await FileSystem.downloadAsync(exportUrl(config), target, {
        headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}
      })
      if (res.status !== 200) throw new Error(String(res.status))
      await Share.share({ url: res.uri, message: 'Mine Jarvis-data' })
    } catch {
      Alert.alert('Eksport', 'Kunne ikke hente dine data. Prøv igen.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} style={styles.circle}>
          <X size={20} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        <Text style={styles.title}>Datastyring</Text>
        <View style={styles.circleGhost} />
      </View>

      <ScrollView contentContainerStyle={styles.list}>
        <Text style={styles.intro}>
          Jarvis husker fire forskellige ting om dig. Du kan slette dem hver for sig.
        </Text>
        {/* Endeligheden skal stå FØR knapperne, ikke i en dialog bagefter.
            Alle workspaces undtagen ejerens er krypterede, og der findes ingen
            læsbar kopi at fortryde fra. Det er ikke en advarsel man kan nøjes
            med at give i det øjeblik man trykker. */}
        <View style={styles.warning}>
          <ShieldAlert size={18} color={tokens.color.warn} strokeWidth={1.9} />
          <Text style={styles.warningText}>
            Dine data er krypteret, og sletning er endelig. Der findes ingen
            læsbar kopi at hente tilbage fra — heller ikke for Bjørn.
          </Text>
        </View>

        {layers === null ? (
          <ActivityIndicator color={tokens.color.accent} style={styles.loader} />
        ) : (
          layers.map((layer) => (
            <View key={layer.key} testID={`layer-${layer.key}`} style={styles.card}>
              <View style={styles.cardTop}>
                <View style={styles.cardText}>
                  <Text style={styles.cardLabel}>{layer.label}</Text>
                  <Text style={styles.cardCount}>{describeLayer(layer)}</Text>
                </View>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Slet ${layer.label}`}
                  disabled={busy !== null}
                  onPress={() => confirmDelete(layer)}
                  style={({ pressed }) => [styles.delBtn, pressed && styles.pressed]}
                >
                  {busy === layer.key ? (
                    <ActivityIndicator size="small" color={tokens.color.error} />
                  ) : (
                    <Text style={styles.delText}>Slet</Text>
                  )}
                </Pressable>
              </View>
              <Text style={styles.cardDetail}>{layer.detail}</Text>
            </View>
          ))
        )}

        <Pressable
          testID="export-data"
          accessibilityRole="button"
          disabled={busy !== null}
          onPress={() => void doExport()}
          style={({ pressed }) => [styles.wideCard, pressed && styles.pressed]}
        >
          <Download size={20} color={tokens.color.fg1} strokeWidth={1.9} />
          <Text style={styles.wideText}>
            {busy === 'export' ? 'Henter dine data…' : 'Eksportér mine data'}
          </Text>
        </Pressable>
        <Text style={styles.note}>
          Alt vi har om dig, som én JSON-fil du selv bestemmer hvor havner.
          Den kan være stor — hentes til en fil frem for at åbnes i appen.
        </Text>

        <Pressable
          testID="delete-all"
          accessibilityRole="button"
          disabled={busy !== null}
          onPress={confirmDeleteAll}
          style={({ pressed }) => [styles.dangerCard, pressed && styles.pressed]}
        >
          <Text style={styles.dangerText}>Slet alt Jarvis ved om mig</Text>
        </Pressable>
        <Text style={styles.note}>
          Alle fire lag på én gang. Han starter forfra, og det kan ikke fortrydes.
        </Text>
      </ScrollView>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0, paddingTop: 48 },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.md, paddingBottom: tokens.spacing.md
  },
  circle: {
    width: 40, height: 40, borderRadius: 20, alignItems: 'center',
    justifyContent: 'center', backgroundColor: tokens.color.bg2
  },
  circleGhost: { width: 40, height: 40 },
  title: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700' },
  list: { padding: tokens.spacing.lg, gap: tokens.spacing.sm, paddingBottom: tokens.spacing.xl },
  intro: { color: tokens.color.fg2, fontSize: 14.5, lineHeight: 21, marginBottom: tokens.spacing.sm },
  loader: { marginVertical: tokens.spacing.xl },
  warning: {
    flexDirection: 'row', gap: tokens.spacing.sm, alignItems: 'flex-start',
    backgroundColor: tokens.color.bg2, borderRadius: tokens.radius.md,
    padding: tokens.spacing.md, marginBottom: tokens.spacing.sm,
    borderLeftWidth: 3, borderLeftColor: tokens.color.warn
  },
  warningText: { color: tokens.color.fg2, fontSize: 13.5, lineHeight: 20, flexShrink: 1 },
  card: {
    backgroundColor: tokens.color.bg2, borderRadius: tokens.radius.lg,
    padding: tokens.spacing.lg, gap: 6
  },
  cardTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  cardText: { flexShrink: 1 },
  cardLabel: { color: tokens.color.fg1, fontSize: 16, fontWeight: '600' },
  cardCount: { color: tokens.color.fg2, fontSize: 13.5, marginTop: 2 },
  cardDetail: { color: tokens.color.fg3, fontSize: 13, lineHeight: 19 },
  delBtn: {
    paddingHorizontal: tokens.spacing.md, paddingVertical: 7,
    borderRadius: 16, borderWidth: 1, borderColor: tokens.color.error, minWidth: 62,
    alignItems: 'center'
  },
  delText: { color: tokens.color.error, fontSize: 14, fontWeight: '600' },
  wideCard: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.md,
    backgroundColor: tokens.color.bg2, borderRadius: tokens.radius.lg,
    padding: tokens.spacing.lg, marginTop: tokens.spacing.lg
  },
  wideText: { color: tokens.color.fg1, fontSize: 16 },
  dangerCard: {
    alignItems: 'center', backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.lg, padding: tokens.spacing.lg,
    marginTop: tokens.spacing.lg
  },
  dangerText: { color: tokens.color.error, fontSize: 16, fontWeight: '600' },
  note: { color: tokens.color.fg3, fontSize: 12.5, lineHeight: 18, paddingHorizontal: 4 },
  pressed: { opacity: 0.7 }
})
