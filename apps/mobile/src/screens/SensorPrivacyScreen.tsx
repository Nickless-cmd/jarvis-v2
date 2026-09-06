import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { ShieldCheck, X } from 'lucide-react-native'
import type { SensorPrivacyRow } from '../lib/sensorPrivacy'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function SensorPrivacyScreen({
  onClose,
  rows
}: {
  onClose: () => void
  rows: SensorPrivacyRow[]
}) {
  const tokens = useTheme()
  const styles = useStyles(makes)
  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} style={styles.circle}>
          <X size={20} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        <Text style={styles.title}>Sanser & privatliv</Text>
        <View style={styles.circleGhost} />
      </View>
      <ScrollView contentContainerStyle={styles.body}>
        <View style={styles.hero}>
          <ShieldCheck size={20} color={tokens.color.accent} strokeWidth={1.9} />
          <Text style={styles.heroText}>Alt Jarvis kan sanse fra telefonen, samlet ét sted.</Text>
        </View>
        {rows.map((row) => (
          <View key={row.id} style={styles.card}>
            <View style={styles.rowTop}>
              <Text style={styles.label}>{row.label}</Text>
              <Text style={[styles.risk, row.risk === 'high' ? styles.high : row.risk === 'medium' ? styles.medium : styles.low]}>
                {row.risk}
              </Text>
            </View>
            <Text style={styles.value}>{row.value}</Text>
          </View>
        ))}
      </ScrollView>
    </View>
  )
}

const makes = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0, paddingTop: 48 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: tokens.spacing.md, paddingBottom: tokens.spacing.md },
  circle: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: tokens.color.bg2 },
  circleGhost: { width: 40, height: 40 },
  title: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700' },
  body: { padding: tokens.spacing.lg, gap: tokens.spacing.sm, paddingBottom: tokens.spacing.xl },
  hero: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.md, backgroundColor: tokens.color.bg1, borderRadius: tokens.radius.lg, padding: tokens.spacing.lg },
  heroText: { flex: 1, color: tokens.color.fg2, lineHeight: 20 },
  card: { backgroundColor: tokens.color.bg2, borderRadius: tokens.radius.lg, padding: tokens.spacing.lg, gap: 6 },
  rowTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: tokens.spacing.md },
  label: { color: tokens.color.fg1, fontWeight: '700', fontSize: 15 },
  value: { color: tokens.color.fg2, lineHeight: 20 },
  risk: { fontSize: 11, fontWeight: '900', textTransform: 'uppercase' },
  low: { color: tokens.color.accentText },
  medium: { color: tokens.color.warn },
  high: { color: tokens.color.error }
})
