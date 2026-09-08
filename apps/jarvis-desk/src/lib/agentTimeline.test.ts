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

/**
 * Bjørn 8/9-2026: «forløbet i bunden af hans besked er rimelig ubrugeligt uden
 * metadata … de viser bare "kørt kommando bash", ikke hvad de faktisk lavede.»
 *
 * Dataen lå i `input` hele tiden — kun testkørsler bar en detalje.
 */
describe('forløbet siger hvad der faktisk skete', () => {
  it('kommandoen står ved en kørsel', () => {
    const [f] = byggeTidslinje([
      { type: 'tool_use', id: '1', name: 'bash', input: { command: 'git status --short' }, status: 'done' },
    ])
    expect(f!.detaljer).toEqual(['git status --short'])
  })

  it('filen står ved en læsning — kun de sidste to led af stien', () => {
    // Den fulde sti er sjældent det man leder efter, og den skubber alt andet
    // ud af linjen.
    const [f] = byggeTidslinje([
      { type: 'tool_use', id: '1', name: 'read_file', input: { file_path: '/media/projects/jarvis-v2/core/db.py' }, status: 'done' },
    ])
    expect(f!.detaljer).toEqual(['core/db.py'])
  })

  it('mønstret står ved en søgning', () => {
    const [f] = byggeTidslinje([
      { type: 'tool_use', id: '1', name: 'grep', input: { pattern: 'def issue_token' }, status: 'done' },
    ])
    expect(f!.detaljer).toEqual(['def issue_token'])
  })

  it('en sammenslået fase samler flere detaljer', () => {
    const [f] = byggeTidslinje([
      { type: 'tool_use', id: '1', name: 'read_file', input: { file_path: 'a.py' }, status: 'done' },
      { type: 'tool_use', id: '2', name: 'read_file', input: { file_path: 'b.py' }, status: 'done' },
    ])
    expect(f!.antal).toBe(2)
    expect(f!.detaljer).toEqual(['a.py', 'b.py'])
  })

  it('men højst seks — en fase må ikke fylde skærmen', () => {
    const [f] = byggeTidslinje(
      Array.from({ length: 12 }, (_, i) => ({
        type: 'tool_use' as const, id: String(i), name: 'read_file',
        input: { file_path: `f${i}.py` }, status: 'done' as const,
      })),
    )
    expect(f!.antal).toBe(12)
    expect(f!.detaljer.length).toBe(6)
  })

  it('Jarvis egen narration bliver til metadata på fasen', () => {
    // Den stod før i sit EGET «Forløb»-felt — to forløb på samme besked.
    const [f] = byggeTidslinje([
      { type: 'tool_use', id: 'c1', name: 'bash', input: { command: 'ls' }, status: 'done' },
      { type: 'progress', tool_use_id: 'c1', parent_tool_use_id: null, message: 'Kiggede i mappen', status: 'done' },
    ])
    expect(f!.detaljer).toEqual(['ls', 'Kiggede i mappen'])
  })

  it('en detalje uden indhold laver ikke en tom linje', () => {
    const [f] = byggeTidslinje([
      { type: 'tool_use', id: '1', name: 'bash', input: {}, status: 'done' },
    ])
    expect(f!.detaljer).toEqual([])
  })
})

describe('narration uden en fase at høre til', () => {
  it('opfinder ikke en fase — den droppes', () => {
    // Første forsøg lavede en «Tænkte sig om»-fase af narration der ikke kunne
    // hænge på noget, og så stod der en falsk fase fuld af rå værktøjsnavne.
    const faser = byggeTidslinje([
      { type: 'progress', tool_use_id: 'x', parent_tool_use_id: null, message: 'løs narration', status: 'done' },
    ])
    expect(faser).toEqual([])
  })

  it('spilder ikke over i en ny fase når den forrige er fuld', () => {
    const blokke: ContentBlock[] = [
      { type: 'tool_use', id: '1', name: 'bash', input: { command: 'a' }, status: 'done' },
      ...Array.from({ length: 9 }, (_, i) => ({
        type: 'progress' as const, tool_use_id: '1', parent_tool_use_id: null,
        message: `n${i}`, status: 'done' as const,
      })),
    ]
    const faser = byggeTidslinje(blokke)
    expect(faser.length).toBe(1)
    expect(faser[0]!.detaljer.length).toBe(6)
  })
})
