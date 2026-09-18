/**
 * Insertions/deletions for et fil-ændrende tool-kald — vises som +N −M i
 * rundelinjen og i kortet. `null` for tools der ikke ændrer en fil.
 *
 * ## Hvorfor den blev skrevet om (Bjørn 18/9-2026: «tool result linje i
 * chatview mangler +xx og −xx grøn/rød som mobil appen har»)
 *
 * Den ledte efter `old_string`/`new_string`. Værktøjet hedder dem `old_text`
 * og `new_text`. Målt på CT105 over de seneste 400 svar med værktøjskald:
 * 666 af 672 `edit_file`-kald bar `old_text`, 3 bar `old_string`. Den ramte
 * altså under én procent, returnerede `null` resten af tiden, og så blev
 * linjen slet ikke tegnet — ikke gråtonet, men fraværende. Det var derfor
 * mobilen havde tal og desk ikke.
 *
 * ## Samme regnemåde som serveren
 *
 * Tallene tælles som HELE blokke — hele `new_text` tilføjet, hele `old_text`
 * fjernet — ikke som en minimal diff. Det er ikke sjusk: det er hvad
 * `core/tools/file_tools_exec.linjetal` gør, og dermed hvad `linjer_tilfoejet`
 * i resultatet betyder. En minimal diff ville give PÆNERE tal, men så ville
 * samme kald vise ét tal mens det kører og et andet når svaret er inde — og
 * desk ville sige noget andet end mobilen om den samme handling.
 */
export function diffStat(name: string, args: unknown): { add: number; del: number } | null {
  // `operator_edit_file` er samme værktøj på den anden side af broen.
  const n = (name || '').toLowerCase().replace(/^operator_/, '')
  const o = somArgumenter(args)

  if (n === 'edit_file') return fraPar(o.old_text ?? o.old_string, o.new_text ?? o.new_string)

  if (n === 'multi_edit') {
    // `edits` eller `items` — begge former findes i værktøjsdefinitionerne.
    const raa = Array.isArray(o.edits) ? o.edits : Array.isArray(o.items) ? o.items : null
    if (!raa) return null
    let add = 0
    let del = 0
    let nogen = false
    for (const e of raa) {
      const r = (e ?? {}) as Record<string, unknown>
      const d = fraPar(r.old_text ?? r.old_string, r.new_text ?? r.new_string)
      if (d) { add += d.add; del += d.del; nogen = true }
    }
    return nogen ? { add, del } : null
  }

  if (n === 'write_file') {
    const indhold = o.content ?? o.file_text
    if (typeof indhold !== 'string' || !indhold) return null
    // KUN tilføjet. Argumenterne siger ikke om filen fandtes i forvejen, og
    // at kalde dens tidligere indhold «fjernet» ville være et gæt på et tal
    // vi ikke har. Serverens målte tal dækker det tilfælde — se nedenfor.
    return { add: linjer(indhold), del: 0 }
  }

  return null
}

/**
 * Argumenterne, uanset om de er et objekt eller en streng under streaming.
 *
 * Et værktøjs argumenter lander i `partialJson` — en streng samlet af
 * `input_json_delta` — før de findes som objekt. En HALV streng giver `{}`
 * frem for at kaste: indtil argumenterne er hele er der intet at vise, og en
 * linje der kaster ville tage hele tråden med sig.
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

function fraPar(gammel: unknown, ny: unknown): { add: number; del: number } | null {
  const g = typeof gammel === 'string' ? gammel : null
  const n = typeof ny === 'string' ? ny : null
  if (g === null && n === null) return null
  return { add: n ? linjer(n) : 0, del: g ? linjer(g) : 0 }
}

/**
 * Linjer i et tekststykke — som Claude Desktop (19/9-2026) og serverens
 * `_linjer`: antal linjeskift + 1. «a\n» er to linjer, som hos dem.
 *
 * Tom streng er stadig NUL linjer, ikke én: ellers ville en sletning se ud som
 * «én tom linje tilføjet». Det gør Claude Desktop også (`new_str ? … : 0`).
 */
function linjer(s: string): number {
  if (!s) return 0
  return s.split('\n').length
}


/**
 * Linjetal som SERVEREN har målt — frem for klientens gæt. 1:1 med mobilens
 * `toolDiff.diffFraResultat`.
 *
 * `diffStat` ovenfor regner ud af kaldets argumenter, og for `write_file`
 * satte den altid `del: 0`. Den KUNNE ikke vide om filen fandtes. Serveren
 * kan: den har filen i hånden lige før den skriver, og returnerer nu
 * `linjer_tilfoejet`/`linjer_fjernet` målt på det faktiske indhold.
 *
 * `null` når serveren ikke har målt noget — et læsende værktøj har ingen tal,
 * og «ingenting at vise» er en anden besked end «nul». Et resultat der
 * FAKTISK siger 0 og 0 er målt, og returneres som sådan.
 *
 * Et halvt JSON-objekt midt i en stream giver null frem for at kaste: chippen
 * skal kunne tegnes mens svaret stadig kommer ind.
 */
export function diffFraResultat(resultat: unknown): { add: number; del: number } | null {
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
  const a = o.linjer_tilfoejet
  const d = o.linjer_fjernet
  if (typeof a !== 'number' || typeof d !== 'number') return null
  if (!Number.isFinite(a) || !Number.isFinite(d)) return null
  return { add: a, del: d }
}
