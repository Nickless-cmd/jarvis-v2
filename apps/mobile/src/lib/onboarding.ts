import * as SecureStore from 'expo-secure-store'

/** Tilladelses-guiden: hvorfor, i rækkefølge, med lov til at sige nej.
 *
 *  Bjørn: «så kamera/mic/location/push ikke føles tilfældigt». Problemet med
 *  tilfældige pop-ups er ikke at de er mange — det er at de kommer UDEN
 *  grund. En dialog der spørger om lokation midt i en samtale om kode ligner
 *  overvågning; den samme dialog med «så han kan svare på hvor du er» er et
 *  tilbud.
 *
 *  Tre valg der bærer designet:
 *
 *  1. RÆKKEFØLGE efter hvad appen ikke kan undvære. Push først: uden den kan
 *     han ikke nå dig, og så er halvdelen af appen stum. Lokation sidst: den
 *     er den mest indgribende og den mindst nødvendige.
 *
 *  2. HVERT trin kan springes over. En guide man ikke kan komme ud af er en
 *     tvang, og så siger folk ja til alt for at komme videre — hvilket er
 *     værre end et ærligt nej.
 *
 *  3. Den vises ÉN gang. Har man sagt nej til kameraet, skal appen ikke blive
 *     ved med at spørge; det står i indstillinger, hvor man selv kan finde
 *     det når man får brug for det.
 */

export type Tilladelse = 'push' | 'mikrofon' | 'kamera' | 'lokation'

export interface Trin {
  tilladelse: Tilladelse
  titel: string
  /** HVORFOR — det er hele forskellen på et tilbud og en pop-up. */
  hvorfor: string
  /** Hvad man mister ved at sige nej. Ærligt, ikke truende. */
  udenDen: string
}

export const TRIN: Trin[] = [
  {
    tilladelse: 'push',
    titel: 'Må han sige til?',
    hvorfor: 'Så han kan nå dig når noget er færdigt, eller når han skal have lov til noget.',
    udenDen: 'Du skal selv åbne appen for at se om der er sket noget.',
  },
  {
    tilladelse: 'mikrofon',
    titel: 'Vil du kunne tale til ham?',
    hvorfor: 'Så du kan diktere i stedet for at skrive — også mens du går.',
    udenDen: 'Du kan stadig skrive. Stemme er slået fra.',
  },
  {
    tilladelse: 'kamera',
    titel: 'Må han se hvad du ser?',
    hvorfor: 'Så du kan vise ham en skærm, en fejl eller en ting frem for at beskrive den.',
    udenDen: 'Du kan stadig vedhæfte billeder fra galleriet.',
  },
  {
    tilladelse: 'lokation',
    titel: 'Skal han vide hvor du er?',
    hvorfor: 'Så «hvor længe hjem?» og «er der åbent?» kan besvares uden at du forklarer hvor.',
    udenDen: 'Du kan altid dele din position i den enkelte besked i stedet.',
  },
]

const NOEGLE = 'jarvis.onboarding.fuldfoert'

export async function erGennemfoert(): Promise<boolean> {
  try {
    return (await SecureStore.getItemAsync(NOEGLE)) === '1'
  } catch {
    // Kan vi ikke læse det, viser vi den ikke igen — at gentage guiden ved
    // hver start ville være værre end at springe den over.
    return true
  }
}

export async function markerGennemfoert(): Promise<void> {
  try {
    await SecureStore.setItemAsync(NOEGLE, '1')
  } catch {
    /* stille */
  }
}

/** Kun de trin der stadig giver mening. Har man allerede givet mikrofon i en
 *  tidligere version, skal guiden ikke spørge igen. */
export function resterendeTrin(alleredeGivet: Tilladelse[]): Trin[] {
  const givet = new Set(alleredeGivet)
  return TRIN.filter((t) => !givet.has(t.tilladelse))
}

export interface GuideStatus {
  faerdig: boolean
  trin: Trin | null
  nummer: number      // 1-baseret, til «2 af 4»
  ialt: number
}

export function statusFor(trin: Trin[], indeks: number): GuideStatus {
  if (indeks >= trin.length) return { faerdig: true, trin: null, nummer: trin.length, ialt: trin.length }
  return { faerdig: false, trin: trin[indeks] ?? null, nummer: indeks + 1, ialt: trin.length }
}
