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
  /** Serveren svarede, men svaret kan ikke bruges som fladeindhold. */
  | 'invalid_tool_result'

export type FladeUdfald =
  | { status: 'delivered'; retryable: false }
  | { status: 'failed'; kode: FladeFejlKode; besked: string; retryable: boolean }

export type DeferredTurnAddress = {
  accountId: string
  conversationId: string
  sourceMessageId: string
  widgetInstanceId: string
  contentRevision: number
}

export type DeferredToolRequest = {
  address: DeferredTurnAddress
  tool: string
  arguments: Record<string, unknown>
}

export type DeferredToolUdfald =
  | { status: 'delivered'; retryable: false; result: unknown; address: DeferredTurnAddress }
  | { status: 'failed'; retryable: boolean; kode: FladeFejlKode; besked: string; address: DeferredTurnAddress }

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
    case 'invalid_tool_result':
      return 'svaret kunne ikke bruges'
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
    const r = ret as { status?: unknown; kode?: unknown; code?: unknown; besked?: unknown; message?: unknown; retryable?: unknown }
    if (r.status === 'delivered') return { status: 'delivered', retryable: false }
    if (r.status === 'failed') {
      const kode = r.kode ?? r.code
      const gyldig: FladeFejlKode[] = ['component_unavailable', 'empty_action', 'tool_failed', 'invalid_tool_result']
      return {
        status: 'failed',
        kode: gyldig.includes(kode as FladeFejlKode) ? (kode as FladeFejlKode) : 'tool_failed',
        besked: typeof r.besked === 'string' ? r.besked : (typeof r.message === 'string' ? r.message : ''),
        retryable: r.retryable === true,
      }
    }
  }
  return { status: 'failed', kode: 'component_unavailable', besked: '', retryable: false }
}

type DeferredFetchConfig = { apiBaseUrl: string; authToken: string | null }
type DeferredOptions = {
  fetcher?: typeof fetch
  wait?: (ms: number) => Promise<void>
}

const vent = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

/** Start en adresseret tool-turn og vent på et eventuelt eksisterende approval-kort. */
export async function udførDeferredTool(
  config: DeferredFetchConfig,
  request: DeferredToolRequest,
  options: DeferredOptions = {},
): Promise<DeferredToolUdfald> {
  const fetcher = options.fetcher ?? fetch
  const wait = options.wait ?? vent
  let sti = '/chat/flade/deferred-turn'
  let body: unknown = request
  for (let forsøg = 0; forsøg < 400; forsøg += 1) {
    let response: Response
    try {
      response = await fetcher(new URL(sti, config.apiBaseUrl), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${config.authToken ?? ''}`,
        },
        body: JSON.stringify(body),
      })
    } catch (fejl) {
      return {
        status: 'failed', kode: 'tool_failed', retryable: true,
        besked: String((fejl as Error)?.message || fejl), address: request.address,
      }
    }
    let raw: Record<string, unknown>
    try {
      raw = await response.json() as Record<string, unknown>
    } catch {
      return {
        status: 'failed', kode: 'invalid_tool_result', retryable: false,
        besked: 'Serveren returnerede ikke JSON.', address: request.address,
      }
    }
    if (!response.ok) {
      return {
        status: 'failed', kode: 'tool_failed', retryable: response.status >= 500,
        besked: String(raw.detail || `HTTP ${response.status}`), address: request.address,
      }
    }
    if (raw.status === 'approval_required' && typeof raw.approvalId === 'string') {
      sti = '/chat/flade/deferred-turn/status'
      body = { address: raw.address ?? request.address, approvalId: raw.approvalId }
      await wait(750)
      continue
    }
    const address = (raw.address && typeof raw.address === 'object'
      ? raw.address : request.address) as DeferredTurnAddress
    if (raw.status === 'delivered' && 'result' in raw) {
      return { status: 'delivered', retryable: false, result: raw.result, address }
    }
    const normal = normalisérUdfald(raw)
    if (normal.status === 'failed') return { ...normal, address }
    return {
      status: 'failed', kode: 'invalid_tool_result', retryable: false,
      besked: 'Serverens udfald manglede et resultat.', address,
    }
  }
  return {
    status: 'failed', kode: 'tool_failed', retryable: true,
    besked: 'Godkendelsen udløb uden svar.', address: request.address,
  }
}
