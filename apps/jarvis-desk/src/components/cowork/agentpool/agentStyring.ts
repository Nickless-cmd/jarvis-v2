/** Rene hjælpefunktioner til agent-styringen. Ingen React, ingen netværk — så de kan testes alene.
 *
 *  Gyldigheden af en model-rute afgøres af BACKENDEN (agent_model_policy). Her bygges og
 *  vises kun ruten; en afvisning fra serveren vises som den er.
 */

export interface RuteValg {
  udbyder: string
  standard_model: string
  kun_ejer: boolean
  eksempel: string
}

export interface StartKladde {
  rolle: string
  opgave: string
  udbyder: string
  model: string
}

/** «claude-cli» + «default» -> «claude-cli/default». Ingen udbyder = automatisk valg (tom streng). */
export function byggRoute(udbyder: string, model: string): string {
  const u = udbyder.trim()
  if (!u) return ''
  const m = model.trim()
  return m ? `${u}/${m}` : u
}

/** Dansk fejltekst; tom streng hvis kladden kan sendes. Rute-gyldighed er IKKE tjekket her. */
export function kladdeFejl(k: StartKladde): string {
  if (!k.rolle.trim()) return 'Vælg en rolle.'
  if (!k.opgave.trim()) return 'Beskriv opgaven.'
  if (k.opgave.length > 8000) return 'Opgaven er for lang (maks. 8000 tegn).'
  return ''
}

export function startBody(k: StartKladde): { rolle: string; opgave: string; model_route: string } {
  return { rolle: k.rolle.trim(), opgave: k.opgave.trim(), model_route: byggRoute(k.udbyder, k.model) }
}

const LIVSSTATUS: Record<string, string> = {
  queued: 'I kø', active: 'Kører', running: 'Kører', waiting: 'Venter',
  planned: 'Planlagt', completed: 'Gennemført', failed: 'Fejlet',
  cancelled: 'Annulleret', expired: 'Udløbet', closing: 'Lukker', closed: 'Lukket',
}

export function livsstatus(status?: string | null): string {
  return status ? LIVSSTATUS[status] ?? status : 'Ukendt'
}

const I_GANG = new Set(['queued', 'active', 'running', 'waiting', 'planned'])
const LUKKET = new Set(['closing', 'closed'])

export interface Handlinger { interrupt: boolean; luk: boolean; followup: boolean }

/** Hvilke knapper der giver mening. Interrupt kun for noget i gang; follow-up ikke til en lukket agent. */
export function handlinger(status?: string | null, erAktiv?: boolean): Handlinger {
  const s = status ?? ''
  const lukket = LUKKET.has(s)
  return {
    interrupt: !lukket && (erAktiv ?? I_GANG.has(s)),
    luk: !lukket,
    followup: !lukket,
  }
}

/** Tekst efter en styringshandling. `stop_requested` er en anmodning, ikke et bevis for stop. */
export function handlingsKvittering(handling: 'start' | 'interrupt' | 'close' | 'followup',
                                    svar: { status?: string; lifecycle_status?: string }): string {
  switch (handling) {
    case 'start': return 'Agenten er startet.'
    case 'followup': return 'Opfølgende opgave er sendt.'
    case 'interrupt':
      return svar.status === 'noop' ? 'Agenten har ingen aktiv opgave at afbryde.'
        : 'Stop er anmodet — agenten stopper ved næste mulighed.'
    case 'close':
      return svar.lifecycle_status === 'closed' ? 'Agenten er lukket.'
        : 'Agenten lukker, når dens igangværende arbejde er færdigt.'
  }
}

/** Gør en serverfejl læsbar. Backendens egen årsag bevares. */
export function styringsFejl(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e ?? '')
  if (/HTTP 403|auth/i.test(msg)) return 'Kun ejeren kan styre agenter.'
  return msg ? `Styringen fejlede: ${msg}` : 'Styringen fejlede.'
}
