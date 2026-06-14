import { describe, it, expect } from 'vitest'
import { planDispatch, type AppInstruction } from './appDispatch'

function instr(p: Partial<AppInstruction>): AppInstruction {
  return {
    id: 'd1', action: 'notify', target_user: 'bjorn', channel: null,
    payload: {}, requester: 'jarvis', ...p,
  }
}

describe('planDispatch', () => {
  it('notify → native notifikation med titel + body', () => {
    const p = planDispatch(instr({ action: 'notify', payload: { title: 'Møde', text: 'om 10 min' } }))
    expect(p).toEqual({ kind: 'notify', title: 'Møde', body: 'om 10 min' })
  })

  it('notify uden titel → default "Jarvis"', () => {
    const p = planDispatch(instr({ action: 'notify', payload: { text: 'hej' } }))
    expect(p).toEqual({ kind: 'notify', title: 'Jarvis', body: 'hej' })
  })

  it('send_message til discord med channel_name → discord-plan', () => {
    const p = planDispatch(instr({
      action: 'send_message', channel: 'discord',
      payload: { channel_name: 'general', text: 'vejret bliver fint' },
    }))
    expect(p).toEqual({ kind: 'discord', channelName: 'general', text: 'vejret bliver fint' })
  })

  it('send_report behandles som besked', () => {
    const p = planDispatch(instr({
      action: 'send_report', channel: 'discord',
      payload: { channel_name: 'rapporter', text: 'ugerapport' },
    }))
    expect(p).toEqual({ kind: 'discord', channelName: 'rapporter', text: 'ugerapport' })
  })

  it('discord uden channel_name → unsupported', () => {
    const p = planDispatch(instr({ action: 'send_message', channel: 'discord', payload: { text: 'x' } }))
    expect(p.kind).toBe('unsupported')
  })

  it('discord med tom tekst → unsupported', () => {
    const p = planDispatch(instr({ action: 'send_message', channel: 'discord', payload: { channel_name: 'g' } }))
    expect(p.kind).toBe('unsupported')
  })

  it('ukendt kanal → unsupported', () => {
    const p = planDispatch(instr({ action: 'send_message', channel: 'slack', payload: { text: 'x' } }))
    expect(p.kind).toBe('unsupported')
  })

  it('ukendt action → unsupported', () => {
    const p = planDispatch(instr({ action: 'launch_missiles' }))
    expect(p.kind).toBe('unsupported')
  })
})
