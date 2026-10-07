import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { StyleSheet, Text, View, useWindowDimensions } from 'react-native'
import { WebView } from 'react-native-webview'

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

  return (
    <View style={[styles.ramme, { height: hoejde, width: bredde }]}>
      <WebView
        testID="widget-webview"
        accessibilityLabel={titel || 'widget'}
        // INTET baseUrl — se komponentens docstring.
        source={{ html }}
        originWhitelist={[]}
        // GATEN SER PAA ADRESSEN, IKKE PAA HVOR MANGE GANGE DEN ER KALDT.
        //
        // Foerste udgave talte: «foerste kald = dokumentet, alt derefter =
        // navigation». Det var forkert. Android indlaeser `source={{html}}` med
        // `loadDataWithBaseURL("about:blank", …)` og fyrer navigations-tjekket
        // MERE END EN GANG for den ene indlaesning — saa taelleren slap den
        // foerste igennem og blokerede selve dokumentet. Bjoern saa en tom
        // ramme hvor widget'en skulle staa (6/10-2026).
        //
        // `about:blank` og `data:` ER dokumentet. Alt andet er navigation ud af
        // sandkassen og afvises. Det er baade rigtigere og strammere end at
        // taelle: en gate der siger HVAD den tillader kan ikke narres af
        // hvor mange gange den bliver spurgt.
        //
        // Bemaerk at `originWhitelist` ikke daekker det: biblioteket laegger
        // selv `about:blank` foerst i listen (`compileWhitelist` i
        // WebViewShared), saa en tom liste tillader stadig dokumentet. Gaten
        // her er den der afgoer sagen.
        onShouldStartLoadWithRequest={(req) => dokumentets_egen(req?.url)}
        javaScriptEnabled
        injectedJavaScript={HOEJDE_SCRIPT}
        onMessage={(e) => {
          try {
            const d = JSON.parse(String(e.nativeEvent.data || '{}'))

            if (d?.type === 'jarvis-widget-hoejde') {
              const h = Number(d.hoejde)
              if (!Number.isFinite(h) || h <= 0) return
              setHoejde(Math.min(Math.max(Math.round(h), 48), 1200))
              return
            }

            if (d?.type === 'jarvis-widget-prompt') {
              const nu = Date.now()
              if (sendte.current.antal >= MAX_PROMPTS) return
              if (nu - sendte.current.sidst < MIN_MS_MELLEM) return
              const tekst = typeof d.tekst === 'string' ? d.tekst.trim() : ''
              if (!tekst || tekst.length > MAX_PROMPT_TEGN) return
              // MAERKET kommer fra serveren. Mangler det, sender vi IKKE: en
              // umaerket besked ville laeses som Bjoerns egne ord.
              const maerke = typeof d.maerke === 'string' ? d.maerke.trim() : ''
              if (!maerke.startsWith('[fra widget')) return
              sendte.current = { antal: sendte.current.antal + 1, sidst: nu }
              onPrompt?.(`${maerke} ${tekst}`)
            }
          } catch {
            // En uparsebar besked er hverken en hoejde eller en prompt.
          }
        }}
        // Alt herunder er lukket MED VILJE og staar eksplicit, saa en aendret
        // standard i biblioteket ikke kan aabne noget.
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
        scrollEnabled={false}
        // Gennemsigtig, saa dokumentets egen gennemsigtige baggrund lader
        // trådens flade skinne igennem i baade lyst og moerkt tema.
        style={styles.web}
        backgroundColor="transparent"
      />
    </View>
  )
}

const styles = StyleSheet.create({
  ramme: { marginVertical: 4, overflow: 'hidden' },
  web: { flex: 1, backgroundColor: 'transparent' },
  fejl: { fontSize: 13, opacity: 0.8, paddingVertical: 8, paddingHorizontal: 10 },
})
