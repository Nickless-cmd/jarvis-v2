import { useEffect, useState } from 'react'
import { ActivityIndicator, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { ChevronLeft, Folder, HardDrive, Monitor, Check } from 'lucide-react-native'
import {
  forael, hentServerRoedder, hentTrae, underSti,
  type ServerRod, type TraePost, type WsArt,
} from '../lib/workspaceApi'
import type { ApiConfig } from '../lib/types'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Hvor skal Jarvis arbejde? — bag et tryk på titlen i code-headeren.
 *
 * ## To slags steder, og hvorfor de ser forskellige ud
 *
 * Server-rødderne er en KORT, LUKKET liste: rollen bestemmer hvad man må se,
 * og der er tre af dem. Din egen computer er et helt filsystem, og det kan
 * man kun finde rundt i ved at gå. Derfor knapper i den ene halvdel og en
 * browser i den anden — ikke fordi det er to forskellige funktioner, men
 * fordi det er to forskellige mængder.
 *
 * ## Hvorfor man ikke kan vælge en fil
 *
 * Kun mapper kan vælges; filer vises i grå. De er med for at man kan se at
 * man står det rigtige sted — en mappe uden indhold og en forkert mappe ser
 * ellers ens ud.
 */
export function WorkspacePicker({
  aaben, onClose, config, nuvaerende, onVaelg,
}: {
  aaben: boolean
  onClose: () => void
  config: ApiConfig
  /** Det sessionen er bundet til nu — typisk hvad desk sidst brugte. */
  nuvaerende: { kind: WsArt; root: string } | null
  onVaelg: (kind: WsArt, root: string) => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [roedder, setRoedder] = useState<ServerRod[] | null>(null)
  const [sti, setSti] = useState<string>('')
  const [poster, setPoster] = useState<TraePost[] | null>(null)
  const [fejl, setFejl] = useState('')

  useEffect(() => {
    if (!aaben) return
    hentServerRoedder(config).then(setRoedder).catch(() => setRoedder([]))
    // Start dér hvor sessionen allerede peger hen, hvis det er en mappe på
    // computeren. Ellers roden — man kan ikke gætte et hjem-katalog uden at
    // spørge maskinen, og et forkert gæt ville bare være et blindt tryk mere.
    setSti(nuvaerende?.kind === 'workstation' ? nuvaerende.root : '/')
  }, [aaben, config.apiBaseUrl, nuvaerende?.kind, nuvaerende?.root])

  useEffect(() => {
    if (!aaben || !sti) return
    let levende = true
    setPoster(null)
    setFejl('')
    hentTrae(config, 'workstation', sti, '')
      .then((p) => { if (levende) setPoster(p) })
      // SIG DET. En tom mappe og en doed forbindelse ser ens ud og betyder
      // stik modsat; uden beskeden ville man tro computeren var tom.
      .catch(() => { if (levende) { setPoster([]); setFejl('Kunne ikke læse mappen — svarer computeren?') } })
    return () => { levende = false }
  }, [aaben, sti, config.apiBaseUrl])

  const valgt = (kind: WsArt, root: string) =>
    nuvaerende?.kind === kind && nuvaerende?.root === root

  return (
    <Modal transparent visible={aaben} animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.scrim} onPress={onClose}>
        <Pressable style={styles.ark} onPress={(e) => e.stopPropagation()}>
          <View style={styles.greb} />
          <Text style={styles.titel}>Hvor skal Jarvis arbejde?</Text>

          <Text style={styles.afsnit}>På serveren</Text>
          {roedder === null ? (
            <ActivityIndicator size="small" color={tokens.color.fg2} style={styles.spinner} />
          ) : roedder.length === 0 ? (
            <Text style={styles.tom}>Ingen tilgængelige.</Text>
          ) : roedder.map((r) => (
            <Pressable
              key={r.navn}
              testID={`rod-${r.navn}`}
              accessibilityRole="button"
              accessibilityLabel={r.navn}
              onPress={() => { onVaelg('container', r.navn); onClose() }}
              style={({ pressed }) => [styles.raekke, pressed ? styles.trykket : null]}
            >
              <HardDrive size={17} color={tokens.color.fg2} strokeWidth={1.8} />
              <View style={styles.raekkeTekst}>
                <Text style={styles.navn}>{r.navn}</Text>
                {r.sti ? <Text style={styles.sti} numberOfLines={1}>{r.sti}</Text> : null}
              </View>
              {valgt('container', r.navn)
                ? <Check size={16} color={tokens.color.accent} strokeWidth={2.4} /> : null}
            </Pressable>
          ))}

          <View style={styles.linje} />
          <View style={styles.browserTop}>
            <Pressable
              testID="ws-op"
              accessibilityRole="button"
              accessibilityLabel="Et niveau op"
              onPress={() => setSti((s) => forael(s))}
              hitSlop={8}
              style={styles.opknap}
            >
              <ChevronLeft size={18} color={tokens.color.fg1} strokeWidth={2} />
            </Pressable>
            <Monitor size={15} color={tokens.color.fg2} strokeWidth={1.8} />
            <Text style={styles.browserSti} numberOfLines={1}>{sti || '/'}</Text>
          </View>

          <Pressable
            testID="ws-vaelg-denne"
            accessibilityRole="button"
            accessibilityLabel={`Vælg ${sti}`}
            onPress={() => { onVaelg('workstation', sti); onClose() }}
            style={({ pressed }) => [styles.vaelgKnap, pressed ? styles.trykket : null]}
          >
            <Text style={styles.vaelgTekst}>Brug denne mappe</Text>
          </Pressable>

          {fejl ? <Text style={styles.fejl}>{fejl}</Text> : null}

          <ScrollView style={styles.liste} keyboardShouldPersistTaps="handled">
            {poster === null ? (
              <ActivityIndicator size="small" color={tokens.color.fg2} style={styles.spinner} />
            ) : poster.length === 0 && !fejl ? (
              <Text style={styles.tom}>Tom mappe.</Text>
            ) : poster.map((p) => p.mappe ? (
              <Pressable
                key={p.navn}
                testID={`mappe-${p.navn}`}
                accessibilityRole="button"
                accessibilityLabel={p.navn}
                onPress={() => setSti((s) => underSti(s, p.navn))}
                style={({ pressed }) => [styles.raekke, pressed ? styles.trykket : null]}
              >
                <Folder size={17} color={tokens.color.fg2} strokeWidth={1.8} />
                <Text style={styles.navn}>{p.navn}</Text>
              </Pressable>
            ) : (
              // Filer kan IKKE vaelges. De staar der for at man kan se at man
              // er det rigtige sted - en tom mappe og en forkert mappe ser
              // ellers ens ud.
              <View key={p.navn} style={styles.raekke}>
                <Text style={styles.fil} numberOfLines={1}>{p.navn}</Text>
              </View>
            ))}
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  ark: {
    maxHeight: '85%',
    backgroundColor: tokens.color.bg1,
    borderTopLeftRadius: 18, borderTopRightRadius: 18,
    paddingBottom: 24, paddingTop: 8, paddingHorizontal: tokens.spacing.sm,
  },
  greb: {
    alignSelf: 'center', width: 36, height: 4, borderRadius: 2,
    backgroundColor: tokens.color.bg2, marginBottom: 10,
  },
  titel: {
    color: tokens.color.fg1, fontSize: 15, fontWeight: '600',
    paddingHorizontal: tokens.spacing.sm, paddingBottom: 8,
  },
  afsnit: {
    color: tokens.color.fg2, fontSize: 11, letterSpacing: 0.6,
    textTransform: 'uppercase',
    paddingHorizontal: tokens.spacing.sm, paddingTop: 4, paddingBottom: 4,
  },
  raekke: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    paddingVertical: 11, paddingHorizontal: tokens.spacing.sm, borderRadius: 10,
  },
  raekkeTekst: { flex: 1 },
  navn: { color: tokens.color.fg1, fontSize: 15 },
  sti: { color: tokens.color.fg3 ?? tokens.color.fg2, fontSize: 11 },
  fil: { color: tokens.color.fg3 ?? tokens.color.fg2, fontSize: 14, marginLeft: 25 },
  trykket: { opacity: 0.6 },
  linje: {
    height: StyleSheet.hairlineWidth, backgroundColor: tokens.color.bg2,
    marginVertical: 8,
  },
  browserTop: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    paddingHorizontal: tokens.spacing.sm, paddingBottom: 6,
  },
  opknap: {
    width: 30, height: 30, borderRadius: 15,
    backgroundColor: tokens.color.bg2, alignItems: 'center', justifyContent: 'center',
  },
  browserSti: { color: tokens.color.fg1, fontSize: 13, flex: 1 },
  vaelgKnap: {
    backgroundColor: tokens.color.accent, borderRadius: 10,
    paddingVertical: 11, alignItems: 'center',
    marginHorizontal: tokens.spacing.sm, marginBottom: 6,
  },
  vaelgTekst: { color: tokens.color.bg0, fontSize: 14, fontWeight: '600' },
  fejl: {
    color: tokens.color.warn, fontSize: 12,
    paddingHorizontal: tokens.spacing.sm, paddingBottom: 6,
  },
  liste: { maxHeight: 320 },
  tom: { color: tokens.color.fg2, fontSize: 13, padding: tokens.spacing.sm },
  spinner: { paddingVertical: 16 },
})
