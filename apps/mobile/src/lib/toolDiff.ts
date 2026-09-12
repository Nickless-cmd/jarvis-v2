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
export function toolDiff(navn: string, input: unknown): ToolDiff | null {
  const t = (navn || '').replace(/^operator_/, '')
  const o = (input && typeof input === 'object' ? input : {}) as Record<string, unknown>

  if (t === 'edit_file') return fraPar(o.old_text, o.new_text)

  if (t === 'multi_edit') {
    // `edits` eller `items` — begge former findes i værktøjsdefinitionerne.
    const raa = Array.isArray(o.edits) ? o.edits : Array.isArray(o.items) ? o.items : null
    if (!raa) return null
    let t2 = 0
    let f = 0
    let nogen = false
    for (const e of raa) {
      const d = fraPar((e as Record<string, unknown>)?.old_text, (e as Record<string, unknown>)?.new_text)
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
  if (!s) return 0
  const rent = s.endsWith('\n') ? s.slice(0, -1) : s
  return rent.split('\n').length
}
