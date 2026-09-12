import { useEffect, useRef, useState } from 'react'
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
import { TopBarMenu } from './components/TopBarMenu'
import type { ContextUsage, GitStatus } from './lib/apiClient'
import { OnboardingGuide } from './components/OnboardingGuide'
import { erGennemfoert, type Tilladelse } from './lib/onboarding'
import { alleredeGivneTilladelser } from './lib/permissionRequests'
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
import { startBro } from './lib/broOpstart'
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
  const [guideOpen, setGuideOpen] = useState(false)
  const [givneTilladelser, setGivneTilladelser] = useState<Tilladelse[]>([])
  // Arbejde-rummet (V2). Tilstanden bor her — ikke i en navigation-lib;
  // to bevidste tilstande af samme forhold til Jarvis, ikke to apps.
  const [mode, setMode] = useState<AppMode>('snak')
  // Et approval-push skal lande i Arbejde → GODKEND. Signalet tæller op, så
  // to pushes i træk begge rammer fanen, også hvis man selv har skiftet væk.
  const [approveFokus, setApproveFokus] = useState(0)
  const [syncSignal, setSyncSignal] = useState(0)
  const [pendingWork, setPendingWork] = useState(0)
  const [menuSignal, setMenuSignal] = useState(0)
  const [syncing, setSyncing] = useState(false)
  // Kontekst-fyldet meldes OP fra ChatScreen, som er den der kender den
  // aktive session. Headeren ejer ringen, men ikke tallet.
  const [kontekst, setKontekst] = useState<ContextUsage | null>(null)
  const [mereAaben, setMereAaben] = useState(false)
  const [compactSignal, setCompactSignal] = useState(0)
  // Code-fladen. Den er IKKE porten fra en QR: målt 12/9-2026 udsteder
  // `/auth/pair/*` et login-token og binder ikke telefonen til en bestemt
  // desk-instans. Der findes intet led mellem de to enheder at hænge den på,
  // så fladen slås til fra menuen og porten står åben som en note.
  const [kodeTilstand, setKodeTilstand] = useState(false)
  // Titel og git meldes OP fra ChatScreen, som er den der kender sessionen.
  const [kodeKontekst, setKodeKontekst] = useState<{ titel: string; git: GitStatus | null }>({
    titel: '', git: null,
  })
  // Headeren SVÆVER. Alt der ligger i den almindelige kolonne starter derfor
  // øverst på skærmen — altså BAG bjælken. Tråden må gerne rulle bagved (det er
  // med vilje), men en opdaterings- eller fejlbesked må ikke gemme sig der:
  // Bjørn kunne se at der stod noget, men ikke læse eller trykke på det.
  //
  // Højden MÅLES, ikke gættes: bjælken har allerede skiftet højde én gang
  // (44 → 40 dp), og en konstant ville tie stille næste gang den gør det.
  const [headerHeight, setHeaderHeight] = useState(72)
  // Batterispare-flaget bruges KUN af presence, aldrig i render. Derfor en ref
  // og ikke en tilstand: en tilstand ville gentegne, OG - fordi den stod i
  // effektens afhaengigheder nedenfor - rive broen ned og bygge den op igen ved
  // hvert skift. Flaget genindlaeses ved hver 'active', altsaa hver gang appen
  // kommer i forgrunden, saa det skete tit. Maalt 12/9-2026: kommentaren under
  // broen sagde "hoerer til token'et, ikke til en skaerm" mens arrayet sagde
  // token OG batteriflag. Nu siger de det samme.
  const batterySaverRef = useRef(false)

  useEffect(() => {
    const gem = (v: boolean) => {
      batterySaverRef.current = v
    }
    void loadBatterySaver().then(gem)
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') void loadBatterySaver().then(gem)
    })
    return () => sub.remove()
  }, [])

  // FCM: registrér device-token efter login + lyt på data-only i forgrunden.
  // Uden for tidlig return (hooks må ikke være betingede); guardet på authToken.
  useEffect(() => {
    if (!config?.authToken) return
    void registerForPush(config)
    const unsub = attachForegroundHandler(config)
    const stopPresence = startPresenceReporting(config, { getBatterySaver: () => batterySaverRef.current })
    // Broen: gør telefonen til en enhed Jarvis kan udføre ting på, ikke bare
    // en skærm han skriver til. Samme livstid som push og presence — den
    // hører til token'et, ikke til en skærm.
    const stopBro = startBro(config)
    return () => {
      unsub()
      stopPresence()
      stopBro()
    }
  }, [config?.authToken])

  // Et tryk på en godkendelses-notifikation skal lande i Arbejde → Godkend,
  // ikke i Snak. Ellers fører notifikationen hen til det forkerte rum, og
  // Bjørn skal selv finde det der ventede.
  useEffect(() => {
    void openedFromApprovalPush().then((yes) => {
      if (yes) {
        setMode('arbejde')
        setApproveFokus((n) => n + 1)
      }
    })
    return attachApprovalTapHandler(() => {
      setMode('arbejde')
      setApproveFokus((n) => n + 1)
    })
  }, [])

  // Tilladelses-guiden vises ÉN gang, og først efter login: at spørge om
  // kamera og lokation før man overhovedet er logget ind ligner en app der
  // beder om alt uden at have gjort sig fortjent til noget.
  useEffect(() => {
    if (!config?.authToken) return
    // Tilstanden læses FØR guiden vises, ellers spørger den om ting man
    // allerede har givet — og en guide der spørger om det åbenlyse mister
    // tilliden på sit første trin.
    void (async () => {
      const [faerdig, givet] = await Promise.all([
        erGennemfoert().catch(() => true),
        alleredeGivneTilladelser().catch(() => [] as Tilladelse[])
      ])
      setGivneTilladelser(givet)
      setGuideOpen(!faerdig)
    })()
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
        <OnboardingGuide visible={guideOpen} alleredeGivet={givneTilladelser} onDone={() => setGuideOpen(false)} />
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
            kodeTilstand={kodeTilstand}
            kodeTitel={kodeKontekst.titel}
            git={kodeKontekst.git}
            kontekst={mode === 'snak' ? kontekst : null}
            onMereMenu={() => setMereAaben(true)}
          />
        </View>
        <TopBarMenu
          aaben={mereAaben}
          onClose={() => setMereAaben(false)}
          onSync={() => { setSyncing(true); setSyncSignal((n) => n + 1) }}
          // Komprimér vises KUN når der er en ring at komprimere. Et punkt
          // der ikke kan gøre noget er værre end et der ikke er der.
          onCompact={mode === 'snak' && kontekst ? () => setCompactSignal((n) => n + 1) : undefined}
          kodeTilstand={kodeTilstand}
          onTilbageTilChat={() => setKodeTilstand(false)}
        />
        {/* Begge skærme holdes monteret: Snak må ikke miste stream-tilstand
            fordi Bjørn kigger på Arbejde. Skjult frem for unmountet. */}
        <View style={mode === 'snak' ? styles.visible : styles.hidden}>
          <ErrorBoundary label="chat">
            <ChatScreen
              openPanelSignal={menuSignal}
              syncSignal={mode === 'snak' ? syncSignal : 0}
              onSyncDone={() => setSyncing(false)}
              onKontekst={setKontekst}
              compactSignal={compactSignal}
              kodeTilstand={kodeTilstand}
              onSkiftFlade={setKodeTilstand}
              onKodeKontekst={setKodeKontekst}
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
              focusTab="approve"
              focusSignal={approveFokus}
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
