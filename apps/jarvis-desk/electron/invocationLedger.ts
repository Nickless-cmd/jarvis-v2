/**
 * Klientens bog over agent-kald (agent-contract-v1 E, spec 8.1).
 *
 * Serveren sender hvert agent-kald med et stabilt `invocation_id`. Bogen er det der gør et tabt svar
 * undersøgeligt: efter et reconnect spørger serveren "hvad skete der med kald X?", og klienten kan kun
 * svare ærligt, hvis den SKREV at den var begyndt FØR den udførte noget.
 *
 *   - `begin` skriver `running` til disk (synkront) FØR handleren kører.
 *   - `finish` skriver `completed`/`failed` med resultatet.
 *   - Et id klienten har set før køres ALDRIG igen (heller ikke en læsning): svaret genudleveres fra bogen.
 *   - Fandtes et id i bogen som `running` da processen startede, døde klienten midt i udførelsen: status er
 *     `unknown` (aldrig `not_started`).
 *   - `not_started` betyder KUN at id'et aldrig er set — og kan derfor bruges af serveren som bevis for at
 *     skrivningen ikke skete.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync, renameSync } from 'node:fs'
import { dirname } from 'node:path'

export type LedgerState = 'running' | 'completed' | 'failed' | 'unknown'
export interface LedgerEntry {
  state: LedgerState
  tool: string
  at: number
  result?: string
  error?: string
}
export type Begin =
  | { kind: 'new' }
  | { kind: 'seen'; entry: LedgerEntry }
export type ReportStatus = 'completed' | 'failed' | 'running' | 'not_started' | 'unknown'

const MAX_ENTRIES = 1000
const MAX_AGE_MS = 7 * 24 * 3600 * 1000
const MAX_RESULT_CHARS = 65_536

export class InvocationLedger {
  private entries: Record<string, LedgerEntry> = {}

  constructor(private readonly path: string, private readonly now: () => number = Date.now) {
    this.load()
  }

  private load(): void {
    try {
      if (!existsSync(this.path)) return
      const raw = JSON.parse(readFileSync(this.path, 'utf8'))
      if (raw && typeof raw === 'object') this.entries = raw as Record<string, LedgerEntry>
    } catch {
      // En ulæselig bog må ALDRIG læses som "intet er set": så ville et genforsøg køre en skrivning to gange.
      this.entries = { __ulaeselig__: { state: 'unknown', tool: '', at: this.now() } }
    }
    for (const e of Object.values(this.entries)) {
      if (e.state === 'running') e.state = 'unknown' // processen døde midt i udførelsen
    }
    this.persist()
  }

  private persist(): void {
    const ids = Object.keys(this.entries)
    if (ids.length > MAX_ENTRIES) {
      ids
        .sort((a, b) => this.entries[a].at - this.entries[b].at)
        .slice(0, ids.length - MAX_ENTRIES)
        .forEach((id) => delete this.entries[id])
    }
    const cutoff = this.now() - MAX_AGE_MS
    for (const id of Object.keys(this.entries)) {
      const st = this.entries[id].state
      if (this.entries[id].at < cutoff && (st === 'completed' || st === 'failed')) delete this.entries[id]
    }
    mkdirSync(dirname(this.path), { recursive: true })
    const tmp = `${this.path}.tmp`
    writeFileSync(tmp, JSON.stringify(this.entries), 'utf8')
    renameSync(tmp, this.path)
  }

  begin(id: string, tool: string): Begin {
    const seen = this.entries[id]
    if (seen) return { kind: 'seen', entry: seen }
    this.entries[id] = { state: 'running', tool, at: this.now() }
    this.persist()
    return { kind: 'new' }
  }

  finish(id: string, ok: boolean, payload: unknown): void {
    const e = this.entries[id]
    if (!e) return
    e.state = ok ? 'completed' : 'failed'
    if (ok) {
      const text = typeof payload === 'string' ? payload : JSON.stringify(payload ?? null)
      e.result = text.length > MAX_RESULT_CHARS ? text.slice(0, MAX_RESULT_CHARS) : text
    } else {
      e.error = String(payload ?? '').slice(0, 500)
    }
    this.persist()
  }

  status(id: string): ReportStatus {
    const e = this.entries[id]
    return e ? e.state : 'not_started'
  }

  report(ids: string[]): Array<{ invocation_id: string; status: ReportStatus; result?: string; error?: string }> {
    return ids.map((id) => {
      const e = this.entries[id]
      const status = this.status(id)
      return { invocation_id: id, status, ...(e?.result ? { result: e.result } : {}), ...(e?.error ? { error: e.error } : {}) }
    })
  }
}
