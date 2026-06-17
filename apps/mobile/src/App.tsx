import { StatusBar, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { tokens } from './theme/tokens'

export default function App() {
  return (
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="light-content" />
      <View style={styles.center}>
        <Text style={styles.title}>Jarvis</Text>
        <Text style={styles.subtitle}>Mobile companion</Text>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: tokens.spacing.sm
  },
  title: {
    color: tokens.color.fg1,
    fontSize: 28,
    fontWeight: '700'
  },
  subtitle: {
    color: tokens.color.fg2,
    fontSize: 16
  }
})
