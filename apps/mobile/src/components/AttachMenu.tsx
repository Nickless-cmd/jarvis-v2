import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

/** Lille bund-menu fra '+': vælg kamera eller galleri. */
export function AttachMenu({
  visible,
  onCamera,
  onGallery,
  onClose
}: {
  visible: boolean
  onCamera: () => void
  onGallery: () => void
  onClose: () => void
}) {
  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.scrim} onPress={onClose} accessibilityRole="button" accessibilityLabel="Luk">
        <View style={styles.sheet}>
          <Row label="📷  Tag billede" onPress={onCamera} />
          <View style={styles.divider} />
          <Row label="🖼  Vælg fra galleri" onPress={onGallery} />
          <View style={styles.divider} />
          <Row label="Annullér" muted onPress={onClose} />
        </View>
      </Pressable>
    </Modal>
  )
}

function Row({ label, onPress, muted }: { label: string; onPress: () => void; muted?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
    >
      <Text style={[styles.rowText, muted && styles.rowMuted]}>{label}</Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: tokens.color.bg1,
    borderTopLeftRadius: tokens.radius.lg,
    borderTopRightRadius: tokens.radius.lg,
    paddingVertical: tokens.spacing.sm,
    paddingBottom: tokens.spacing.xl
  },
  row: { paddingVertical: tokens.spacing.md, paddingHorizontal: tokens.spacing.lg, alignItems: 'center' },
  rowText: { color: tokens.color.fg1, fontSize: 16 },
  rowMuted: { color: tokens.color.fg3 },
  divider: { height: 1, backgroundColor: tokens.color.line },
  pressed: { opacity: 0.6 }
})
