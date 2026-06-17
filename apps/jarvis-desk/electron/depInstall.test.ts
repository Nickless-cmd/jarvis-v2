import { describe, it, expect } from 'vitest'
import { installCommand } from './depInstall'

describe('installCommand', () => {
  it('linux apt → pkexec apt-get install', () => {
    expect(installCommand('git', { platform: 'linux', pkgManager: 'apt' }))
      .toEqual({ cmd: 'pkexec', args: ['apt-get', 'install', '-y', 'git'] })
  })
  it('mac → brew install (rg → ripgrep)', () => {
    expect(installCommand('rg', { platform: 'darwin' }))
      .toEqual({ cmd: 'brew', args: ['install', 'ripgrep'] })
  })
  it('windows → winget install med accept-flags', () => {
    const c = installCommand('gh', { platform: 'win32' })
    expect(c!.cmd).toBe('winget')
    expect(c!.args).toContain('--accept-source-agreements')
    expect(c!.args).toContain('GitHub.cli')
  })
  it('ukendt værktøj → null', () => {
    expect(installCommand('whatever', { platform: 'linux' })).toBeNull()
  })
})
