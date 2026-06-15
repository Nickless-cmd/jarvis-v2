import { describe, it, expect, vi } from 'vitest'
import { resolveAppAction } from './appAction'

describe('resolveAppAction', () => {
  it('switch_to_code_mode → setSurface(code) + arm auto-continue', () => {
    const setSurface = vi.fn()
    const setPermission = vi.fn()
    const armAutoContinue = vi.fn()
    resolveAppAction('switch_to_code_mode', { setSurface, setPermission, armAutoContinue }, 'ret bug')
    expect(setSurface).toHaveBeenCalledWith('code')
    expect(setPermission).not.toHaveBeenCalled()
    expect(armAutoContinue).toHaveBeenCalledWith('ret bug')
  })

  it('request_full_access → setPermission(trust) + arm auto-continue', () => {
    const setSurface = vi.fn()
    const setPermission = vi.fn()
    const armAutoContinue = vi.fn()
    resolveAppAction('request_full_access', { setSurface, setPermission, armAutoContinue }, 'kør tests')
    expect(setPermission).toHaveBeenCalledWith('trust')
    expect(setSurface).not.toHaveBeenCalled()
    expect(armAutoContinue).toHaveBeenCalledWith('kør tests')
  })

  it('does not arm auto-continue when message is empty', () => {
    const armAutoContinue = vi.fn()
    resolveAppAction('switch_to_code_mode', { setSurface: vi.fn(), setPermission: vi.fn(), armAutoContinue }, '')
    expect(armAutoContinue).not.toHaveBeenCalled()
  })
})
