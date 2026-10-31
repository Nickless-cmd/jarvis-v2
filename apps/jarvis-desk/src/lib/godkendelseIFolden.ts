import type { ChatMessage } from './api'
import type { ContentBlock } from './sseProtocol'

/** Ét godkendelses-kort, læst ud af en persisteret række. */
export interface GodkendelsesHaendelse {
  approval_id: string
  tool: string
  action: string
  status: string
  risk?: string
  decided_by?: string
  decided_at?: string
}

/**
 * Godkendelsen hører til TUREN — ikke til samtalen.
 *
 * MAALT 31/10-2026 (Bjørn, med skærmbillede): efter 0.6.295 stod de to
 * godkendelses-rækker som to SELVSTÆNDIGE blokke midt i samtalen, uden for
 * enhver fold. Hans ord: «Burde disse 2 ikk have ligget inde i det foldet
 * hovede ved de runder de hørte til?»
 *
 * Han har ret, og der var TO fejl i én:
 *
 * 1. TO RÆKKER FOR ÉN GODKENDELSE. Serveren skriver append-only — `pending`
 *    da kortet blev lavet, `approved` da det blev afgjort. Det er den rigtige
 *    form i basen (en UPDATE ville bryde ledger-invarianten), men det er ikke
 *    den rigtige form på skærmen. Klienten skal gruppere på `approval_id` og
 *    vise den SIDSTE status. Ellers står samme godkendelse to gange.
 *
 * 2. PLACERET SOM SAMTALE, IKKE SOM ARBEJDE. En godkendelse er noget der skete
 *    MIDT i turen — den hører i folden sammen med værktøjskaldene, ikke som en
 *    selvstændig besked mellem Bjørn og svaret. Den lå som top-level række
 *    fordi den ER en række i `chat_messages`, men rækkens form i basen må ikke
 *    bestemme dens form på skærmen.
 *
 * HVORFOR KLIENTEN OG IKKE SERVEREN: assistent-rækken skrives ved turens
 * SLUTNING, godkendelsen midt i den. Serveren kan derfor ikke lægge blokken
 * ind da den skrives — og en fletning ved skrivetid ville kun ramme NYE ture.
 * Her rammer den også historikken der ligger i forvejen.
 */
export function forsteGodkendelse(raa: unknown): GodkendelsesHaendelse {
  const liste = Array.isArray(raa) ? raa : []
  const blok = liste[0] as Partial<GodkendelsesHaendelse> | undefined
  return {
    approval_id: String(blok?.approval_id ?? ''),
    tool: String(blok?.tool ?? 'godkendelse'),
    action: String(blok?.action ?? ''),
    status: String(blok?.status ?? 'pending'),
    risk: blok?.risk ? String(blok.risk) : undefined,
    decided_by: blok?.decided_by ? String(blok.decided_by) : undefined,
    decided_at: blok?.decided_at ? String(blok.decided_at) : undefined,
  }
}

/**
 * Fletter `approval_request`-rækker ind i den assistent-tur de hørte til.
 *
 * Reglen er mekanisk: en godkendelse hører til den FØRSTE assistent-besked der
 * følger efter den. Rækkefølgen i `chat_messages` er user → (værktøj) →
 * (godkendelse) → assistant, så «første assistent efter» er præcis turen.
 *
 * Findes der ingen følgende assistent endnu, kører turen stadig — så bliver
 * rækken stående som selvstændig. Det er ikke en fallback-undantagelse, det er
 * det eneste rigtige: en igangværende godkendelse skal kunne besvares NU, og
 * den kan ikke vente på et svar der ikke er skrevet.
 */
/* Generisk over besked-typen: viewene baerer `LocalMessage`, som har felter
 * `ChatMessage` ikke kender (`clientStatus`). Returnerer vi den brede type,
 * taber kalderen dem — og typecheckeren fanger det foerst der. */
export function fletGodkendelser<T extends ChatMessage>(messages: readonly T[]): T[] {
  const ind = [...messages]

  // ── 1. Gruppér på approval_id. Sidste række vinder: den bærer afgørelsen. ──
  const grupper = new Map<string, { haendelse: GodkendelsesHaendelse; indeks: number[] }>()
  ind.forEach((m, i) => {
    if (m.role !== 'approval_request') return
    const haendelse = forsteGodkendelse(m.content_json)
    // En række uden id må ikke smelte sammen med en anden uden id.
    const noegle = haendelse.approval_id || `anonym-${i}`
    const gruppe = grupper.get(noegle)
    if (gruppe) {
      gruppe.haendelse = haendelse
      gruppe.indeks.push(i)
    } else {
      grupper.set(noegle, { haendelse, indeks: [i] })
    }
  })
  if (grupper.size === 0) return ind

  const fjern = new Set<number>()
  const tilfoej = new Map<number, ContentBlock[]>()

  for (const gruppe of grupper.values()) {
    const sidste = gruppe.indeks[gruppe.indeks.length - 1]
    if (sidste === undefined) continue

    let maal = -1
    for (let i = sidste + 1; i < ind.length; i += 1) {
      if (ind[i]?.role === 'assistant') { maal = i; break }
    }
    // Turen kører stadig: rækken bliver stående, så kortet kan besvares.
    if (maal < 0) continue

    const blok = { type: 'approval', ...gruppe.haendelse } as ContentBlock
    const liste = tilfoej.get(maal)
    if (liste) liste.push(blok)
    else tilfoej.set(maal, [blok])

    for (const i of gruppe.indeks) fjern.add(i)
  }

  // ── 2. Læg blokken SIDST i turens arbejde. `deriveChatFlow` sender alt der
  // ikke er tekst til `workBlocks`, så den havner i folden — og sidst betyder
  // «det sidste der skete i arbejdet», hvilket er sandt for en godkendelse. ──
  const ud: T[] = []
  ind.forEach((m, i) => {
    const ekstra = tilfoej.get(i)
    if (ekstra) {
      ud.push({ ...m, content: [...m.content, ...ekstra] })
      return
    }
    if (fjern.has(i)) return
    ud.push(m)
  })
  return ud
}
