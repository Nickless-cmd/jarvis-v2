import { useEffect, useState } from 'react'
import { ActivityIndicator, AppState, StatusBar, StyleSheet, View } from 'react-native'
import * as Application from 'expo-application'
import { SafeAreaProvider, SafeAreaView, initialWindowMetrics } from 'react-native-safe-area-context'
import { ChatScreen } from './screens/ChatScreen'
import { LoginScreen } from './screens/LoginScreen'
import { registerForPush, attachForegroundHandler } from './lib/push'
import { startPresenceReporting } from './lib/presence'
import { checkForUpdate, type UpdateManifest } from './lib/appUpdate'
import { downloadAndInstall } from './lib/installApk'
import { UpdateBanner } from './components/UpdateBanner'
import { AuthProvider, useAuth } from './state/AuthContext'
import { SessionProvider } from './state/SessionContext'
import { StreamProvider } from './state/StreamContext'
import { tokens } from './theme/tokens'

function AppBody() {
  const { config, loading } = useAuth()
  const [update, setUpdate] = useState<UpdateManifest | null>(null)
  const [updBusy, setUpdBusy] = useState(false)
  const [updProgress, setUpdProgress] = useState(0)
  const [updDismissed, setUpdDismissed] = useState(false)

  // FCM: registrér device-token efter login + lyt på data-only i forgrunden.
  // Uden for tidlig return (hooks må ikke være betingede); guardet på authToken.
  useEffect(() => {
    if (!config?.authToken) return
    void registerForPush(config)
    const unsub = attachForegroundHandler(config)
    const stopPresence = startPresenceReporting(config)
    return () => {
      unsub()
      stopPresence()
    }
  }, [config?.authToken])

  // Auto-updater: check ved opstart + når app vender tilbage til forgrunden.
  useEffect(() => {
    if (!config?.authToken) return
    const installedVc = Number(Application.nativeBuildVersion ?? '0') || 0
    const run = () => {
      void checkForUpdate(config, installedVc).then((m) => {
        if (m) setUpdate(m)
      })
    }
    run()
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') run()
    })
    return () => sub.remove()
  }, [config?.authToken])

  const onUpdate = () => {
    if (!config || !update) return
    setUpdBusy(true)
    setUpdProgress(0)
    void downloadAndInstall(config, update, setUpdProgress).catch(() => setUpdBusy(false))
  }

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
        {update && !updDismissed ? (
          <UpdateBanner
            manifest={update}
            busy={updBusy}
            progress={updProgress}
            onUpdate={onUpdate}
            onDismiss={() => setUpdDismissed(true)}
          />
        ) : null}
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
