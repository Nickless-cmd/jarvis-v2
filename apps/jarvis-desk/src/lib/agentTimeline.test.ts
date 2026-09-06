import { describe, expect, it } from 'vitest'
import { byggeTidslinje } from './agentTimeline'
import type { ContentBlock } from './sseProtocol'

const t = (name: string, input: Record<string, unknown> = {}, status: 'done' | 'error' | 'running' = 'done') =>
  ({ type: 'tool_use', id: name + Math.random(), name, input, status }) as ContentBlock
const taenk = (s = 'hmm') => ({ type: 'thinking', thinking: s }) as ContentBlock
const tekst = (s = 'færdig') => ({ type: 'text', text: s }) as ContentBlock

describe('byggeTidslinje', () => {
  it('gengiver forløbet som Codex beskrev det', () => {
    const f = byggeTidslinje([
      taenk(),
      t('read_file'), t('read_file'), t('read_file'),
      t('edit_file'),
      t('bash', { command: 'pytest tests/ -q' }, 'error'),
      t('edit_file'),
      t('bash', { command: 'pytest tests/ -q' }),
      tekst(),
    ])
    expect(f.map((x) => x.label)).toEqual([
      'Tænkte sig om', 'Læste 3 filer', 'Ændrede en fil',
      'Kørte tests', 'Ændrede en fil', 'Kørte tests', 'Svarede',
    ])
    expect(f[3]?.status).toBe('fejl')   // den første testkørsel fejlede
    expect(f[5]?.status).toBe('ok')     // og den næste bestod
  })

  it('slår ens naboer sammen i stedet for én linje pr. kald', () => {
    const f = byggeTidslinje([t('read_file'), t('read_file'), t('read_file'), t('read_file')])
    expect(f).toHaveLength(1)
    expect(f[0]?.label).toBe('Læste 4 filer')
  })

  it('skiller tests fra almindelige kommandoer', () => {
    const f = byggeTidslinje([
      t('bash', { command: 'ls -la' }),
      t('bash', { command: 'npm run test' }),
    ])
    expect(f.map((x) => x.slags)).toEqual(['koerte', 'testede'])
  })

  it('lader en fejl i gruppen farve hele fasen', () => {
    const f = byggeTidslinje([t('read_file'), t('read_file', {}, 'error')])
    expect(f[0]).toMatchObject({ antal: 2, status: 'fejl' })
  })

  it('viser kørende faser mens turen stadig arbejder', () => {
    expect(byggeTidslinje([t('bash', { command: 'sleep 5' }, 'running')])[0]?.status).toBe('koerer')
  })

  it('tæller kun det afsluttende svar, ikke tekst undervejs', () => {
    const f = byggeTidslinje([tekst('jeg kigger…'), t('read_file'), tekst('færdig')])
    expect(f.filter((x) => x.slags === 'svarede')).toHaveLength(1)
    expect(f[f.length - 1]?.slags).toBe('svarede')
  })

  it('udelader værktøjer der ikke er en fase — de ville sløre linjen', () => {
    expect(byggeTidslinje([t('recall_memories'), t('open_ui_panel')])).toEqual([])
  })

  it('springer tom tænkning og tom tekst over', () => {
    expect(byggeTidslinje([taenk('   '), tekst('  ')])).toEqual([])
  })
})
