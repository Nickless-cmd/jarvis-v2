import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { Check, ShieldCheck } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export type ApprovalMode = 'ask' | 'trust'

const VALG: Array<{ mode: ApprovalMode; navn: string; forklaring: string }> = [
  {
    mode: 'ask',
    navn: 'Spørg først',
    forklaring: 'Jarvis beder om lov, før han ændrer noget'
  },
  {
    mode: 'trust',
    navn: 'Fuld adgang',
    forklaring: 'Han handler uden at spørge. Farlige kommandoer blokeres stadig'
  }
]

/** Bottom-sheet for den permission-værdi stream-API'et faktisk modtager. */
export function PermissionPicker({
  open,
  selected,
  onSelect,
  onClose
}: {
  open: boolean
  selected: ApprovalMode
  onSelect: (mode: ApprovalMode) => void
  onClose: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <Modal transparent visible={open} animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.scrim} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
          <View style={styles.grabber} />
          <View style={styles.titleRow}>
            <ShieldCheck size={17} color={tokens.color.fg2} strokeWidth={2} />
            <Text style={styles.title}>Tilladelser</Text>
          </View>
          {VALG.map((valg) => {
            const active = valg.mode === selected
            return (
              <Pressable
                key={valg.mode}
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
                onPress={() => {
                  onSelect(valg.mode)
                  onClose()
                }}
                style={({ pressed }) => [styles.row, pressed && styles.pressed]}
              >
                <View style={styles.copy}>
                  <Text style={[styles.name, active && styles.nameActive]}>{valg.navn}</Text>
                  <Text style={styles.description}>{valg.forklaring}</Text>
                </View>
                {active ? <Check size={18} color={tokens.color.accentText} strokeWidth={2.4} /> : null}
              </Pressable>
            )
          })}
        </Pressable>
      </Pressable>
    </Modal>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: tokens.color.bg1,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: tokens.spacing.lg,
    paddingTop: tokens.spacing.sm,
    paddingBottom: tokens.spacing.xl
  },
  grabber: {
    alignSelf: 'center',
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: tokens.color.bg3,
    marginBottom: tokens.spacing.md
  },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 7, marginBottom: tokens.spacing.sm },
  title: { color: tokens.color.fg3, fontSize: 12, fontWeight: '700', textTransform: 'uppercase' },
  row: {
    minHeight: 70,
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1,
    paddingVertical: tokens.spacing.md
  },
  copy: { flex: 1, gap: 4 },
  name: { color: tokens.color.fg1, fontSize: 16, fontWeight: '600' },
  nameActive: { color: tokens.color.accentText },
  description: { color: tokens.color.fg3, fontSize: 13, lineHeight: 18 },
  pressed: { opacity: 0.7 }
})
