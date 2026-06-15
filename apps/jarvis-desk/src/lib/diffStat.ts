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
