import { soegIBeskeder, soegbarTekst, flytTraef } from './chatSearch'
import type { ChatMessage } from './types'

const m = (id: string, role: ChatMessage['role'], content: string, blocks?: unknown): ChatMessage =>
  ({ id, role, content, created_at: '', ...(blocks ? { blocks } : {}) }) as ChatMessage

const BESKEDER = [
  m('1', 'user', 'kan du kigge på netværket'),
  m('2', 'assistant', 'Jeg fandt en løs USB-NIC på broen vmbr0 og satte den tilbage.'),
  m('3', 'user', 'tak'),
]

it('finder beskeden og giver et uddrag man kan genkende', () => {
  const t = soegIBeskeder(BESKEDER, 'usb')
  expect(t).toHaveLength(1)
  expect(t[0]?.id).toBe('2')
  expect(t[0]?.index).toBe(1)
  expect(t[0]?.uddrag).toContain('USB-NIC')
})

it('er ikke versalfølsom', () => {
  expect(soegIBeskeder(BESKEDER, 'VMBR0')).toHaveLength(1)
})

it('tier ved tom og ét-tegns søgning — ét tegn matcher alt', () => {
  expect(soegIBeskeder(BESKEDER, '')).toEqual([])
  expect(soegIBeskeder(BESKEDER, '  ')).toEqual([])
  expect(soegIBeskeder(BESKEDER, 'a')).toEqual([])
})

it('søger også i strukturerede blokke, ikke kun content', () => {
  const med = [m('9', 'assistant', 'kort svar', [{ type: 'text', text: 'detaljen står i blokken' }])]
  expect(soegIBeskeder(med, 'blokken')).toHaveLength(1)
})

it('markerer hvor i uddraget træffet står', () => {
  const t = soegIBeskeder(BESKEDER, 'broen')[0]!
  expect(t.uddrag.slice(t.traefStart, t.traefStart + t.traefLaengde).toLowerCase()).toBe('broen')
})

it('folder nye linjer sammen, så rækken ikke hopper', () => {
  const t = soegIBeskeder([m('1', 'user', 'linje et\n\nlinje to med ordet')], 'ordet')[0]!
  expect(t.uddrag).not.toContain('\n')
})

it('flytter mellem træf med ombrydning', () => {
  expect(flytTraef(3, 0, 1)).toBe(1)
  expect(flytTraef(3, 2, 1)).toBe(0)
  expect(flytTraef(3, 0, -1)).toBe(2)
  expect(flytTraef(0, 0, 1)).toBe(0)
})

it('søgbar tekst samler content og blokke', () => {
  const t = soegbarTekst(m('1', 'assistant', 'a', [{ type: 'text', text: 'b' }]))
  expect(t).toContain('a')
  expect(t).toContain('b')
})

it('uddraget viser tekst, ikke markdown-tegn', () => {
  const m = [{ id: '1', role: 'assistant', content: 'noget om **sikkerhedshuller** her', created_at: '' }] as any
  const t = soegIBeskeder(m, 'sikkerhedshuller')
  const traef = t[0]!
  expect(traef.uddrag).not.toMatch(/\*\*/)
  expect(traef.uddrag).toContain('sikkerhedshuller')
})

it('fremhævningen peger stadig på træffet efter oprydning', () => {
  const m = [{ id: '1', role: 'assistant', content: '**fed** og så broen', created_at: '' }] as any
  const t = soegIBeskeder(m, 'broen')
  const traef = t[0]!
  const u = traef.uddrag
  expect(u.slice(traef.traefStart, traef.traefStart + traef.traefLaengde)).toBe('broen')
})
