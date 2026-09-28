/** Indstillingernes STRUKTUR — grupperne og deres punkter, i den rækkefølge
 * brugeren møder dem.
 *
 * Hvorfor en fil og ikke bare JSX i skærmen: rækkefølgen ER beslutningen her,
 * og den kan ikke bo to steder. Skærmen OG testen læser begge herfra, så de
 * ikke kan drive fra hinanden — flytter man et punkt, flytter testen med. Det
 * er samme fejlklasse som model-navnene og `ThinkingMode`, der begge lå
 * erklæret to steder og kun holdt hinanden i sync ved held.
 *
 * Fire grupper + «Avanceret» i bunden. Pointen med Avanceret er ikke at skjule
 * noget — det hele er der stadig — men at teknikken (diagnostik, API-test,
 * device-presence, tankestrøm, boble) ikke skal stå side om side med «lys eller
 * mørk» for en der lige har hentet appen. Målt før omlægningen: «Udseende» var
 * den niende sektion, efter fire tekniske helbreds-fliser og fire sektioner.
 *
 * `noegle` er søgeordene, skrevet som ord en bruger faktisk ville skrive —
 * «mørk», «dansk», «husker» — ikke som kode-navne. Søgefeltet matcher mod dem.
 */

export type SettingsPunktId =
  | 'udseende'
  | 'sprog'
  | 'svarstil'
  | 'hukommelse'
  | 'sanser'
  | 'lokation'
  | 'batteri'
  | 'enheder'
  | 'tjenester'
  | 'notifikationer'
  | 'google'
  | 'forbind'
  | 'konto'
  | 'data'
  | 'status'
  | 'diagnostik'
  | 'chat'
  | 'boble'

export type SettingsPunkt = { id: SettingsPunktId; noegle: string }
export type SettingsGruppe = { navn: string; punkter: SettingsPunkt[] }

export const SETTINGS_GRUPPER: SettingsGruppe[] = [
  {
    navn: 'Jarvis',
    punkter: [
      { id: 'udseende', noegle: 'udseende lys mørk tema farve accent' },
      { id: 'sprog', noegle: 'sprog dansk engelsk' },
      { id: 'svarstil', noegle: 'svarstil hvordan svarer jarvis' },
      { id: 'hukommelse', noegle: 'hukommelse husker memory glem' }
    ]
  },
  {
    navn: 'Sanser & privatliv',
    punkter: [
      { id: 'sanser', noegle: 'sanser privatliv sensor kamera mikrofon dashboard' },
      { id: 'lokation', noegle: 'lokation gps hvor er jeg del' },
      { id: 'batteri', noegle: 'batteri optimering strøm' }
    ]
  },
  {
    navn: 'Forbindelser',
    punkter: [
      { id: 'enheder', noegle: 'enheder telefoner devices parret' },
      { id: 'tjenester', noegle: 'tjenester plugins connectors tilsluttede' },
      { id: 'notifikationer', noegle: 'notifikationer push beskeder' },
      { id: 'google', noegle: 'google konto login' },
      { id: 'forbind', noegle: 'forbind enhed qr parre ny telefon' }
    ]
  },
  {
    navn: 'Data & konto',
    punkter: [
      { id: 'konto', noegle: 'konto email rolle tier forbindelse' },
      { id: 'data', noegle: 'dine data slet eksport datastyring' }
    ]
  },
  {
    navn: 'Avanceret',
    punkter: [
      { id: 'status', noegle: 'status forbindelse push mikrofon kamera' },
      { id: 'diagnostik', noegle: 'diagnostik test api device presence' },
      { id: 'chat', noegle: 'chat tankestrøm tænkning' },
      { id: 'boble', noegle: 'chatboble flydende boble' }
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
 * «theme mode». */
export function matcherSoegning(noegle: string, soeg: string): boolean {
  const q = soeg.trim().toLowerCase()
  return q.length === 0 || noegle.toLowerCase().includes(q)
}
