import { describe, it, expect } from 'vitest'
import {
  byggRoute, kladdeFejl, startBody, livsstatus, handlinger, handlingsKvittering, styringsFejl,
} from './agentStyring'

describe('agentStyring', () => {
  it('bygger en rute af udbyder og model', () => {
    expect(byggRoute('claude-cli', 'default')).toBe('claude-cli/default')
    expect(byggRoute('ollama', '  qwen3:4b ')).toBe('ollama/qwen3:4b')
    expect(byggRoute('deepseek', '')).toBe('deepseek')
    expect(byggRoute('', 'x')).toBe('')            // automatisk valg
  })

  it('kladden kræver rolle og opgave, ikke en gyldig rute', () => {
    const k = { rolle: 'researcher', opgave: 'find', udbyder: 'bogus', model: 'x' }
    expect(kladdeFejl(k)).toBe('')                 // ruten afgør backend
    expect(kladdeFejl({ ...k, opgave: '  ' })).toBe('Beskriv opgaven.')
    expect(kladdeFejl({ ...k, rolle: '' })).toBe('Vælg en rolle.')
    expect(kladdeFejl({ ...k, opgave: 'x'.repeat(8001) })).toMatch(/for lang/)
  })

  it('startBody trimmer og sender ruten som ét felt', () => {
    expect(startBody({ rolle: ' coder ', opgave: ' gør det ', udbyder: 'codex-cli', model: 'default' }))
      .toEqual({ rolle: 'coder', opgave: 'gør det', model_route: 'codex-cli/default' })
  })

  it('oversætter status til dansk og lader ukendt stå', () => {
    expect(livsstatus('running')).toBe('Kører')
    expect(livsstatus('closing')).toBe('Lukker')
    expect(livsstatus('mærkelig')).toBe('mærkelig')
    expect(livsstatus(null)).toBe('Ukendt')
  })

  it('knapperne følger agentens tilstand', () => {
    expect(handlinger('running')).toEqual({ interrupt: true, luk: true, followup: true })
    expect(handlinger('completed', false)).toEqual({ interrupt: false, luk: true, followup: true })
    expect(handlinger('closed')).toEqual({ interrupt: false, luk: false, followup: false })
    expect(handlinger('closing', true).followup).toBe(false)
  })

  it('kvitteringen lover ikke mere end backenden gør', () => {
    expect(handlingsKvittering('interrupt', { status: 'stop_requested' })).toMatch(/anmodet/)
    expect(handlingsKvittering('interrupt', { status: 'noop' })).toMatch(/ingen aktiv/)
    expect(handlingsKvittering('close', { lifecycle_status: 'closing' })).toMatch(/lukker/)
    expect(handlingsKvittering('close', { lifecycle_status: 'closed' })).toBe('Agenten er lukket.')
  })

  it('fejltekster er danske og bevarer serverens årsag', () => {
    expect(styringsFejl(new Error('HTTP 403'))).toBe('Kun ejeren kan styre agenter.')
    expect(styringsFejl(new Error('modelkravet deepseek/x kan ikke opfyldes')))
      .toBe('Styringen fejlede: modelkravet deepseek/x kan ikke opfyldes')
  })
})
