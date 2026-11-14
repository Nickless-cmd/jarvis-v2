/**
 * Udfaldet af en handling en FLADE satte i gang — ikke af turen den startede.
 *
 * ## Hvorfor den findes (14/11-2026)
 *
 * En flade kunne indtil nu råbe en sætning ind i samtalen og fik intet igen.
 * `WidgetPrompt` var `(tekst) => void`, så fladen kunne ikke se om nogen
 * lyttede. To fejl fulgte af det, og begge er den form Bjørn kalder teater:
 *
 * 1. **Den tavse døde knap.** Uden provider blev knappen `disabled`, og der
 *    stod intet om hvorfor. Fladen SÅ ud som om den kunne handles, men
 *    indgangsbetingelsen var tom — og ingen kunne se det.
 * 2. **Ingen forskel på «ingen lytter» og «det gik galt».** Begge endte som
 *    intet. En flade der fejler må kunne sige det, ellers retter ingen den.
 *
 * ## Hvad udfaldet IKKE lover
 *
 * `delivered` betyder AFLEVERET til turen — ikke at turen lykkedes. Turen
 * kører asynkront i sin egen stream, og dens fejl opstår længe efter at
 * fladen har fået svar. At kalde det `ok` ville være den samme løgn som
 * `send_alert` der svarede True mens intet nåede telefonen (målt 13/11-2026).
 *
 * Derfor er der ingen `ok`. Der er `delivered`, og der er de tre måder det
 * kan gå galt FØR afleveringen.
 */

/** Hvorfor en flade-handling ikke nåede frem. */
export type FladeFejlKode =
  /** Fladen står et sted der ikke kan sende: et arkiv, en test, code mode. */
  | 'component_unavailable'
  /** Der var ingen tekst at sende — en tom handling er ikke en handling. */
  | 'empty_action'
  /** Afsendelsen kastede. Turen blev IKKE startet. */
  | 'tool_failed'

export type FladeUdfald =
  | { status: 'delivered' }
  | { status: 'failed'; kode: FladeFejlKode; besked: string }

/** Én sætning Bjørn kan læse, pr. fejlkode.
 *
 *  Bevidst uden «prøv igen» og uden undskyldninger: fladen skal sige hvad der
 *  er i vejen, ikke hvad nogen føler om det. */
export function beskrivUdfald(u: FladeUdfald): string {
  if (u.status === 'delivered') return ''
  switch (u.kode) {
    case 'component_unavailable':
      return 'kan ikke sende herfra'
    case 'empty_action':
      return 'handlingen var tom'
    case 'tool_failed':
      return 'kunne ikke sende'
  }
}

/** Normalisér hvad en provider returnerede.
 *
 *  Providerne er ældre end udfaldet, så de kan stadig returnere `undefined`
 *  (den gamle `void`-kontrakt). Vi opgraderer IKKE en tavs retur til
 *  `delivered`: så ville en provider der glemte at svare se ud som en succes.
 *  En manglende retur er præcis `component_unavailable` — der kom intet svar,
 *  så vi ved ikke om nogen lyttede. */
export function normalisérUdfald(ret: unknown): FladeUdfald {
  if (ret && typeof ret === 'object' && 'status' in ret) {
    const r = ret as { status?: unknown; kode?: unknown; besked?: unknown }
    if (r.status === 'delivered') return { status: 'delivered' }
    if (r.status === 'failed') {
      const kode = r.kode
      const gyldig: FladeFejlKode[] = ['component_unavailable', 'empty_action', 'tool_failed']
      return {
        status: 'failed',
        kode: gyldig.includes(kode as FladeFejlKode) ? (kode as FladeFejlKode) : 'tool_failed',
        besked: typeof r.besked === 'string' ? r.besked : '',
      }
    }
  }
  return { status: 'failed', kode: 'component_unavailable', besked: '' }
}
