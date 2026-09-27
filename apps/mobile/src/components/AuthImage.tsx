import { useEffect, useRef, useState } from 'react'
import {
  Animated,
  Easing,
  Image,
  StyleSheet,
  View,
  type ImageResizeMode,
  type ImageStyle,
  type StyleProp,
  type ViewStyle,
} from 'react-native'
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg'
import * as FileSystem from 'expo-file-system/legacy'
import type { ApiConfig } from '../lib/types'
import { useReducedMotion } from '../lib/useReducedMotion'
import { useTheme } from '../theme/ThemeContext'

/**
 * Et billede bag en beskyttet rute.
 *
 * ## Hvorfor ikke bare `<Image source={{uri, headers}}>`
 *
 * Fordi den ikke virker. MÅLT 12/9-2026 på telefonen: gitteret hentede fire
 * billeder, og serveren svarede 401 på alle fire med
 * «missing or invalid bearer token» — mens listningen af de SAMME billeder,
 * med det SAMME token, gik igennem. React Natives billed-loader sendte
 * anmodningen uden headeren.
 *
 * Det er ikke en ny fejl. `MessageAttachments` har haft præcis samme mønster,
 * så billeder i tråden har været tomme felter på samme måde.
 *
 * Her hentes filen i stedet med `FileSystem`, som beviseligt bærer sin
 * Authorization igennem (samme vej som `installApk` og `aabnUdgivetFil`), og
 * `Image` peges på den lokale kopi. Cache-mappen, ikke dokument-mappen:
 * systemet må gerne rydde den.
 */
export function AuthImage({
  config, url, navn, style, resizeMode = 'cover', testID,
}: {
  config: ApiConfig
  url: string
  /** Stabilt navn til den lokale kopi — normalt attachment-id'et. */
  navn: string
  style?: StyleProp<ImageStyle>
  resizeMode?: ImageResizeMode
  testID?: string
}) {
  const [lokal, setLokal] = useState<string | null>(null)

  useEffect(() => {
    let levende = true
    void hentTilCache(config, url, navn)
      .then((sti) => { if (levende) setLokal(sti) })
      // Tavs: et billede der ikke kan hentes bliver et tomt felt, ikke et
      // braekket skaermbillede. Pladsen staar der stadig, saa gitteret ikke
      // hopper naar resten lander.
      .catch(() => { if (levende) setLokal(null) })
    return () => { levende = false }
  }, [config.apiBaseUrl, config.authToken, url, navn])

  if (!lokal) return <BilledePlads stil={style} testID={testID} />
  return <Image source={{ uri: lokal }} style={style} resizeMode={resizeMode} testID={testID} />
}

/**
 * Pladsen mens billedet hentes.
 *
 * ## Hvorfor ikke bare et tomt felt
 *
 * Før stod der `<Image source={{ uri: '' }}>` — et felt uden indhold. Det
 * sagde hverken «der kommer noget» eller «noget gik i stykker», og på et
 * genereret billede, hvor ventetiden er 20-60 s, stod hullet længe nok til at
 * man troede det var en fejl. Bjørn pegede på det 27/9-2026 med ChatGPT-appen
 * som facit: dér ANIMERER pladsen mens billedet laves.
 *
 * Nu står der en flade i SAMME størrelse med et bånd der glider hen over.
 * Formen siger «her lander det», bevægelsen siger «det tager tid» — samme
 * sprog som resten af tråden (`StreamIndicator`, `Prikker`).
 *
 * ## Hvorfor bredden måles
 *
 * Båndet skal glide præcis sin egen bredde, så loop-resettet sker mens det er
 * uden for kanten (ellers ser man et hak hver 1,4 s). Størrelsen kommer fra
 * kalderens stil — 240×240 i tråden, andet i fuldskærm — så vi kan ikke kende
 * den på forhånd. `onLayout` giver den, og indtil da tegnes kun fladen.
 *
 * «Reducer bevægelse» respekteres: så står fladen helt stille.
 */
function BilledePlads({ stil, testID }: { stil?: StyleProp<ImageStyle>; testID?: string }) {
  const tokens = useTheme()
  const reduced = useReducedMotion()
  const glid = useRef(new Animated.Value(0)).current
  const [maal, setMaal] = useState({ b: 0, h: 0 })

  useEffect(() => {
    if (reduced || maal.b <= 0) {
      glid.stopAnimation()
      glid.setValue(0)
      return
    }
    glid.setValue(0)
    const loop = Animated.loop(
      Animated.timing(glid, {
        toValue: 1,
        duration: 1400,
        easing: Easing.inOut(Easing.ease),
        useNativeDriver: true,
      }),
    )
    loop.start()
    return () => loop.stop()
  }, [glid, maal.b, reduced])

  // -B → +B: ved begge yderpunkter er det B-brede bånd helt uden for fladen,
  // så resettet er usynligt. Ved reduceret bevægelse står `glid` på 0, altså
  // helt til venstre — fladen er ren.
  const translateX = maal.b > 0
    ? glid.interpolate({ inputRange: [0, 1], outputRange: [-maal.b, maal.b] })
    : 0

  return (
    <View
      testID={testID}
      accessibilityLabel="Henter billede"
      onLayout={(e) => {
        const b = Math.round(e.nativeEvent.layout.width)
        const h = Math.round(e.nativeEvent.layout.height)
        if (b > 0 && (b !== maal.b || h !== maal.h)) setMaal({ b, h })
      }}
      // Kalderens stil bærer størrelse, radius og baggrund — den skal med, så
      // pladsen optager præcis den plads billedet får. `overflow: hidden` er
      // vores egen: uden den tegner båndet hen over naboerne i tråden.
      style={[stil as unknown as StyleProp<ViewStyle>, stilPlads.plads]}
    >
      {maal.b > 0 && maal.h > 0 ? (
        <Animated.View style={{ width: maal.b, transform: [{ translateX }] }}>
          <Svg width={maal.b} height={maal.h}>
            <Defs>
              <LinearGradient id="billedeplads" x1="0" y1="0" x2="1" y2="0">
                <Stop offset="0" stopColor={tokens.color.fg3} stopOpacity="0" />
                <Stop offset="0.5" stopColor={tokens.color.fg3} stopOpacity="0.28" />
                <Stop offset="1" stopColor={tokens.color.fg3} stopOpacity="0" />
              </LinearGradient>
            </Defs>
            <Rect width={maal.b} height={maal.h} fill="url(#billedeplads)" />
          </Svg>
        </Animated.View>
      ) : null}
    </View>
  )
}

const stilPlads = StyleSheet.create({
  plads: { overflow: 'hidden' },
})

/**
 * Hent én gang, genbrug bagefter.
 *
 * Findes filen allerede, hentes den ikke igen — et galleri man ruller frem og
 * tilbage i, må ikke hente det samme billede ti gange over mobilnettet.
 */
export async function hentTilCache(
  config: ApiConfig, url: string, navn: string,
): Promise<string> {
  const rent = String(navn || 'b').replace(/[^A-Za-z0-9._-]/g, '_')
  const dest = `${FileSystem.cacheDirectory}img-${rent}`
  const info = await FileSystem.getInfoAsync(dest)
  if (info.exists && (info.size ?? 0) > 0) return dest
  const opg = FileSystem.createDownloadResumable(
    url, dest,
    { headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {} },
  )
  const res = await opg.downloadAsync()
  if (!res?.uri) throw new Error('hentningen gav ingen fil')
  return res.uri
}
