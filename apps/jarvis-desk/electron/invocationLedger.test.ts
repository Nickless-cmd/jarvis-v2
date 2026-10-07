import { describe, expect, it } from 'vitest'
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { InvocationLedger } from './invocationLedger'

const fresh = () => join(mkdtempSync(join(tmpdir(), 'ledger-')), 'inv.json')

describe('InvocationLedger', () => {
  it('writes running to disk BEFORE the handler runs and never re-runs a seen id', () => {
    const p = fresh()
    const l = new InvocationLedger(p)
    expect(l.begin('inv-1', 'operator_write_file')).toEqual({ kind: 'new' })
    expect(JSON.parse(readFileSync(p, 'utf8'))['inv-1'].state).toBe('running')
    const again = l.begin('inv-1', 'operator_write_file')
    expect(again.kind).toBe('seen')
    l.finish('inv-1', true, { bytes_written: 3 })
    const done = l.begin('inv-1', 'operator_write_file')
    expect(done).toMatchObject({ kind: 'seen', entry: { state: 'completed', result: '{"bytes_written":3}' } })
  })

  it('answers not_started only for ids it has never seen', () => {
    const l = new InvocationLedger(fresh())
    l.begin('inv-a', 'operator_read_file')
    l.finish('inv-a', false, 'ENOENT')
    expect(l.report(['inv-a', 'inv-ukendt'])).toEqual([
      { invocation_id: 'inv-a', status: 'failed', error: 'ENOENT' },
      { invocation_id: 'inv-ukendt', status: 'not_started' },
    ])
  })

  it('reports unknown (never not_started) for a call that was running when the process died', () => {
    const p = fresh()
    const first = new InvocationLedger(p)
    first.begin('inv-x', 'operator_bash')                   // ... og processen dør her
    const afterRestart = new InvocationLedger(p)
    expect(afterRestart.status('inv-x')).toBe('unknown')
    expect(afterRestart.begin('inv-x', 'operator_bash').kind).toBe('seen')
  })

  it('treats an unreadable ledger as "unsure", not as "nothing seen"', () => {
    const p = fresh()
    writeFileSync(p, '{ikke json', 'utf8')
    const l = new InvocationLedger(p)
    expect(l.status('__ulaeselig__')).toBe('unknown')
  })

  it('bounds its size and forgets only finished entries older than a week', () => {
    let t = 1_000_000
    const l = new InvocationLedger(fresh(), () => t)
    l.begin('gammel', 'operator_read_file')
    l.finish('gammel', true, 'x')
    l.begin('uafgjort', 'operator_bash')
    t += 8 * 24 * 3600 * 1000
    l.begin('ny', 'operator_read_file')                       // udløser persist + oprydning
    expect(l.status('gammel')).toBe('not_started')
    expect(l.status('uafgjort')).toBe('running')               // en uafgjort post glemmes aldrig af alder
  })
})
