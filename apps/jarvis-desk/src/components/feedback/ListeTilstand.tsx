import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'
import { SettingsState } from '../settings/SettingsState'

/**
 * Listens tre tilstande — bygget PÅ `SettingsState`, ikke ved siden af.
 *
 * ## Hvorfor (Codex' punkt 2, videregivet af Bjørn 21/9-2026)
 *
 * «Brugeren skal kunne se forskel på: der er endnu ikke tilføjet noget / det
 * bliver hentet / det kunne ikke hentes — prøv igen.»
 *
 * Målt i 0.6.64: 18 komponenter henter data ind i en liste, og **14 havde
 * ingen fejl-tilstand**. Falder kaldet, står der det samme som når kassen
 * bare er tom. (Én af de fjorten var min egen browser-rude fra samme aften.)
 *
 * ## Hvorfor den ikke er sin egen ordlyd
 *
 * Første udgave af denne fil var en DUBLET: `SettingsState` fandtes i
 * forvejen, brugt 15 steder, og sagde allerede «Henter …», «Kunne ikke hente
 * …» og «Prøv igen». At have to komponenter med hver sin formulering ville
 * give to slags app.
 *
 * De kan bare ikke bytte plads: `SettingsState` drives af `ResourceStatus`
 * fra `useSettingsResource`, og de fjorten paneler henter selv med almindelig
 * `useState`. Så den her oversætter panelernes form til den vokabular der
 * allerede findes — og tilføjer det ene den ikke dækker: den ÆGTE tomme
 * liste, som hidtil lå som løse `settings-empty`-afsnit hos hver kalder.
 */
export interface ListeTilstandProps {
  /** Henter vi lige nu? */
  henter?: boolean
  /** Slog hentningen fejl? */
  fejl?: boolean
  /** Hvad listen hedder i en sætning: «Kunne ikke hente {navn}.» */
  navn: string
  /** Hvor mange elementer listen fik. 0 + ingen fejl = ægte tom. */
  antal: number
  /** Hvad der står når kassen er tom, fordi der ikke ER noget endnu. */
  tomTekst: string
  /** Prøv igen. `null` når der ikke findes en vej videre. */
  onIgen: (() => void) | null
  children?: ReactNode
}

export function ListeTilstand({
  henter = false, fejl = false, navn, antal, tomTekst, onIgen, children,
}: ListeTilstandProps) {
  // Rækkefølgen er en påstand, og begge dele er pinnet i testene:
  //  * HENTER vinder — men kun når listen er TOM. Ellers ville en
  //    genhentning blinke «Henter…» forbi hver gang.
  //  * FEJL vinder over et gammelt resultat. Ellers ser man forrige
  //    hentnings data og tror de er friske.
  if (fejl) {
    return <SettingsState status="error" label={navn} onRetry={onIgen ?? (() => {})} />
  }
  if (henter && antal === 0) {
    return <SettingsState status="loading" label={navn} onRetry={() => {}} />
  }
  if (antal === 0) {
    return (
      <div className="liste-tom">
        <Inbox size={14} aria-hidden="true" />
        <span>{tomTekst}</span>
      </div>
    )
  }
  return <>{children}</>
}
