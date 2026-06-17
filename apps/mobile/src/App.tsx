import { ActivityIndicator, StatusBar, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { LoginScreen } from './screens/LoginScreen'
import { AuthProvider, useAuth } from './state/AuthContext'
import { SessionProvider } from './state/SessionContext'
import { tokens } from './theme/tokens'

function AppBody() {
  const { config, loading } = useAuth()

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={tokens.color.accent} />
      </View>
    )
  }

  if (!config) {
    return <LoginScreen />
  }

  return (
      <View style={styles.center}>
        <Text style={styles.title}>Jarvis chat klar</Text>
      </View>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <SessionProvider>
        <SafeAreaView style={styles.root}>
          <StatusBar barStyle="light-content" />
          <AppBody />
        </SafeAreaView>
      </SessionProvider>
    </AuthProvider>
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
    justifyContent: 'center'
  },
  title: {
    color: tokens.color.fg1,
    fontSize: 20,
    fontWeight: '700'
  }
})
