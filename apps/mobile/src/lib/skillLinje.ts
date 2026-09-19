/**
 * Spejl af apps/jarvis-desk/src/lib/skillLinje.ts (19/9-2026, Bjørn: «ja port
 * skill linje») — samme regler, så en skill står ens på begge flader. Ret
 * begge. Eneste forskel: kaldet er mobilens egen form (se `SkillKald`), og
 * `unwrapToolResult` er kopieret ind, fordi mobilen ikke har desk'ens
 * `environmentEvidence`.
 */

/**
 * Skill-gate og skill-indlæsning som deres EGEN linje i tråden.
 *
 * Bjørn 16/9-2026: «der skal laves en linje lige som tool results når
 * skillgates og skill loades.. og med live meta data». Før forsvandt de ind i
 * runde-linjen som «Kørte 2 ting», eller stod som «Skill Invoke» — og det man
 * vil vide (hvilken skill, hvor sikkert et match, blev den faktisk indlæst?)
 * lå begravet i JSON'en bag chevronen.
 *
 * Begge er almindelige værktøjskald; der findes intet særskilt skill-event i
 * streamen. Alt her udledes derfor af kaldets input og resultat.
 *
 * Live-resultatet er klippet ved 4.000 tegn, og et `skill_invoke`-resultat
 * bærer hele instruktionen — så JSON'en er ofte UGYLDIG under streaming. Der
 * falder vi tilbage til at fiske felterne ud én ad gangen, og viser hellere
 * intet tal end et forkert (størrelsen udelades hvis den ikke kan måles).
 */
export const SKILL_VAERKTOEJER = new Set(['skill_gate', 'skill_invoke'])

/** Det skill-linjen har brug for fra et kald — live eller gemt. */
export interface SkillKald {
  name: string
  input?: Record<string, unknown>
  result?: string
  status?: string
}
type ToolUse = SkillKald

export interface SkillMatch { name: string; score: number }

export interface SkillOversigt {
  slags: 'gate' | 'indlaes'
  /** Hovedlinjen — nutid mens den kører, datid bagefter. */
  titel: string
  /** Den dæmpede metadata efter titlen: score, størrelse, tilstand. */
  meta: string[]
  beskrivelse?: string
  matches: SkillMatch[]
  advarsel?: boolean
  fejl: boolean
  koerer: boolean
}

export function erSkillKald(b: { type: string; name?: string }): boolean {
  return b.type === 'tool_use' && SKILL_VAERKTOEJER.has(b.name ?? '')
}

export function skillOversigt(b: ToolUse): SkillOversigt {
  const koerer = (b.status ?? 'running') === 'running'
  const fejl = b.status === 'error'
  const r = laesResultat(b.result)
  const input = (b.input ?? {}) as Record<string, unknown>

  if (b.name === 'skill_invoke') {
    const skill = (r.obj?.skill && typeof r.obj.skill === 'object' ? r.obj.skill : r.obj ?? {}) as Record<string, unknown>
    const navn = str(skill.skill_name) || str(input.name) || r.felt('skill_name') || 'skill'
    const instr = typeof skill.instructions === 'string' ? skill.instructions : undefined
    const meta: string[] = []
    if (instr) meta.push(`${tegn(instr.length)} tegn`)
    const advarsel = !!skill.security_warning || /"security_warning"/.test(b.result ?? '')
    if (advarsel) meta.push('sikkerhedsadvarsel')
    return {
      slags: 'indlaes', koerer, fejl, advarsel, matches: [],
      titel: fejl ? `Kunne ikke indlæse skill ${navn}` : `${koerer ? 'Indlæser' : 'Indlæste'} skill ${navn}`,
      meta,
      beskrivelse: str(skill.description) || r.felt('description') || undefined,
    }
  }

  // skill_gate
  const o = r.obj ?? {}
  const udfald = str(o.gate_result) || r.felt('gate_result')
  const navn = str(o.skill_name) || r.felt('skill_name')
  const score = num(o.score) ?? num(r.felt('score'))
  const matches = Array.isArray(o.all_matches)
    ? (o.all_matches as unknown[]).flatMap((m) => {
      const mm = m as { name?: unknown; score?: unknown }
      return typeof mm?.name === 'string' && typeof mm.score === 'number' ? [{ name: mm.name, score: mm.score }] : []
    })
    : Array.isArray(o.suggestions)
      ? (o.suggestions as unknown[]).flatMap((m) => {
        const mm = m as { name?: unknown; score?: unknown }
        return typeof mm?.name === 'string' && typeof mm.score === 'number' ? [{ name: mm.name, score: mm.score }] : []
      })
      : []
  const meta: string[] = []
  let titel: string
  if (koerer) {
    const q = str(input.query)
    titel = q ? `Tjekker skills for «${kort(q)}»` : 'Tjekker skills'
  } else if (fejl || o.status === 'error') {
    titel = 'Skill-gaten fejlede'
  } else if (udfald === 'invoked' && navn) {
    titel = `Skill-gate: ${navn}`
    if (score != null) meta.push(scoreTekst(score))
    const mode = str(o.mode) || r.felt('mode')
    if (mode === 'auto_use') {
      meta.push('indlæst')
      const n = num(o.instructions_full_length) ?? num(r.felt('instructions_full_length'))
      if (n != null) meta.push(`${tegn(n)} tegn`)
    } else if (mode === 'suggested') {
      meta.push('kun foreslået')
    }
  } else if (udfald === 'low_match') {
    titel = 'Skill-gate: intet sikkert match'
    const bedst = matches[0]
    if (bedst) meta.push(`bedst ${bedst.name} ${scoreTekst(bedst.score)}`)
  } else if (udfald === 'no_match') {
    titel = 'Skill-gate: ingen skill matchede'
  } else {
    titel = 'Tjekkede skills'
  }
  return {
    slags: 'gate', koerer, fejl: fejl || o.status === 'error', matches, meta, titel,
    beskrivelse: str(o.skill_description) || undefined,
  }
}

/** 0,82 — dansk komma, to decimaler. */
export function scoreTekst(s: number): string {
  return s.toFixed(2).replace('.', ',')
}

/** 4.213 → «4,2k», 812 → «812». */
function tegn(n: number): string {
  return n >= 1000 ? `${(Math.round(n / 100) / 10).toString().replace('.', ',')}k` : String(n)
}

function kort(s: string): string {
  const t = s.trim().replace(/\s+/g, ' ')
  return t.length > 48 ? `${t.slice(0, 47)}…` : t
}

function str(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

function num(v: unknown): number | undefined {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string' && v.trim() !== '' && Number.isFinite(Number(v))) return Number(v)
  return undefined
}

/** JSON hvis den er hel; ellers et opslag der fisker enkelte felter ud. */
function laesResultat(result?: string): { obj: Record<string, unknown> | null; felt: (k: string) => string } {
  const tekst = unwrapToolResult(result)
  let obj: Record<string, unknown> | null = null
  try {
    const v = JSON.parse(tekst)
    if (v && typeof v === 'object' && !Array.isArray(v)) obj = v as Record<string, unknown>
  } catch { /* klippet — se felt() */ }
  const felt = (k: string) => {
    const m = tekst.match(new RegExp(`"${k}"\\s*:\\s*(?:"((?:[^"\\\\]|\\\\.)*)"|(-?[0-9.]+))`))
    if (!m) return ''
    return m[1] !== undefined ? m[1].replace(/\\"/g, '"').replace(/\\n/g, ' ') : m[2] ?? ''
  }
  return { obj, felt }
}

/** Spejl af desk'ens `environmentEvidence.unwrapToolResult`. */
export function unwrapToolResult(result?: string): string {
  if (!result) return ''
  let tekst = result.trim()
  tekst = tekst.replace(/^⚠[^\n]*\n\n/, '').trim()
  const hegn = tekst.match(/^\[UTROET kilde=[^\]]*\]\n([\s\S]*?)(?:\n\[\/UTROET\])?$/)
  if (hegn) tekst = hegn[1]!.trim()
  tekst = tekst.replace(/\n\[keys: [\s\S]*$/, '').trim()
  return tekst
}
