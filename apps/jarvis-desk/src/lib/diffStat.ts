import { lineDiff } from './diff'

/** Insertions/deletions for et fil-ændrende tool-kald — vises som +N −M i chip'en.
 *  Returnerer null for tools der ikke ændrer en fil (eller mangler args). */
export function diffStat(name: string, args: Record<string, unknown>): { add: number; del: number } | null {
  const n = name.toLowerCase()
  if (n.includes('edit_file')) {
    const oldS = String(args.old_string ?? args.old ?? '')
    const newS = String(args.new_string ?? args.new ?? '')
    if (!oldS && !newS) return null
    const d = lineDiff(oldS, newS)
    return {
      add: d.filter((x) => x.type === 'add').length,
      del: d.filter((x) => x.type === 'del').length,
    }
  }
  if (n.includes('write_file')) {
    const content = String(args.content ?? '')
    if (!content) return null
    return { add: content.split('\n').length, del: 0 }
  }
  return null
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
