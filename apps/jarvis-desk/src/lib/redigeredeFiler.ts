import type { ContentBlock } from './sseProtocol'

/**
 * Hvilke filer redigerede Jarvis i denne tur?
 *
 * Bjørn 16/9-2026: «lav forløb under hans besked om til det på billedet og kun
 * vist hvis han har redigeret en fil eller flere».
 *
 * KILDEN ER TOOL-KALDENE, ikke tool-svarene. Svarene bærer `bytes_written` og
 * `line_count` — men IKKE hvor mange linjer der blev tilføjet og fjernet i
 * forhold til det der stod før. De tal findes ikke nogen steder pr. redigering.
 *
 * Derfor kommer `+/−` fra arbejdstræets diff (samme kilde som Ændringer-ruden),
 * slået op pr. sti. Det er ærligt så længe man ved hvad tallet ER: ændringer
 * mod HEAD, ikke mod filens tilstand før netop denne tur. Er filen allerede
 * committet, står der intet tal frem for et forkert et.
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

/** Kort filnavn til visning: sidste to led af stien er nok til at skelne. */
export function kortSti(sti: string): string {
  const dele = sti.split('/').filter(Boolean)
  return dele.length <= 2 ? sti : dele.slice(-2).join('/')
}
