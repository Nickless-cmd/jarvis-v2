import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useAuth } from '../state/AuthContext'
import { tokens } from '../theme/tokens'

export function SettingsScreen() {
  const { config, signOut } = useAuth()

  return (
    <View style={styles.root}>
      <Text style={styles.heading}>Indstillinger</Text>
      <View style={styles.section}>
        <Text style={styles.label}>API</Text>
        <Text style={styles.value}>{config?.apiBaseUrl ?? 'Ikke forbundet'}</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.label}>Token</Text>
        <Text style={styles.value}>{config?.authToken ? 'Gemt sikkert' : 'Mangler'}</Text>
      </View>
      <Pressable accessibilityRole="button" onPress={() => void signOut()} style={styles.signOut}>
        <Text style={styles.signOutText}>Log ud</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0,
    padding: tokens.spacing.md
  },
  heading: {
    color: tokens.color.fg1,
    fontSize: 22,
    fontWeight: '700',
    marginBottom: tokens.spacing.md
  },
  section: {
    paddingVertical: tokens.spacing.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  label: {
    color: tokens.color.fg3,
    marginBottom: tokens.spacing.xs
  },
  value: {
    color: tokens.color.fg1
  },
  signOut: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg3,
    marginTop: tokens.spacing.xl
  },
  signOutText: {
    color: tokens.color.fg1,
    fontWeight: '700'
  }
})
