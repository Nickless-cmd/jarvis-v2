import type { ReactNode } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import {
  Bell, Brain, Camera, ChevronRight, Database, FlaskConical, Globe,
  MapPin, MessageCircle, Palette, Plug, Shield, Smartphone,
} from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import type { IkonNavn } from '../lib/settingsGrupper'

/** Navn → komponent. Strukturen i `settingsGrupper` bærer kun strengen, så den
 *  kan testes uden at rendere noget; opslaget hører til her, hvor der tegnes. */
const IKONER: Record<IkonNavn, typeof Bell> = {
  'palette': Palette,
  'globe': Globe,
  'message-circle': MessageCircle,
  'brain': Brain,
  'camera': Camera,
  'map-pin': MapPin,
  'shield': Shield,
  'plug': Plug,
  'bell': Bell,
  'smartphone': Smartphone,
  'database': Database,
  'flask-conical': FlaskConical,
}

/**
 * Én indstilling som en RÆKKE: `ikon · navn · værdi · ›`.
 *
 * Værdien er pointen. Før stod hver indstilling foldet ud med sine knapper, og
 * man kunne kun se hvordan noget stod ved at rulle ned til det. «Mørk»,
 * «Dansk», «Slukket» svarer på «hvordan står det egentlig?» uden at man åbner
 * noget — og en forkert indstilling kan ses med ét blik.
 *
 * Ikonet gør rækken genkendelig på et halvt sekund, også for en der ikke læser
 * hele linjen.
 */
export function SettingsRaekke({ navn, ikon, vaerdi, onPress, foerste, sidste }: {
  navn: string
  ikon: IkonNavn
  /** Nuværende værdi. Tom når rækken ikke HAR en — fx «Hukommelse». */
  vaerdi?: string
  onPress: () => void
  /** Til de afrundede hjørner: gruppen er ét kort, rækkerne deler kant. */
  foerste?: boolean
  sidste?: boolean
}) {
  const tokens = useTheme()
  const styles = useStyles(makeStyles)
  const Ikon = IKONER[ikon]
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={vaerdi ? `${navn}, ${vaerdi}` : navn}
      testID={`settings-raekke-${navn}`}
      onPress={onPress}
      style={({ pressed }) => [
        styles.raekke,
        foerste && styles.foerste,
        sidste && styles.sidste,
        !sidste && styles.medSkillelinje,
        pressed && styles.trykket,
      ]}
    >
      <Ikon size={19} color={tokens.color.fg2} strokeWidth={1.75} />
      <Text style={styles.navn} numberOfLines={1}>{navn}</Text>
      {vaerdi ? <Text style={styles.vaerdi} numberOfLines={1}>{vaerdi}</Text> : null}
      <ChevronRight size={18} color={tokens.color.fg3} strokeWidth={2} />
    </Pressable>
  )
}

/**
 * Kontoen som en RÆKKE, ikke et portræt.
 *
 * Før stod et 76 px avatar midt på skærmen med navn og mail under — det fyldte
 * den øverste tredjedel uden at svare på mere end «hvem er jeg?». Som række
 * svarer den på det samme, plus om der ER forbindelse og til hvilken maskine,
 * og den koster fire linjer i stedet for en skærmfuld.
 */
export function SettingsKontoRaekke({ navn, initialer, forbundet, vaert, onPress }: {
  navn: string
  initialer: string
  forbundet: boolean
  /** Maskinen han er forbundet TIL — «CheifOne». Tom når den er ukendt. */
  vaert?: string
  onPress: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makeStyles)
  const under = [forbundet ? 'Forbundet' : 'Ikke forbundet', vaert].filter(Boolean).join(' · ')
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${navn}, ${under}`}
      testID="settings-konto-raekke"
      onPress={onPress}
      style={({ pressed }) => [styles.kort, styles.konto, pressed && styles.trykket]}
    >
      <View style={[styles.avatar, { backgroundColor: tokens.color.accent }]}>
        <Text style={[styles.avatarTekst, { color: tokens.color.onAccent }]}>{initialer}</Text>
      </View>
      <View style={styles.kontoTekst}>
        <Text style={styles.kontoNavn} numberOfLines={1}>{navn}</Text>
        <View style={styles.kontoUnder}>
          <View
            testID={forbundet ? 'settings-konto-prik-online' : 'settings-konto-prik-offline'}
            style={[styles.prik, { backgroundColor: forbundet ? tokens.color.ok : tokens.color.fg3 }]}
          />
          <Text style={styles.kontoStatus} numberOfLines={1}>{under}</Text>
        </View>
      </View>
      <ChevronRight size={18} color={tokens.color.fg3} strokeWidth={2} />
    </Pressable>
  )
}

/** Gruppen som ÉT kort med en overskrift over. Rækkerne deler kant, så de
 *  hører sammen visuelt — i stedet for at flyde som løse kort. */
export function SettingsGruppeKort({ navn, children }: { navn: string; children: ReactNode }) {
  const styles = useStyles(makeStyles)
  return (
    <View style={styles.gruppe}>
      <Text style={styles.gruppeNavn}>{navn.toUpperCase()}</Text>
      <View style={styles.kort}>{children}</View>
    </View>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  gruppe: { marginTop: tokens.spacing.lg },
  gruppeNavn: {
    color: tokens.color.fg3, fontSize: 12, fontWeight: '700',
    letterSpacing: 0.8, marginBottom: tokens.spacing.xs,
    marginHorizontal: tokens.spacing.xs,
  },
  kort: {
    backgroundColor: tokens.color.bg2, borderRadius: 14, overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line,
  },
  raekke: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md, minHeight: 52,
  },
  // Skillelinjen starter efter ikonet, som i systemets egne lister.
  medSkillelinje: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: tokens.color.line,
  },
  foerste: {},
  sidste: {},
  trykket: { backgroundColor: tokens.color.bg3 },
  navn: { flex: 1, color: tokens.color.fg1, fontSize: 16 },
  konto: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md, paddingVertical: 12,
    marginTop: tokens.spacing.md,
  },
  avatar: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  avatarTekst: { fontSize: 15, fontWeight: '700' },
  kontoTekst: { flex: 1, gap: 3 },
  kontoNavn: { color: tokens.color.fg1, fontSize: 16, fontWeight: '600' },
  kontoUnder: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  prik: { width: 7, height: 7, borderRadius: 4 },
  kontoStatus: { color: tokens.color.fg3, fontSize: 13 },
  vaerdi: { color: tokens.color.fg3, fontSize: 15, maxWidth: '45%' },
})
