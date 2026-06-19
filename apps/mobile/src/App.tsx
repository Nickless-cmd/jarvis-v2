import { useEffect } from 'react'
import { ActivityIndicator, StatusBar, StyleSheet, View } from 'react-native'
import { SafeAreaProvider, SafeAreaView, initialWindowMetrics } from 'react-native-safe-area-context'
import { ChatScreen } from './screens/ChatScreen'
import { LoginScreen } from './screens/LoginScreen'
import { registerForPush, attachForegroundHandler } from './lib/push'
import { AuthProvider, useAuth } from './state/AuthContext'
import { SessionProvider } from './state/SessionContext'
import { StreamProvider } from './state/StreamContext'
import { tokens } from './theme/tokens'

function AppBody() {
  const { config, loading } = useAuth()

  // FCM: registrér device-token efter login + lyt på data-only i forgrunden.
  // Uden for tidlig return (hooks må ikke være betingede); guardet på authToken.
  useEffect(() => {
    if (!config?.authToken) return
    void registerForPush(config)
    const unsub = attachForegroundHandler(config)
    return () => {
      unsub()
    }
  }, [config?.authToken])

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
    <SessionProvider key={JSON.stringify([config.apiBaseUrl, config.authToken])}>
      <StreamProvider>
        <ChatScreen />
      </StreamProvider>
    </SessionProvider>
  )
}

export default function App() {
  return (
    <SafeAreaProvider initialMetrics={initialWindowMetrics}>
      <AuthProvider>
        <SafeAreaView style={styles.root}>
          <StatusBar barStyle="light-content" />
          <AppBody />
        </SafeAreaView>
      </AuthProvider>
    </SafeAreaProvider>
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
  }
})
