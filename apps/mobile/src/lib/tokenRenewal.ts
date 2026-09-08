/**
 * Fornyelse af bearer-tokenet — så telefonen ikke låses ude af tiden alene.
 *
 * Mikkels telefon gav 927 × 401 på seks timer med grunden `token expired`.
 * Den havde ingen vej tilbage: tokenet er en JWT med fast udløbsdato, og
 * eneste kur var at Bjørn mintede et nyt og fik det installeret i hånden.
 *
 * Serveren har nu `POST /api/auth/renew`, som veksler det medsendte token —
 * også et der ER udløbet, inden for et nådevindue. Denne fil er klientens
 * halvdel: tjek ved opstart, og forny i god tid.
 *
 * ## Hvorfor "i god tid" og ikke "når det fejler"
 *
 * Fordi et token der udløber mens telefonen ligger i en skuffe ikke fejler —
 * det bliver bare gammelt. Fornyer vi først ved 401, er vi afhængige af at
 * nådevinduet ikke er løbet ud. Fornyer vi ved en tredjedel tilbage, når en
 * enhed der bruges normalt aldrig i nærheden af udløb.
 */
import type { ApiConfig } from './types'

/** Forny når der er mindre end en tredjedel af levetiden tilbage. */
const FORNY_VED_ANDEL = 1 / 3

export interface TokenKrav {
  iat: number
  exp: number
}

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'  // pragma: allowlist secret (base64url-alfabetet, ikke en nøgle)

/**
 * Læs `iat`/`exp` ud af et JWT uden at verificere det.
 *
 * Egen base64url-afkoder frem for `atob`: den findes ikke pålideligt i alle
 * React Native-runtimes, og en fornyelse der stille kaster på nogle telefoner
 * ville være værre end ingen fornyelse. Kravene er ren ASCII.
 *
 * Signaturen betyder intet her — vi bruger kun tallene til at beslutte HVORNÅR
 * vi spørger serveren. Serveren verificerer.
 */
export function laesKrav(token: string): TokenKrav | null {
  const dele = String(token || '').split('.')
  if (dele.length !== 3) return null
  const raw = dele[1] ?? ''
  let bits = 0
  let antal = 0
  let ud = ''
  for (const tegn of raw) {
    const v = B64.indexOf(tegn)
    if (v < 0) continue
    bits = (bits << 6) | v
    antal += 6
    if (antal >= 8) {
      antal -= 8
      ud += String.fromCharCode((bits >> antal) & 0xff)
    }
  }
  try {
    const krav = JSON.parse(ud)
    const iat = Number(krav?.iat)
    const exp = Number(krav?.exp)
    if (!Number.isFinite(iat) || !Number.isFinite(exp)) return null
    return { iat, exp }
  } catch {
    return null
  }
}

/** Er det tid til at forny? Et token vi ikke kan læse forsøger vi også på. */
export function boerFornys(token: string, nuMs: number = Date.now()): boolean {
  const krav = laesKrav(token)
  if (!krav) return true
  const levetid = krav.exp - krav.iat
  if (levetid <= 0) return true
  const tilbage = krav.exp - nuMs / 1000
  return tilbage < levetid * FORNY_VED_ANDEL
}

/**
 * Forny tokenet hvis det trænger. Returnerer den config der skal bruges —
 * den nye hvis det lykkedes, ellers den gamle uændret.
 *
 * Fejler ALDRIG udad: en telefon uden net skal starte på det token den har,
 * ikke gå i stå på et fornyelsesforsøg.
 */
export async function fornyOmNoedvendigt(
  config: ApiConfig,
  gem: (c: ApiConfig) => Promise<void>,
  nuMs: number = Date.now()
): Promise<ApiConfig> {
  if (!config?.authToken || !boerFornys(config.authToken, nuMs)) return config
  try {
    const svar = await fetch(`${config.apiBaseUrl}api/auth/renew`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${config.authToken}` }
    })
    if (!svar.ok) return config
    const krop = await svar.json()
    const nyt = String(krop?.token || '').trim()
    if (!nyt) return config
    const naeste: ApiConfig = { ...config, authToken: nyt }
    await gem(naeste)
    return naeste
  } catch {
    // Uden net, eller serveren er nede. Vi prøver igen næste gang appen åbner;
    // nådevinduet på serveren er der netop for at det må tage tid.
    return config
  }
}
