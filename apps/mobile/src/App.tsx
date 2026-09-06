import { useEffect, useState } from 'react'
import { ActivityIndicator, AppState, StatusBar, StyleSheet, View } from 'react-native'
import * as Application from 'expo-application'
import {
  SafeAreaProvider,
  SafeAreaView,
  initialWindowMetrics,
  useSafeAreaInsets
} from 'react-native-safe-area-context'
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
import { loadBatterySaver } from './lib/batteryPrefs'
import { checkForUpdate, type UpdateManifest } from './lib/appUpdate'
import { downloadAndInstall } from './lib/installApk'
import { UpdateBanner } from './components/UpdateBanner'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AuthProvider, useAuth } from './state/AuthContext'
import { SessionProvider } from './state/SessionContext'
import { StreamProvider } from './state/StreamContext'
import { tokens } from './theme/tokens'
import { ThemeProvider } from './theme/ThemeContext'
import { useStyles, useTheme, type Theme } from './theme/ThemeContext'

function AppBody() {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config, loading } = useAuth()
  // En absolut placeret child slipper uden om SafeAreaViews polstring —
  // top: 0 ville lægge bjælken op i statusbaren. Insettet skal med.
  const insets = useSafeAreaInsets()
  const [update, setUpdate] = useState<UpdateManifest | null>(null)
  const [updBusy, setUpdBusy] = useState(false)
  const [updProgress, setUpdProgress] = useState(0)
  const [updDismissed, setUpdDismissed] = useState(false)
  // Arbejde-rummet (V2). Tilstanden bor her — ikke i en navigation-lib;
  // to bevidste tilstande af samme forhold til Jarvis, ikke to apps.
  const [mode, setMode] = useState<AppMode>('snak')
  const [syncSignal, setSyncSignal] = useState(0)
  const [pendingWork, setPendingWork] = useState(0)
  const [menuSignal, setMenuSignal] = useState(0)
  const [syncing, setSyncing] = useState(false)
  // Headeren SVÆVER. Alt der ligger i den almindelige kolonne starter derfor
  // øverst på skærmen — altså BAG bjælken. Tråden må gerne rulle bagved (det er
  // med vilje), men en opdaterings- eller fejlbesked må ikke gemme sig der:
  // Bjørn kunne se at der stod noget, men ikke læse eller trykke på det.
  //
  // Højden MÅLES, ikke gættes: bjælken har allerede skiftet højde én gang
  // (44 → 40 dp), og en konstant ville tie stille næste gang den gør det.
  const [headerHeight, setHeaderHeight] = useState(72)
  const [batterySaver, setBatterySaver] = useState(false)

  useEffect(() => {
    void loadBatterySaver().then(setBatterySaver)
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') void loadBatterySaver().then(setBatterySaver)
    })
    return () => sub.remove()
  }, [])

  // FCM: registrér device-token efter login + lyt på data-only i forgrunden.
  // Uden for tidlig return (hooks må ikke være betingede); guardet på authToken.
  useEffect(() => {
    if (!config?.authToken) return
    void registerForPush(config)
    const unsub = attachForegroundHandler(config)
    const stopPresence = startPresenceReporting(config, { getBatterySaver: () => batterySaver })
    return () => {
      unsub()
      stopPresence()
    }
  }, [config?.authToken, batterySaver])

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
          <View style={{ marginTop: headerHeight + insets.top }}>
          <UpdateBanner
            manifest={update}
            busy={updBusy}
            progress={updProgress}
            onUpdate={onUpdate}
            onDismiss={() => setUpdDismissed(true)}
          />
          </View>
        ) : null}
        {/* TopBar SVÆVER over indholdet: tråden ruller BAG den, som i
            ChatGPT-appen. En bjælke der skubber indholdet ned stjæler en
            skærmhøjde man hellere vil læse i — og overgangen mellem «under»
            og «bag» er dét der får fladen til at føles rolig frem for
            opdelt. */}
        <View
          style={[styles.floatTop, { top: insets.top }]}
          pointerEvents="box-none"
          onLayout={(e) => {
            const h = Math.round(e.nativeEvent.layout.height)
            setHeaderHeight((prev) => (Math.abs(prev - h) > 1 ? h : prev))
          }}
        >
          <TopBar
            mode={mode}
            onModeChange={setMode}
            onMenu={() => {
              // Menuen (sessioner, plugins, indstillinger) hører til Snak-rummet.
              setMode('snak')
              setMenuSignal((n) => n + 1)
            }}
            onSync={() => {
              setSyncing(true)
              setSyncSignal((n) => n + 1)
            }}
            syncing={syncing}
            pendingWork={pendingWork > 0}
          />
        </View>
        {/* Begge skærme holdes monteret: Snak må ikke miste stream-tilstand
            fordi Bjørn kigger på Arbejde. Skjult frem for unmountet. */}
        <View style={mode === 'snak' ? styles.visible : styles.hidden}>
          <ErrorBoundary label="chat">
            <ChatScreen
              openPanelSignal={menuSignal}
              syncSignal={mode === 'snak' ? syncSignal : 0}
              onSyncDone={() => setSyncing(false)}
            />
          </ErrorBoundary>
        </View>
        <View style={mode === 'arbejde' ? styles.visible : styles.hidden}>
          <ErrorBoundary label="arbejde">
            <WorkScreen
              topInset={headerHeight + insets.top}
              syncSignal={mode === 'arbejde' ? syncSignal : 0}
              onPendingCount={setPendingWork}
              onSyncDone={() => setSyncing(false)}
            />
          </ErrorBoundary>
        </View>
      </StreamProvider>
    </SessionProvider>
  )
}

/**
 * Fladen under alt. Skilt ud fra App, fordi den skal LÆSE temaet — og en
 * provider kan ikke bruge sin egen context i samme komponent.
 *
 * Statusbjælken vender med: lyse ikoner på mørk flade, mørke på lys. Uden det
 * ville uret og batteriet forsvinde i lyst tema.
 */
function Shell() {
  const t = useTheme()
  const styles = useStyles(makestyles)
  return (
    <SafeAreaView style={[styles.root, { backgroundColor: t.color.bg0 }]}>
      <StatusBar barStyle={t.scheme === 'light' ? 'dark-content' : 'light-content'} />
      <AppBody />
    </SafeAreaView>
  )
}

export default function App() {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <ErrorBoundary label="app">
      <SafeAreaProvider initialMetrics={initialWindowMetrics}>
        <ThemeProvider>
          <AuthProvider>
            <Shell />
          </AuthProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </ErrorBoundary>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
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
  },
  // Svævende topbjælke. `box-none` lader tryk gå igennem til tråden bagved
  // overalt hvor der ikke sidder en knap.
  floatTop: {
    position: 'absolute',
    left: 0,
    right: 0,
    zIndex: 10
  }
})
