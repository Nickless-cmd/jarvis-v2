import { useEffect, useRef, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
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

export function WidgetFlade({ html, titel }: { html: string; titel?: string }) {
  const [hoejde, setHoejde] = useState(160)
  const foerste = useRef(true)

  useEffect(() => { foerste.current = true }, [html])

  if (!html) {
    return <Text style={styles.fejl}>Widget kunne ikke vises: tomt dokument</Text>
  }
  if (html.length > MAX_WIDGET_BYTES) {
    return <Text style={styles.fejl}>Widget kunne ikke vises: for stor</Text>
  }

  return (
    <View style={[styles.ramme, { height: hoejde }]}>
      <WebView
        testID="widget-webview"
        accessibilityLabel={titel || 'widget'}
        // INTET baseUrl — se komponentens docstring.
        source={{ html }}
        originWhitelist={[]}
        // Den foerste indlaesning ER dokumentet selv; alt derefter er
        // navigation og afvises.
        onShouldStartLoadWithRequest={() => {
          if (foerste.current) { foerste.current = false; return true }
          return false
        }}
        javaScriptEnabled
        injectedJavaScript={HOEJDE_SCRIPT}
        onMessage={(e) => {
          try {
            const d = JSON.parse(String(e.nativeEvent.data || '{}'))
            if (d?.type !== 'jarvis-widget-hoejde') return
            const h = Number(d.hoejde)
            if (!Number.isFinite(h) || h <= 0) return
            setHoejde(Math.min(Math.max(Math.round(h), 48), 1200))
          } catch {
            // En uparsebar besked er ikke en hoejde. Ingen handling.
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
  ramme: { width: '100%', marginVertical: 4, overflow: 'hidden' },
  web: { flex: 1, backgroundColor: 'transparent' },
  fejl: { fontSize: 13, opacity: 0.8, paddingVertical: 8, paddingHorizontal: 10 },
})
