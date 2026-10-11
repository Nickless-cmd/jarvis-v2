import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { Modal, Pressable, StyleSheet, Text, View, useWindowDimensions } from 'react-native'
import { WebView } from 'react-native-webview'
import { Maximize2, X } from 'lucide-react-native'
import { tokens } from '../theme/tokens'

/**
 * En widget paa telefonen: model-skrevet HTML i en WebView der ikke kan naa
 * noget.
 *
 * **Mobilen har ingen `sandbox`-attribut.** Desks graense er
 * `sandbox="allow-scripts"` uden `allow-same-origin`; her skal den samme
 * graense bygges af flag, og de er listet eksplicit nedenfor frem for at
 * arve WebView'ens standarder. En standard der aendrer sig i en ny udgave af
 * biblioteket maa ikke kunne aabne en doer vi aldrig har besluttet.
 *
 * Tre lag:
 *  1. SERVEREN (`core/services/widget_dokument.py`) har givet dokumentet en
 *     CSP med `default-src 'none'` — intet netvaerk ind eller ud. Det er
 *     SAMME dokument som desk faar, saa de to flader ikke kan drive fra
 *     hinanden.
 *  2. `originWhitelist={[]}` + `onShouldStartLoadWithRequest` → ingen
 *     navigation nogen steder. Et klik paa et link doer her, ikke i et
 *     halvt-indlaest vindue.
 *  3. Ingen fil-adgang, ingen delt storage, ingen flere vinduer. Og INTET
 *     `baseUrl` paa `source`: uden den er dokumentets origin `about:blank`,
 *     altsaa ugennemsigtig — sat vi en baseUrl til API'et, ville dokumentet
 *     faa API'ets origin.
 *
 * Tokenet kommer aldrig ind i WebView'en: HTML'en hentes af `ChatScreen` med
 * `Authorization` og gives videre som ren tekst.
 */

/** Uafhaengigt loft. Serveren capper ved 256 KB; her staar et eget, saa en
 *  forkert reference ikke kan trække en stor fil ind paa telefonen. */
export const MAX_WIDGET_BYTES = 512 * 1024

/** Takt-graenser for `jarvis.sendPrompt`. Widget'en koerer model-skrevet JS, saa
 *  graenserne er ikke hoeflighed — de er loftet over hvad en loekke kan koste.
 *  Hver sendt besked starter et run. Samme tal som desk. */
const MAX_PROMPTS = 5
const MIN_MS_MELLEM = 2000
const MAX_PROMPT_TEGN = 2000

/** Hvor en widget-initieret besked skal hen. Context og ikke en prop: vejen fra
 *  ChatScreen gaar gennem MessageBubble og MessageAttachments, og en prop ville
 *  aendre to signaturer der intet har med widgets at goere.
 *
 *  Standard er `null`: en widget i en visning der ikke kan sende skal tie. */
export const WidgetPrompt = createContext<((markeretTekst: string) => void) | null>(null)

const HOEJDE_SCRIPT = `
(function () {
  function sig() {
    try {
      var h = Math.max(
        document.body ? document.body.scrollHeight : 0,
        document.documentElement ? document.documentElement.scrollHeight : 0
      );
      window.ReactNativeWebView.postMessage(JSON.stringify({
        type: 'jarvis-widget-hoejde', hoejde: h + 24
      }));
    } catch (e) {}
  }
  sig();
  window.addEventListener('load', sig);
  if (window.ResizeObserver && document.body) { new ResizeObserver(sig).observe(document.body); }
})();
true;
`

/** Luft ud til skaermkanten. Boblen og vedhaeftnings-wrapperen tager hver
 *  sin margen; 20 pr. side rammer den samme kant som teksten staar paa. */
const SIDE_LUFT = 20

/** Previewet bor midt i en samtale. Selv en widget der bruger `100vh` eller
 *  rapporterer et stort desktop-canvas maa ikke skubbe resten af svaret en hel
 *  skaerm vaek. Hele fladen findes bag udvid-knappen. */
const INLINE_MAKS_HOEJDE = 420
const MOBIL_VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes">'

/** Allerede udgivne widgets bliver ikke pakket igen paa serveren. Giv derfor
 *  ogsaa gamle dokumenter mobilens virkelige CSS-bredde lokalt. Uden denne
 *  meta antager Android WebView en desktopside paa omtrent 980 px og skalerer
 *  hele fladen ned til ulæselig størrelse. */
export function medMobilViewport(html: string): string {
  if (/<meta\b[^>]*\bname\s*=\s*["']?viewport\b/i.test(html)) return html
  if (/<head(?:\s[^>]*)?>/i.test(html)) {
    return html.replace(/<head(?:\s[^>]*)?>/i, (head) => `${head}\n${MOBIL_VIEWPORT}`)
  }
  return `${MOBIL_VIEWPORT}\n${html}`
}

/** Er adressen dokumentet selv — eller et forsoeg paa at navigere ud?
 *
 *  `source={{ html }}` indlaeses som `about:blank` (Android:
 *  `loadDataWithBaseURL`) eller som en `data:`-URL. Begge ER widget'en. Alt
 *  andet — http, https, intent:, file: — er et forsoeg paa at forlade
 *  sandkassen og afvises. Eksporteret saa en test kan se den afvise. */
export function dokumentets_egen(url: unknown): boolean {
  const u = String(url ?? '').trim().toLowerCase()
  return u === '' || u === 'about:blank' || u.startsWith('data:')
}

export function WidgetFlade({ html, titel }: { html: string; titel?: string }) {
  const [hoejde, setHoejde] = useState(160)
  const [fuld, setFuld] = useState(false)
  // EN DEFINIT BREDDE, IKKE EN PROCENT (Bjoern 6/10-2026: «Og saa virker
  // widget ikk i mobilen» — og paa spoergsmaalet om hvad der stod paa
  // skaermen: «Ingenting»).
  //
  // Rammen havde `width: '100%'`. Foraelderen er `MessageAttachments`'
  // `venstre`-stil, som saetter `alignSelf: 'flex-start'` OG
  // `alignItems: 'flex-start'` — altsaa en bredde der kommer FRA indholdet, og
  // boern der ikke straekkes. En procent resolver mod foraelderens definite
  // bredde; har foraelderen ingen, bliver den nul. Med `overflow: 'hidden'`
  // og en hoejde paa 160 giver det praecis det Bjoern saa: ingenting.
  //
  // Det er ogsaa hvorfor BILLEDER virker i samme wrapper: de har fast
  // `width: 240`. Widget'en var det eneste barn med en procent.
  //
  // Maalt foerst: blokken NAAR frem (se MessageAttachments.test), telefonen
  // koerer 282, og APK'en har baade det native modul og JS-koden. Alt andet
  // var udelukket foer denne linje blev roert.
  //
  // `alignSelf: 'stretch'` loeser det ikke: et straakt barn har ingen egen
  // bredde at give en foraelder der selv skal maales af sine boern.
  // EN TOM RAMME MAA IKKE KUNNE FORBLIVE TVETYDIG (6/10-2026).
  //
  // To rettelser i traek ramte ved siden af, fordi en blank flade ikke kan
  // skelne «indlaeste aldrig» fra «indlaeste og malede intet» fra «fejlede
  // tavst». WebView'ens egne fejl-callbacks blev slet ikke lyttet paa, saa en
  // fejl forsvandt. Nu siger rammen hvad der skete — paa skaermen, hvor den
  // der ser problemet ogsaa kan laese svaret.
  //
  // TREDJE GANG, 7/10-2026 — og denne gang var det MIN EGEN komponent der loej:
  // `onLoadEnd` satte tilstanden til «klar» og SKJULTE dermed fejlbeskeden.
  // Biblioteket kalder `onError` FOER `onLoadEnd` (se `onLoadingError` i
  // `WebViewShared.tsx`), saa fejlen naaede at blive skrevet og blev derefter
  // overskrevet i samme render. En hvilken som helst indlaesningsfejl var
  // derfor usynlig — og det er praecis derfor tre runder gik med at gaette.
  //
  // Reglen er nu: en tilstand der beskriver noget GALT maa ikke kunne
  // overskrives af en tilstand der beskriver noget godt. `onLoadEnd` maa kun
  // loefte «indlaeser»/«starter», aldrig slette en fejl.
  const [tilstand, setTilstand] = useState<string>('indlaeser')
  // Dokumentet har RAPPORTERET sin hoejde = det koerer og kan maales. Foerst da
  // forsvinder statuslinjen. En tom ramme kan derfor ikke laengere vaere tavs:
  // staar der tekst, er der noget galt, og teksten siger hvad.
  const [malet, setMalet] = useState(false)
  useEffect(() => {
    setTilstand('indlaeser')
    setMalet(false)
    const t = setTimeout(() => {
      setTilstand((n) => (n === 'indlaeser' ? 'svarede ikke paa 6 sekunder' : n))
    }, 6000)
    return () => clearTimeout(t)
  }, [html])

  const vindue = useWindowDimensions()
  const bredde = Math.max(240, Math.round(vindue.width) - 2 * SIDE_LUFT)
  // Teksten er FAERDIG-MAERKET naar den naar hertil.
  const onPrompt = useContext(WidgetPrompt)
  const sendte = useRef({ antal: 0, sidst: 0 })


  if (!html) {
    return <Text style={styles.fejl}>Widget kunne ikke vises: tomt dokument</Text>
  }
  if (html.length > MAX_WIDGET_BYTES) {
    return <Text style={styles.fejl}>Widget kunne ikke vises: for stor</Text>
  }

  const haandterBesked = (e: { nativeEvent: { data?: string } }) => {
    try {
      const d = JSON.parse(String(e.nativeEvent.data || '{}'))

      if (d?.type === 'jarvis-widget-hoejde') {
        const h = Number(d.hoejde)
        if (!Number.isFinite(h) || h <= 0) return
        setMalet(true)
        setHoejde(Math.min(Math.max(Math.round(h), 48), INLINE_MAKS_HOEJDE))
        return
      }

      if (d?.type === 'jarvis-widget-prompt') {
        const nu = Date.now()
        if (sendte.current.antal >= MAX_PROMPTS) return
        if (nu - sendte.current.sidst < MIN_MS_MELLEM) return
        const tekst = typeof d.tekst === 'string' ? d.tekst.trim() : ''
        if (!tekst || tekst.length > MAX_PROMPT_TEGN) return
        const maerke = typeof d.maerke === 'string' ? d.maerke.trim() : ''
        if (!maerke.startsWith('[fra widget')) return
        sendte.current = { antal: sendte.current.antal + 1, sidst: nu }
        onPrompt?.(`${maerke} ${tekst}`)
      }
    } catch {
      // En uparsebar besked er hverken en hoejde eller en prompt.
    }
  }

  const flade = (testID: string, iFuldSkaerm: boolean) => (
    <WebView
      testID={testID}
      accessibilityLabel={iFuldSkaerm ? `${titel || 'Widget'} i fuld skærm` : (titel || 'widget')}
      source={{ html: medMobilViewport(html) }}
      originWhitelist={[]}
      onShouldStartLoadWithRequest={(req) => {
        const ok = dokumentets_egen(req?.url)
        if (!ok) setTilstand(`blokeret: ${String(req?.url ?? '')}`)
        return ok
      }}
      androidLayerType="hardware"
      onLoadStart={(e) =>
        setTilstand((n) => (n === 'indlaeser' ? `starter: ${String(e?.nativeEvent?.url ?? '?')}` : n))
      }
      onLoadEnd={() =>
        setTilstand((n) =>
          n === 'indlaeser' || n.startsWith('starter')
            ? 'loadet — men dokumentet svarede ikke'
            : n,
        )
      }
      onError={(e) => setTilstand(`fejl: ${String(e?.nativeEvent?.description || 'ukendt')}`)}
      onHttpError={(e) => setTilstand(`http ${e?.nativeEvent?.statusCode ?? '?'}`)}
      onRenderProcessGone={() => setTilstand('webview-processen doede')}
      javaScriptEnabled
      injectedJavaScript={HOEJDE_SCRIPT}
      onMessage={haandterBesked}
      domStorageEnabled={false}
      allowFileAccess={false}
      allowFileAccessFromFileURLs={false}
      allowUniversalAccessFromFileURLs={false}
      allowsInlineMediaPlayback={false}
      mediaPlaybackRequiresUserAction
      setSupportMultipleWindows={false}
      incognito
      cacheEnabled={false}
      thirdPartyCookiesEnabled={false}
      scrollEnabled={iFuldSkaerm}
      nestedScrollEnabled={iFuldSkaerm}
      scalesPageToFit
      setBuiltInZoomControls
      setDisplayZoomControls={false}
      style={iFuldSkaerm ? styles.fullWeb : styles.web}
      backgroundColor="transparent"
    />
  )

  return (
    <>
      <View style={[styles.ramme, { height: hoejde, width: bredde }]}>
        {!malet ? (
          <Text style={styles.tilstand} testID="widget-tilstand">
            {tilstand === 'indlaeser' ? 'Widget indlaeses…' : `Widget: ${tilstand}`}
          </Text>
        ) : null}
        {flade('widget-webview', false)}
        <Pressable
          testID="widget-expand"
          accessibilityRole="button"
          accessibilityLabel="Åbn widget i fuld skærm"
          hitSlop={8}
          onPress={() => setFuld(true)}
          style={styles.udvid}
        >
          <Maximize2 size={18} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
      </View>
      <Modal visible={fuld} animationType="fade" onRequestClose={() => setFuld(false)}>
        {fuld ? (
          <View style={styles.fullRoot}>
            <View style={styles.fullTop}>
              <Text style={styles.fullTitel} numberOfLines={1}>{titel || 'Widget'}</Text>
              <Pressable
                testID="widget-close"
                accessibilityRole="button"
                accessibilityLabel="Luk widget"
                hitSlop={10}
                onPress={() => setFuld(false)}
                style={styles.luk}
              >
                <X size={22} color={tokens.color.fg1} strokeWidth={2} />
              </Pressable>
            </View>
            {flade('widget-fullscreen-webview', true)}
          </View>
        ) : null}
      </Modal>
    </>
  )
}

const styles = StyleSheet.create({
  // Kanten er ikke pynt: en tom ramme UDEN kant er usynlig, og saa kan ingen —
  // heller ikke den der kigger paa skaermen — se forskel paa «widget'en er der
  // ikke» og «widget'en er der og maler intet».
  ramme: {
    marginVertical: 4,
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(128,128,128,0.45)',
    borderRadius: 10,
  },
  web: { flex: 1, backgroundColor: 'transparent' },
  udvid: {
    position: 'absolute', top: 8, right: 8, zIndex: 2,
    width: 36, height: 36, borderRadius: 18,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: 'rgba(20,20,20,0.84)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(255,255,255,0.22)',
  },
  fullRoot: { flex: 1, backgroundColor: tokens.color.bg0 },
  fullTop: {
    minHeight: 60, paddingHorizontal: tokens.spacing.lg,
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: tokens.color.line,
  },
  fullTitel: { flex: 1, color: tokens.color.fg1, fontSize: 15, fontWeight: '700' },
  luk: {
    width: 40, height: 40, borderRadius: 20,
    alignItems: 'center', justifyContent: 'center', backgroundColor: tokens.color.bg2,
  },
  fullWeb: { flex: 1, backgroundColor: 'transparent' },
  tilstand: {
    position: 'absolute', top: 6, left: 10, zIndex: 1,
    fontSize: 12, opacity: 0.75,
  },
  fejl: { fontSize: 13, opacity: 0.8, paddingVertical: 8, paddingHorizontal: 10 },
})
