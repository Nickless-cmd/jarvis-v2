import type { ContentBlock } from './sseProtocol'
import { diffFraResultat } from './diffStat'

/**
 * Hvilke filer redigerede Jarvis i denne tur?
 *
 * Bjørn 16/9-2026: «lav forløb under hans besked om til det på billedet og kun
 * vist hvis han har redigeret en fil eller flere».
 *
 * Filernes stier kommer fra tool-kaldene. Nogle tool-svar indeholder desuden
 * servermålte linjetal for ændringen.
 *
 * `maalteRedigeringer` bruger kun serverens målte +/- fra værktøjsresultatet.
 * Hvis et kald mangler tal, vises intet samlet tal for filen.
 */

/** Værktøjer der SKRIVER i en fil. Læsning, søgning og listning hører ikke til. */
const SKRIVER = new Set([
  'write_file', 'edit_file', 'multi_edit', 'apply_patch', 'create_file',
  'operator_write_file', 'operator_edit_file', 'operator_multi_edit',
  'notebook_edit', 'phone_write_file',
])

export interface RedigeretFil {
  path: string
  /** Antal gange filen blev rørt i turen. To redigeringer af samme fil er
   *  ÉN fil i listen — ellers ville en fil der rettes tre gange fylde tre
   *  rækker og se ud som tre filer. */
  gange: number
}

function stiFra(input: unknown): string {
  if (!input || typeof input !== 'object') return ''
  const o = input as Record<string, unknown>
  for (const navn of ['path', 'file_path', 'filepath', 'file']) {
    const v = o[navn]
    if (typeof v === 'string' && v.trim()) return v.trim()
  }
  return ''
}

export function redigeredeFiler(blocks: readonly ContentBlock[]): RedigeretFil[] {
  const talt = new Map<string, number>()
  for (const b of blocks) {
    if (!b || b.type !== 'tool_use') continue
    if (!SKRIVER.has(b.name)) continue
    // Kun kald der FAKTISK skrev. Et kald der blev afvist af gaten, fejlede
    // eller venter på godkendelse har ikke redigeret noget, og at tælle det
    // ville love en ændring der ikke findes.
    if (b.status === 'error') continue
    const sti = stiFra(b.input)
    if (!sti) continue
    talt.set(sti, (talt.get(sti) ?? 0) + 1)
  }
  return [...talt.entries()].map(([path, gange]) => ({ path, gange }))
}

/** Summer kun servermålte linjetal. Et manglende resultat gør filens tal ukendt. */
export function maalteRedigeringer(blocks: readonly ContentBlock[]): Record<string, { added: number; removed: number }> {
  const tal = new Map<string, { added: number; removed: number }>()
  const ukendte = new Set<string>()
  for (const b of blocks) {
    if (!b || b.type !== 'tool_use' || !SKRIVER.has(b.name) || b.status === 'error') continue
    const path = stiFra(b.input)
    if (!path) continue
    const diff = diffFraResultat(b.result)
    if (!diff) { ukendte.add(path); continue }
    const nu = tal.get(path) ?? { added: 0, removed: 0 }
    tal.set(path, { added: nu.added + diff.add, removed: nu.removed + diff.del })
  }
  for (const path of ukendte) tal.delete(path)
  return Object.fromEntries(tal)
}

/** Kort filnavn til visning: sidste to led af stien er nok til at skelne. */
export function kortSti(sti: string): string {
  const dele = sti.split('/').filter(Boolean)
  return dele.length <= 2 ? sti : dele.slice(-2).join('/')
}
