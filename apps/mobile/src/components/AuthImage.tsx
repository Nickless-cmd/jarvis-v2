import { useEffect, useState } from 'react'
import { Image, type ImageResizeMode, type StyleProp, type ImageStyle } from 'react-native'
import * as FileSystem from 'expo-file-system/legacy'
import type { ApiConfig } from '../lib/types'

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

  if (!lokal) return <Image source={{ uri: '' }} style={style} testID={testID} />
  return <Image source={{ uri: lokal }} style={style} resizeMode={resizeMode} testID={testID} />
}

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
