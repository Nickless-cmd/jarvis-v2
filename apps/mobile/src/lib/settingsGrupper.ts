/** Indstillingernes STRUKTUR — grupperne, deres punkter og det man ser på
 * rækken, i den rækkefølge brugeren møder dem.
 *
 * Hvorfor en fil og ikke bare JSX i skærmen: rækkefølgen ER beslutningen her,
 * og den kan ikke bo to steder. Skærmen OG testen læser begge herfra, så de
 * ikke kan drive fra hinanden — flytter man et punkt, flytter testen med. Det
 * er samme fejlklasse som model-navnene og `ThinkingMode`, der begge lå
 * erklæret to steder og kun holdt hinanden i sync ved held.
 *
 * ## Formen: en RÆKKE, ikke en sektion
 *
 * Skærmen var én flad rulleliste hvor hver indstilling stod foldet ud med sine
 * knapper. «Udseende» fyldte tre store valg plus seks farvecirkler, før man
 * overhovedet nåede «Sprog». Man kunne ikke SE hvad der fandtes — kun rulle
 * til man faldt over det.
 *
 * Nu er hvert punkt én række: `ikon · navn · nuværende værdi · ›`. Værdien er
 * pointen — «Mørk», «Dansk», «Slukket» svarer på «hvordan står det egentlig?»
 * uden at man åbner noget, og en forkert indstilling kan ses med ét blik.
 * Indholdet er uændret; det ligger bag rækken i stedet for under den.
 *
 * ## Avanceret er en RÆKKE, ikke en gruppe
 *
 * Diagnostik, API-test, device-presence, tankestrøm, chatboble og de fire
 * helbreds-fliser er stadig der — de fylder bare ikke for en der lige har
 * hentet appen. En femte gruppe ville stille dem side om side med «lys eller
 * mørk» igen, bare med en overskrift over.
 *
 * `noegle` er søgeordene, skrevet som ord en bruger faktisk ville skrive —
 * «mørk», «dansk», «husker» — ikke som kode-navne. Søgefeltet matcher mod dem,
 * så «mikrofon» finder rækken selv om den bor under Sanser.
 */

export type SettingsPunktId =
  | 'udseende'
  | 'sprog'
  | 'svarstil'
  | 'hukommelse'
  | 'sanser'
  | 'lokation'
  | 'batteri'
  | 'tjenester'
  | 'notifikationer'
  | 'enheder'
  | 'data'
  | 'avanceret'

/** Ikonets navn i `lucide-react-native`. Skærmen slår op i sit eget kort — en
 *  streng her holder strukturen fri af React, så den kan testes uden at
 *  rendere noget. */
export type IkonNavn =
  | 'palette' | 'globe' | 'message-circle' | 'brain'
  | 'camera' | 'map-pin' | 'shield'
  | 'plug' | 'bell' | 'smartphone'
  | 'database' | 'flask-conical'

export type SettingsPunkt = {
  id: SettingsPunktId
  /** Det man læser på rækken. */
  navn: string
  ikon: IkonNavn
  noegle: string
}

export type SettingsGruppe = { navn: string; punkter: SettingsPunkt[] }

export const SETTINGS_GRUPPER: SettingsGruppe[] = [
  {
    navn: 'Jarvis',
    punkter: [
      { id: 'udseende', navn: 'Udseende', ikon: 'palette',
        noegle: 'udseende lys mørk tema farve accent' },
      { id: 'sprog', navn: 'Sprog', ikon: 'globe',
        noegle: 'sprog dansk engelsk' },
      { id: 'svarstil', navn: 'Svarstil', ikon: 'message-circle',
        noegle: 'svarstil hvordan svarer jarvis tone' },
      { id: 'hukommelse', navn: 'Hukommelse', ikon: 'brain',
        noegle: 'hukommelse husker memory glem' }
    ]
  },
  {
    navn: 'Sanser & privatliv',
    punkter: [
      { id: 'sanser', navn: 'Kamera & mikrofon', ikon: 'camera',
        noegle: 'sanser privatliv sensor kamera mikrofon dashboard' },
      { id: 'lokation', navn: 'Lokation', ikon: 'map-pin',
        noegle: 'lokation gps hvor er jeg del' },
      { id: 'batteri', navn: 'Privatliv & batteri', ikon: 'shield',
        noegle: 'batteri optimering strøm privatliv baggrund' }
    ]
  },
  {
    navn: 'Forbindelser',
    punkter: [
      { id: 'tjenester', navn: 'Tjenester', ikon: 'plug',
        noegle: 'tjenester plugins connectors tilsluttede google' },
      { id: 'notifikationer', navn: 'Notifikationer', ikon: 'bell',
        noegle: 'notifikationer push beskeder' },
      { id: 'enheder', navn: 'Enheder', ikon: 'smartphone',
        noegle: 'enheder telefoner devices parret forbind qr ny telefon' }
    ]
  },
  {
    navn: 'Data & konto',
    punkter: [
      { id: 'data', navn: 'Dine data', ikon: 'database',
        noegle: 'dine data slet eksport datastyring konto email' },
      { id: 'avanceret', navn: 'Avanceret', ikon: 'flask-conical',
        noegle: 'avanceret diagnostik test api device presence status '
              + 'tankestrøm tænkning chatboble boble teknisk' }
    ]
  }
]

/** Alle punkt-id'er i visningsrækkefølge — flad, så rækkefølgen kan måles. */
export const SETTINGS_PUNKTER: SettingsPunktId[] = SETTINGS_GRUPPER.flatMap((g) =>
  g.punkter.map((p) => p.id)
)

/** Tom søgning viser alt. Ellers: er søgeordet en del af punktets ord?
 *
 * Delstreng og ikke fritekst-søgning med vilje: punkterne har håndskrevne ord
 * netop fordi et ord som «mørk» skal ramme udseende uden at brugeren skriver
 * «theme mode». Navnet er med i søgningen, så det man LÆSER også rammer. */
export function matcherSoegning(punkt: SettingsPunkt, soeg: string): boolean {
  const q = soeg.trim().toLowerCase()
  if (!q) return true
  return `${punkt.navn} ${punkt.noegle}`.toLowerCase().includes(q)
}


// ── Vaerdien paa hver raekke ──────────────────────────────────────────────
//
// «Hvordan staar det egentlig?» besvaret uden at aabne noget. Den bor her og
// ikke i skaermen, fordi den er en BESLUTNING — hvilke ord brugeren ser — og
// fordi den saa kan proeves uden at rendere noget.
//
// Tom streng betyder «denne raekke har ingen vaerdi» (Hukommelse, Dine data):
// saa staar der bare navnet. Det er ikke det samme som «ved ikke endnu», som
// ogsaa giver tom — en raekke maa hellere staa uden tal end med et forkert.

export type VaerdiKilde = {
  temaTilstand: 'light' | 'dark' | 'auto'
  sprog: 'da' | 'en' | 'auto' | null
  /** Navnet paa svarstilen, eller null mens den hentes. */
  svarstil: string | null
  kameraLyd: boolean
  lokation: 'off' | 'city' | 'area' | 'now' | 'precise' | 'background'
  batteriSparer: boolean
  /** null mens tjenesterne hentes — ellers antal AKTIVE. */
  aktiveTjenester: number | null
  /** null mens push-indstillingerne hentes. */
  pushTil: boolean | null
  antalEnheder: number
}

const LOKATION_ORD: Record<VaerdiKilde['lokation'], string> = {
  off: 'Slukket', city: 'By', area: 'Område',
  now: 'Kun nu', precise: 'Præcis', background: 'Baggrund',
}

export function settingsVaerdier(k: VaerdiKilde): Record<SettingsPunktId, string> {
  return {
    udseende: { light: 'Lys', dark: 'Mørk', auto: 'Automatisk' }[k.temaTilstand] ?? '',
    sprog: { da: 'Dansk', en: 'English', auto: 'Automatisk' }[k.sprog ?? 'auto'] ?? '',
    svarstil: k.svarstil ?? '',
    hukommelse: '',
    sanser: k.kameraLyd ? 'Til' : 'Fra',
    lokation: LOKATION_ORD[k.lokation] ?? '',
    batteri: k.batteriSparer ? 'Til' : 'Fra',
    tjenester: k.aktiveTjenester == null ? '' : `${k.aktiveTjenester} aktive`,
    notifikationer: k.pushTil == null ? '' : (k.pushTil ? 'Til' : 'Fra'),
    enheder: k.antalEnheder > 0 ? String(k.antalEnheder) : '',
    data: '',
    avanceret: 'Diagnostik m.m.',
  }
}
