import { useEffect, useState } from 'react'
import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native'
import { useVideoPlayer, VideoView } from 'expo-video'
import type { ApiConfig } from '../lib/types'
import { useTheme, type Theme } from '../theme/ThemeContext'
import { hentTilCache } from './AuthImage'

/**
 * En video bag en beskyttet rute.
 *
 * ## Samme fælde som billederne, samme løsning
 *
 * React Natives medie-loadere sender ikke `Authorization` med. Målt
 * 12/9-2026 svarede serveren 401 på fire billeder hentet den vej, mens
 * listningen af de samme billeder med det samme token gik igennem. Derfor
 * henter `AuthImage` filen med `FileSystem` og peger `Image` på den lokale
 * kopi — og derfor gør denne det samme for video.
 *
 * Det er også grunden til at afspilleren ikke behøver kunne headers: den ser
 * kun en fil på telefonen. Enhver afspiller kan spille en lokal fil.
 *
 * ## Hvorfor der ikke er nogen animeret plads
 *
 * `AuthImage` har en `BilledePlads` der glider mens billedet hentes. Den
 * hører hjemme dér, hvor ventetiden ER hentningen. For video er hentningen
 * kort og GENERERINGEN lang (op til 600 s) — og den har sin egen animation i
 * `VideoGenerationCard`, mens værktøjet kører. Her står blot et roligt felt.
 */
export function AuthVideo({
  config, url, navn, style, testID,
}: {
  config: ApiConfig
  url: string
  /** Stabilt navn til den lokale kopi — normalt attachment-id'et. */
  navn: string
  style?: StyleProp<ViewStyle>
  testID?: string
}) {
  const tokens = useTheme()
  const styles = stilAf(tokens)
  const [lokal, setLokal] = useState<string | null>(null)
  const [fejlede, setFejlede] = useState(false)

  useEffect(() => {
    let levende = true
    setFejlede(false)
    void hentTilCache(config, url, navn, 'vid-')
      .then((sti) => { if (levende) setLokal(sti) })
      .catch(() => { if (levende) { setLokal(null); setFejlede(true) } })
    return () => { levende = false }
  }, [config.apiBaseUrl, config.authToken, url, navn])

  // Hooket skal kaldes ubetinget — en tidlig return over det ville bryde
  // hook-rækkefølgen og tage HELE visningen med sig (det skete 20/9-2026 i
  // desk af samme grund). Null er en lovlig kilde og giver en tom afspiller.
  const player = useVideoPlayer(lokal, (p) => { p.loop = false })

  if (fejlede) {
    return (
      <View style={[styles.plads, style]} testID={testID}>
        <Text style={styles.besked}>{navn} kunne ikke hentes</Text>
      </View>
    )
  }
  if (!lokal) {
    return (
      <View style={[styles.plads, style]} testID={testID} accessibilityLabel="Henter video">
        <Text style={styles.besked}>Henter video…</Text>
      </View>
    )
  }
  return (
    <VideoView
      testID={testID}
      player={player}
      style={[styles.afspiller, style]}
      nativeControls
      contentFit="contain"
    />
  )
}

const stilAf = (tokens: Theme) => StyleSheet.create({
  afspiller: { width: '100%', aspectRatio: 16 / 9, borderRadius: 12, backgroundColor: tokens.color.bg3 },
  plads: {
    width: '100%', aspectRatio: 16 / 9, borderRadius: 12,
    backgroundColor: tokens.color.bg3, alignItems: 'center', justifyContent: 'center',
  },
  besked: { color: tokens.color.fg3, fontSize: 12 },
})
