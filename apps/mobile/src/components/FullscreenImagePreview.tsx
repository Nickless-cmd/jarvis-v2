import { Image, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { X } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function FullscreenImagePreview({
  visible,
  uri,
  title,
  headers,
  onClose
}: {
  visible: boolean
  uri: string
  title?: string
  headers?: Record<string, string>
  onClose: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makes)
  return (
    <Modal visible={visible} transparent={false} animationType="fade" onRequestClose={onClose}>
      <View style={styles.root}>
        <View style={styles.top}>
          <Text style={styles.title} numberOfLines={1}>{title || 'Billede'}</Text>
          <Pressable accessibilityRole="button" accessibilityLabel="Luk preview" onPress={onClose} hitSlop={12} style={styles.close}>
            <X size={22} color={tokens.color.fg1} strokeWidth={2} />
          </Pressable>
        </View>
        <Image
          testID="attachment-fullscreen-image"
          source={{ uri, headers }}
          resizeMode="contain"
          style={styles.image}
        />
      </View>
    </Modal>
  )
}

const makes = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  top: {
    minHeight: 64,
    paddingHorizontal: tokens.spacing.lg,
    paddingTop: tokens.spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: tokens.spacing.md
  },
  title: { flex: 1, color: tokens.color.fg1, fontSize: 15, fontWeight: '700' },
  close: { width: 40, height: 40, borderRadius: 20, backgroundColor: tokens.color.bg2, alignItems: 'center', justifyContent: 'center' },
  image: { flex: 1, width: '100%', backgroundColor: tokens.color.bg0 }
})
