import { useEffect, useState } from 'react'
import { ActivityIndicator, AppState, StatusBar, StyleSheet, View } from 'react-native'
import * as Application from 'expo-application'
import { SafeAreaProvider, SafeAreaView, initialWindowMetrics } from 'react-native-safe-area-context'
import { ChatScreen } from './screens/ChatScreen'
import { WorkScreen } from './screens/WorkScreen'
import { TopBar, type AppMode } from './components/TopBar'
import { LoginScreen } from './screens/LoginScreen'
import {
  attachApprovalTapHandler,
  attachForegroundHandler,
  openedFromApprovalPush,
  registerForPush
} from './lib/push'
import { startPresenceReporting } from './lib/presence'
import { checkForUpdate, type UpdateManifest } from './lib/appUpdate'
import { downloadAndInstall } from './lib/installApk'
import { UpdateBanner } from './components/UpdateBanner'
import { ErrorBoundary } from './components/ErrorBoundary'
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
  // Arbejde-rummet (V2). Tilstanden bor her — ikke i en navigation-lib;
  // to bevidste tilstande af samme forhold til Jarvis, ikke to apps.
  const [mode, setMode] = useState<AppMode>('snak')
  const [syncSignal, setSyncSignal] = useState(0)
  const [pendingWork, setPendingWork] = useState(0)

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

  // Et tryk på en godkendelses-notifikation skal lande i Arbejde → Godkend,
  // ikke i Snak. Ellers fører notifikationen hen til det forkerte rum, og
  // Bjørn skal selv finde det der ventede.
  useEffect(() => {
    void openedFromApprovalPush().then((yes) => {
      if (yes) setMode('arbejde')
    })
    return attachApprovalTapHandler(() => setMode('arbejde'))
  }, [])

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
        <TopBar
          mode={mode}
          onModeChange={setMode}
          onMenu={() => setMode('snak')}
          onSync={() => setSyncSignal((n) => n + 1)}
          pendingWork={pendingWork > 0}
        />
        {/* Begge skærme holdes monteret: Snak må ikke miste stream-tilstand
            fordi Bjørn kigger på Arbejde. Skjult frem for unmountet. */}
        <View style={mode === 'snak' ? styles.visible : styles.hidden}>
          <ErrorBoundary label="chat">
            <ChatScreen />
          </ErrorBoundary>
        </View>
        <View style={mode === 'arbejde' ? styles.visible : styles.hidden}>
          <ErrorBoundary label="arbejde">
            <WorkScreen syncSignal={syncSignal} onPendingCount={setPendingWork} />
          </ErrorBoundary>
        </View>
      </StreamProvider>
    </SessionProvider>
  )
}

export default function App() {
  return (
    <ErrorBoundary label="app">
      <SafeAreaProvider initialMetrics={initialWindowMetrics}>
        <AuthProvider>
          <SafeAreaView style={styles.root}>
            <StatusBar barStyle="light-content" />
            <AppBody />
          </SafeAreaView>
        </AuthProvider>
      </SafeAreaProvider>
    </ErrorBoundary>
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
  visible: {
    flex: 1
  },
  hidden: {
    display: 'none'
  }
})
