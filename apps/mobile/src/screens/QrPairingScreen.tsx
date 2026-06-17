import { StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

export function QrPairingScreen() {
  return (
    <View style={styles.root}>
      <Text style={styles.title}>QR pairing</Text>
      <Text style={styles.body}>
        QR pairing aktiveres, når Jarvis API har en kortlivet pairing exchange.
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0,
    padding: tokens.spacing.xl,
    justifyContent: 'center'
  },
  title: {
    color: tokens.color.fg1,
    fontSize: 24,
    fontWeight: '700',
    marginBottom: tokens.spacing.md
  },
  body: {
    color: tokens.color.fg2,
    fontSize: 16,
    lineHeight: 23
  }
})
