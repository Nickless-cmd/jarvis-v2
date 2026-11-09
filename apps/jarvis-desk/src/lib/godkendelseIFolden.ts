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
  const tilfoej = new Map<number, GodkendelsesHaendelse[]>()

  for (const gruppe of grupper.values()) {
    const sidste = gruppe.indeks[gruppe.indeks.length - 1]
    if (sidste === undefined) continue

    // ── Kun den SIDSTE række pr. godkendelse bliver stående (9/11-2026) ──
    //
    // FØR blev ALLE rækker i gruppen fjernet når turen var skrevet, og ALLE
    // blev stående når den ikke var. Serveren skriver to pr. godkendelse
    // (`pending` og `approved`/`denied`), så midt i en igangværende tur — hvor
    // der ingen assistant-række er efter dem — stod BEGGE og blev tegnet.
    // Bjørn så to kort for én godkendelse, både i desk og i PWA.
    //
    // MÅLT 9/11-2026 mod `chat_messages`: alle 17 godkendelser i den aktive
    // session har 2 rækker, omgivet af `tool`-rækker uden assistant imellem.
    //
    // Reglen er nu: den sidste række bærer afgørelsen og bliver stående, de
    // øvrige fjernes. Det holder antallet på ÉT kort pr. godkendelse uanset om
    // turen er skrevet, og lader `findesGodkendelseIRækken` se rækken — så
    // fallback-kortet over composeren ikke dublerer den.
    for (const i of gruppe.indeks) {
      if (i !== sidste) fjern.add(i)
    }

    let maal = -1
    for (let i = sidste + 1; i < ind.length; i += 1) {
      if (ind[i]?.role === 'assistant') { maal = i; break }
    }
    // Turen kører stadig: den sidste række bliver stående, så kortet kan
    // besvares nu — men de ældre rækker i samme gruppe er allerede fjernet.
    if (maal < 0) continue

    const liste = tilfoej.get(maal)
    if (liste) liste.push(gruppe.haendelse)
    else tilfoej.set(maal, [gruppe.haendelse])

    fjern.add(sidste)
  }

  // ── 2. Læg blokken VED DET KALD DEN GJALDT (2/11-2026).
  //
  // FØR: blokken blev lagt SIDST i turens indhold. Den havnede dermed i folden,
  // men ved den forkerte runde — og i code mode slet ikke i folden, fordi
  // `opdel` kalder alt efter sidste værktøjskald for svar. Bjørn så derfor
  // kortene nederst i beskeden: «Du burde ligge inde i turhoved ved de runde
  // linjer de høre til?»
  //
  // MÅLT mod `chat_messages` 2/11-2026: godkendelsens `action` er ordret lig
  // `input.command` (eller `input.path`) på det kald den gjaldt — 326 og 365
  // tegn, eksakt match ved indeks [9] og [13] i samme tur. Placeringen er
  // derfor ikke et gæt: den udledes af hvilket kald der blev godkendt.
  const ud: T[] = []
  ind.forEach((m, i) => {
    const ekstra = tilfoej.get(i)
    if (ekstra) {
      ud.push({ ...m, content: indsaetVedKald(m.content, ekstra) })
      return
    }
    if (fjern.has(i)) return
    ud.push(m)
  })
  return ud
}

/**
 * Find indekset for det `tool_use` en godkendelse gjaldt.
 *
 * Returnerer -1 når intet kald matcher. Så ved vi det ikke — og så må blokken
 * lægges sidst i arbejdet frem for foran et tilfældigt kald. Et gæt ville være
 * værre end en ærlig placering: kortet ville påstå at høre til en runde det
 * ikke hørte til.
 */
function kaldIndeks(
  blokke: readonly ContentBlock[],
  haendelse: GodkendelsesHaendelse,
  brugte: ReadonlySet<number>,
): number {
  const handling = haendelse.action.trim()
  if (!handling) return -1
  for (let i = 0; i < blokke.length; i += 1) {
    if (brugte.has(i)) continue
    const b = blokke[i]
    if (!b || b.type !== 'tool_use') continue
    if (b.name !== haendelse.tool) continue
    const input = b.input ?? {}
    const kommando = typeof input.command === 'string' ? input.command.trim() : ''
    const sti = typeof input.path === 'string' ? input.path.trim() : ''
    if (kommando === handling || sti === handling) return i
  }
  return -1
}

/** Indsæt hver godkendelse umiddelbart FØR sit eget kald. */
function indsaetVedKald(
  blokke: readonly ContentBlock[],
  haendelser: readonly GodkendelsesHaendelse[],
): ContentBlock[] {
  const foer = new Map<number, ContentBlock[]>()
  const brugte = new Set<number>()
  const loese: ContentBlock[] = []

  for (const haendelse of haendelser) {
    const blok = { type: 'approval', ...haendelse } as ContentBlock
    const i = kaldIndeks(blokke, haendelse, brugte)
    if (i < 0) {
      loese.push(blok)
      continue
    }
    brugte.add(i)
    const liste = foer.get(i)
    if (liste) liste.push(blok)
    else foer.set(i, [blok])
  }

  const ud: ContentBlock[] = []
  blokke.forEach((b, i) => {
    const liste = foer.get(i)
    if (liste) ud.push(...liste)
    ud.push(b)
  })
  // Intet match: blokken bliver i arbejdet, men uden en påstand om hvilken runde.
  ud.push(...loese)
  return ud
}
