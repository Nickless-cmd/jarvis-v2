import type { ReactNode } from 'react'
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { ChevronLeft } from 'lucide-react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Ruden bag en indstillings-række.
 *
 * Indholdet er UÆNDRET — det er de samme sektioner som før, med de samme
 * knapper og kontakter. De ligger bare bag rækken i stedet for under den, så
 * listen kan vise hvad der findes i stedet for at være alt på én gang.
 *
 * Tilbage-pilen og ikke et kryds: man går et skridt tilbage i indstillingerne,
 * man lukker dem ikke. Krydset sidder stadig på selve indstillings-skærmen.
 */
export function SettingsDetalje({ titel, aaben, onLuk, children }: {
  titel: string
  aaben: boolean
  onLuk: () => void
  children: ReactNode
}) {
  const tokens = useTheme()
  const styles = useStyles(makeStyles)
  const insets = useSafeAreaInsets()
  return (
    <Modal visible={aaben} animationType="slide" onRequestClose={onLuk}>
      <View style={[styles.rod, { paddingTop: insets.top }]}>
        <View style={styles.hoved}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Tilbage"
            testID="settings-detalje-tilbage"
            onPress={onLuk}
            hitSlop={10}
          >
            <ChevronLeft size={26} color={tokens.color.fg1} strokeWidth={2} />
          </Pressable>
          <Text style={styles.titel} numberOfLines={1}>{titel}</Text>
        </View>
        <ScrollView
          testID="settings-detalje-krop"
          contentContainerStyle={[styles.krop, { paddingBottom: insets.bottom + 32 }]}
          keyboardShouldPersistTaps="handled"
        >
          {children}
        </ScrollView>
      </View>
    </Modal>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  rod: { flex: 1, backgroundColor: tokens.color.bg1 },
  hoved: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: tokens.color.line,
  },
  titel: { flex: 1, color: tokens.color.fg1, fontSize: 20, fontWeight: '700' },
  krop: { paddingHorizontal: tokens.spacing.lg, paddingTop: tokens.spacing.md },
})
