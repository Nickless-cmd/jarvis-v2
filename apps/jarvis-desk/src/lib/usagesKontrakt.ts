import { unwrapToolResult, type ToolEvidence } from './environmentEvidence'

/** Værktøjs-kontrakten fra `core/tools/code_navigation_tools.py`:
 *  `{status, name, backend?, count, hits:[{file, line, kind?, snippet?, enclosing?}], truncated}`.
 *  `find_usages` markerer i `backend` om LSP eller ripgrep svarede. */
export interface UsageHit {
  file: string
  line: number
  kind?: string
  snippet?: string
  enclosing?: string
}

export interface UsagesSvar {
  tool: 'find_usages' | 'find_symbol'
  toolId: string
  navn: string
  backend?: string
  hits: UsageHit[]
  truncated: boolean
}

export type UsagesParse = { ok: true; svar: UsagesSvar } | { ok: false; fejl: string }

const erTekst = (v: unknown): v is string => typeof v === 'string' && v !== ''

export function erUsagesTool(t: ToolEvidence): boolean {
  return t.name === 'find_usages' || t.name === 'find_symbol'
}

export function parseUsages(t: ToolEvidence): UsagesParse {
  if (t.status === 'running') return { ok: false, fejl: 'Opslaget kører stadig …' }
  const raa = unwrapToolResult(t.result)
  let json: unknown
  try { json = JSON.parse(raa) } catch { return { ok: false, fejl: 'Resultatet er ikke gyldig JSON' } }
  if (typeof json !== 'object' || json === null) return { ok: false, fejl: 'Uventet resultatform' }
  const o = json as Record<string, unknown>
  if (o.status === 'error') return { ok: false, fejl: erTekst(o.error) ? o.error : 'Værktøjet fejlede' }
  if (!Array.isArray(o.hits)) return { ok: false, fejl: 'Resultatet har ingen `hits`' }
  const hits: UsageHit[] = []
  for (const h of o.hits) {
    if (typeof h !== 'object' || h === null) continue
    const r = h as Record<string, unknown>
    if (!erTekst(r.file)) continue
    hits.push({
      file: r.file,
      line: typeof r.line === 'number' ? r.line : 0,
      kind: erTekst(r.kind) ? r.kind : undefined,
      snippet: erTekst(r.snippet) ? r.snippet : undefined,
      enclosing: erTekst(r.enclosing) ? r.enclosing : undefined,
    })
  }
  const navn = erTekst(o.name) ? o.name : String(t.input.name ?? t.input.symbol ?? '')
  return {
    ok: true,
    svar: {
      tool: t.name as UsagesSvar['tool'], toolId: t.id, navn,
      backend: erTekst(o.backend) ? o.backend : undefined, hits, truncated: o.truncated === true,
    },
  }
}
