import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * side-2974014f15 — code mode læste klientens VERBS-tabel i stedet for serverens
 * `working_step`. `wait_agents` står ikke i tabellen og gav «Bruger et værktøj…».
 * Vagten (`isMeaningfulStatus`) holder rå værktøjsnavne ude, som i chat mode.
 */

const koerende = (name: string): ContentBlock[] => [
  { type: 'tool_use', id: `${name}-1`, name, input: {}, status: 'running' },
]
const afsluttet = (name: string): ContentBlock[] => [
  { type: 'tool_use', id: `${name}-1`, name, input: {}, status: 'done' },
]
const linje = (c: HTMLElement) => c.querySelector('.rv-arbejdsfortaelling')?.textContent ?? null

beforeEach(() => { localStorage.setItem(RAEKKE_KEY, '1') })

describe('RaekkeTranskript — workingStep som levende kilde', () => {
  it('viser serverens working_step mens runden kører', () => {
    const { container } = render(
      <RaekkeTranskript blocks={koerende('wait_agents')} streaming workingStep="Venter på agenter…" />)
    expect(linje(container)).toBe('Venter på agenter…')
  })

  it('viser IKKE et råt værktøjsnavn — falder tilbage til describeTool', () => {
    const { container } = render(
      <RaekkeTranskript blocks={koerende('wait_agents')} streaming workingStep="operator_bash" />)
    expect(linje(container)).not.toContain('operator_bash')
    expect(linje(container)).toBeTruthy()
  })

  it('workingStep=null falder tilbage uden at kaste', () => {
    const { container } = render(
      <RaekkeTranskript blocks={koerende('wait_agents')} streaming workingStep={null} />)
    expect(linje(container)).toBeTruthy()
  })

  it('rundeetiketten vinder når runden ikke kører', () => {
    const { container } = render(
      <RaekkeTranskript blocks={afsluttet('wait_agents')} streaming workingStep="Venter på agenter…"
        rundeEtiketter={{ 'wait_agents-1': 'Ventede på to agenter' }} />)
    expect(linje(container)).toBe('Ventede på to agenter')
  })
})
