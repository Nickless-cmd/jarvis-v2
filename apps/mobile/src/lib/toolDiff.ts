export interface ToolDiff {
  tilfoejet: number
  fjernet: number
}

/**
 * Hvor mange linjer ændrede DETTE værktøjskald?
 *
 * ## Hvorfor det regnes i klienten
 *
 * Fordi tallene allerede er der. Et `edit_file`-kald bærer `old_text` og
 * `new_text` i sine argumenter, og dem får klienten i forvejen i
 * `tool_use`-blokken. Serveren kunne regne det ud og sende det, men så var der
 * et felt mere at holde i sync — og ingen ny oplysning.
 *
 * ## Hvad den IKKE gør
 *
 * Den gætter ikke. Et `write_file` uden `old_text` ved ikke om filen fandtes i
 * forvejen, så den siger kun hvor meget der blev skrevet — aldrig hvor meget
 * der blev overskrevet. Et værktøj der ikke redigerer, giver null; så står
 * rækken uden tal frem for med et opdigtet nul.
 */
/**
 * Argumenterne, uanset om de er et objekt eller en streng under streaming.
 *
 * Et værktøjs argumenter lander i `partialJson` — en streng samlet af
 * `input_json_delta` — og ikke i `input`. `toolBody` i MessageList har hele
 * tiden foretrukket strengen; diff'en gjorde ikke, og derfor manglede
 * «+12 −4» på præcis de runder hvor en fil blev redigeret.
 *
 * En HALV streng midt i streamen giver `{}` frem for at kaste: indtil
 * argumenterne er hele, er der intet at vise, og en række der kaster ville
 * tage hele tråden med sig.
 */
function somArgumenter(input: unknown): Record<string, unknown> {
  if (input && typeof input === 'object') return input as Record<string, unknown>
  if (typeof input === 'string' && input.trim()) {
    try {
      const p = JSON.parse(input)
      if (p && typeof p === 'object') return p as Record<string, unknown>
    } catch {
      return {}
    }
  }
  return {}
}

export function toolDiff(navn: string, input: unknown): ToolDiff | null {
  const t = (navn || '').replace(/^operator_/, '')
  const o = somArgumenter(input)

  // `edit_file` sender old_text/new_text; `operator_edit_file` (broen til
  // CheifOne) sender old_string/new_string — målt 19/9-2026 i Bjørns tråd, hvor
  // de redigeringer derfor stod uden +/−. Desk'ens `diffStat` læser begge.
  if (t === 'edit_file') return fraPar(o.old_text ?? o.old_string, o.new_text ?? o.new_string)

  if (t === 'multi_edit') {
    // `edits` eller `items` — begge former findes i værktøjsdefinitionerne.
    const raa = Array.isArray(o.edits) ? o.edits : Array.isArray(o.items) ? o.items : null
    if (!raa) return null
    let t2 = 0
    let f = 0
    let nogen = false
    for (const e of raa) {
      const r = (e ?? {}) as Record<string, unknown>
      const d = fraPar(r.old_text ?? r.old_string, r.new_text ?? r.new_string)
      if (d) { t2 += d.tilfoejet; f += d.fjernet; nogen = true }
    }
    return nogen ? { tilfoejet: t2, fjernet: f } : null
  }

  if (t === 'write_file') {
    const indhold = o.content ?? o.file_text
    if (typeof indhold !== 'string') return null
    // KUN tilføjet. Vi ved ikke om filen fandtes; at kalde dens tidligere
    // indhold for «fjernet» ville være et gæt på et tal man ikke har.
    return { tilfoejet: linjer(indhold), fjernet: 0 }
  }

  return null
}

/**
 * Selve ændringen i et kald — til diff-arket (Claude Desktop §9, 19/9-2026).
 * Samme feltnavne som `toolDiff` ovenfor (old_text/old_string, content/
 * file_text). `null` for et kald der ikke redigerer eller skriver en fil.
 */
export function aendringAf(navn: string, input: unknown): { sti: string; gammel: string; ny: string } | null {
  const t = (navn || '').replace(/^operator_/, '')
  const o = somArgumenter(input)
  const sti = typeof o.path === 'string' ? o.path : typeof o.file_path === 'string' ? o.file_path : ''
  if (!sti) return null
  if (t === 'edit_file') {
    const g = o.old_text ?? o.old_string
    const n = o.new_text ?? o.new_string
    if (typeof g !== 'string' && typeof n !== 'string') return null
    return { sti, gammel: typeof g === 'string' ? g : '', ny: typeof n === 'string' ? n : '' }
  }
  if (t === 'write_file') {
    const indhold = o.content ?? o.file_text
    return typeof indhold === 'string' ? { sti, gammel: '', ny: indhold } : null
  }
  return null
}

function fraPar(gammel: unknown, ny: unknown): ToolDiff | null {
  const g = typeof gammel === 'string' ? gammel : null
  const n = typeof ny === 'string' ? ny : null
  if (g === null && n === null) return null
  return { tilfoejet: n ? linjer(n) : 0, fjernet: g ? linjer(g) : 0 }
}

/**
 * Linjer i et tekststykke.
 *
 * Tom streng er NUL linjer, ikke én. En sletning der erstatter tekst med
 * ingenting skal vise `-N +0` — ikke `-N +1` for en linje der ikke findes.
 */
function linjer(s: string): number {
  // Som Claude Desktop, desk og serveren (19/9-2026): linjeskift + 1.
  if (!s) return 0
  return s.split('\n').length
}


/**
 * Linjetal som SERVEREN har målt — frem for klientens gæt.
 *
 * `toolDiff` ovenfor regner ud af kaldets argumenter, og for `write_file`
 * stod der en ærlig indrømmelse: vi ved ikke om filen fandtes, så «fjernet»
 * kunne ikke opgøres. Klienten havde ret — den KUNNE ikke vide det.
 *
 * Serveren kan: den har filen i hånden lige før den skriver.
 * `edit_file`/`write_file` returnerer nu `linjer_tilfoejet` og
 * `linjer_fjernet`, målt på det faktiske indhold. Rækkefølgen er derfor:
 * målt slår gættet.
 *
 * `null` når serveren ikke har målt noget — et læsende værktøj har ingen tal,
 * og «ingenting at vise» er en anden besked end «nul». Men et resultat der
 * FAKTISK siger 0 og 0 er målt, og returneres som sådan.
 *
 * Et halvt JSON-objekt midt i en stream giver null frem for at kaste: linjen
 * skal kunne tegnes mens svaret stadig kommer ind.
 */
export function diffFraResultat(resultat: unknown): ToolDiff | null {
  let o: Record<string, unknown> | null = null
  if (resultat && typeof resultat === 'object') {
    o = resultat as Record<string, unknown>
  } else if (typeof resultat === 'string' && resultat.trim()) {
    try {
      const p = JSON.parse(resultat)
      if (p && typeof p === 'object') o = p as Record<string, unknown>
    } catch {
      return null
    }
  }
  if (!o) return null
  const t = o.linjer_tilfoejet
  const f = o.linjer_fjernet
  if (typeof t !== 'number' || typeof f !== 'number') return null
  if (!Number.isFinite(t) || !Number.isFinite(f)) return null
  return { tilfoejet: t, fjernet: f }
}
